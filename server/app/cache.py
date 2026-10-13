"""Redis 缓存封装（全部 fail-open）。

约定：
- Redis 不可用或处于熔断窗口时，读返回 None、写静默跳过，由调用方回源；
- 缓存只用于减少数据库/序列化开销，**任何正确性判断都必须回源到权威存储**。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from . import redis_client

logger = logging.getLogger(__name__)


async def cache_get_json(key: str) -> Any | None:
    """读缓存并反序列化；未命中/不可用/解析失败都返回 None。"""
    raw = await redis_client.execute("get", key)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        logger.debug("缓存内容无法解析，按未命中处理：%s", key)
        return None


async def cache_set_json(key: str, value: Any, ttl: int) -> None:
    """写缓存；ttl <= 0 或不可用时静默跳过。"""
    if ttl <= 0:
        return
    try:
        payload = json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        logger.debug("缓存内容无法序列化，跳过写入：%s", key)
        return
    await redis_client.execute("set", key, payload, ex=ttl)


async def cache_delete(*keys: str) -> None:
    """删除缓存键（写操作后调用，保证下一次读取回源）。"""
    targets = [item for item in keys if item]
    if not targets:
        return
    await redis_client.execute("delete", *targets)
