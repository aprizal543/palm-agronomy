from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.models.enums import FarmAccessRole, RecordStatus
from app.models.farm import Farm, FarmMember
from app.models.production import ProductionRecord
from app.models.telegram import Conversation


def _decimal(value: Decimal | None) -> Decimal:
    return value or Decimal(0)


def format_decimal_2(value: Decimal | None) -> str:
    return f"{_decimal(value):.2f}"


class ProductionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def _context_query(self, chat_id: int, telegram_user_id: int) -> Select:
        writable_member = (
            select(FarmMember.farm_id)
            .where(
                FarmMember.user_id == Conversation.user_id,
                FarmMember.farm_id == Farm.id,
                FarmMember.access_role.in_(
                    [FarmAccessRole.EDITOR, FarmAccessRole.VALIDATOR]
                ),
            )
            .exists()
        )
        return (
            select(
                Conversation.user_id,
                Farm.id.label("farm_id"),
                Farm.name.label("farm_name"),
                Farm.owner_id,
                Block.id.label("block_id"),
                Block.block_code,
                Block.name.label("block_name"),
                Block.area_ha,
                or_(Farm.owner_id == Conversation.user_id, writable_member).label("can_write"),
            )
            .join(Block, Block.id == Conversation.current_block_id)
            .join(Farm, Farm.id == Block.farm_id)
            .where(
                Conversation.chat_id == chat_id,
                Conversation.telegram_user_id == telegram_user_id,
                Farm.status == RecordStatus.CONFIRMED,
                Block.status == RecordStatus.CONFIRMED,
            )
        )

    async def get_active_context(self, chat_id: int, telegram_user_id: int) -> dict[str, Any]:
        conversation = await self.session.get(Conversation, chat_id)
        if conversation is None or conversation.telegram_user_id != telegram_user_id:
            return {"status": "no_conversation"}
        if conversation.current_block_id is None:
            return {"status": "no_block"}

        result = await self.session.execute(self._context_query(chat_id, telegram_user_id))
        row = result.mappings().first()
        if row is None:
            return {"status": "unavailable"}
        return {
            "status": "ready",
            "user_id": str(row["user_id"]),
            "farm_id": str(row["farm_id"]),
            "farm_name": row["farm_name"],
            "block_id": str(row["block_id"]),
            "block_code": row["block_code"],
            "block_name": row["block_name"],
            "area_ha": str(row["area_ha"]),
            "can_write": bool(row["can_write"]),
        }

    async def record_confirmed(
        self,
        *,
        chat_id: int,
        telegram_user_id: int,
        confirmation_action_id: UUID,
        source_update_id: int,
        block_id: UUID,
        harvest_date: date,
        ffb_weight_kg: Decimal,
        bunch_count: int | None,
        notes: str | None,
    ) -> dict[str, Any]:
        context = await self.get_active_context(chat_id, telegram_user_id)
        if context.get("status") != "ready":
            return {"status": "context_unavailable"}
        if not context["can_write"]:
            return {"status": "access_denied"}
        if UUID(context["block_id"]) != block_id:
            return {"status": "context_changed"}

        statement = (
            insert(ProductionRecord)
            .values(
                farm_id=UUID(context["farm_id"]),
                block_id=block_id,
                harvest_date=harvest_date,
                ffb_weight_kg=ffb_weight_kg,
                bunch_count=bunch_count,
                notes=notes,
                recorded_by=UUID(context["user_id"]),
                confirmation_action_id=confirmation_action_id,
                source_update_id=source_update_id,
            )
            .on_conflict_do_nothing(
                index_elements=[ProductionRecord.confirmation_action_id]
            )
            .returning(ProductionRecord.id)
        )
        record_id = (await self.session.execute(statement)).scalar_one_or_none()
        if record_id is None:
            record_id = await self.session.scalar(
                select(ProductionRecord.id).where(
                    ProductionRecord.confirmation_action_id == confirmation_action_id
                )
            )
        return {
            "status": "recorded",
            "record_id": str(record_id),
            "farm_id": context["farm_id"],
            "farm_name": context["farm_name"],
            "block_id": context["block_id"],
            "block_code": context["block_code"],
            "harvest_date": harvest_date.isoformat(),
            "ffb_weight_kg": str(ffb_weight_kg),
            "bunch_count": bunch_count,
        }

    async def history(
        self, *, chat_id: int, telegram_user_id: int, limit: int
    ) -> dict[str, Any]:
        context = await self.get_active_context(chat_id, telegram_user_id)
        if context.get("status") != "ready":
            return {"status": "context_unavailable", "records": []}
        if not context["can_write"]:
            return {"status": "access_denied", "records": []}

        rows = (
            await self.session.execute(
                select(ProductionRecord)
                .where(ProductionRecord.block_id == UUID(context["block_id"]))
                .order_by(ProductionRecord.harvest_date.desc(), ProductionRecord.created_at.desc())
                .limit(limit)
            )
        ).scalars()
        records = [
            {
                "id": str(item.id),
                "harvest_date": item.harvest_date.isoformat(),
                "ffb_weight_kg": str(item.ffb_weight_kg),
                "bunch_count": item.bunch_count,
            }
            for item in rows
        ]
        return {
            "status": "ready",
            "block_id": context["block_id"],
            "block_code": context["block_code"],
            "records": records,
        }

    async def summary(
        self, *, chat_id: int, telegram_user_id: int, days: int
    ) -> dict[str, Any]:
        context = await self.get_active_context(chat_id, telegram_user_id)
        if context.get("status") != "ready":
            return {"status": "context_unavailable"}
        if not context["can_write"]:
            return {"status": "access_denied"}

        since = datetime.now(UTC).date() - timedelta(days=days - 1)
        row = (
            await self.session.execute(
                select(
                    func.count(ProductionRecord.id).label("record_count"),
                    func.coalesce(func.sum(ProductionRecord.ffb_weight_kg), 0).label(
                        "total_ffb_kg"
                    ),
                    func.coalesce(func.sum(ProductionRecord.bunch_count), 0).label(
                        "total_bunches"
                    ),
                    func.coalesce(func.avg(ProductionRecord.ffb_weight_kg), 0).label(
                        "average_ffb_kg"
                    ),
                ).where(
                    ProductionRecord.block_id == UUID(context["block_id"]),
                    ProductionRecord.harvest_date >= since,
                )
            )
        ).mappings().one()
        return {
            "status": "ready",
            "block_id": context["block_id"],
            "block_code": context["block_code"],
            "days": days,
            "record_count": row["record_count"],
            "total_ffb_kg": format_decimal_2(row["total_ffb_kg"]),
            "total_bunches": row["total_bunches"],
            "average_ffb_kg_per_record": format_decimal_2(row["average_ffb_kg"]),
        }
