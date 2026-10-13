"""FastAPI 应用入口（默认监听 9135）。"""

from __future__ import annotations

import asyncio
import logging
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from . import __version__
from .cache import cache_delete
from .config import get_settings
from .database import SessionLocal, dispose_db, init_db
from .llm import close_clients
from .model_registry import registry
from .redis_client import close_redis, init_redis, redis_state
from .routers import auth, catalog, chat, usage
from .routers.catalog import CACHE_KEY as CATALOG_CACHE_KEY
from .usage import QuotaExceeded

settings = get_settings()

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger("noschat")


def _ensure_loop_compatible() -> None:
    """Windows 上 psycopg 异步模式无法在 ProactorEventLoop 中运行，提前给出明确提示。"""
    if sys.platform != "win32":
        return
    loop = asyncio.get_running_loop()
    if isinstance(loop, asyncio.ProactorEventLoop):
        raise RuntimeError(
            "检测到 Windows ProactorEventLoop：数据库异步驱动无法工作。"
            "请使用 `python run.py` 启动服务（会自动切换到 SelectorEventLoop）。"
        )


async def _wait_for_database() -> None:
    """等待数据库就绪（容器编排时数据库可能晚于应用启动）。"""
    last_error: Exception | None = None
    for attempt in range(1, settings.db_connect_retries + 1):
        try:
            async with SessionLocal() as session:
                await session.execute(text("SELECT 1"))
            return
        except (SQLAlchemyError, OSError) as exc:
            last_error = exc
            logger.warning(
                "数据库暂不可用（第 %d/%d 次重试）：%s",
                attempt,
                settings.db_connect_retries,
                str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__,
            )
            await asyncio.sleep(settings.db_connect_retry_interval)
    raise RuntimeError(f"数据库连接失败：{last_error}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _ensure_loop_compatible()
    registry.load()
    await init_redis()
    # 模型清单缓存与注册表必须一致：启动时清一次，避免沿用旧镜像/旧配置的缓存
    await cache_delete(CATALOG_CACHE_KEY)
    await _wait_for_database()
    await init_db()

    if settings.jwt_secret_is_default:
        logger.warning("JWT_SECRET 仍为默认值，请在生产环境中替换为随机长字符串")
    if not settings.smtp_enabled and not settings.auth_dev_echo_code:
        logger.warning("未配置 SMTP 且未开启 AUTH_DEV_ECHO_CODE，注册/登录将无法发送验证码")
    if not settings.redis_enabled:
        logger.warning("未配置 REDIS_URL：缓存与限流将以进程内降级模式运行")

    logger.info(
        "NosChat API 已启动：port=%s models=%d cors=%s daily_token_limit=%d",
        settings.port,
        len(registry.models),
        settings.cors_origin_list,
        settings.daily_output_token_limit,
    )
    try:
        yield
    finally:
        await close_clients()
        await close_redis()
        await dispose_db()
        logger.info("NosChat API 已关闭")


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    description="NosChat 后端：模型清单、邮件验证码注册登录、流式对话与会话持久化。",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(SQLAlchemyError)
async def _database_error_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    logger.exception("数据库操作失败：%s %s", request.method, request.url.path)
    return JSONResponse(status_code=503, content={"detail": "数据库暂时不可用，请稍后重试"})


@app.exception_handler(QuotaExceeded)
async def _quota_error_handler(request: Request, exc: QuotaExceeded) -> JSONResponse:
    """额度用尽：402（与限流的 429 区分），前端据此锁定输入框。

    这是后端的硬闸门——前端是否锁定、是否被绕过都不影响该判定。
    """
    logger.info("输出 token 额度已用尽：user=%s used=%s/%s", request.url.path, exc.used, exc.limit)
    return JSONResponse(status_code=402, content=exc.payload())


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(catalog.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)
app.include_router(usage.router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"], summary="健康检查")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "models": len(registry.models),
        "redis": await redis_state(),
    }
