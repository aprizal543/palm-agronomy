import json
from pathlib import Path

import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.integrations.telegram import TelegramBotAPI

ROOT = Path(__file__).parents[1]


def webhook_settings(**overrides) -> Settings:
    values = {
        "telegram_enabled": True,
        "telegram_mode": "webhook",
        "telegram_bot_token": SecretStr("bot-token"),
        "telegram_webhook_secret": SecretStr("valid_secret-123"),
        "telegram_webhook_auto_register": True,
        "public_base_url": "https://palm.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_webhook_url_uses_public_base_url() -> None:
    settings = webhook_settings()
    settings.validate_runtime()

    assert settings.telegram_webhook_url == (
        "https://palm.example.com/api/v1/telegram/webhook"
    )


def test_webhook_url_can_use_railway_domain() -> None:
    settings = webhook_settings(
        public_base_url=None, railway_public_domain="palm-production.up.railway.app"
    )
    settings.validate_runtime()

    assert settings.telegram_webhook_url == (
        "https://palm-production.up.railway.app/api/v1/telegram/webhook"
    )


def test_auto_registration_rejects_non_https_origin() -> None:
    settings = webhook_settings(public_base_url="http://palm.example.com")

    with pytest.raises(ValueError, match="HTTPS publik"):
        settings.validate_runtime()


def test_webhook_secret_rejects_unsupported_characters() -> None:
    settings = webhook_settings(telegram_webhook_secret=SecretStr("secret with spaces"))

    with pytest.raises(ValueError, match="huruf, angka"):
        settings.validate_runtime()


@pytest.mark.asyncio
async def test_gateway_registers_webhook_with_safe_payload() -> None:
    calls: list[tuple[str, dict]] = []
    gateway = TelegramBotAPI("token")

    async def fake_post(method: str, payload: dict, request_timeout_s=None):
        calls.append((method, payload))
        return True

    gateway._post = fake_post  # type: ignore[method-assign]
    result = await gateway.set_webhook(
        "https://palm.example.com/api/v1/telegram/webhook",
        "valid_secret-123",
        max_connections=20,
    )

    assert result is True
    assert calls == [
        (
            "setWebhook",
            {
                "url": "https://palm.example.com/api/v1/telegram/webhook",
                "secret_token": "valid_secret-123",
                "max_connections": 20,
                "drop_pending_updates": False,
                "allowed_updates": ["message", "callback_query"],
            },
        )
    ]


def test_railway_runs_migration_before_start_and_checks_readiness() -> None:
    config = json.loads((ROOT / "railway.json").read_text(encoding="utf-8"))
    deploy = config["deploy"]

    assert deploy["preDeployCommand"] == ["python -m alembic upgrade head"]
    assert deploy["healthcheckPath"] == "/api/v1/health/ready"
    assert "$PORT" in deploy["startCommand"]
    assert deploy["restartPolicyType"] == "ON_FAILURE"
