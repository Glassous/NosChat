"""后端接口冒烟测试（需要后端与 PostgreSQL 已启动）。

用法：
    python tests/smoke_api.py --base-url http://127.0.0.1:9135
    python tests/smoke_api.py --email you@example.com --code 123456   # 已配置真实 SMTP 时

说明：
    - 未配置 SMTP 时依赖 AUTH_DEV_ECHO_CODE=true（/auth/send-code 直接回传验证码）；
    - 已配置真实 SMTP 时不会回传验证码，需用 --email 指定可收信邮箱并从邮箱读取验证码后经 --code 传入；
    - 默认使用时间戳生成唯一邮箱，可重复执行。
"""

from __future__ import annotations

import argparse
import json
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
    args = parser.parse_args()

    base = args.base_url.rstrip("/")
    api = f"{base}/api"
    email = args.email.strip() or f"smoke-{int(time.time())}@example.com"
    password = "smoke-pass-123"
    nickname = "冒烟测试"
    print(f"目标后端：{base}\n测试邮箱：{email}\n")

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

        # 2. 模型清单
        models = client.get(f"{api}/models")
        if models.status_code != 200:
            _fail(f"模型清单失败：{models.status_code} {models.text}")
        model_list = models.json()
        if not model_list:
            _fail("模型清单为空（请检查 server/config/models.json）")
        _ok(f"模型清单：{len(model_list)} 个，首个={model_list[0]['id']} latency={model_list[0]['latency']}")

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
        created = client.post(f"{api}/conversations", json={"model": "deepseek-r1"}, headers=auth)
        if created.status_code != 201:
            _fail(f"新建会话失败：{created.status_code} {created.text}")
        payload = created.json()
        conversation_id = payload["conversation"]["id"]
        if len(payload["messages"]) != 1 or payload["messages"][0]["type"] != "ai":
            _fail(f"欢迎消息异常：{payload['messages']}")
        _ok(f"新建会话：{conversation_id} 欢迎语={payload['messages'][0]['content'][:24]}…")

        # 8. 流式对话
        thinking, content, done = [], [], False
        with client.stream(
            "POST",
            f"{api}/chat/stream",
            headers=auth,
            json={"conversationId": conversation_id, "model": "deepseek-r1", "content": "帮我算一下 1+1"},
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
                elif event["type"] == "error":
                    _fail(f"流式对话返回错误：{event['message']}")

        if not done:
            _fail("未收到 done 事件")
        if not thinking:
            _fail("推理模型未返回 thinking 增量")
        if not content:
            _fail("未返回 content 增量")
        _ok(f"流式对话：thinking={len(''.join(thinking))} 字，content={len(''.join(content))} 字")

        # 9. 消息落库
        messages = client.get(f"{api}/conversations/{conversation_id}/messages", headers=auth)
        rows = messages.json()
        if len(rows) != 3:
            _fail(f"消息数量异常（期望 3）：{len(rows)}")
        assistant = rows[-1]
        if assistant["type"] != "ai" or not assistant["content"] or not assistant["thinking"]:
            _fail(f"助手消息落库异常：{assistant}")
        _ok(f"消息落库：{len(rows)} 条，thinkingSec={assistant['thinkingSec']}")

        # 10. 会话列表 / 重命名 / 删除
        listing = client.get(f"{api}/conversations", headers=auth).json()
        if len(listing) != 1 or listing[0]["id"] != conversation_id:
            _fail(f"会话列表异常：{listing}")
        renamed = client.patch(
            f"{api}/conversations/{conversation_id}", headers=auth, json={"title": "冒烟测试会话"}
        )
        if renamed.status_code != 200 or renamed.json()["title"] != "冒烟测试会话":
            _fail(f"重命名失败：{renamed.status_code} {renamed.text}")
        _ok("会话列表与重命名通过")

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

    print("\n全部冒烟用例通过")


if __name__ == "__main__":
    main()
