"""认证路由：验证码注册、验证码登录（未注册自动注册）、找回密码、密码登录。"""

from __future__ import annotations

import logging
import math
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from .. import ratelimit
from ..config import get_settings
from ..database import get_db
from ..deps import get_current_user
from ..mailer import MailError, send_verification_code
from ..models import EmailVerification, User, utcnow
from ..schemas import (
    CodeLoginRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    SendCodeRequest,
    SendCodeResponse,
    TokenResponse,
    UpdateProfileRequest,
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
PURPOSE_LOGIN = "login"
PURPOSE_RESET = "reset"

# 过期验证码记录的保留时长
_RECORD_RETENTION = timedelta(hours=24)
# 验证码自动注册的账号没有密码，写入不可用的随机哈希（可用「找回密码」设置新密码）
_UNUSABLE_PASSWORD_BYTES = 32


def _as_aware(value: datetime | None) -> datetime | None:
    """兼容不同驱动返回的 naive datetime（按 UTC 处理）。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def _default_nickname(nickname: str | None, email: str) -> str:
    """昵称留空时使用邮箱（需求：不填昵称就把邮箱填入昵称）。"""
    value = (nickname or "").strip()
    return value[:64] if value else email


def _token_response(user: User, is_new_user: bool = False) -> TokenResponse:
    token, expires_in = create_access_token(user.id, token_version=user.token_version)
    return TokenResponse(
        token=token,
        token_type="bearer",
        expires_in=expires_in,
        user=user_out(user),
        is_new_user=is_new_user,
    )


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


async def _guard_email(
    request: Request, scope: str, email: str, limit: int, window: int
) -> None:
    """账号维度 + IP 维度的双重限流（账号维度是暴力破解的主防线）。

    用于登录 / 验证码登录 / 重置密码：同一邮箱在窗口内尝试次数受限，
    同时用登录 IP 阈值兜住"换邮箱撞库"的场景。
    """
    settings = get_settings()
    await ratelimit.enforce(scope, ratelimit.email_identity(email), limit, window)
    await ratelimit.enforce(
        f"{scope}-ip",
        ratelimit.client_ip(request),
        settings.login_rate_limit_per_ip,
        settings.login_rate_limit_window_seconds,
    )


async def _guard_ip(request: Request, scope: str, limit: int, window: int) -> None:
    """仅按 IP 限流（用于发码 / 注册这类没有账号可归因的入口）。"""
    await ratelimit.enforce(scope, ratelimit.client_ip(request), limit, window)


async def _consume_code(db: AsyncSession, email: str, purpose: str, code: str) -> None:
    """校验验证码并标记为已使用；失败时抛出 HTTPException。

    标记结果由调用方统一提交，若后续步骤失败会一并回滚。
    """
    settings = get_settings()
    record = await _latest_code(db, email, purpose)
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

    if not verify_code(code.strip(), record.code_hash):
        record.attempts += 1
        await db.commit()
        remaining = max(0, settings.code_max_attempts - record.attempts)
        message = "验证码不正确" if remaining else "验证码错误次数过多，请重新获取"
        raise HTTPException(status.HTTP_400_BAD_REQUEST, message)

    record.consumed_at = now
    await db.flush()


@router.post("/send-code", response_model=SendCodeResponse, summary="发送邮箱验证码")
async def send_code(
    payload: SendCodeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> SendCodeResponse:
    """按用途发送验证码：register 注册 / login 验证码登录 / reset 找回密码。

    - register：邮箱必须未注册；
    - login：不限制（未注册时由验证码登录自动注册）；
    - reset：邮箱必须已注册。
    """
    settings = get_settings()
    email = _normalize_email(payload.email)
    purpose = payload.purpose

    await _guard_ip(
        request,
        "send-code",
        settings.send_code_rate_limit_per_ip,
        settings.send_code_rate_limit_window_seconds,
    )

    user_exists = await db.scalar(select(User.id).where(User.email == email)) is not None
    if purpose == PURPOSE_REGISTER and user_exists:
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册，请直接登录")
    if purpose == PURPOSE_RESET and not user_exists:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该邮箱尚未注册，请先注册")

    now = utcnow()
    latest = await _latest_code(db, email, purpose)
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
        purpose=purpose,
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
            await send_verification_code(email, code, settings.code_ttl_seconds, purpose)
        except MailError as exc:
            logger.warning("验证码邮件发送失败（%s/%s）：%s", email, purpose, exc)
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    elif settings.auth_dev_echo_code:
        # 本地开发：未配置 SMTP 时把验证码回传，便于自测
        dev_code = code
        logger.info("SMTP 未配置，开发模式返回验证码：%s/%s -> %s", email, purpose, code)
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
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    email = _normalize_email(payload.email)
    settings = get_settings()

    await _guard_ip(
        request,
        "register",
        settings.register_rate_limit_per_ip,
        settings.register_rate_limit_window_seconds,
    )

    if await db.scalar(select(User.id).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "该邮箱已注册，请直接登录")

    await _consume_code(db, email, PURPOSE_REGISTER, payload.code)

    user = User(
        email=email,
        nickname=_default_nickname(payload.nickname, email),
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    logger.info("新用户注册成功：%s", email)
    return _token_response(user, is_new_user=True)


@router.post("/login", response_model=TokenResponse, summary="邮箱密码登录")
async def login(
    payload: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    email = _normalize_email(payload.email)

    # 限流先于密码校验：暴力破解在触碰数据库比对之前就被挡下
    await _guard_email(
        request,
        "login",
        email,
        settings.login_rate_limit_per_email,
        settings.login_rate_limit_window_seconds,
    )

    user = await db.scalar(select(User).where(User.email == email))

    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "邮箱或密码错误")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用")

    return _token_response(user)


@router.post(
    "/login-code",
    response_model=TokenResponse,
    summary="邮箱验证码登录（未注册的邮箱自动注册）",
)
async def login_with_code(
    payload: CodeLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    email = _normalize_email(payload.email)

    await _guard_email(
        request,
        "login-code",
        email,
        settings.login_rate_limit_per_email,
        settings.login_rate_limit_window_seconds,
    )

    await _consume_code(db, email, PURPOSE_LOGIN, payload.code)

    user = await db.scalar(select(User).where(User.email == email))
    is_new_user = False

    if user is None:
        user = User(
            email=email,
            # 昵称留空时使用邮箱
            nickname=_default_nickname(payload.nickname, email),
            hashed_password=hash_password(secrets.token_urlsafe(_UNUSABLE_PASSWORD_BYTES)),
            is_active=True,
        )
        db.add(user)
        is_new_user = True

    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用")

    try:
        await db.commit()
    except IntegrityError as exc:  # 并发下同一邮箱被同时创建
        await db.rollback()
        user = await db.scalar(select(User).where(User.email == email))
        if user is None:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "账号创建冲突，请重试"
            ) from exc
        is_new_user = False

    await db.refresh(user)

    if is_new_user:
        logger.info("验证码登录自动注册：%s（昵称：%s）", email, user.nickname)
    else:
        logger.info("验证码登录：%s", email)

    return _token_response(user, is_new_user=is_new_user)


@router.post(
    "/reset-password",
    response_model=TokenResponse,
    summary="找回密码（验证码校验后重置，旧令牌全部失效）",
)
async def reset_password(
    payload: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    settings = get_settings()
    email = _normalize_email(payload.email)

    await _guard_email(
        request,
        "reset",
        email,
        settings.login_rate_limit_per_email,
        settings.login_rate_limit_window_seconds,
    )

    user = await db.scalar(select(User).where(User.email == email))

    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "该邮箱尚未注册，请先注册")
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "账号已被禁用")

    await _consume_code(db, email, PURPOSE_RESET, payload.code)

    user.hashed_password = hash_password(payload.password)
    user.token_version += 1
    await db.commit()
    await db.refresh(user)

    logger.info("密码已重置：%s", email)
    return _token_response(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="退出登录（撤销该账号此前签发的全部令牌）",
)
async def logout(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    """登出。

    令牌版本号 +1，使该账号**此前签发的所有访问令牌立即失效**（含其它设备）。
    这是无状态 JWT 下不引入黑名单即可做到服务端撤销的最简方式；
    代价是多设备需各自重新登录。
    """
    user.token_version += 1
    await db.commit()
    logger.info("用户已登出，旧令牌全部失效：%s", user.email)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="当前登录用户")
async def me(user: User = Depends(get_current_user)) -> UserOut:
    return user_out(user)


@router.patch("/me", response_model=UserOut, summary="更新当前用户昵称")
async def update_me(
    payload: UpdateProfileRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserOut:
    """设置昵称；昵称留空时回退为邮箱（需求：不填就用邮箱）。"""
    user.nickname = _default_nickname(payload.nickname, user.email)
    await db.commit()
    await db.refresh(user)

    logger.info("昵称已更新：%s -> %s", user.email, user.nickname)
    return user_out(user)
