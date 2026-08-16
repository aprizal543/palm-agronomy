from functools import lru_cache

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
    telegram_enabled: bool = False
    telegram_mode: str = "webhook"
    telegram_bot_token: SecretStr | None = Field(default=None, repr=False)
    telegram_webhook_secret: SecretStr | None = Field(default=None, repr=False)
    telegram_request_timeout_s: float = 10.0
    agent_provider: str = "deterministic"
    agent_model: str | None = None

    @property
    def migration_url(self) -> str:
        return self.migration_database_url or self.database_url

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
