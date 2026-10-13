"""每用户每日输出 token 额度。

口径与设计：
- 只统计模型**输出** token（thinking + content），输入 token 不计；
- 优先采用上游上报的 completion_tokens，缺失时用文档化的字符估算；
- PostgreSQL 的 daily_usage 是唯一权威来源，Redis 只缓存当日快照（fail-open）；
- 判定发生在请求开始：额度未用尽则放行整轮，即使该轮把用量推过上限
  （「最后一个对话可以超出一点来换完整」）；之后直到重置前一律拒绝。
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from . import cache, redis_client
from .config import get_settings
from .database import SessionLocal
from .models import DailyUsage, utcnow

logger = logging.getLogger(__name__)

# 估算用的 CJK 区间
_CJK_RANGES = (
    ("\u4e00", "\u9fff"),  # 基本汉字
    ("\u3400", "\u4dbf"),  # 扩展 A
    ("\u3000", "\u303f"),  # CJK 标点
    ("\uff00", "\uffef"),  # 全角字符
)
_ASCII_CHARS_PER_TOKEN = 4


class QuotaExceeded(Exception):
    """当日输出 token 额度已用尽（对应用户可读的 402 响应）。"""

    def __init__(self, *, limit: int, used: int, reset_at: str, day: str, timezone: str) -> None:
        super().__init__("今日输出 token 已达上限")
        self.limit = limit
        self.used = used
        self.reset_at = reset_at
        self.day = day
        self.timezone = timezone

    def payload(self) -> dict:
        return {
            "detail": (
                f"今日输出 token 已达上限（{self.limit}），"
                f"将于 {self.reset_at} 重置"
            ),
            "code": "quota_exceeded",
            "limit": self.limit,
            "used": self.used,
            "resetAt": self.reset_at,
            "day": self.day,
            "timezone": self.timezone,
        }


@dataclass(frozen=True)
class UsageSnapshot:
    """某用户当日额度快照。"""

    limit: int
    used: int
    reset_at: str
    day: str
    timezone: str

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def exceeded(self) -> bool:
        return self.used >= self.limit

    def as_dict(self) -> dict:
        return {
            "limit": self.limit,
            "used": self.used,
            "remaining": self.remaining,
            "exceeded": self.exceeded,
            "resetAt": self.reset_at,
            "day": self.day,
            "timezone": self.timezone,
        }


def _quota_now() -> datetime:
    return datetime.now(get_settings().quota_tzinfo)


def current_quota_day() -> date:
    """当前额度自然日（按 QUOTA_TIMEZONE 切分）。"""
    return _quota_now().date()


def next_reset_at() -> datetime:
    """下一次额度重置时刻（当地次日 0 点）。"""
    now = _quota_now()
    return datetime.combine(now.date() + timedelta(days=1), time.min, tzinfo=now.tzinfo)


def _reset_label() -> str:
    return next_reset_at().strftime("%Y-%m-%d %H:%M")


def estimate_output_tokens(text: str) -> int:
    """字符估算输出 token（上游未上报用量时的回退口径）。

    CJK 字符按 1 token/字，其余按 4 字符/token。这是文档化的近似值，
    精确值取决于上游分词器，因此会随用量负载标记 estimated=true。
    """
    if not text:
        return 0
    cjk = 0
    for char in text:
        for low, high in _CJK_RANGES:
            if low <= char <= high:
                cjk += 1
                break
    other = len(text) - cjk
    return cjk + math.ceil(other / _ASCII_CHARS_PER_TOKEN)


def _snapshot(used: int, limit: int, day: date, timezone_name: str) -> UsageSnapshot:
    return UsageSnapshot(
        limit=limit,
        used=max(0, used),
        reset_at=_reset_label(),
        day=day.isoformat(),
        timezone=timezone_name,
    )


def _cache_key(user_id: int, day: date) -> str:
    return redis_client.key("quota", user_id, day.isoformat())


async def used_tokens(db: AsyncSession, user_id: int, day: date) -> int:
    """读数据库中该用户当日的输出 token 累计（权威值）。"""
    value = await db.scalar(
        select(DailyUsage.output_tokens).where(
            DailyUsage.user_id == user_id, DailyUsage.day == day
        )
    )
    return int(value or 0)


async def get_usage(db: AsyncSession, user_id: int) -> UsageSnapshot:
    """取用户当日额度快照：先看 Redis 缓存，未命中回源 PostgreSQL。"""
    settings = get_settings()
    day = current_quota_day()
    limit = settings.daily_output_token_limit

    cached = await cache.cache_get_json(_cache_key(user_id, day))
    if isinstance(cached, dict) and isinstance(cached.get("used"), int):
        return _snapshot(cached["used"], limit, day, settings.quota_timezone)

    used = await used_tokens(db, user_id, day)
    snapshot = _snapshot(used, limit, day, settings.quota_timezone)
    if not snapshot.exceeded:
        # 超额后不再缓存，避免重置前反复命中「已用尽」以外的判断
        await cache.cache_set_json(_cache_key(user_id, day), {"used": used}, settings.quota_cache_seconds)
    return snapshot


async def ensure_within_quota(db: AsyncSession, user_id: int) -> UsageSnapshot:
    """请求开始时的额度闸门：已用尽则抛 QuotaExceeded，否则返回当前快照。"""
    snapshot = await get_usage(db, user_id)
    if snapshot.exceeded:
        raise QuotaExceeded(
            limit=snapshot.limit,
            used=snapshot.used,
            reset_at=snapshot.reset_at,
            day=snapshot.day,
            timezone=snapshot.timezone,
        )
    return snapshot


async def add_output_tokens(user_id: int, tokens: int, requests: int = 1) -> None:
    """累加当日输出用量（独立会话，失败不影响已返回的内容）。"""
    if tokens <= 0 and requests <= 0:
        return
    day = current_quota_day()
    try:
        async with SessionLocal() as session:
            await _upsert(session, user_id, day, max(0, tokens), max(0, requests))
            await session.commit()
    except Exception:  # noqa: BLE001 - 记账失败不应影响对话结果
        logger.exception("输出 token 用量记账失败（user=%s day=%s）", user_id, day)
        return

    await cache.cache_delete(_cache_key(user_id, day))


async def _upsert(session: AsyncSession, user_id: int, day: date, tokens: int, requests: int) -> None:
    """原子累加当日用量（PostgreSQL upsert；其它方言退化为读写两步）。"""
    settings = get_settings()
    if settings.database_dsn.startswith("postgresql"):
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        statement = pg_insert(DailyUsage).values(
            user_id=user_id,
            day=day,
            output_tokens=tokens,
            requests=requests,
            updated_at=utcnow(),
        )
        statement = statement.on_conflict_do_update(
            constraint="uq_daily_usage_user_day",
            set_={
                "output_tokens": DailyUsage.output_tokens + statement.excluded.output_tokens,
                "requests": DailyUsage.requests + statement.excluded.requests,
                "updated_at": statement.excluded.updated_at,
            },
        )
        await session.execute(statement)
        return

    row = await session.scalar(
        select(DailyUsage).where(DailyUsage.user_id == user_id, DailyUsage.day == day)
    )
    if row is None:
        session.add(
            DailyUsage(
                user_id=user_id,
                day=day,
                output_tokens=tokens,
                requests=requests,
            )
        )
    else:
        row.output_tokens += tokens
        row.requests += requests
        row.updated_at = utcnow()
