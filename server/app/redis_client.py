"""Redis 连接管理（缓存 + 限流）。

设计要点：
- Redis 只承担**缓存**与**限流计数**，每日额度以 PostgreSQL 为准；
- 采用**短超时 + 熔断**：Redis 出错后进入退避窗口，窗口内直接跳过 Redis
  走降级路径，避免每次请求都等待连接超时；
- 一切失败都是 fail-open：调用方拿到 None/降级结果后继续工作，Redis
  不可用不会让服务中断。
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import redis.asyncio as aioredis
from redis.exceptions import RedisError

from .config import get_settings

logger = logging.getLogger(__name__)

# 熔断状态：monotonic 时间戳，在此之前不再尝试 Redis
_circuit_open_until: float = 0.0
_client: aioredis.Redis | None = None
_degraded_logged = False


def _now() -> float:
    return time.monotonic()


def circuit_open() -> bool:
    """熔断是否处于打开状态（打开时不发 Redis 请求）。"""
    return _now() < _circuit_open_until


def _trip(reason: object) -> None:
    """打开熔断并记录一次降级告警（避免日志风暴）。"""
    global _circuit_open_until, _degraded_logged
    settings = get_settings()
    _circuit_open_until = _now() + settings.redis_retry_seconds
    if not _degraded_logged:
        _degraded_logged = True
        logger.warning(
            "Redis 不可用（%s），%.0fs 内降级运行：缓存直接回源、限流走进程内兜底",
            reason,
            settings.redis_retry_seconds,
        )


def _recover() -> None:
    """Redis 恢复后复位告警标记，便于下次故障继续提示。"""
    global _degraded_logged
    if _degraded_logged:
        _degraded_logged = False
        logger.info("Redis 已恢复，缓存与限流回到 Redis 路径")


def get_redis() -> aioredis.Redis | None:
    """取全局 Redis 客户端；未配置或熔断中返回 None。"""
    global _client
    settings = get_settings()
    if not settings.redis_enabled or circuit_open():
        return None
    if _client is None:
        _client = aioredis.from_url(
            settings.redis_url.strip(),
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=settings.redis_socket_timeout,
            socket_connect_timeout=settings.redis_socket_timeout,
            health_check_interval=30,
        )
    return _client


def key(*parts: object) -> str:
    """拼接带前缀与版本号的缓存键。"""
    prefix = get_settings().redis_key_prefix.strip() or "noschat"
    return ":".join([prefix, "v1", *(str(part) for part in parts)])


async def execute(command: str, *args: Any, **kwargs: Any) -> Any:
    """执行一条 Redis 命令；失败/熔断时返回 None 并触发熔断。"""
    client = get_redis()
    if client is None:
        return None
    try:
        result = await getattr(client, command)(*args, **kwargs)
        _recover()
        return result
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        _trip(exc)
        return None


async def ping() -> bool:
    """健康探测（供启动日志与 /health 使用）。"""
    client = get_redis()
    if client is None:
        return False
    try:
        await client.ping()
        _recover()
        return True
    except (RedisError, OSError, asyncio.TimeoutError) as exc:
        _trip(exc)
        return False


async def incr_with_ttl(key: str, ttl: int) -> int | None:
    """自增计数并设置过期时间（一次 pipeline，单次往返）。

    返回自增后的计数；Redis 不可用或熔断时返回 None。
    """
    client = get_redis()
    if client is None:
        return None
    try:
        async with client.pipeline(transaction=False) as pipe:
            pipe.incr(key)
            pipe.expire(key, max(1, ttl))
            count, _ = await pipe.execute()
        _recover()
        return int(count)
    except (RedisError, OSError, asyncio.TimeoutError, TypeError, ValueError) as exc:
        _trip(exc)
        return None


async def redis_state() -> str:
    """Redis 状态：ok / down / disabled（用于 /health）。"""
    if not get_settings().redis_enabled:
        return "disabled"
    if circuit_open():
        return "down"
    return "ok" if await ping() else "down"


async def init_redis() -> None:
    """启动时探测一次，仅记录日志，不阻塞启动。"""
    settings = get_settings()
    if not settings.redis_enabled:
        logger.warning("未配置 REDIS_URL，缓存与限流将以进程内降级模式运行")
        return
    if await ping():
        logger.info("Redis 已连接：%s", settings.redis_url)
    else:
        logger.warning("Redis 连接失败，本次启动将以降级模式运行")


async def close_redis() -> None:
    """释放连接池（应用关闭时调用）。"""
    global _client
    if _client is None:
        return
    try:
        closer = getattr(_client, "aclose", None) or getattr(_client, "close", None)
        if closer is not None:
            result = closer()
            if asyncio.iscoroutine(result):
                await result
    except Exception:  # noqa: BLE001 - 关闭失败不影响退出
        logger.debug("关闭 Redis 连接失败", exc_info=True)
    finally:
        _client = None
