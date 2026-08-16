from typing import Protocol

import httpx

from app.schemas.telegram import InlineKeyboardMarkup


class TelegramGateway(Protocol):
    async def send_message(
        self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None
    ) -> None: ...

    async def answer_callback(self, callback_query_id: str, text: str) -> None: ...


class TelegramBotAPI:
    def __init__(self, token: str, timeout_s: float = 10.0):
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.timeout_s = timeout_s

    async def _post(self, method: str, payload: dict, request_timeout_s: float | None = None):
        timeout = request_timeout_s if request_timeout_s is not None else self.timeout_s
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(f"{self.base_url}/{method}", json=payload)
            response.raise_for_status()
            body = response.json()
            if not body.get("ok"):
                raise RuntimeError(f"Telegram Bot API menolak {method}")
            return body.get("result")

    async def send_message(
        self, chat_id: int, text: str, reply_markup: InlineKeyboardMarkup | None = None
    ) -> None:
        payload: dict = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup.model_dump(mode="json")
        await self._post("sendMessage", payload)

    async def answer_callback(self, callback_query_id: str, text: str) -> None:
        await self._post(
            "answerCallbackQuery", {"callback_query_id": callback_query_id, "text": text}
        )

    async def prepare_polling(self) -> None:
        # Telegram does not allow getUpdates while a webhook is active.
        await self._post("deleteWebhook", {"drop_pending_updates": False})

    async def get_updates(self, offset: int | None, timeout_s: int = 30) -> list[dict]:
        payload: dict = {
            "timeout": timeout_s,
            "allowed_updates": ["message", "callback_query"],
        }
        if offset is not None:
            payload["offset"] = offset
        # The HTTP read timeout must exceed Telegram's long-poll timeout.
        return (
            await self._post(
                "getUpdates", payload, request_timeout_s=max(self.timeout_s, timeout_s + 5.0)
            )
            or []
        )
