"""请求/响应模型（对外统一 camelCase，与前端既有字段保持一致）。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field
from pydantic.alias_generators import to_camel

from .models import Conversation, Message, User


class CamelModel(BaseModel):
    """统一使用 camelCase 别名、并允许按字段名构造。"""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


# ---------------------------------------------------------------- 鉴权


class SendCodeRequest(CamelModel):
    email: EmailStr
    purpose: Literal["register"] = "register"


class SendCodeResponse(CamelModel):
    ok: bool = True
    expires_in: int
    resend_after: int
    dev_code: str | None = None


class RegisterRequest(CamelModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8)
    nickname: str = Field(min_length=1, max_length=32)
    password: str = Field(min_length=6, max_length=64)


class LoginRequest(CamelModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=64)


class UserOut(CamelModel):
    id: int
    email: str
    nickname: str
    username: str
    created_at: datetime


class TokenResponse(CamelModel):
    token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserOut


# ---------------------------------------------------------------- 模型清单


class ModelOut(CamelModel):
    id: str
    model: str
    name: str
    provider: str
    icon: str
    badge: str
    color: str
    desc: str
    tags: list[str]
    context: str
    released: str
    speed: int
    intelligence: int
    temp: float
    reasoning: bool
    latency: list[int]


# ---------------------------------------------------------------- 会话与消息


class ConversationOut(CamelModel):
    id: str
    title: str
    preview: str
    model: str
    pinned: bool
    unread: bool
    created_at: datetime
    updated_at: datetime


class MessageOut(CamelModel):
    id: str
    type: Literal["user", "ai"]
    role: str
    model: str
    content: str
    thinking: str
    thinking_sec: int
    created_at: datetime


class ConversationCreated(CamelModel):
    conversation: ConversationOut
    messages: list[MessageOut]


class CreateConversationRequest(CamelModel):
    model: str = ""
    title: str | None = None


class UpdateConversationRequest(CamelModel):
    title: str | None = Field(default=None, max_length=60)
    model: str | None = None
    pinned: bool | None = None
    unread: bool | None = None


class ChatStreamRequest(CamelModel):
    conversation_id: str
    model: str = ""
    content: str = Field(min_length=1, max_length=4000)


# ---------------------------------------------------------------- 序列化辅助


def user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        email=user.email,
        nickname=user.nickname,
        username=user.username,
        created_at=user.created_at,
    )


def conversation_out(conv: Conversation) -> ConversationOut:
    return ConversationOut(
        id=conv.id,
        title=conv.title,
        preview=conv.preview,
        model=conv.model_id,
        pinned=conv.pinned,
        unread=conv.unread,
        created_at=conv.created_at,
        updated_at=conv.updated_at,
    )


def message_out(msg: Message) -> MessageOut:
    return MessageOut(
        id=msg.id,
        type="ai" if msg.role == "assistant" else "user",
        role=msg.role,
        model=msg.model_id,
        content=msg.content,
        thinking=msg.thinking,
        thinking_sec=msg.thinking_sec,
        created_at=msg.created_at,
    )
