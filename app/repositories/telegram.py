from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.enums import DataOrigin
from app.models.telegram import AgentAuditLog, Conversation, PendingAction, TelegramUpdate
from app.models.user import User


class TelegramRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def claim_update(
        self,
        *,
        update_id: int,
        chat_id: int | None,
        telegram_user_id: int | None,
        update_kind: str,
        raw_update: dict,
    ) -> bool:
        statement = (
            insert(TelegramUpdate)
            .values(
                update_id=update_id,
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                update_kind=update_kind,
                raw_update=raw_update,
                status="processing",
            )
            .on_conflict_do_update(
                index_elements=[TelegramUpdate.update_id],
                set_={
                    "status": "processing",
                    "attempts": TelegramUpdate.attempts + 1,
                    "error_message": None,
                    "received_at": func.now(),
                    "raw_update": raw_update,
                },
                where=or_(
                    TelegramUpdate.status == "failed",
                    and_(
                        TelegramUpdate.status == "processing",
                        TelegramUpdate.received_at < func.now() - text("interval '5 minutes'"),
                    ),
                ),
            )
            .returning(TelegramUpdate.update_id)
        )
        claimed = (await self.session.execute(statement)).scalar_one_or_none()
        return claimed is not None

    async def mark_update(self, update_id: int, status: str, error: str | None = None) -> None:
        values: dict = {"status": status, "error_message": error}
        if status == "processed":
            values["processed_at"] = datetime.now(UTC)
        await self.session.execute(
            update(TelegramUpdate).where(TelegramUpdate.update_id == update_id).values(**values)
        )

    async def upsert_user(self, telegram_user_id: int, full_name: str, language: str) -> User:
        statement = (
            insert(User)
            .values(
                telegram_user_id=telegram_user_id,
                full_name=full_name or f"Telegram {telegram_user_id}",
                preferred_language=language or "id",
                data_origin=DataOrigin.USER_INPUT,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_user_id],
                set_={"full_name": full_name or f"Telegram {telegram_user_id}"},
            )
            .returning(User.id)
        )
        user_id = (await self.session.execute(statement)).scalar_one()
        return await self.session.get(User, user_id)

    async def upsert_conversation(
        self, chat_id: int, telegram_user_id: int, user_id: UUID
    ) -> Conversation:
        statement = (
            insert(Conversation)
            .values(chat_id=chat_id, telegram_user_id=telegram_user_id, user_id=user_id)
            .on_conflict_do_update(
                index_elements=[Conversation.chat_id],
                set_={"telegram_user_id": telegram_user_id, "user_id": user_id},
            )
            .returning(Conversation.chat_id)
        )
        await self.session.execute(statement)
        return await self.session.get(Conversation, chat_id)

    async def create_pending_location(
        self, *, chat_id: int, telegram_user_id: int, payload: dict
    ) -> PendingAction:
        await self.session.execute(
            update(PendingAction)
            .where(PendingAction.chat_id == chat_id, PendingAction.status == "pending")
            .values(status="cancelled", resolved_at=datetime.now(UTC))
        )
        action = PendingAction(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            action_type="confirm_block_location",
            payload=payload,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        self.session.add(action)
        await self.session.flush()
        return action

    async def create_pending_production(
        self, *, chat_id: int, telegram_user_id: int, payload: dict
    ) -> PendingAction:
        await self.session.execute(
            update(PendingAction)
            .where(PendingAction.chat_id == chat_id, PendingAction.status == "pending")
            .values(status="cancelled", resolved_at=datetime.now(UTC))
        )
        action = PendingAction(
            chat_id=chat_id,
            telegram_user_id=telegram_user_id,
            action_type="confirm_production_record",
            payload=payload,
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        self.session.add(action)
        await self.session.flush()
        return action

    async def get_pending(self, action_id: UUID) -> PendingAction | None:
        return await self.session.scalar(
            select(PendingAction).where(PendingAction.id == action_id).with_for_update()
        )

    async def confirm_pending(self, action: PendingAction, block_id: UUID) -> None:
        action.status = "confirmed"
        action.resolved_at = datetime.now(UTC)
        await self.session.execute(
            update(Conversation)
            .where(Conversation.chat_id == action.chat_id)
            .values(
                state="idle",
                current_block_id=block_id,
                current_farm_id=select(Block.farm_id)
                .where(Block.id == block_id)
                .scalar_subquery(),
            )
        )

    async def resolve_pending(self, action: PendingAction, status: str) -> None:
        action.status = status
        action.resolved_at = datetime.now(UTC)

    async def set_current_block(self, chat_id: int, block_id: UUID) -> None:
        await self.session.execute(
            update(Conversation)
            .where(Conversation.chat_id == chat_id)
            .values(
                state="idle",
                current_block_id=block_id,
                current_farm_id=select(Block.farm_id)
                .where(Block.id == block_id)
                .scalar_subquery(),
            )
        )

    def add_audit(
        self,
        *,
        trace_id: UUID,
        update_id: int,
        chat_id: int | None,
        telegram_user_id: int | None,
        event_type: str,
        status: str,
        intent: str | None = None,
        tool_name: str | None = None,
        input_data: dict | None = None,
        output_data: dict | None = None,
        latency_ms: int | None = None,
        error_message: str | None = None,
    ) -> None:
        self.session.add(
            AgentAuditLog(
                trace_id=trace_id,
                update_id=update_id,
                chat_id=chat_id,
                telegram_user_id=telegram_user_id,
                event_type=event_type,
                intent=intent,
                tool_name=tool_name,
                input_data=input_data,
                output_data=output_data,
                status=status,
                latency_ms=latency_ms,
                error_message=error_message,
            )
        )
