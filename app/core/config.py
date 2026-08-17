import re
from functools import lru_cache
from urllib.parse import urlsplit

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    app_name: str = "PalmAgronomy API"
    api_v1_prefix: str = "/api/v1"
    database_url: str = Field(
        default="postgresql+asyncpg://palm:palm@localhost:5432/palm",
        repr=False,
    )
    migration_database_url: str | None = Field(default=None, repr=False)
    db_pool_size: int = 5
    db_max_overflow: int = 5
    sql_echo: bool = False
    log_level: str = "INFO"
    json_logs: bool = False
    readiness_timeout_s: float = 5.0
    public_base_url: str | None = None
    railway_public_domain: str | None = None
    telegram_enabled: bool = False
    telegram_mode: str = "webhook"
    telegram_bot_token: SecretStr | None = Field(default=None, repr=False)
    telegram_webhook_secret: SecretStr | None = Field(default=None, repr=False)
    telegram_webhook_auto_register: bool = False
    telegram_webhook_max_connections: int = 40
    telegram_request_timeout_s: float = 10.0
    agent_provider: str = "deterministic"
    agent_model: str | None = None

    @property
    def migration_url(self) -> str:
        return self.migration_database_url or self.database_url

    @property
    def resolved_public_base_url(self) -> str | None:
        explicit_url = (self.public_base_url or "").strip().rstrip("/")
        if explicit_url:
            return explicit_url
        railway_domain = (self.railway_public_domain or "").strip().strip("/")
        if railway_domain:
            return f"https://{railway_domain}"
        return None

    @property
    def telegram_webhook_url(self) -> str | None:
        base_url = self.resolved_public_base_url
        if base_url is None:
            return None
        prefix = "/" + self.api_v1_prefix.strip("/")
        return f"{base_url}{prefix}/telegram/webhook"

    def validate_runtime(self) -> None:
        environment = self.app_env.casefold()
        mode = self.telegram_mode.casefold()
        if mode not in {"polling", "webhook"}:
            raise ValueError("TELEGRAM_MODE harus polling atau webhook")
        if self.telegram_enabled:
            token = (
                self.telegram_bot_token.get_secret_value().strip()
                if self.telegram_bot_token is not None
                else ""
            )
            if not token:
                raise ValueError("TELEGRAM_BOT_TOKEN wajib ketika Telegram aktif")
            if mode == "webhook":
                secret = (
                    self.telegram_webhook_secret.get_secret_value().strip()
                    if self.telegram_webhook_secret is not None
                    else ""
                )
                if not secret:
                    raise ValueError("TELEGRAM_WEBHOOK_SECRET wajib pada mode webhook")
                if not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", secret):
                    raise ValueError(
                        "TELEGRAM_WEBHOOK_SECRET hanya boleh berisi huruf, angka, _ dan -"
                    )
                if not 1 <= self.telegram_webhook_max_connections <= 100:
                    raise ValueError("TELEGRAM_WEBHOOK_MAX_CONNECTIONS harus antara 1 dan 100")
                if self.telegram_webhook_auto_register:
                    public_url = self.resolved_public_base_url
                    if public_url is None:
                        raise ValueError(
                            "PUBLIC_BASE_URL atau RAILWAY_PUBLIC_DOMAIN wajib untuk "
                            "registrasi webhook otomatis"
                        )
                    parsed_url = urlsplit(public_url)
                    if (
                        parsed_url.scheme != "https"
                        or not parsed_url.hostname
                        or parsed_url.username is not None
                        or parsed_url.password is not None
                        or parsed_url.query
                        or parsed_url.fragment
                        or parsed_url.path not in {"", "/"}
                    ):
                        raise ValueError("PUBLIC_BASE_URL harus berupa origin HTTPS publik")
                    if parsed_url.hostname in {"localhost", "127.0.0.1", "::1"}:
                        raise ValueError("PUBLIC_BASE_URL tidak boleh menggunakan localhost")
        if environment == "production" and self.sql_echo:
            raise ValueError("SQL_ECHO harus false pada production")
        if self.readiness_timeout_s <= 0 or self.readiness_timeout_s > 30:
            raise ValueError("READINESS_TIMEOUT_S harus lebih dari 0 dan maksimal 30")


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.migration_database_url is None:
        settings.migration_database_url = settings.database_url
    settings.validate_runtime()
    return settings
