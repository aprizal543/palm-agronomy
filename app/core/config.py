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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.migration_database_url is None:
        settings.migration_database_url = settings.database_url
    return settings
