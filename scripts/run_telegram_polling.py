"""Development adapter for Telegram long polling. Do not run beside webhook mode."""

import asyncio
import logging

from app.core.config import get_settings
from app.core.observability import configure_logging
from app.db.session import SessionLocal, engine
from app.integrations.telegram import TelegramBotAPI
from app.schemas.telegram import TelegramUpdate
from app.services.telegram_agent import TelegramAgentService

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    configure_logging(level=settings.log_level, json_logs=settings.json_logs)
    if not settings.telegram_enabled:
        raise RuntimeError("Set TELEGRAM_ENABLED=true terlebih dahulu")
    if settings.telegram_mode.lower() != "polling":
        raise RuntimeError("Set TELEGRAM_MODE=polling untuk menjalankan script ini")
    if settings.telegram_bot_token is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi")

    gateway = TelegramBotAPI(
        settings.telegram_bot_token.get_secret_value(), settings.telegram_request_timeout_s
    )
    await gateway.prepare_polling()
    logger.info("Telegram polling aktif. Tekan Ctrl+C untuk berhenti.")
    offset: int | None = None
    try:
        while True:
            updates = await gateway.get_updates(offset)
            for raw_update in updates:
                update = TelegramUpdate.model_validate(raw_update)
                async with SessionLocal() as session:
                    try:
                        result = await TelegramAgentService(session, gateway).handle(update)
                        logger.info("update_id=%s status=%s", update.update_id, result.status)
                    except Exception:
                        logger.exception("update_failed update_id=%s", update.update_id)
                offset = update.update_id + 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Telegram polling dihentikan.")
