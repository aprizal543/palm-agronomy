import time
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4

import httpx
from fastapi.encoders import jsonable_encoder
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.tools import AgronomyToolRegistry
from app.integrations.telegram import TelegramGateway
from app.repositories.telegram import TelegramRepository
from app.schemas.production import ProductionDraft
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
    "• kirim Location — pilih konteks blok berdasarkan GPS\n"
    "• /context — tampilkan kebun dan blok aktif\n"
    "• /produksi <kg> [tandan] [YYYY-MM-DD] — siapkan catatan TBS\n"
    "• /riwayat [jumlah] — tampilkan catatan terakhir (maksimal 10)\n"
    "• /ringkasan [hari] — ringkasan produksi (maksimal 365 hari)"
)


def safe_error_label(exc: Exception) -> str:
    """Return an audit-safe error label without SQL, payloads, or credentials."""
    original = getattr(exc, "orig", None)
    sqlstate = getattr(original, "sqlstate", None)
    if sqlstate:
        return f"{type(exc).__name__}[sqlstate={sqlstate}]"
    return type(exc).__name__


def parse_production_command(command_text: str, today: date | None = None) -> ProductionDraft:
    parts = command_text.split()
    if not parts or parts[0].lower() not in {"/produksi", "/production"}:
        raise ValueError("Perintah produksi tidak valid")
    if len(parts) < 2 or len(parts) > 4:
        raise ValueError("Format: /produksi <kg> [tandan] [YYYY-MM-DD]")
    try:
        weight = Decimal(parts[1].replace(",", "."))
        bunch_count = None if len(parts) < 3 or parts[2] == "-" else int(parts[2])
        harvest_date = (
            date.fromisoformat(parts[3])
            if len(parts) == 4
            else (today or datetime.now(UTC).date())
        )
        return ProductionDraft(
            ffb_weight_kg=weight,
            bunch_count=bunch_count,
            harvest_date=harvest_date,
        )
    except (InvalidOperation, ValueError, ValidationError) as exc:
        raise ValueError("Format: /produksi <kg> [tandan] [YYYY-MM-DD]") from exc


class TelegramAgentService:
    def __init__(self, session: AsyncSession, gateway: TelegramGateway):
        self.session = session
        self.gateway = gateway
        self.repository = TelegramRepository(session)
        self.tools = AgronomyToolRegistry(session)

    async def _clear_callback_buttons(self, callback: TelegramCallbackQuery) -> None:
        if callback.message is None:
            return
        try:
            await self.gateway.clear_inline_keyboard(
                callback.message.chat.id, callback.message.message_id
            )
        except (httpx.HTTPError, RuntimeError):
            # Button cleanup is best-effort and must not roll back a confirmed database action.
            return

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
            callback_data = update.callback_query.data or ""
            return "confirm_production" if callback_data.startswith("prod:") else "confirm_location"
        if update.message and update.message.location:
            return "resolve_location"
        text = (update.message.text if update.message else "") or ""
        command = text.split(maxsplit=1)[0].lower()
        intents = {
            "/start": "start",
            "/help": "help",
            "/context": "get_context",
            "/produksi": "prepare_production",
            "/production": "prepare_production",
            "/riwayat": "production_history",
            "/ringkasan": "production_summary",
        }
        if command in intents:
            return intents[command]
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
        elif command == "/context":
            await self._handle_context(update, message, trace_id)
        elif command in {"/produksi", "/production"}:
            await self._handle_production_draft(update, message, trace_id)
        elif command == "/riwayat":
            await self._handle_production_history(update, message, trace_id)
        elif command == "/ringkasan":
            await self._handle_production_summary(update, message, trace_id)
        else:
            await self.gateway.send_message(
                message.chat.id,
                "Saya belum memahami pesan itu. Ketik /help untuk melihat perintah.",
            )

    async def _execute_tool(
        self,
        *,
        update: TelegramUpdate,
        trace_id: UUID,
        intent: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.perf_counter()
        try:
            result = await self.tools.execute(tool_name, **arguments)
        except Exception as exc:
            self.repository.add_audit(
                trace_id=trace_id,
                update_id=update.update_id,
                chat_id=update.chat_id,
                telegram_user_id=update.telegram_user_id,
                event_type="tool_call",
                intent=intent,
                tool_name=tool_name,
                input_data=jsonable_encoder(arguments),
                status="failed",
                latency_ms=int((time.perf_counter() - started) * 1000),
                error_message=safe_error_label(exc),
            )
            raise
        self.repository.add_audit(
            trace_id=trace_id,
            update_id=update.update_id,
            chat_id=update.chat_id,
            telegram_user_id=update.telegram_user_id,
            event_type="tool_call",
            intent=intent,
            tool_name=tool_name,
            input_data=jsonable_encoder(arguments),
            output_data=jsonable_encoder(result),
            status="succeeded",
            latency_ms=int((time.perf_counter() - started) * 1000),
        )
        return result

    async def _context_result(
        self, update: TelegramUpdate, trace_id: UUID, intent: str
    ) -> dict[str, Any]:
        return await self._execute_tool(
            update=update,
            trace_id=trace_id,
            intent=intent,
            tool_name="get_farm_block_context",
            arguments={
                "chat_id": update.chat_id or 0,
                "telegram_user_id": update.telegram_user_id or 0,
            },
        )

    async def _handle_context(
        self, update: TelegramUpdate, message: TelegramMessage, trace_id: UUID
    ) -> None:
        result = await self._context_result(update, trace_id, "get_context")
        if result["status"] != "ready":
            await self.gateway.send_message(
                message.chat.id,
                "Belum ada blok aktif. Kirim Location Telegram dari area blok Anda.",
            )
            return
        access = "dapat mencatat produksi" if result["can_write"] else "akses baca saja"
        await self.gateway.send_message(
            message.chat.id,
            f"Konteks aktif:\nKebun: {result['farm_name']}\n"
            f"Blok: {result['block_code']} ({result['area_ha']} ha)\nHak akses: {access}.",
        )

    async def _handle_production_draft(
        self, update: TelegramUpdate, message: TelegramMessage, trace_id: UUID
    ) -> None:
        try:
            draft = parse_production_command(message.text or "")
        except ValueError as exc:
            await self.gateway.send_message(message.chat.id, str(exc))
            return
        context = await self._context_result(update, trace_id, "prepare_production")
        if context["status"] != "ready":
            await self.gateway.send_message(
                message.chat.id,
                "Belum ada blok aktif. Kirim Location Telegram terlebih dahulu.",
            )
            return
        if not context["can_write"]:
            await self.gateway.send_message(
                message.chat.id,
                "Akun Anda belum memiliki akses editor/validator pada kebun ini.",
            )
            return

        payload = {
            "farm_id": context["farm_id"],
            "farm_name": context["farm_name"],
            "block_id": context["block_id"],
            "block_code": context["block_code"],
            **draft.model_dump(mode="json"),
            "source_update_id": update.update_id,
        }
        action = await self.repository.create_pending_production(
            chat_id=message.chat.id,
            telegram_user_id=update.telegram_user_id or 0,
            payload=payload,
        )
        bunch_text = (
            f"{draft.bunch_count} tandan" if draft.bunch_count is not None else "tidak diisi"
        )
        buttons = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Simpan",
                        callback_data=f"prod:{action.id}:confirm",
                    ),
                    InlineKeyboardButton(
                        text="Batalkan",
                        callback_data=f"prod:{action.id}:cancel",
                    ),
                ]
            ]
        )
        await self.gateway.send_message(
            message.chat.id,
            "Konfirmasi catatan produksi:\n"
            f"Kebun: {context['farm_name']}\nBlok: {context['block_code']}\n"
            f"Tanggal: {draft.harvest_date.isoformat()}\n"
            f"Berat TBS: {draft.ffb_weight_kg} kg\nJumlah tandan: {bunch_text}",
            buttons,
        )

    async def _handle_production_history(
        self, update: TelegramUpdate, message: TelegramMessage, trace_id: UUID
    ) -> None:
        parts = (message.text or "").split()
        try:
            limit = 5 if len(parts) == 1 else int(parts[1])
            if len(parts) > 2 or limit < 1 or limit > 10:
                raise ValueError
        except ValueError:
            await self.gateway.send_message(message.chat.id, "Format: /riwayat [1-10]")
            return
        result = await self._execute_tool(
            update=update,
            trace_id=trace_id,
            intent="production_history",
            tool_name="list_production_history",
            arguments={
                "chat_id": message.chat.id,
                "telegram_user_id": update.telegram_user_id or 0,
                "limit": limit,
            },
        )
        if result["status"] != "ready":
            await self.gateway.send_message(
                message.chat.id, "Konteks blok atau hak akses produksi belum tersedia."
            )
            return
        if not result["records"]:
            await self.gateway.send_message(
                message.chat.id, f"Belum ada catatan produksi untuk Blok {result['block_code']}."
            )
            return
        lines = [f"Riwayat Blok {result['block_code']}:"]
        for item in result["records"]:
            bunches = f", {item['bunch_count']} tandan" if item["bunch_count"] else ""
            lines.append(f"• {item['harvest_date']}: {item['ffb_weight_kg']} kg{bunches}")
        await self.gateway.send_message(message.chat.id, "\n".join(lines))

    async def _handle_production_summary(
        self, update: TelegramUpdate, message: TelegramMessage, trace_id: UUID
    ) -> None:
        parts = (message.text or "").split()
        try:
            days = 30 if len(parts) == 1 else int(parts[1])
            if len(parts) > 2 or days < 1 or days > 365:
                raise ValueError
        except ValueError:
            await self.gateway.send_message(message.chat.id, "Format: /ringkasan [1-365]")
            return
        result = await self._execute_tool(
            update=update,
            trace_id=trace_id,
            intent="production_summary",
            tool_name="summarize_production",
            arguments={
                "chat_id": message.chat.id,
                "telegram_user_id": update.telegram_user_id or 0,
                "days": days,
            },
        )
        if result["status"] != "ready":
            await self.gateway.send_message(
                message.chat.id, "Konteks blok atau hak akses produksi belum tersedia."
            )
            return
        await self.gateway.send_message(
            message.chat.id,
            f"Ringkasan {result['days']} hari — Blok {result['block_code']}:\n"
            f"Catatan: {result['record_count']}\n"
            f"Total TBS: {result['total_ffb_kg']} kg\n"
            f"Total tandan: {result['total_bunches']}\n"
            f"Rata-rata/catatan: {result['average_ffb_kg_per_record']} kg",
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
        result = await self._execute_tool(
            update=update,
            trace_id=trace_id,
            intent="resolve_location",
            tool_name="resolve_block_by_location",
            arguments=arguments,
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
            prefix, raw_action_id, choice = callback.data.split(":", maxsplit=2)
            action_id = UUID(raw_action_id)
        except (ValueError, TypeError):
            await self.gateway.answer_callback(callback.id, "Konfirmasi tidak valid")
            return
        if prefix not in {"loc", "prod"}:
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
            await self._clear_callback_buttons(callback)
            await self.gateway.answer_callback(
                callback.id, "Konfirmasi sudah diproses atau kedaluwarsa"
            )
            return
        if prefix == "prod":
            await self._handle_production_callback(update, callback, trace_id, action, choice)
            return
        await self._handle_location_callback(update, callback, trace_id, action, choice)

    async def _handle_location_callback(
        self,
        update: TelegramUpdate,
        callback: TelegramCallbackQuery,
        trace_id: UUID,
        action: Any,
        choice: str,
    ) -> None:
        assert callback.message is not None
        try:
            index = int(choice)
        except ValueError:
            await self.gateway.answer_callback(callback.id, "Pilihan blok tidak valid")
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

    async def _handle_production_callback(
        self,
        update: TelegramUpdate,
        callback: TelegramCallbackQuery,
        trace_id: UUID,
        action: Any,
        choice: str,
    ) -> None:
        assert callback.message is not None
        if action.action_type != "confirm_production_record":
            await self.gateway.answer_callback(callback.id, "Jenis konfirmasi tidak sesuai")
            return
        if choice == "cancel":
            await self.repository.resolve_pending(action, "cancelled")
            self.repository.add_audit(
                trace_id=trace_id,
                update_id=update.update_id,
                chat_id=callback.message.chat.id,
                telegram_user_id=callback.from_user.id,
                event_type="human_confirmation",
                intent="confirm_production",
                output_data={"decision": "cancelled", "action_id": str(action.id)},
                status="rejected",
            )
            await self._clear_callback_buttons(callback)
            await self.gateway.answer_callback(callback.id, "Pencatatan dibatalkan")
            await self.gateway.send_message(
                callback.message.chat.id, "Draft produksi tidak disimpan."
            )
            return
        if choice != "confirm":
            await self.gateway.answer_callback(callback.id, "Pilihan tidak valid")
            return

        try:
            draft = ProductionDraft.model_validate(action.payload)
            block_id = UUID(action.payload["block_id"])
            source_update_id = int(action.payload["source_update_id"])
        except (KeyError, ValueError, ValidationError):
            await self.repository.resolve_pending(action, "cancelled")
            await self.gateway.answer_callback(callback.id, "Draft produksi tidak valid")
            return
        result = await self._execute_tool(
            update=update,
            trace_id=trace_id,
            intent="confirm_production",
            tool_name="record_production",
            arguments={
                "chat_id": callback.message.chat.id,
                "telegram_user_id": callback.from_user.id,
                "confirmation_action_id": action.id,
                "source_update_id": source_update_id,
                "block_id": block_id,
                "harvest_date": draft.harvest_date,
                "ffb_weight_kg": draft.ffb_weight_kg,
                "bunch_count": draft.bunch_count,
                "notes": draft.notes,
            },
        )
        if result["status"] != "recorded":
            await self.repository.resolve_pending(action, "cancelled")
            await self.gateway.answer_callback(callback.id, "Produksi tidak dapat disimpan")
            await self.gateway.send_message(
                callback.message.chat.id,
                "Konteks blok atau hak akses berubah. Buat draft produksi baru.",
            )
            return
        await self.repository.resolve_pending(action, "confirmed")
        self.repository.add_audit(
            trace_id=trace_id,
            update_id=update.update_id,
            chat_id=callback.message.chat.id,
            telegram_user_id=callback.from_user.id,
            event_type="human_confirmation",
            intent="confirm_production",
            output_data={
                "decision": "confirmed",
                "record_id": result["record_id"],
                "block_id": result["block_id"],
            },
            status="succeeded",
        )
        await self._clear_callback_buttons(callback)
        await self.gateway.answer_callback(callback.id, "Produksi disimpan")
        await self.gateway.send_message(
            callback.message.chat.id,
            f"Produksi Blok {result['block_code']} berhasil disimpan: "
            f"{result['ffb_weight_kg']} kg pada {result['harvest_date']}.",
        )
