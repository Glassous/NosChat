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
from .config import get_settings
from .database import SessionLocal, dispose_db, init_db
from .llm import close_clients
from .model_registry import registry
from .routers import auth, catalog, chat

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
    await _wait_for_database()
    await init_db()

    if settings.jwt_secret_is_default:
        logger.warning("JWT_SECRET 仍为默认值，请在生产环境中替换为随机长字符串")
    if not settings.smtp_enabled and not settings.auth_dev_echo_code:
        logger.warning("未配置 SMTP 且未开启 AUTH_DEV_ECHO_CODE，注册/登录将无法发送验证码")

    logger.info(
        "NosChat API 已启动：port=%s models=%d cors=%s",
        settings.port,
        len(registry.models),
        settings.cors_origin_list,
    )
    try:
        yield
    finally:
        await close_clients()
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


app.include_router(auth.router, prefix=settings.api_prefix)
app.include_router(catalog.router, prefix=settings.api_prefix)
app.include_router(chat.router, prefix=settings.api_prefix)


@app.get("/health", tags=["system"], summary="健康检查")
async def health() -> dict:
    return {
        "status": "ok",
        "version": __version__,
        "models": len(registry.models),
    }
