import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import AgronomyToolRegistry
from app.integrations.telegram import TelegramGateway
from app.repositories.telegram import TelegramRepository
from app.schemas.telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    TelegramCallbackQuery,
    TelegramMessage,
    TelegramUpdate,
    TelegramWebhookResult,
)

WELCOME = (
    "Halo! Saya PalmAgronomy Agent. Kirim lokasi Telegram Anda untuk mencari blok kebun. "
    "Hasil geometri dan luas selalu berasal dari PostGIS."
)
HELP = (
    "Perintah yang tersedia:\n"
    "• /start — mulai atau perbarui profil Telegram\n"
    "• /help — tampilkan bantuan\n"
    "• kirim Location — identifikasi blok berdasarkan GPS dan akurasinya"
)


def safe_error_label(exc: Exception) -> str:
    """Return an audit-safe error label without SQL, payloads, or credentials."""
    original = getattr(exc, "orig", None)
    sqlstate = getattr(original, "sqlstate", None)
    if sqlstate:
        return f"{type(exc).__name__}[sqlstate={sqlstate}]"
    return type(exc).__name__


class TelegramAgentService:
    def __init__(self, session: AsyncSession, gateway: TelegramGateway):
        self.session = session
        self.gateway = gateway
        self.repository = TelegramRepository(session)
        self.tools = AgronomyToolRegistry(session)

    async def handle(self, update: TelegramUpdate) -> TelegramWebhookResult:
        claimed = await self.repository.claim_update(
            update_id=update.update_id,
            chat_id=update.chat_id,
            telegram_user_id=update.telegram_user_id,
            update_kind=update.kind,
            raw_update=update.model_dump(mode="json", by_alias=True, exclude_none=True),
        )
        if not claimed:
            await self.session.rollback()
            return TelegramWebhookResult(status="duplicate", update_id=update.update_id)

        # Persist the idempotency key before any external Telegram call.
        await self.session.commit()
        trace_id = uuid4()
        started = time.perf_counter()
        intent = self._detect_intent(update)
        self.repository.add_audit(
            trace_id=trace_id,
            update_id=update.update_id,
            chat_id=update.chat_id,
            telegram_user_id=update.telegram_user_id,
            event_type="intent",
            intent=intent,
            status="started",
        )
        try:
            if update.message is not None:
                await self._handle_message(update, update.message, trace_id)
            elif update.callback_query is not None:
                await self._handle_callback(update, update.callback_query, trace_id)
            else:
                await self.repository.mark_update(update.update_id, "processed")
                await self.session.commit()
                return TelegramWebhookResult(status="ignored", update_id=update.update_id)

            self.repository.add_audit(
                trace_id=trace_id,
                update_id=update.update_id,
                chat_id=update.chat_id,
                telegram_user_id=update.telegram_user_id,
                event_type="intent",
                intent=intent,
                status="succeeded",
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            await self.repository.mark_update(update.update_id, "processed")
            await self.session.commit()
            return TelegramWebhookResult(status="processed", update_id=update.update_id)
        except Exception as exc:
            await self.session.rollback()
            error_label = safe_error_label(exc)
            await self.repository.mark_update(update.update_id, "failed", error_label)
            self.repository.add_audit(
                trace_id=trace_id,
                update_id=update.update_id,
                chat_id=update.chat_id,
                telegram_user_id=update.telegram_user_id,
                event_type="intent",
                intent=intent,
                status="failed",
                latency_ms=int((time.perf_counter() - started) * 1000),
                error_message=error_label,
            )
            await self.session.commit()
            raise

    @staticmethod
    def _detect_intent(update: TelegramUpdate) -> str:
        if update.callback_query is not None:
            return "confirm_location"
        if update.message and update.message.location:
            return "resolve_location"
        text = (update.message.text if update.message else "") or ""
        if text.split(maxsplit=1)[0].lower() in {"/start", "/help"}:
            return text.split(maxsplit=1)[0].lower().removeprefix("/")
        return "unknown"

    async def _ensure_identity(self, message: TelegramMessage) -> None:
        sender = message.from_user
        if sender is None:
            raise ValueError("Pesan Telegram tidak memiliki pengirim")
        user = await self.repository.upsert_user(
            sender.id, sender.display_name, sender.language_code or "id"
        )
        await self.repository.upsert_conversation(message.chat.id, sender.id, user.id)

    async def _handle_message(
        self, update: TelegramUpdate, message: TelegramMessage, trace_id: UUID
    ) -> None:
        await self._ensure_identity(message)
        if message.location is not None:
            await self._handle_location(update, message, trace_id)
            return

        command = (message.text or "").split(maxsplit=1)[0].lower()
        if command == "/start":
            await self.gateway.send_message(message.chat.id, WELCOME)
        elif command == "/help":
            await self.gateway.send_message(message.chat.id, HELP)
        else:
            await self.gateway.send_message(
                message.chat.id,
                "Saya belum memahami pesan itu. Ketik /help atau kirim Location Telegram.",
            )

    async def _handle_location(
        self, update: TelegramUpdate, message: TelegramMessage, trace_id: UUID
    ) -> None:
        location = message.location
        assert location is not None
        arguments = {
            "longitude": location.longitude,
            "latitude": location.latitude,
            "accuracy_m": location.horizontal_accuracy or 0.0,
        }
        tool_started = time.perf_counter()
        result = await self.tools.execute("resolve_block_by_location", **arguments)
        self.repository.add_audit(
            trace_id=trace_id,
            update_id=update.update_id,
            chat_id=message.chat.id,
            telegram_user_id=update.telegram_user_id,
            event_type="tool_call",
            intent="resolve_location",
            tool_name="resolve_block_by_location",
            input_data=arguments,
            output_data=result,
            status="succeeded",
            latency_ms=int((time.perf_counter() - tool_started) * 1000),
        )

        status = result["status"]
        candidates = result["candidates"]
        if status == "not_found":
            await self.gateway.send_message(
                message.chat.id,
                "Lokasi belum cocok dengan blok terkonfirmasi. Periksa GPS atau hubungi petugas.",
            )
            return
        if status == "matched":
            candidate = candidates[0]
            await self.repository.set_current_block(message.chat.id, UUID(candidate["block_id"]))
            await self.gateway.send_message(
                message.chat.id,
                f"Lokasi cocok dengan Blok {candidate['block_code']} "
                f"(luas PostGIS {candidate['area_ha']} ha).",
            )
            return

        action = await self.repository.create_pending_location(
            chat_id=message.chat.id,
            telegram_user_id=update.telegram_user_id or 0,
            payload=result,
        )
        buttons = [
            [
                InlineKeyboardButton(
                    text=f"Blok {candidate['block_code']}",
                    callback_data=f"loc:{action.id}:{index}",
                )
            ]
            for index, candidate in enumerate(candidates)
        ]
        prompt = (
            "Akurasi GPS menyentuh batas blok. Pilih blok yang benar:"
            if status == "confirmation_required"
            else "Lokasi memiliki beberapa kandidat. Pilih blok yang benar:"
        )
        await self.gateway.send_message(
            message.chat.id, prompt, InlineKeyboardMarkup(inline_keyboard=buttons)
        )

    async def _handle_callback(
        self, update: TelegramUpdate, callback: TelegramCallbackQuery, trace_id: UUID
    ) -> None:
        if callback.message is None or not callback.data:
            await self.gateway.answer_callback(callback.id, "Konfirmasi tidak valid")
            return
        try:
            prefix, raw_action_id, raw_index = callback.data.split(":", maxsplit=2)
            action_id = UUID(raw_action_id)
            index = int(raw_index)
        except (ValueError, TypeError):
            await self.gateway.answer_callback(callback.id, "Konfirmasi tidak valid")
            return
        if prefix != "loc":
            await self.gateway.answer_callback(callback.id, "Aksi tidak dikenal")
            return

        action = await self.repository.get_pending(action_id)
        now = datetime.now(UTC)
        if (
            action is None
            or action.telegram_user_id != callback.from_user.id
            or action.status != "pending"
            or action.expires_at <= now
        ):
            await self.gateway.answer_callback(callback.id, "Konfirmasi sudah kedaluwarsa")
            return
        candidates = action.payload.get("candidates", [])
        if index < 0 or index >= len(candidates):
            await self.gateway.answer_callback(callback.id, "Pilihan blok tidak valid")
            return
        candidate = candidates[index]
        await self.repository.confirm_pending(action, UUID(candidate["block_id"]))
        self.repository.add_audit(
            trace_id=trace_id,
            update_id=update.update_id,
            chat_id=callback.message.chat.id,
            telegram_user_id=callback.from_user.id,
            event_type="human_confirmation",
            intent="confirm_location",
            output_data={"block_id": candidate["block_id"]},
            status="succeeded",
        )
        await self.gateway.answer_callback(callback.id, "Blok dikonfirmasi")
        await self.gateway.send_message(
            callback.message.chat.id,
            f"Blok {candidate['block_code']} dipilih sebagai konteks aktif.",
        )
