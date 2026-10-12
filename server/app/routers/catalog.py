"""模型清单路由：前端启动后拉取，用于模型选择器与工具栏展示。"""

from __future__ import annotations

from fastapi import APIRouter

from ..model_registry import registry
from ..schemas import ModelOut

router = APIRouter(tags=["catalog"])


@router.get("/models", response_model=list[ModelOut], summary="可用模型清单")
async def list_models() -> list[ModelOut]:
    """返回配置文件声明的模型（含介绍、发布日期等前端展示字段）。"""
    return [ModelOut(**item) for item in registry.public_models()]
