"""每日输出 token 额度的端到端测试（需要后端以低额度启动）。

用法：
    # 终端 1：用很低的上限启动后端，便于在几轮内把额度打满
    cd server
    set DAILY_OUTPUT_TOKEN_LIMIT=30 & python run.py      # Windows PowerShell: $env:DAILY_OUTPUT_TOKEN_LIMIT=30
    DAILY_OUTPUT_TOKEN_LIMIT=30 python run.py            # Linux/macOS

    # 终端 2：
    python tests/quota_smoke.py

覆盖点（重点是"绕过前端也过不了后端"）：
    1. 新账号当日 used 从 0 开始；
    2. 正常一轮后 used 增长，done 事件带回 usage 快照；
    3. **直接调用 /api/chat/stream**（完全不经前端输入框）持续对话，
       直到返回 402 quota_exceeded —— 证明锁定输入框不是安全边界；
    4. 触发额度上限的那一轮仍然完整跑完（收到 done、内容非空），
       即"最后一个对话可以超出一点来换完整"；
    5. 额度用尽后再次直连调用依旧 402；
    6. 另开账号额度独立、可正常对话（额度按 user 隔离）；
    7. 额度快照的 exceeded / resetAt 字段可解析。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import httpx


def _fail(message: str) -> None:
    print(f"FAIL  {message}")
    sys.exit(1)


def _ok(message: str) -> None:
    print(f"OK    {message}")


def _code_of(response: httpx.Response, fallback: str) -> str:
    dev = response.json().get("devCode")
    return dev or fallback


def _stream_once(
    client: httpx.Client,
    api: str,
    auth: dict,
    conversation_id: str,
    model_id: str,
    content: str,
) -> tuple[int, dict, str]:
    """发一轮对话；返回 (状态码, done/error 事件, 正文)。非 200 时事件为空。"""
    with client.stream(
        "POST",
        f"{api}/chat/stream",
        headers=auth,
        json={"conversationId": conversation_id, "model": model_id, "content": content},
    ) as response:
        if response.status_code != 200:
            return response.status_code, {}, ""
        done_event: dict = {}
        error_event: dict = {}
        text_parts: list[str] = []
        for line in response.iter_lines():
            if not line.startswith("data: "):
                continue
            event = json.loads(line[6:])
            if event["type"] == "content":
                text_parts.append(event["delta"])
            elif event["type"] == "done":
                done_event = event
            elif event["type"] == "error":
                error_event = event
        return 200, (done_event or error_event), "".join(text_parts)


def _register(client: httpx.Client, base: str, api: str, tag: str) -> tuple[str, dict]:
    """注册一个全新账号，返回 (email, auth headers)。"""
    email = f"quota-{tag}-{int(time.time())}@example.com"
    password = "quota-pass-123"
    sent = client.post(f"{api}/auth/send-code", json={"email": email})
    if sent.status_code != 200:
        _fail(f"发送验证码失败：{sent.status_code} {sent.text}")
    registered = client.post(
        f"{api}/auth/register",
        json={
            "email": email,
            "code": _code_of(sent, ""),
            "nickname": f"额度用例{tag}",
            "password": password,
        },
    )
    if registered.status_code != 201:
        _fail(f"注册失败：{registered.status_code} {registered.text}")
    return email, {"Authorization": f"Bearer {registered.json()['token']}"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9135")
    parser.add_argument("--code", default="", help="已配置真实 SMTP 时需传入邮箱收到的验证码")
    parser.add_argument(
        "--expect-limit",
        type=int,
        default=int(os.environ.get("DAILY_OUTPUT_TOKEN_LIMIT", "30")),
        help="后端启动时的 DAILY_OUTPUT_TOKEN_LIMIT（默认 30）",
    )
    parser.add_argument("--max-turns", type=int, default=25, help="打满额度允许的最大轮数")
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api = f"{base}/api"
    limit = args.expect_limit
    print(f"目标后端：{base}\n期望额度上限：{limit}\n")

    with httpx.Client(timeout=120.0, trust_env=False) as client:
        health = client.get(f"{base}/health")
        if health.status_code != 200:
            _fail(f"健康检查失败：{health.status_code}")
        if health.json().get("redis") not in {"ok", "down", "disabled"}:
            _fail(f"/health 的 redis 字段异常：{health.json()}")

        models = client.get(f"{api}/models").json()
        if not models:
            _fail("模型清单为空")
        model_id = models[0]["id"]

        # 1. 新账号额度从 0 开始
        print("—— 用例：额度按用户隔离，初始为 0 ——")
        email_a, auth_a = _register(client, base, api, "a")
        usage_a = client.get(f"{api}/usage/today", headers=auth_a)
        if usage_a.status_code != 200:
            _fail(f"查询额度失败：{usage_a.status_code} {usage_a.text}")
        snapshot = usage_a.json()
        if snapshot["limit"] != limit:
            _fail(f"额度上限应为 {limit}（后端是否用 DAILY_OUTPUT_TOKEN_LIMIT={limit} 启动？）：{snapshot['limit']}")
        if snapshot["used"] != 0 or snapshot["exceeded"] is not False:
            _fail(f"新账号额度应为 0 且未超额：{snapshot}")
        _ok(f"新账号额度：used={snapshot['used']}/{snapshot['limit']} resetAt={snapshot['resetAt']}")

        created = client.post(f"{api}/conversations", json={"model": model_id}, headers=auth_a)
        if created.status_code != 201:
            _fail(f"新建会话失败：{created.status_code} {created.text}")
        conversation_a = created.json()["conversation"]["id"]

        # 2 + 3. 持续直连对话，直到额度打满
        print("—— 用例：绕过前端直接调用接口，打满额度后必须被后端拦下 ——")
        blocked_status = 0
        blocked_payload: dict = {}
        last_ok_event: dict = {}
        last_ok_text = ""
        turns = 0
        for _ in range(args.max_turns):
            status, event, text = _stream_once(
                client, api, auth_a, conversation_a, model_id, "请用一句话回复我"
            )
            if status == 200:
                if not event:
                    _fail("对话未返回 done/error 事件")
                if event.get("type") == "error":
                    _fail(f"对话返回错误：{event.get('message')}")
                last_ok_event, last_ok_text = event, text
                turns += 1
            elif status == 402:
                blocked_status = status
                break
            else:
                _fail(f"对话返回意外状态：{status}")

        if not turns:
            _fail("未能完成任何一轮对话（额度上限是否过小？）")
        if last_ok_event.get("usage", {}).get("used", 0) <= 0:
            _fail(f"done 事件未带回用量：{last_ok_event.get('usage')}")
        _ok(f"前 {turns} 轮正常，最后一轮 done.usage.used={last_ok_event['usage']['used']}")

        # 4. 触发上限的那一轮必须完整跑完（有 done、有内容）
        if last_ok_event.get("type") != "done":
            _fail(f"额度用尽前的最后一轮应正常收尾（done），实际：{last_ok_event.get('type')}")
        if not last_ok_text.strip():
            _fail("额度用尽前的最后一轮应返回完整内容")
        if last_ok_event.get("preview") is None:
            _fail("最后一轮 done 事件缺少 preview")
        _ok(f"额度用尽前的最后一轮完整收尾：内容 {len(last_ok_text)} 字，未被中途截断")

        # 额度应当确实被打满（这正是"最后一轮允许超出"的结果）
        if last_ok_event["usage"]["used"] < limit:
            _fail(f"额度尚未打满却已停止：{last_ok_event['usage']}")

        # 5. 用原始 HTTP 再确认一次：仍然 402
        probe = client.post(
            f"{api}/chat/stream",
            headers=auth_a,
            json={"conversationId": conversation_a, "model": model_id, "content": "再试一次"},
        )
        blocked_status = probe.status_code
        try:
            blocked_payload = probe.json()
        except ValueError:
            blocked_payload = {}

        if blocked_status != 402:
            _fail(f"额度用尽后应返回 402，实际 {blocked_status}")
        if blocked_payload.get("code") != "quota_exceeded":
            _fail(f"402 响应应带 code=quota_exceeded：{blocked_payload}")
        if blocked_payload.get("limit") != limit:
            _fail(f"402 响应应带正确 limit：{blocked_payload}")
        _ok(
            f"绕过前端直连接口被后端拦下：402 code={blocked_payload.get('code')} "
            f"used={blocked_payload.get('used')}/{blocked_payload.get('limit')}"
        )

        # 6. 快照字段可解析
        final_usage = client.get(f"{api}/usage/today", headers=auth_a).json()
        if final_usage["exceeded"] is not True:
            _fail(f"额度用尽后 exceeded 应为 true：{final_usage}")
        if not final_usage["remaining"] == 0:
            _fail(f"额度用尽后 remaining 应为 0：{final_usage}")
        reset_at = final_usage["resetAt"]
        if not reset_at or " " not in reset_at:
            _fail(f"resetAt 应可解析为“YYYY-MM-DD HH:MM”：{reset_at!r}")
        _ok(f"额度快照：exceeded={final_usage['exceeded']} resetAt={reset_at}（{final_usage['timezone']}）")

        # 7. 另一个账号额度独立
        print("—— 用例：额度按用户隔离 ——")
        email_b, auth_b = _register(client, base, api, "b")
        usage_b = client.get(f"{api}/usage/today", headers=auth_b).json()
        if usage_b["used"] != 0 or usage_b["exceeded"] is not False:
            _fail(f"新账号额度不应受其它账号影响：{usage_b}")
        created_b = client.post(f"{api}/conversations", json={"model": model_id}, headers=auth_b)
        conversation_b = created_b.json()["conversation"]["id"]
        status_b, event_b, text_b = _stream_once(
            client, api, auth_b, conversation_b, model_id, "请用一句话回复我"
        )
        if status_b != 200 or not text_b.strip():
            _fail(f"新账号应可正常对话：status={status_b} text={text_b[:80]!r}")
        _ok(f"账号隔离通过：{email_b} 可正常对话（used={event_b.get('usage', {}).get('used')}）")

    print("\n额度用例全部通过")


if __name__ == "__main__":
    main()
