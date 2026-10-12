"""NosChat 后端启动入口。

Windows 说明：psycopg 的异步模式不支持 ProactorEventLoop，而 uvicorn 在 Windows 上
默认使用 ProactorEventLoop。因此这里自行创建事件循环（Windows 使用 SelectorEventLoop），
再交给 uvicorn 运行，避免 `python -m uvicorn app.main:app` 时数据库连接报
"Psycopg cannot use the 'ProactorEventLoop' to run in async mode"。

用法：
    python run.py                 # 读取 .env 中的 PORT（默认 9135）
"""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Callable
from typing import Any

import uvicorn

from app.config import get_settings


def _loop_factory() -> Callable[[], asyncio.AbstractEventLoop] | None:
    """Windows 下强制使用 SelectorEventLoop。"""
    if sys.platform == "win32":
        return asyncio.SelectorEventLoop
    return None


def main() -> None:
    settings = get_settings()
    config = uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=settings.port,
        log_level="debug" if settings.debug else "info",
        loop="none",  # 事件循环由本脚本创建
        access_log=True,
    )
    server = uvicorn.Server(config)

    kwargs: dict[str, Any] = {}
    factory = _loop_factory()
    if factory is not None:
        kwargs["loop_factory"] = factory

    asyncio.run(server.serve(), **kwargs)


if __name__ == "__main__":
    main()
