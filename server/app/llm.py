"""上游模型调用：OpenAI 兼容接口（一个 base url + 一个 key + 多个 model），流式输出。"""

from __future__ import annotations

import logging
import re
from collections.abc import AsyncIterator
from typing import Any

import httpx
from openai import (
    APIConnectionError,
    APIError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    BadRequestError,
    NotFoundError,
    PermissionDeniedError,
    RateLimitError,
)

from .config import get_settings

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """上游模型调用失败（对外可直接展示的友好信息）。"""


_clients: dict[str, AsyncOpenAI] = {}

# 兼容不同厂商对「思考内容」的字段命名
_REASONING_ATTRS = (
    "reasoning_content",
    "reasoning",
    "reasoning_text",
    "thinking",
)


def get_client(base_url: str | None = None) -> AsyncOpenAI:
    """按 base url 复用客户端；未配置密钥时抛出 LLMError。"""
    settings = get_settings()
    if not settings.openai_api_key:
        raise LLMError("服务端未配置 OPENAI_API_KEY，无法调用模型")

    url = (base_url or settings.openai_base_url or "").rstrip("/")
    if not url:
        raise LLMError("服务端未配置 OPENAI_BASE_URL，无法调用模型")

    client = _clients.get(url)
    if client is None:
        client = _build_client(url)
        _clients[url] = client
    return client


def _normalize_base_url(url: str) -> str:
    """规整 base url：去掉末尾斜杠，并把路径里重复的斜杠合并（如 https://x.top//v1）。"""
    cleaned = re.sub(r"(?<!:)/{2,}", "/", url.strip())
    return cleaned.rstrip("/")


def _build_client(url: str) -> AsyncOpenAI:
    """创建上游客户端（显式控制超时与代理行为）。"""
    settings = get_settings()
    url = _normalize_base_url(url)
    http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(settings.openai_timeout, connect=15.0),
        trust_env=settings.openai_trust_env,
        limits=httpx.Limits(max_connections=64, max_keepalive_connections=16),
    )
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=url,
        max_retries=settings.openai_max_retries,
        http_client=http_client,
    )


def _friendly_error(exc: Exception, model: str) -> str:
    if isinstance(exc, AuthenticationError):
        return "上游模型服务鉴权失败，请检查 OPENAI_API_KEY"
    if isinstance(exc, PermissionDeniedError):
        return f"没有访问模型「{model}」的权限"
    if isinstance(exc, NotFoundError):
        return f"模型「{model}」不存在或未开通"
    if isinstance(exc, RateLimitError):
        return "上游模型服务触发限流，请稍后重试"
    if isinstance(exc, APITimeoutError):
        return "上游模型服务响应超时，请稍后重试"
    if isinstance(exc, APIConnectionError):
        return "无法连接上游模型服务，请检查 OPENAI_BASE_URL 与网络"
    if isinstance(exc, BadRequestError):
        return f"请求被上游拒绝：{getattr(exc, 'message', None) or exc}"
    if isinstance(exc, APIError):
        return f"上游模型服务返回错误：{getattr(exc, 'message', None) or exc}"
    return f"调用模型失败：{exc}"


def _reasoning_delta(delta: Any) -> str:
    """提取思考内容增量（不同网关字段名不同）。"""
    for attr in _REASONING_ATTRS:
        value = getattr(delta, attr, None)
        if isinstance(value, str) and value:
            return value
    extra = getattr(delta, "model_extra", None)
    if isinstance(extra, dict):
        for attr in _REASONING_ATTRS:
            value = extra.get(attr)
            if isinstance(value, str) and value:
                return value
    return ""


def _content_delta(delta: Any) -> str:
    value = getattr(delta, "content", None)
    if isinstance(value, str):
        return value
    return ""


def _completion_tokens(chunk: Any) -> int | None:
    """从流式块里取上游上报的输出 token 数（多数网关只在最后一块给）。"""
    usage = getattr(chunk, "usage", None)
    if usage is None:
        return None
    for attr in ("completion_tokens", "output_tokens"):
        value = getattr(usage, attr, None)
        if isinstance(value, int) and value >= 0:
            return value
    return None


async def stream_chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float | None = None,
    base_url: str | None = None,
    usage_sink: dict[str, int] | None = None,
) -> AsyncIterator[tuple[str, str]]:
    """流式调用上游模型，逐块产出 ("thinking" | "content", delta)。

    用量上报（可选）：上游若在流中返回 usage，会写入 usage_sink["completion_tokens"]，
    供调用方做每日输出 token 记账；网关不上报时该键保持不存在，由调用方回退估算。
    """
    settings = get_settings()
    client = get_client(base_url)
    payload: dict[str, Any] = {"model": model, "messages": messages, "stream": True}
    if temperature is not None:
        payload["temperature"] = temperature
    if settings.openai_stream_usage:
        # 部分第三方网关不认该参数，因此默认关闭；开启后若被拒会按坏请求处理
        payload["stream_options"] = {"include_usage": True}

    try:
        stream = await client.chat.completions.create(**payload)
    except Exception as exc:  # noqa: BLE001 - 统一转换为友好错误
        logger.warning("上游模型请求失败（%s）：%s", model, exc)
        raise LLMError(_friendly_error(exc, model)) from exc

    try:
        async for chunk in stream:
            if usage_sink is not None:
                tokens = _completion_tokens(chunk)
                if tokens is not None:
                    usage_sink["completion_tokens"] = tokens
            choices = getattr(chunk, "choices", None) or []
            if not choices:
                continue
            delta = getattr(choices[0], "delta", None)
            if delta is None:
                continue
            reasoning = _reasoning_delta(delta)
            if reasoning:
                yield "thinking", reasoning
            content = _content_delta(delta)
            if content:
                yield "content", content
    except Exception as exc:  # noqa: BLE001 - 流式过程中的异常同样需要友好化
        logger.warning("上游模型流式输出中断（%s）：%s", model, exc)
        raise LLMError(_friendly_error(exc, model)) from exc
    finally:
        close = getattr(stream, "close", None)
        if callable(close):
            try:
                await close()
            except Exception:  # noqa: BLE001 - 关闭失败不影响主流程
                logger.debug("关闭上游流失败", exc_info=True)


async def close_clients() -> None:
    """应用关闭时释放连接。"""
    for client in _clients.values():
        try:
            await client.close()
        except Exception:  # noqa: BLE001
            logger.debug("关闭模型客户端失败", exc_info=True)
    _clients.clear()
