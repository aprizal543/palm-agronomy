"""Development adapter for Telegram long polling. Do not run beside webhook mode."""

import asyncio
import logging

import httpx
from pydantic import ValidationError

from app.core.config import get_settings
from app.db.session import SessionLocal, engine
from app.integrations.telegram import TelegramBotAPI
from app.schemas.telegram import TelegramUpdate
from app.services.telegram_agent import TelegramAgentService

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)
MAX_UPDATE_ATTEMPTS = 3
# httpx logs the complete Telegram Bot API URL, which contains the bot token.
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


async def main() -> None:
    settings = get_settings()
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
    failure_counts: dict[int, int] = {}
    try:
        while True:
            try:
                updates = await gateway.get_updates(offset)
            except httpx.TimeoutException:
                logger.warning("Polling timeout; mencoba kembali.")
                continue
            except httpx.HTTPError as exc:
                logger.warning(
                    "Jaringan Telegram bermasalah (%s); retry 3 detik.", type(exc).__name__
                )
                await asyncio.sleep(3)
                continue
            for raw_update in updates:
                try:
                    update = TelegramUpdate.model_validate(raw_update)
                except ValidationError:
                    raw_update_id = raw_update.get("update_id")
                    logger.exception("Payload Telegram tidak valid; update dilewati.")
                    if isinstance(raw_update_id, int):
                        offset = raw_update_id + 1
                    continue
                async with SessionLocal() as session:
                    try:
                        result = await TelegramAgentService(session, gateway).handle(update)
                        logger.info("update_id=%s status=%s", update.update_id, result.status)
                    except Exception:
                        attempt = failure_counts.get(update.update_id, 0) + 1
                        failure_counts[update.update_id] = attempt
                        logger.exception(
                            "Gagal memproses update_id=%s (percobaan %s/%s)",
                            update.update_id,
                            attempt,
                            MAX_UPDATE_ATTEMPTS,
                        )
                        if attempt >= MAX_UPDATE_ATTEMPTS:
                            logger.error(
                                "update_id=%s tetap gagal dan dilewati setelah %s percobaan; "
                                "detail tersimpan di audit database.",
                                update.update_id,
                                MAX_UPDATE_ATTEMPTS,
                            )
                            failure_counts.pop(update.update_id, None)
                            offset = update.update_id + 1
                            continue
                        await asyncio.sleep(3)
                        # Do not acknowledge this update. Fetch it again before newer updates.
                        break
                    else:
                        failure_counts.pop(update.update_id, None)
                        offset = update.update_id + 1
    finally:
        await engine.dispose()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Telegram polling dihentikan.")
