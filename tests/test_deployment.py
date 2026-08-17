from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import SecretStr

from app.api.routes.health import liveness, readiness
from app.core.config import Settings
from app.core.observability import JsonLogFormatter
from app.core.version import APP_VERSION

ROOT = Path(__file__).parents[1]


def test_production_rejects_sql_echo() -> None:
    settings = Settings(_env_file=None, app_env="production", sql_echo=True)

    with pytest.raises(ValueError, match="SQL_ECHO"):
        settings.validate_runtime()


def test_enabled_webhook_requires_secret() -> None:
    settings = Settings(
        _env_file=None,
        telegram_enabled=True,
        telegram_mode="webhook",
        telegram_bot_token=SecretStr("token"),
        telegram_webhook_secret=None,
    )

    with pytest.raises(ValueError, match="TELEGRAM_WEBHOOK_SECRET"):
        settings.validate_runtime()


def test_polling_runtime_accepts_token_without_webhook_secret() -> None:
    settings = Settings(
        _env_file=None,
        telegram_enabled=True,
        telegram_mode="polling",
        telegram_bot_token=SecretStr("token"),
        telegram_webhook_secret=None,
    )

    settings.validate_runtime()


def test_deployment_artifacts_do_not_copy_environment_secret() -> None:
    dockerignore = (ROOT / ".dockerignore").read_text(encoding="utf-8")
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert ".env" in dockerignore
    assert "COPY .env" not in dockerfile
    assert "USER palm" in dockerfile


def test_app_version_is_single_source_of_truth() -> None:
    assert APP_VERSION == "0.9.0"


def test_json_formatter_is_available_for_container_logs() -> None:
    assert JsonLogFormatter.__name__ == "JsonLogFormatter"


@pytest.mark.asyncio
async def test_liveness_does_not_require_database() -> None:
    assert await liveness() == {"status": "alive", "version": APP_VERSION}


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_fails() -> None:
    class FailedSession:
        async def execute(self, _statement):
            raise RuntimeError("database unavailable")

    with pytest.raises(HTTPException) as exc_info:
        await readiness(FailedSession())

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Service belum siap"
