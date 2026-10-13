"""后端接口冒烟测试（需要后端与 PostgreSQL 已启动）。

用法：
    python tests/smoke_api.py --base-url http://127.0.0.1:9135
    python tests/smoke_api.py --email you@example.com --code 123456   # 已配置真实 SMTP 时

说明：
    - 未配置 SMTP 时依赖 AUTH_DEV_ECHO_CODE=true（/auth/send-code 直接回传验证码）；
    - 已配置真实 SMTP 时不会回传验证码，需用 --email 指定可收信邮箱并从邮箱读取验证码后经 --code 传入；
    - 默认使用时间戳生成唯一邮箱，可重复执行；
    - 限流用例会用一次性邮箱连续错误密码登录，阈值需与后端的
      LOGIN_RATE_LIMIT_PER_EMAIL 保持一致（可用 --login-limit 覆盖）。
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


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:9135")
    parser.add_argument("--email", default="", help="注册邮箱（已配置真实 SMTP 时必填，需可收信）")
    parser.add_argument("--code", default="", help="邮箱收到的验证码（真实 SMTP 场景使用）")
    parser.add_argument(
        "--login-limit",
        type=int,
        default=int(os.environ.get("LOGIN_RATE_LIMIT_PER_EMAIL", "5")),
        help="与后端 LOGIN_RATE_LIMIT_PER_EMAIL 保持一致（默认 5）",
    )
    parser.add_argument(
        "--expect-limit",
        type=int,
        default=int(os.environ.get("DAILY_OUTPUT_TOKEN_LIMIT", "100000")),
        help="与后端 DAILY_OUTPUT_TOKEN_LIMIT 保持一致（默认 100000）",
    )
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api = f"{base}/api"
    email = args.email.strip() or f"smoke-{int(time.time())}@example.com"
    password = "smoke-pass-123"
    nickname = "冒烟测试"
    login_limit_per_email = max(1, args.login_limit)
    quota_limit = max(1, args.expect_limit)
    print(f"目标后端：{base}\n测试邮箱：{email}\n额度上限：{quota_limit}\n")

    def _code_of(response: httpx.Response) -> str:
        """开发模式取回传验证码；真实 SMTP 场景用 --code 传入邮箱收到的验证码。"""
        dev = response.json().get("devCode")
        if not dev and not args.code.strip():
            _fail(
                "未拿到验证码：未配置 SMTP 时需 AUTH_DEV_ECHO_CODE=true；"
                "已配置真实 SMTP 时请用 --code 传入验证码"
            )
        return dev or args.code.strip()

    # trust_env=False：避免本机代理软件拦截 localhost 请求
    with httpx.Client(timeout=30.0, trust_env=False) as client:
        # 1. 健康检查
        health = client.get(f"{base}/health")
        if health.status_code != 200:
            _fail(f"健康检查失败：{health.status_code} {health.text}")
        _ok(f"健康检查：{health.json()}")
        redis_state = health.json().get("redis")
        if redis_state not in {"ok", "down", "disabled"}:
            _fail(f"/health 的 redis 字段取值异常：{redis_state!r}")
        _ok(f"Redis 状态：{redis_state}（down/disabled 时缓存直接回源、限流走进程内兜底）")

        # 2. 模型清单
        models = client.get(f"{api}/models")
        if models.status_code != 200:
            _fail(f"模型清单失败：{models.status_code} {models.text}")
        model_list = models.json()
        if not model_list:
            _fail("模型清单为空（请检查 server/.env 的 MODEL_* 或 server/config/models.json）")
        # 命中缓存不应改变响应内容
        if client.get(f"{api}/models").json() != model_list:
            _fail("两次 /api/models 响应不一致（缓存引入差异）")
        # 优先选用推理模型，以便校验思考链增量；没有则退化为首个模型
        reasoning_model = next((item for item in model_list if item.get("reasoning")), None)
        target_model = reasoning_model or model_list[0]
        model_id = target_model["id"]
        _ok(
            f"模型清单：{len(model_list)} 个，用例模型={model_id}"
            f"（reasoning={bool(reasoning_model)}，latency={target_model['latency']}）"
        )

        # 3. 发送验证码
        code_resp = client.post(f"{api}/auth/send-code", json={"email": email})
        if code_resp.status_code != 200:
            _fail(f"发送验证码失败：{code_resp.status_code} {code_resp.text}")
        dev_code = code_resp.json().get("devCode") or args.code.strip()
        if not dev_code:
            _fail(
                "未拿到验证码：未配置 SMTP 时需 AUTH_DEV_ECHO_CODE=true；"
                "已配置真实 SMTP 时请用 --code 传入邮箱收到的验证码"
            )
        _ok(f"发送验证码：{email}（验证码已获取）")

        # 4. 注册
        register = client.post(
            f"{api}/auth/register",
            json={"email": email, "code": dev_code, "nickname": nickname, "password": password},
        )
        if register.status_code != 201:
            _fail(f"注册失败：{register.status_code} {register.text}")
        token = register.json()["token"]
        auth = {"Authorization": f"Bearer {token}"}
        _ok(f"注册成功：user={register.json()['user']}")

        # 5. 当前用户
        me = client.get(f"{api}/auth/me", headers=auth)
        if me.status_code != 200 or me.json()["email"] != email:
            _fail(f"获取当前用户失败：{me.status_code} {me.text}")
        _ok("当前用户校验通过")

        # 6. 重复发送验证码应被限流
        again = client.post(f"{api}/auth/send-code", json={"email": email})
        if again.status_code not in (409, 429):
            _fail(f"重复注册/限流校验未生效：{again.status_code} {again.text}")
        _ok(f"重复发送验证码被正确拒绝：{again.status_code}")

        # 7. 新建会话
        created = client.post(f"{api}/conversations", json={"model": model_id}, headers=auth)
        if created.status_code != 201:
            _fail(f"新建会话失败：{created.status_code} {created.text}")
        payload = created.json()
        conversation_id = payload["conversation"]["id"]
        if payload["messages"]:
            _fail(f"新会话不应包含开场白消息：{payload['messages']}")
        if payload["conversation"]["preview"] != "开始新的对话…":
            _fail(f"新会话预览异常：{payload['conversation']['preview']}")
        _ok(f"新建会话：{conversation_id}（无开场白，预览={payload['conversation']['preview']}）")

        # 8. 流式对话
        thinking, content, done, done_event = [], [], False, None
        with client.stream(
            "POST",
            f"{api}/chat/stream",
            headers=auth,
            json={"conversationId": conversation_id, "model": model_id, "content": "用一句话介绍你自己"},
        ) as response:
            if response.status_code != 200:
                _fail(f"流式对话失败：{response.status_code} {response.read()[:200]}")
            for line in response.iter_lines():
                if not line.startswith("data: "):
                    continue
                event = json.loads(line[6:])
                if event["type"] == "thinking":
                    thinking.append(event["delta"])
                elif event["type"] == "content":
                    content.append(event["delta"])
                elif event["type"] == "done":
                    done = True
                    done_event = event
                elif event["type"] == "error":
                    _fail(f"流式对话返回错误：{event['message']}")

        if not done:
            _fail("未收到 done 事件")
        if not content:
            _fail("未返回 content 增量")
        if reasoning_model and not thinking:
            _fail("推理模型未返回 thinking 增量")
        _ok(
            f"流式对话（{model_id}）：thinking={len(''.join(thinking))} 字，"
            f"content={len(''.join(content))} 字"
        )

        # 8.1 done 事件必须带回后端测量的思考耗时、后端派生的预览与额度快照
        thinking_sec = done_event.get("thinkingSec")
        if not isinstance(thinking_sec, int) or thinking_sec < 0:
            _fail(f"done 事件应带非负整数 thinkingSec：{thinking_sec!r}")
        if reasoning_model and thinking_sec <= 0:
            _fail(f"推理模型的 thinkingSec 应大于 0：{thinking_sec}")
        if not isinstance(done_event.get("preview"), str) or not done_event["preview"]:
            _fail(f"done 事件应带后端派生的 preview：{done_event.get('preview')!r}")
        usage = done_event.get("usage")
        if not isinstance(usage, dict) or not usage:
            _fail(f"done 事件应带 usage 额度快照：{usage!r}")
        if usage.get("limit") != quota_limit:
            _fail(f"额度上限应为 {quota_limit}：{usage.get('limit')}")
        if not isinstance(usage.get("used"), int) or usage["used"] <= 0:
            _fail(f"本轮结束后 used 应大于 0：{usage.get('used')}")
        _ok(
            f"done 事件：thinkingSec={thinking_sec} preview={done_event['preview'][:16]!r} "
            f"usage={usage.get('used')}/{usage.get('limit')}（estimated={usage.get('estimated')}）"
        )

        # 9. 消息落库
        messages = client.get(f"{api}/conversations/{conversation_id}/messages", headers=auth)
        rows = messages.json()
        if len(rows) != 2:
            _fail(f"消息数量异常（期望 2：用户 + 助手，无开场白）：{len(rows)}")
        assistant = rows[-1]
        if assistant["type"] != "ai" or not assistant["content"]:
            _fail(f"助手消息落库异常：{assistant}")
        if reasoning_model and not assistant["thinking"]:
            _fail("推理模型的思考内容未落库")
        _ok(f"消息落库：{len(rows)} 条，thinkingSec={assistant['thinkingSec']}")

        # 9.1 落库的思考耗时必须与 done 事件一致（前端据此展示，刷新前后不变）
        if assistant["thinkingSec"] != thinking_sec:
            _fail(
                f"落库 thinkingSec（{assistant['thinkingSec']}）与 done 事件（{thinking_sec}）不一致"
            )

        # 9.2 GET /api/usage/today 的 used 必须与 done 事件一致（额度可持久、可查询）
        usage_resp = client.get(f"{api}/usage/today", headers=auth)
        if usage_resp.status_code != 200:
            _fail(f"查询额度失败：{usage_resp.status_code} {usage_resp.text}")
        usage_now = usage_resp.json()
        if usage_now["used"] != usage["used"]:
            _fail(f"/api/usage/today 的 used（{usage_now['used']}）与 done 事件（{usage['used']}）不一致")
        if usage_now["limit"] != quota_limit or usage_now["exceeded"] is not False:
            _fail(f"额度快照异常：{usage_now}")
        if usage_now["remaining"] != max(0, usage_now["limit"] - usage_now["used"]):
            _fail(f"remaining 计算异常：{usage_now}")
        _ok(
            f"额度查询一致：used={usage_now['used']} remaining={usage_now['remaining']} "
            f"resetAt={usage_now['resetAt']}（{usage_now['timezone']}）"
        )

        # 10. 会话列表 / 重命名 / 删除
        listing = client.get(f"{api}/conversations", headers=auth).json()
        if len(listing) != 1 or listing[0]["id"] != conversation_id:
            _fail(f"会话列表异常：{listing}")

        # 10.1 标记已读必须落库，且不得把 updatedAt 推高（否则会话会跳到列表顶部）
        updated_before = listing[0]["updatedAt"]
        marked = client.patch(
            f"{api}/conversations/{conversation_id}", headers=auth, json={"unread": True}
        )
        if marked.status_code != 200 or marked.json()["unread"] is not True:
            _fail(f"标记未读失败：{marked.status_code} {marked.text}")
        if marked.json()["updatedAt"] != updated_before:
            _fail(
                f"标记未读不应改变 updatedAt：{updated_before} -> {marked.json()['updatedAt']}"
            )
        read = client.patch(
            f"{api}/conversations/{conversation_id}", headers=auth, json={"unread": False}
        )
        if read.status_code != 200 or read.json()["unread"] is not False:
            _fail(f"标记已读失败：{read.status_code} {read.text}")
        if read.json()["updatedAt"] != updated_before:
            _fail(
                f"标记已读不应改变 updatedAt：{updated_before} -> {read.json()['updatedAt']}"
            )
        if client.get(f"{api}/conversations", headers=auth).json()[0]["unread"] is not False:
            _fail("已读状态未落库（刷新后仍为未读）")
        _ok("已读状态已落库，且未推高 updatedAt")

        renamed = client.patch(
            f"{api}/conversations/{conversation_id}", headers=auth, json={"title": "冒烟测试会话"}
        )
        if renamed.status_code != 200 or renamed.json()["title"] != "冒烟测试会话":
            _fail(f"重命名失败：{renamed.status_code} {renamed.text}")
        # 重命名属于内容变化，应当推高 updatedAt
        if renamed.json()["updatedAt"] == updated_before:
            _fail("重命名应更新 updatedAt")
        _ok("会话列表、已读落库与重命名通过")

        deleted = client.delete(f"{api}/conversations/{conversation_id}", headers=auth)
        if deleted.status_code != 204:
            _fail(f"删除会话失败：{deleted.status_code}")
        if client.get(f"{api}/conversations", headers=auth).json():
            _fail("删除后会话列表应为空")
        _ok("删除会话通过")

        # 11. 登录
        login = client.post(f"{api}/auth/login", json={"email": email, "password": password})
        if login.status_code != 200:
            _fail(f"登录失败：{login.status_code} {login.text}")
        bad = client.post(f"{api}/auth/login", json={"email": email, "password": "wrong-pass"})
        if bad.status_code != 401:
            _fail(f"错误密码应返回 401：{bad.status_code}")
        _ok("登录与密码校验通过")

        # 12. 未授权访问
        unauth = client.get(f"{api}/conversations")
        if unauth.status_code != 401:
            _fail(f"未授权访问应返回 401：{unauth.status_code}")
        _ok("未授权访问拦截通过")

        # 13. 验证码登录：未注册邮箱自动注册，昵称留空则使用邮箱
        code_email = f"smoke-code-{int(time.time())}@example.com"
        login_code_resp = client.post(
            f"{api}/auth/send-code", json={"email": code_email, "purpose": "login"}
        )
        if login_code_resp.status_code != 200:
            _fail(f"登录验证码发送失败：{login_code_resp.status_code} {login_code_resp.text}")
        auto = client.post(
            f"{api}/auth/login-code",
            json={"email": code_email, "code": _code_of(login_code_resp), "nickname": ""},
        )
        if auto.status_code != 200:
            _fail(f"验证码登录失败：{auto.status_code} {auto.text}")
        auto_data = auto.json()
        if not auto_data.get("isNewUser"):
            _fail(f"未标记为自动注册：{auto_data}")
        if auto_data["user"]["nickname"] != code_email:
            _fail(f"昵称应回退为邮箱，实际为：{auto_data['user']['nickname']}")
        auto_auth = {"Authorization": f"Bearer {auto_data['token']}"}
        if client.get(f"{api}/auth/me", headers=auto_auth).status_code != 200:
            _fail("自动注册账号的令牌不可用")
        _ok(f"验证码登录自动注册：nickname={auto_data['user']['nickname']}")

        # 13.1 昵称设置：可修改；留空则回退为邮箱
        updated = client.patch(
            f"{api}/auth/me", headers=auto_auth, json={"nickname": "自动注册用户"}
        )
        if updated.status_code != 200 or updated.json()["nickname"] != "自动注册用户":
            _fail(f"昵称更新失败：{updated.status_code} {updated.text}")
        cleared = client.patch(f"{api}/auth/me", headers=auto_auth, json={"nickname": ""})
        if cleared.status_code != 200 or cleared.json()["nickname"] != code_email:
            _fail(f"清空昵称应回退为邮箱：{cleared.status_code} {cleared.text}")
        _ok("昵称设置：可更新，留空回退为邮箱")

        # 14. 验证码登录：已注册邮箱不新建账号、也不覆盖昵称
        existing_code_resp = client.post(
            f"{api}/auth/send-code", json={"email": email, "purpose": "login"}
        )
        if existing_code_resp.status_code != 200:
            _fail(f"已注册邮箱登录验证码发送失败：{existing_code_resp.status_code} {existing_code_resp.text}")
        existing = client.post(
            f"{api}/auth/login-code",
            json={
                "email": email,
                "code": _code_of(existing_code_resp),
                "nickname": "不应生效的昵称",
            },
        )
        if existing.status_code != 200:
            _fail(f"已注册邮箱验证码登录失败：{existing.status_code} {existing.text}")
        if existing.json().get("isNewUser") or existing.json()["user"]["nickname"] != nickname:
            _fail(f"已注册邮箱不应被改动：{existing.json()}")
        _ok("已注册邮箱验证码登录：未新建账号、昵称未被覆盖")

        # 15. 找回密码：新密码可登录，旧密码与旧令牌全部失效
        reset_code_resp = client.post(
            f"{api}/auth/send-code", json={"email": email, "purpose": "reset"}
        )
        if reset_code_resp.status_code != 200:
            _fail(f"重置密码验证码发送失败：{reset_code_resp.status_code} {reset_code_resp.text}")
        new_password = "smoke-pass-456"
        reset = client.post(
            f"{api}/auth/reset-password",
            json={"email": email, "code": _code_of(reset_code_resp), "password": new_password},
        )
        if reset.status_code != 200:
            _fail(f"重置密码失败：{reset.status_code} {reset.text}")
        if client.post(f"{api}/auth/login", json={"email": email, "password": password}).status_code != 401:
            _fail("重置后旧密码仍可登录")
        if client.post(f"{api}/auth/login", json={"email": email, "password": new_password}).status_code != 200:
            _fail("重置后新密码无法登录")
        if client.get(f"{api}/auth/me", headers=auth).status_code != 401:
            _fail("重置密码后旧令牌未失效")
        reset_auth = {"Authorization": f"Bearer {reset.json()['token']}"}
        if client.get(f"{api}/auth/me", headers=reset_auth).status_code != 200:
            _fail("重置密码返回的新令牌不可用")
        _ok("找回密码：新密码可用，旧密码与旧令牌已失效")

        # 16. 验证码用途校验
        if client.post(f"{api}/auth/send-code", json={"email": email, "purpose": "register"}).status_code != 409:
            _fail("已注册邮箱不应允许注册用途验证码")
        unknown_email = f"nobody-{int(time.time())}@example.com"
        if client.post(f"{api}/auth/send-code", json={"email": unknown_email, "purpose": "reset"}).status_code != 404:
            _fail("未注册邮箱不应允许重置密码验证码")
        _ok("验证码用途校验通过（register 需未注册 / reset 需已注册）")

        # 17. 登出：令牌版本 +1，该账号此前签发的所有令牌立即失效
        #     用独立账号，避免与前面用例共享同一邮箱的登录限流额度
        #     （登出会作废该账号的所有令牌，故最后仍可安全地重新登录验证）
        logout_email = f"smoke-logout-{int(time.time())}@example.com"
        logout_sent = client.post(f"{api}/auth/send-code", json={"email": logout_email})
        if logout_sent.status_code != 200:
            _fail(f"登出用例发送验证码失败：{logout_sent.status_code} {logout_sent.text}")
        logout_register = client.post(
            f"{api}/auth/register",
            json={
                "email": logout_email,
                "code": _code_of(logout_sent),
                "nickname": "登出用例",
                "password": password,
            },
        )
        if logout_register.status_code != 201:
            _fail(f"登出用例注册失败：{logout_register.status_code} {logout_register.text}")
        logout_token = logout_register.json()["token"]
        logout_auth = {"Authorization": f"Bearer {logout_token}"}
        if client.get(f"{api}/auth/me", headers=logout_auth).status_code != 200:
            _fail("登出前令牌应可用")

        logged_out = client.post(f"{api}/auth/logout", headers=logout_auth)
        if logged_out.status_code != 204:
            _fail(f"登出失败：{logged_out.status_code} {logged_out.text}")
        if client.get(f"{api}/auth/me", headers=logout_auth).status_code != 401:
            _fail("登出后旧令牌仍然可用（服务端未真正撤销）")
        if client.get(f"{api}/conversations", headers=logout_auth).status_code != 401:
            _fail("登出后旧令牌仍可访问业务接口")

        again = client.post(f"{api}/auth/login", json={"email": logout_email, "password": password})
        if again.status_code != 200:
            _fail(f"登出后重新登录失败：{again.status_code} {again.text}")
        fresh_auth = {"Authorization": f"Bearer {again.json()['token']}"}
        if client.get(f"{api}/auth/me", headers=fresh_auth).status_code != 200:
            _fail("登出后重新登录返回的新令牌不可用")
        _ok("登出：旧令牌全部失效，重新登录可用")

        # 18. 限流：同一邮箱连续错误密码应在阈值后返回 429 + Retry-After
        #     （放在最后，避免消耗 IP 配额影响前面依赖登录的用例）
        throttle_email = f"throttle-{int(time.time())}@example.com"
        last_status, last_retry = 0, None
        for _ in range(login_limit_per_email + 1):
            attempt = client.post(
                f"{api}/auth/login", json={"email": throttle_email, "password": "wrong-pass"}
            )
            last_status = attempt.status_code
            last_retry = attempt.headers.get("Retry-After")
        if last_status != 429:
            _fail(f"连续错误密码应被限流（期望 429，实际 {last_status}）")
        if not last_retry or not last_retry.isdigit():
            _fail(f"限流响应应带 Retry-After 头：{last_retry!r}")
        _ok(f"登录限流生效：第 {login_limit_per_email + 1} 次返回 429，Retry-After={last_retry}s")

    print("\n全部冒烟用例通过")


if __name__ == "__main__":
    main()
