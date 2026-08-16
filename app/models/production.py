from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DataOrigin, RecordStatus
from app.models.types import palm_enum


class ProductionRecord(Base):
    __tablename__ = "production_records"
    __table_args__ = {"schema": "palm"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("palm.farms.id", ondelete="RESTRICT"))
    block_id: Mapped[UUID] = mapped_column(ForeignKey("palm.blocks.id", ondelete="RESTRICT"))
    harvest_date: Mapped[date] = mapped_column(Date)
    ffb_weight_kg: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    bunch_count: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(String(500))
    recorded_by: Mapped[UUID] = mapped_column(
        ForeignKey("palm.users.id", ondelete="RESTRICT")
    )
    confirmation_action_id: Mapped[UUID] = mapped_column(
        ForeignKey("palm.pending_actions.id", ondelete="RESTRICT"), unique=True
    )
    source_update_id: Mapped[int] = mapped_column(
        ForeignKey("palm.telegram_updates.update_id", ondelete="RESTRICT")
    )
    status: Mapped[RecordStatus] = mapped_column(
        palm_enum(RecordStatus, "record_status"), default=RecordStatus.CONFIRMED
    )
    data_origin: Mapped[DataOrigin] = mapped_column(
        palm_enum(DataOrigin, "data_origin"), default=DataOrigin.USER_INPUT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
