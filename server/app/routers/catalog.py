"""模型清单路由：前端启动后拉取，用于模型选择器与工具栏展示。"""

from __future__ import annotations

from fastapi import APIRouter

from .. import cache, redis_client
from ..config import get_settings
from ..model_registry import registry
from ..schemas import ModelOut

router = APIRouter(tags=["catalog"])

CACHE_KEY = redis_client.key("catalog", "models")


@router.get("/models", response_model=list[ModelOut], summary="可用模型清单")
async def list_models() -> list[ModelOut]:
    """返回配置文件声明的模型（含介绍、发布日期等前端展示字段）。

    结果缓存在 Redis（TTL = CATALOG_CACHE_SECONDS）；Redis 不可用时
    直接回源注册表，行为完全一致。
    """
    cached = await cache.cache_get_json(CACHE_KEY)
    if isinstance(cached, list):
        return [ModelOut(**item) for item in cached]

    items = registry.public_models()
    await cache.cache_set_json(CACHE_KEY, items, get_settings().catalog_cache_seconds)
    return [ModelOut(**item) for item in items]
