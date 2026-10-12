"""认证路由：邮箱验证码注册、登录、当前用户。"""

from __future__ import annotations

import logging
import math
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..mailer import MailError, send_verification_code
from ..models import EmailVerification, User, utcnow
from ..schemas import (
    LoginRequest,
    RegisterRequest,
    SendCodeRequest,
    SendCodeResponse,
    TokenResponse,
    UserOut,
    user_out,
)
from ..security import (
    create_access_token,
    generate_code,
    hash_code,
    hash_password,
    verify_code,
    verify_password,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])

PURPOSE_REGISTER = "register"
# 过期验证码记录的保留时长
_RECORD_RETENTION = timedelta(hours=24)


def _as_aware(value: datetime | None) -> datetime | None:
    """兼容不同驱动返回的 naive datetime（按 UTC 处理）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _latest_code(
    db: AsyncSession, email: str, purpose: str
) -> EmailVerification | None:
    stmt = (
        select(EmailVerification)
        .where(
            EmailVerification.email == email,
            EmailVerification.purpose == purpose,
        )
        .order_by(EmailVerification.created_at.desc())
        .limit(1)
    )
    return await db.scalar(stmt)


@router.post("/send-code", response_model=SendCodeResponse, summary="发送注册验证码")
async def send_code(
    payload: SendCodeRequest,
    db: AsyncSession = Depends(get_db),
) -> SendCodeResponse:
    settings = get_settings()
    email = _normalize_email(payload.email)

    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册，请直接登录")

    now = utcnow()
    latest = await _latest_code(db, email, PURPOSE_REGISTER)
    latest_at = _as_aware(latest.created_at) if latest else None
    if latest_at is not None:
        elapsed = (now - latest_at).total_seconds()
        if elapsed < settings.code_resend_interval_seconds:
            wait = math.ceil(settings.code_resend_interval_seconds - elapsed)
            raise HTTPException(
                status.HTTP_429_TOO_MANY_REQUESTS, f"验证码发送过于频繁，请 {wait} 秒后重试"
            )

    code = generate_code()
    record = EmailVerification(
        email=email,
        purpose=PURPOSE_REGISTER,
        code_hash=hash_code(code),
        expires_at=now + timedelta(seconds=settings.code_ttl_seconds),
    )
    db.add(record)
    # 顺手清理该邮箱的历史记录
    await db.execute(
        delete(EmailVerification).where(
            EmailVerification.email == email,
            EmailVerification.created_at < now - _RECORD_RETENTION,
        )
    )
    await db.commit()

    dev_code: str | None = None
    if settings.smtp_enabled:
        try:
            await send_verification_code(email, code, settings.code_ttl_seconds)
        except MailError as exc:
            logger.warning("验证码邮件发送失败（%s）：%s", email, exc)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    elif settings.auth_dev_echo_code:
        # 本地开发：未配置 SMTP 时把验证码回传，便于自测
        dev_code = code
        logger.info("SMTP 未配置，开发模式返回验证码：%s -> %s", email, code)
    else:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "服务端未配置 SMTP 邮件服务，暂时无法发送验证码",
        )

    return SendCodeResponse(
        ok=True,
        expires_in=settings.code_ttl_seconds,
        resend_after=settings.code_resend_interval_seconds,
        dev_code=dev_code,
    )


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="邮箱验证码注册（注册成功即登录）",
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    email = _normalize_email(payload.email)

    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册，请直接登录")

    record = await _latest_code(db, email, PURPOSE_REGISTER)
    if record is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "请先获取邮箱验证码")

    now = utcnow()
    if record.consumed_at is not None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码已使用，请重新获取")
    expires_at = _as_aware(record.expires_at)
    if expires_at is not None and expires_at <= now:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码已过期，请重新获取")
    if record.attempts >= settings.code_max_attempts:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "验证码尝试次数过多，请重新获取")

    if not verify_code(payload.code.strip(), record.code_hash):
        record.attempts += 1
        await db.commit()
        remaining = max(0, settings.code_max_attempts - record.attempts)
        message = "验证码不正确" if remaining else "验证码错误次数过多，请重新获取"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)

    record.consumed_at = now
    user = User(
        email=email,
        nickname=payload.nickname.strip(),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("新用户注册成功：%s", email)

    token, expires_in = create_access_token(user.id)
    return TokenResponse(token=token, token_type="bearer", expires_in=expires_in, user=user_out(user))


@router.post("/login", response_model=TokenResponse, summary="邮箱密码登录")
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    email = _normalize_email(payload.email)
    user = await db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用")

    token, expires_in = create_access_token(user.id)
    return TokenResponse(token=token, token_type="bearer", expires_in=expires_in, user=user_out(user))


@router.get("/me", response_model=UserOut, summary="当前登录用户")
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)
