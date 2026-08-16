import secrets

from fastapi import APIRouter, Header, HTTPException, status

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.integrations.telegram import TelegramBotAPI
from app.schemas.telegram import TelegramUpdate, TelegramWebhookResult
from app.services.telegram_agent import TelegramAgentService

router = APIRouter()


@router.post("/webhook", response_model=TelegramWebhookResult)
async def telegram_webhook(
    payload: TelegramUpdate,
    session: SessionDep,
    secret_header: str | None = Header(default=None, alias="X-Telegram-Bot-Api-Secret-Token"),
):
    settings = get_settings()
    if not settings.telegram_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Telegram adapter belum diaktifkan",
        )
    if settings.telegram_bot_token is None or settings.telegram_webhook_secret is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Konfigurasi Telegram belum lengkap",
        )
    expected = settings.telegram_webhook_secret.get_secret_value()
    if secret_header is None or not secrets.compare_digest(secret_header, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Secret webhook salah")

    gateway = TelegramBotAPI(
        settings.telegram_bot_token.get_secret_value(), settings.telegram_request_timeout_s
    )
    return await TelegramAgentService(session, gateway).handle(payload)
