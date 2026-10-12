"""安全工具：密码哈希（bcrypt）与访问令牌（JWT）、验证码哈希。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from .config import get_settings

# bcrypt 仅处理前 72 字节
_BCRYPT_MAX_BYTES = 72


def _password_bytes(password: str) -> bytes:
    return password.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    """生成 bcrypt 哈希。"""
    return bcrypt.hashpw(_password_bytes(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    """校验密码，异常一律视为失败。"""
    if not hashed:
        return False
    try:
        return bcrypt.checkpw(_password_bytes(password), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | int,
    expires_minutes: int | None = None,
    token_version: int = 0,
) -> tuple[str, int]:
    """签发访问令牌，返回 (token, 有效期秒数)。

    token_version 与用户当前版本比较，用于在重置密码后作废旧令牌。
    """
    settings = get_settings()
    minutes = expires_minutes or settings.access_token_expire_minutes
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=minutes)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": "access",
        "ver": int(token_version or 0),
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, minutes * 60


def decode_access_token(token: str) -> dict[str, Any]:
    """解析访问令牌，失败抛出 jwt.PyJWTError。"""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("type") != "access":
        raise jwt.InvalidTokenError("令牌类型无效")
    return payload


def generate_code(length: int | None = None) -> str:
    """生成纯数字验证码。"""
    settings = get_settings()
    size = length or settings.code_length
    return "".join(str(secrets.randbelow(10)) for _ in range(size))


def hash_code(code: str) -> str:
    """验证码哈希（HMAC-SHA256，密钥复用 jwt_secret）。"""
    settings = get_settings()
    digest = hmac.new(settings.jwt_secret.encode("utf-8"), code.encode("utf-8"), hashlib.sha256)
    return digest.hexdigest()


def verify_code(code: str, code_hash: str) -> bool:
    """常数时间比较验证码。"""
    if not code_hash:
        return False
    return hmac.compare_digest(hash_code(code), code_hash)
