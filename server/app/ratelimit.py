"""限流：Redis 固定窗口为主，Redis 不可用时回退到进程内固定窗口。

设计要点：
- 账号维度是暴力破解的主防线，IP 维度只作补充（代理链可能导致 IP 归属不准）；
- Redis 路径用 INCR + EXPIRE 一次往返，过期键由 Redis TTL 自动回收；
- Redis 不可用时**仍然限流**（进程内兜底），只是多 worker 时计数按 worker 各算一份，
  因此降级不会把防护变成"完全放行"。
"""

from __future__ import annotations

import hashlib
import logging
import math
import time
from dataclasses import dataclass

from fastapi import HTTPException, Request, status

from . import redis_client
from .config import get_settings

logger = logging.getLogger(__name__)

# 进程内兜底计数器：key -> (count, expires_at_monotonic)
_local: dict[str, tuple[int, float]] = {}
_LOCAL_MAX_KEYS = 10000


@dataclass(frozen=True)
class RateLimitResult:
    """一次限流判定的结果。"""

    allowed: bool
    limit: int
    remaining: int
    retry_after: int

    def as_headers(self) -> dict[str, str]:
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
        }
        if not self.allowed:
            headers["Retry-After"] = str(max(1, self.retry_after))
        return headers


def client_ip(request: Request | None) -> str:
    """取客户端 IP：优先由 ASGI 服务器解析（受 forwarded_allow_ips 约束），

    其次回退到 X-Forwarded-For 首项，最后回退 unknown。
    """
    if request is None:
        return "unknown"
    peer = getattr(request.client, "host", None) if request.client else None
    if peer:
        return peer
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        first = forwarded.split(",")[0].strip()
        if first:
            return first
    return "unknown"


def email_identity(email: str) -> str:
    """把邮箱转成不落明文的限流身份（与「验证码只存哈希」的取向一致）。"""
    digest = hashlib.sha256((email or "").strip().lower().encode("utf-8")).hexdigest()
    return f"e:{digest[:32]}"


def _window_start(now: float, window: int) -> int:
    return int(now) // window * window


def _prune_local(now: float) -> None:
    expired = [key for key, (_, expires) in _local.items() if expires <= now]
    for key in expired:
        _local.pop(key, None)
    if len(_local) > _LOCAL_MAX_KEYS:
        # 极端情况下按过期时间丢掉最早的一批，避免无限增长
        ordered = sorted(_local.items(), key=lambda item: item[1][1])
        for key, _ in ordered[: len(_local) - _LOCAL_MAX_KEYS]:
            _local.pop(key, None)


def _hit_local(counter_key: str, window: int, now: float) -> int:
    """进程内固定窗口自增，返回自增后的计数。"""
    _prune_local(now)
    count, expires = _local.get(counter_key, (0, 0.0))
    if expires <= now:
        count, expires = 0, now + window
    count += 1
    _local[counter_key] = (count, expires)
    return count


async def hit(scope: str, identity: str, limit: int, window: int) -> RateLimitResult:
    """记一次访问并判定是否放行。

    scope 例如 login / login-ip / send-code / chat；identity 为邮箱哈希或 IP。
    """
    settings = get_settings()
    if not settings.rate_limit_enabled or limit <= 0 or window <= 0:
        return RateLimitResult(allowed=True, limit=limit, remaining=limit, retry_after=0)

    now = time.time()
    start = _window_start(now, window)
    retry_after = max(1, math.ceil(start + window - now))

    count = await redis_client.incr_with_ttl(
        redis_client.key("rl", scope, identity, start), window
    )
    if count is None:
        # 降级：进程内兜底仍然生效
        count = _hit_local(f"{scope}:{identity}:{start}", window, time.monotonic())

    remaining = limit - count
    return RateLimitResult(
        allowed=count <= limit,
        limit=limit,
        remaining=max(0, remaining),
        retry_after=0 if count <= limit else retry_after,
    )


def too_many(result: RateLimitResult) -> HTTPException:
    """把超限结果转成带 Retry-After 的 429。"""
    return HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=f"操作过于频繁，请 {max(1, result.retry_after)} 秒后重试",
        headers=result.as_headers(),
    )


async def enforce(scope: str, identity: str, limit: int, window: int) -> RateLimitResult:
    """记一次访问；超出阈值时抛 429。"""
    result = await hit(scope, identity, limit, window)
    if not result.allowed:
        raise too_many(result)
    return result
