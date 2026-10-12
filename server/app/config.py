"""应用配置：全部通过环境变量注入，支持 server/.env 文件。"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# server/ 目录（config.py 位于 server/app/config.py）
BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """环境变量配置项。字段名即环境变量名（大小写不敏感）。"""

    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---- 应用 ----
    app_name: str = "NosChat API"
    app_version: str = "1.0.0"
    port: int = 9135
    debug: bool = False
    api_prefix: str = "/api"

    # ---- 数据库（PostgreSQL）----
    # 优先使用完整连接串 DATABASE_URL；未设置时由下面的 POSTGRES_* 分片拼装
    database_url: str = ""
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "noschat"
    postgres_password: str = "noschat"
    postgres_db: str = "noschat"
    db_echo: bool = False
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_connect_retries: int = 15
    db_connect_retry_interval: float = 2.0

    # ---- OpenAI 兼容接口（一个 base url + 一个 key + 多个 model）----
    openai_base_url: str = "https://api.openai.com/v1"
    openai_api_key: str = ""
    openai_timeout: float = 120.0
    openai_max_retries: int = 1
    # 是否遵循系统代理环境变量（HTTP_PROXY/HTTPS_PROXY）。
    # 默认 false：避免本机代理软件拦截对本地/内网模型服务的请求。
    openai_trust_env: bool = False

    # ---- 鉴权 ----
    jwt_secret: str = "please-change-this-secret"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 14

    # ---- 邮件（SMTP）----
    # 账号字段同时接受 SMTP_USERNAME / SMTP_USER，密码字段同时接受 SMTP_PASSWORD / SMTP_PASS
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_username: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_USERNAME", "SMTP_USER", "SMTP_EMAIL"),
    )
    smtp_password: str = Field(
        default="",
        validation_alias=AliasChoices("SMTP_PASSWORD", "SMTP_PASS", "SMTP_AUTH_CODE"),
    )
    # 发件地址：支持 "显示名 <地址>" 形式，也可只写地址并与 SMTP_FROM_NAME 组合
    smtp_from: str = ""
    smtp_from_name: str = "NosChat"
    smtp_starttls: bool = True
    smtp_ssl: bool = False
    smtp_timeout: float = 15.0
    # 未配置 SMTP 时，是否把验证码直接回传给调用方（仅用于本地开发/自测）
    auth_dev_echo_code: bool = False

    # ---- 邮箱验证码策略 ----
    code_length: int = 6
    code_ttl_seconds: int = 300
    code_resend_interval_seconds: int = 60
    code_max_attempts: int = 5

    # ---- 模型清单 ----
    models_config_path: str = str(BASE_DIR / "config" / "models.json")

    # ---- CORS ----
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        """逗号分隔的 CORS 白名单。"""
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def database_dsn(self) -> str:
        """最终使用的数据库连接串（DATABASE_URL 优先，否则由 POSTGRES_* 拼装）。"""
        if self.database_url.strip():
            return self.database_url.strip()
        user = quote(self.postgres_user, safe="")
        password = quote(self.postgres_password, safe="")
        database = quote(self.postgres_db, safe="")
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.postgres_host}:{self.postgres_port}/{database}"
        )

    @property
    def jwt_secret_is_default(self) -> bool:
        """是否仍在使用默认/空密钥（启动时给出警告）。"""
        return self.jwt_secret.strip() in {"", "please-change-this-secret"}

    @property
    def smtp_enabled(self) -> bool:
        """是否具备真实发信能力。"""
        return bool(self.smtp_host)

    @property
    def models_config_file(self) -> Path:
        path = Path(self.models_config_path)
        if not path.is_absolute():
            path = BASE_DIR / path
        return path

    @property
    def env_file_path(self) -> Path:
        """server/.env 路径（供 MODEL_* 等动态环境变量读取）。"""
        return BASE_DIR / ".env"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """进程级单例配置。"""
    return Settings()
