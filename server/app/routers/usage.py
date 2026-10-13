"""用量与额度路由：前端登录后拉取当日输出 token 额度快照。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from .. import usage
from ..database import get_db
from ..deps import get_current_user
from ..models import User
from ..schemas import UsageOut

router = APIRouter(tags=["usage"])


@router.get("/usage/today", response_model=UsageOut, summary="当日输出 token 额度")
async def usage_today(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UsageOut:
    """返回当前用户当日额度快照（限额 / 已用 / 剩余 / 重置时刻）。

    额度只统计模型输出 token（thinking + content），输入 token 不计。
    前端据此锁定输入框；真正的拦截在后端 /api/chat/stream。
    """
    snapshot = await usage.get_usage(db, user.id)
    return UsageOut(**snapshot.as_dict())
