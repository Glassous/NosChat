"""数据库连接与会话管理（SQLAlchemy 2.x 异步）。"""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from .config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class Base(DeclarativeBase):
    """ORM 基类。"""


def _create_engine() -> AsyncEngine:
    kwargs: dict[str, object] = {"echo": settings.db_echo, "pool_pre_ping": True}
    # SQLite 等非连接池驱动不支持 pool_size/max_overflow
    if settings.database_url.startswith("postgresql"):
        kwargs["pool_size"] = settings.db_pool_size
        kwargs["max_overflow"] = settings.db_max_overflow
    return create_async_engine(settings.database_url, **kwargs)


engine: AsyncEngine = _create_engine()

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：请求级数据库会话。"""
    async with SessionLocal() as session:
        yield session


async def init_db() -> None:
    """建表（幂等）。启动阶段调用。"""
    # 触发 ORM 元数据注册
    from . import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表结构已就绪")


async def dispose_db() -> None:
    """释放连接池。"""
    await engine.dispose()
