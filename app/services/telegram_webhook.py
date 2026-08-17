import logging
from urllib.parse import urlsplit

from app.core.config import Settings
from app.integrations.telegram import TelegramBotAPI

logger = logging.getLogger(__name__)


async def register_telegram_webhook(settings: Settings) -> bool:
    """Register the production webhook without logging credentials."""
    if not settings.telegram_enabled or settings.telegram_mode.casefold() != "webhook":
        return False
    if not settings.telegram_webhook_auto_register:
        logger.info("telegram_webhook_auto_register_disabled")
        return False
    if settings.telegram_bot_token is None or settings.telegram_webhook_secret is None:
        raise RuntimeError("Konfigurasi Telegram webhook belum lengkap")

    webhook_url = settings.telegram_webhook_url
    if webhook_url is None:
        raise RuntimeError("URL publik Telegram webhook belum tersedia")

    gateway = TelegramBotAPI(
        settings.telegram_bot_token.get_secret_value(), settings.telegram_request_timeout_s
    )
    registered = await gateway.set_webhook(
        url=webhook_url,
        secret_token=settings.telegram_webhook_secret.get_secret_value(),
        max_connections=settings.telegram_webhook_max_connections,
        drop_pending_updates=False,
    )
    if not registered:
        raise RuntimeError("Telegram menolak registrasi webhook")

    logger.info(
        "telegram_webhook_registered host=%s path=%s",
        urlsplit(webhook_url).hostname,
        urlsplit(webhook_url).path,
    )
    return True
