"""Inspect or manage Telegram webhook registration without exposing credentials."""

import argparse
import asyncio
import json

from app.core.config import get_settings
from app.integrations.telegram import TelegramBotAPI


async def main(action: str, drop_pending_updates: bool) -> None:
    settings = get_settings()
    if settings.telegram_bot_token is None:
        raise RuntimeError("TELEGRAM_BOT_TOKEN belum diisi")

    gateway = TelegramBotAPI(
        settings.telegram_bot_token.get_secret_value(), settings.telegram_request_timeout_s
    )
    if action == "info":
        info = await gateway.get_webhook_info()
        safe_info = {
            "url": info.get("url"),
            "pending_update_count": info.get("pending_update_count"),
            "last_error_date": info.get("last_error_date"),
            "last_error_message": info.get("last_error_message"),
            "max_connections": info.get("max_connections"),
            "allowed_updates": info.get("allowed_updates"),
        }
        print(json.dumps(safe_info, ensure_ascii=False, indent=2))
        return

    if action == "delete":
        deleted = await gateway.delete_webhook(drop_pending_updates=drop_pending_updates)
        print("Webhook dihapus." if deleted else "Telegram menolak penghapusan webhook.")
        return

    if settings.telegram_webhook_secret is None or settings.telegram_webhook_url is None:
        raise RuntimeError("URL publik atau TELEGRAM_WEBHOOK_SECRET belum tersedia")
    registered = await gateway.set_webhook(
        url=settings.telegram_webhook_url,
        secret_token=settings.telegram_webhook_secret.get_secret_value(),
        max_connections=settings.telegram_webhook_max_connections,
        drop_pending_updates=drop_pending_updates,
    )
    print("Webhook terdaftar." if registered else "Telegram menolak registrasi webhook.")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Kelola Telegram webhook PalmAgronomy")
    parser.add_argument("action", choices=("info", "set", "delete"))
    parser.add_argument(
        "--drop-pending-updates",
        action="store_true",
        help="Hapus update yang belum diproses. Gunakan hanya jika memang diinginkan.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    asyncio.run(main(arguments.action, arguments.drop_pending_updates))
