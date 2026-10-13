"""会话与消息路由：会话 CRUD、历史消息，以及 SSE 流式对话。"""

from __future__ import annotations

import asyncio
import json
import logging
import re
import time
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .. import ratelimit, usage
from ..config import get_settings
from ..database import SessionLocal, get_db
from ..deps import get_current_user
from ..llm import LLMError, stream_chat
from ..model_registry import registry
from ..models import Conversation, Message, User, utcnow
from ..schemas import (
    ChatStreamRequest,
    ConversationCreated,
    ConversationOut,
    CreateConversationRequest,
    MessageOut,
    UpdateConversationRequest,
    conversation_out,
    message_out,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])

GREETING_TITLE = "新对话"
GREETING_PREVIEW = "开始新的对话…"
# 传给上游模型的上下文消息条数上限
HISTORY_LIMIT = 20
_PREVIEW_LIMIT = 34
_TITLE_LIMIT = 16
# 早期版本会为每个新会话写入一条开场白，这里在读取时忽略它（界面与上游上下文都不再出现）
_LEGACY_GREETING = re.compile(r"^你好，.+！当前模型是 .+。有什么可以帮你的吗？$")


# ---------------------------------------------------------------- 辅助


def _one_line(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _preview(text: str) -> str:
    one = _one_line(text)
    if not one:
        return GREETING_PREVIEW
    return one[: _PREVIEW_LIMIT] + "…" if len(one) > _PREVIEW_LIMIT else one


def _derive_title(text: str) -> str:
    one = _one_line(text)
    if not one:
        return GREETING_TITLE
    return one[: _TITLE_LIMIT] + "…" if len(one) > _TITLE_LIMIT else one


def _drop_legacy_greeting(rows: list[Message]) -> list[Message]:
    """去掉历史遗留的开场白（会话的第一条助手消息）。"""
    if rows and rows[0].role == "assistant":
        first = (rows[0].content or "").strip()
        if _LEGACY_GREETING.match(first):
            return rows[1:]
    return rows


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def _get_conversation(
    db: AsyncSession, user: User, conversation_id: str
) -> Conversation:
    conversation = await db.get(Conversation, conversation_id)
    if conversation is None or conversation.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "对话不存在")
    return conversation


async def _load_messages(
    db: AsyncSession, conversation_id: str, limit: int | None = None
) -> list[Message]:
    stmt = (
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.desc(), Message.id.desc())
    )
    if limit:
        stmt = stmt.limit(limit)
    rows = list((await db.scalars(stmt)).all())
    rows.reverse()
    return _drop_legacy_greeting(rows)


async def _save_assistant_message(
    *,
    conversation_id: str,
    model_id: str,
    content: str,
    thinking: str,
    thinking_sec: int,
) -> Message:
    """流结束后落库助手消息（使用独立会话，避免长时间占用请求连接）。"""
    async with SessionLocal() as session:
        message = Message(
            conversation_id=conversation_id,
            role="assistant",
            model_id=model_id,
            content=content,
            thinking=thinking,
            thinking_sec=thinking_sec,
        )
        session.add(message)
        conversation = await session.get(Conversation, conversation_id)
        if conversation is not None:
            conversation.updated_at = utcnow()
            if content:
                conversation.preview = _preview(content)
        await session.commit()
        return message


# ---------------------------------------------------------------- 会话 CRUD


@router.get("/conversations", response_model=list[ConversationOut], summary="会话列表")
async def list_conversations(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ConversationOut]:
    stmt = (
        select(Conversation)
        .where(Conversation.user_id == user.id)
        .order_by(Conversation.pinned.desc(), Conversation.updated_at.desc())
    )
    rows = list((await db.scalars(stmt)).all())
    return [conversation_out(item) for item in rows]


@router.post(
    "/conversations",
    response_model=ConversationCreated,
    status_code=status.HTTP_201_CREATED,
    summary="新建会话",
)
async def create_conversation(
    payload: CreateConversationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationCreated:
    model = registry.resolve(payload.model)
    if model is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "服务端未配置任何模型")

    # 新会话不写入开场白消息：避免干扰界面阅读与上游上下文
    conversation = Conversation(
        user_id=user.id,
        title=(payload.title or GREETING_TITLE).strip() or GREETING_TITLE,
        model_id=model["id"],
        preview=GREETING_PREVIEW,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)

    return ConversationCreated(conversation=conversation_out(conversation), messages=[])


@router.get(
    "/conversations/{conversation_id}/messages",
    response_model=list[MessageOut],
    summary="会话消息列表",
)
async def list_messages(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[MessageOut]:
    await _get_conversation(db, user, conversation_id)
    rows = await _load_messages(db, conversation_id)
    return [message_out(item) for item in rows]


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationOut,
    summary="更新会话（标题 / 模型 / 置顶 / 未读）",
)
async def update_conversation(
    conversation_id: str,
    payload: UpdateConversationRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ConversationOut:
    conversation = await _get_conversation(db, user, conversation_id)

    touched = False
    if payload.title is not None:
        title = payload.title.strip()
        if not title:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "标题不能为空")
        conversation.title = title
        touched = True
    if payload.model is not None:
        model = registry.get(payload.model)
        if model is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "模型不存在或未配置")
        conversation.model_id = model["id"]
        touched = True
    if payload.pinned is not None:
        conversation.pinned = payload.pinned
        touched = True
    if payload.unread is not None:
        # 标记已读不属于「会话内容变化」：不推高 updated_at，
        # 否则会话会被顶到列表顶部、时间戳也会变成「刚刚」
        conversation.unread = payload.unread

    if touched:
        conversation.updated_at = utcnow()
    await db.commit()
    await db.refresh(conversation)
    return conversation_out(conversation)


@router.delete(
    "/conversations/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除会话",
)
async def delete_conversation(
    conversation_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    conversation = await _get_conversation(db, user, conversation_id)
    await db.delete(conversation)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------- 流式对话


@router.post("/chat/stream", summary="流式对话（SSE）")
async def chat_stream(
    payload: ChatStreamRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    settings = get_settings()
    content = payload.content.strip()
    if not content:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "消息内容不能为空")

    model = registry.resolve(payload.model)
    if model is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "服务端未配置任何模型")

    conversation = await _get_conversation(db, user, payload.conversation_id)

    # 限流与额度闸门都放在写入用户消息之前：被拒绝的请求不落库、也不产生用量
    await ratelimit.enforce(
        "chat",
        f"u:{user.id}",
        settings.chat_rate_limit_per_user,
        settings.chat_rate_limit_window_seconds,
    )
    # 额度只按 JWT 解析出的 user.id 判定，客户端无法用请求体绕过；
    # 判定通过则整轮放行（允许把用量推过上限，以保证回复完整）
    await usage.ensure_within_quota(db, user.id)

    # 1) 先落库用户消息，并同步会话标题/预览/模型
    user_message = Message(
        conversation_id=conversation.id,
        role="user",
        model_id=model["id"],
        content=content,
    )
    db.add(user_message)
    if not conversation.title or conversation.title == GREETING_TITLE:
        conversation.title = _derive_title(content)
    conversation.model_id = model["id"]
    conversation.preview = _preview(content)
    conversation.updated_at = utcnow()
    await db.commit()
    await db.refresh(user_message)

    conversation_id = conversation.id
    title = conversation.title
    preview = conversation.preview
    user_message_id = user_message.id

    # 2) 组装上游上下文
    history = await _load_messages(db, conversation_id, limit=HISTORY_LIMIT)
    upstream_messages = [
        {"role": item.role, "content": item.content}
        for item in history
        if item.content and item.role in {"user", "assistant"}
    ]
    if not upstream_messages:
        upstream_messages = [{"role": "user", "content": content}]

    model_id = model["id"]
    upstream_name = model["model"]
    temperature = model.get("temp")
    base_url = model.get("base_url")
    user_id = user.id
    # 上游上报的用量落到这里（网关不支持时为空，改用字符估算）
    usage_sink: dict[str, int] = {}

    async def event_stream() -> AsyncIterator[str]:
        thinking_parts: list[str] = []
        content_parts: list[str] = []
        think_started: float | None = None
        think_elapsed = 0.0
        error_message: str | None = None
        assistant_id: str | None = None
        final_thinking_sec = 0
        usage_payload: dict = {}
        final_preview = preview

        yield _sse(
            {
                "type": "start",
                "conversationId": conversation_id,
                "userMessageId": user_message_id,
                "title": title,
                "preview": preview,
            }
        )

        try:
            async for kind, delta in stream_chat(
                model=upstream_name,
                messages=upstream_messages,
                temperature=temperature,
                base_url=base_url,
                usage_sink=usage_sink,
            ):
                if kind == "thinking":
                    if think_started is None:
                        think_started = time.monotonic()
                    thinking_parts.append(delta)
                    yield _sse({"type": "thinking", "delta": delta})
                else:
                    if think_started is not None and think_elapsed <= 0:
                        think_elapsed = max(1.0, time.monotonic() - think_started)
                    content_parts.append(delta)
                    yield _sse({"type": "content", "delta": delta})
        except LLMError as exc:
            error_message = str(exc)
            logger.warning("流式对话失败（conversation=%s）：%s", conversation_id, exc)
        except asyncio.CancelledError:
            # 客户端断开：保留已生成内容后继续抛出
            logger.info("客户端断开流式连接（conversation=%s）", conversation_id)
            raise
        except Exception as exc:  # noqa: BLE001 - 兜底，避免流中断后无提示
            error_message = "服务端处理失败，请稍后重试"
            logger.exception("流式对话异常（conversation=%s）：%s", conversation_id, exc)
        finally:
            final_content = "".join(content_parts)
            final_thinking = "".join(thinking_parts)
            if think_started is not None and think_elapsed <= 0:
                think_elapsed = max(1.0, time.monotonic() - think_started)
            # 思考耗时以服务端测量为准（前端不再自行计算）
            final_thinking_sec = int(round(think_elapsed)) if final_thinking else 0

            # 额度记账：只统计输出 token（thinking + content），输入不计
            upstream_tokens = usage_sink.get("completion_tokens")
            estimated = upstream_tokens is None
            counted = (
                usage.estimate_output_tokens(final_thinking + final_content)
                if estimated
                else int(upstream_tokens or 0)
            )
            try:
                await usage.add_output_tokens(user_id, counted)
            except Exception:  # noqa: BLE001 - 记账失败不应影响已返回内容
                logger.exception("输出 token 记账失败（conversation=%s）", conversation_id)
            try:
                usage_payload = {
                    **(await usage.get_usage(db, user_id)).as_dict(),
                    "estimated": estimated,
                }
            except Exception:  # noqa: BLE001 - 快照读取失败不阻塞收尾
                logger.exception("额度快照读取失败（user=%s）", user_id)

            if final_content or final_thinking:
                try:
                    saved = await _save_assistant_message(
                        conversation_id=conversation_id,
                        model_id=model_id,
                        content=final_content,
                        thinking=final_thinking,
                        thinking_sec=final_thinking_sec,
                    )
                    assistant_id = saved.id
                    if final_content:
                        final_preview = _preview(final_content)
                except Exception:  # noqa: BLE001 - 落库失败不应影响已返回内容
                    logger.exception("助手消息落库失败（conversation=%s）", conversation_id)

        if error_message:
            yield _sse(
                {
                    "type": "error",
                    "message": error_message,
                    "conversationId": conversation_id,
                    "messageId": assistant_id,
                    "thinkingSec": final_thinking_sec,
                    "usage": usage_payload,
                }
            )
            return

        yield _sse(
            {
                "type": "done",
                "conversationId": conversation_id,
                "messageId": assistant_id,
                "title": title,
                "preview": final_preview,
                "thinkingSec": final_thinking_sec,
                "usage": usage_payload,
            }
        )

    headers = {
        "Cache-Control": "no-cache, no-transform",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    logger.info(
        "开始流式对话：user=%s conversation=%s model=%s timeout=%.0fs",
        user.id,
        conversation_id,
        model_id,
        settings.openai_timeout,
    )
    return StreamingResponse(event_stream(), media_type="text/event-stream", headers=headers)
