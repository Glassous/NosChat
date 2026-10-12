"""本地联调用的 OpenAI 兼容 Mock 服务（仅用于开发与自动化验证，不参与部署）。

启动：
    python tests/mock_llm.py                       # 默认监听 127.0.0.1:9901
    MOCK_LLM_HOST=0.0.0.0 python tests/mock_llm.py # 供容器内的后端访问

将 server/.env 的 OPENAI_BASE_URL 指向 http://127.0.0.1:9901/v1 即可；
后端在容器内时使用 http://host.docker.internal:9901/v1。
"""

from __future__ import annotations

import asyncio
import json
import os
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI(title="Mock OpenAI-compatible server")

# 名称包含这些片段的模型会先输出一段「思考」增量
REASONING_HINTS = ("reasoner", "r1", "qwq", "thinking")


def _is_reasoning(model: str) -> bool:
    lowered = (model or "").lower()
    return any(hint in lowered for hint in REASONING_HINTS)


@app.get("/v1/models")
async def list_models() -> dict:
    return {"object": "list", "data": [{"id": "mock-chat", "object": "model"}]}


@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    model = body.get("model", "mock-chat")
    stream = bool(body.get("stream"))
    prompt = ""
    for item in reversed(body.get("messages") or []):
        if item.get("role") == "user":
            prompt = (item.get("content") or "")[:40]
            break

    thinking = f"正在分析「{prompt}」：先确认目标，再拆解步骤，最后给出结论。"
    answer = f"这是来自 Mock 模型（{model}）的回复：关于「{prompt}」，建议先跑通最小闭环，再逐步增强。"

    if not stream:
        return {
            "id": "chatcmpl-mock",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": answer},
                    "finish_reason": "stop",
                }
            ],
        }

    def chunk(delta: dict, finish: str | None = None) -> str:
        payload = {
            "id": "chatcmpl-mock",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{"index": 0, "delta": delta, "finish_reason": finish}],
        }
        return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

    async def event_stream():
        yield chunk({"role": "assistant", "content": ""})
        if _is_reasoning(model):
            for char in thinking:
                await asyncio.sleep(0.01)
                yield chunk({"reasoning_content": char})
        for char in answer:
            await asyncio.sleep(0.01)
            yield chunk({"content": char})
        yield chunk({}, finish="stop")
        yield "data: [DONE]\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("MOCK_LLM_HOST", "127.0.0.1"),
        port=int(os.getenv("MOCK_LLM_PORT", "9901")),
        log_level="warning",
    )
