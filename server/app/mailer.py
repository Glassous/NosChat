"""SMTP 邮件发送（异步）。"""

from __future__ import annotations

import logging
from email.message import EmailMessage
from email.utils import formataddr

import aiosmtplib

from .config import get_settings

logger = logging.getLogger(__name__)


class MailError(RuntimeError):
    """邮件发送失败。"""


class MailNotConfigured(MailError):
    """未配置 SMTP。"""


def _sender() -> str:
    """构造 From 头：已包含显示名（如 `NosChat <a@b.com>`）时原样使用。"""
    settings = get_settings()
    raw = (settings.smtp_from or settings.smtp_username).strip()
    if not raw:
        return ""
    if "<" in raw and ">" in raw:
        return raw
    return formataddr((settings.smtp_from_name, raw))


def build_verification_email(code: str, ttl_minutes: int) -> tuple[str, str, str]:
    """返回 (subject, text, html)。"""
    settings = get_settings()
    subject = f"【{settings.smtp_from_name}】注册验证码：{code}"
    text = (
        f"你正在注册 {settings.smtp_from_name} 账号。\n\n"
        f"验证码：{code}\n"
        f"有效期：{ttl_minutes} 分钟\n\n"
        "如果这不是你的操作，请忽略本邮件。"
    )
    html = f"""\
<div style="font-family:-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;
            max-width:520px;margin:0 auto;padding:32px 24px;color:#1e293b;">
  <h2 style="margin:0 0 8px;font-size:20px;">{settings.smtp_from_name} 注册验证</h2>
  <p style="margin:0 0 20px;color:#64748b;font-size:14px;">请使用下方验证码完成注册，有效期 {ttl_minutes} 分钟。</p>
  <div style="background:linear-gradient(135deg,#667eea,#764ba2);border-radius:12px;padding:18px;
              text-align:center;color:#fff;font-size:30px;font-weight:700;letter-spacing:8px;">
    {code}
  </div>
  <p style="margin:20px 0 0;color:#94a3b8;font-size:12px;">如果这不是你的操作，请忽略本邮件。</p>
</div>"""
    return subject, text, html


async def send_email(to: str, subject: str, text: str, html: str | None = None) -> None:
    """发送邮件；未配置 SMTP 时抛出 MailNotConfigured。"""
    settings = get_settings()
    if not settings.smtp_enabled:
        raise MailNotConfigured("未配置 SMTP 服务器，无法发送邮件")

    message = EmailMessage()
    message["From"] = _sender()
    message["To"] = to
    message["Subject"] = subject
    message.set_content(text)
    if html:
        message.add_alternative(html, subtype="html")

    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username or None,
            password=settings.smtp_password or None,
            start_tls=settings.smtp_starttls and not settings.smtp_ssl,
            use_tls=settings.smtp_ssl,
            timeout=settings.smtp_timeout,
        )
    except aiosmtplib.SMTPAuthenticationError as exc:
        logger.error("SMTP 鉴权失败：%s", exc)
        raise MailError("邮件服务鉴权失败，请联系管理员") from exc
    except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPServerDisconnected, OSError) as exc:
        logger.error("SMTP 连接失败：%s", exc)
        raise MailError("无法连接邮件服务，请稍后重试") from exc
    except aiosmtplib.SMTPException as exc:
        logger.error("SMTP 发送失败：%s", exc)
        raise MailError("验证码邮件发送失败，请稍后重试") from exc


async def send_verification_code(to: str, code: str, ttl_seconds: int) -> None:
    """发送注册验证码邮件。"""
    subject, text, html = build_verification_email(code, max(1, ttl_seconds // 60))
    await send_email(to, subject, text, html)
