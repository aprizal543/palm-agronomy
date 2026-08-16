from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductionDraft(BaseModel):
    ffb_weight_kg: Decimal = Field(gt=0, le=1_000_000, max_digits=14, decimal_places=2)
    bunch_count: int | None = Field(default=None, gt=0, le=1_000_000)
    harvest_date: date
    notes: str | None = Field(default=None, max_length=500)

    @field_validator("harvest_date")
    @classmethod
    def reject_future_date(cls, value: date) -> date:
        if value > datetime.now(UTC).date():
            raise ValueError("Tanggal panen tidak boleh di masa depan")
        return value


class ProductionRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    farm_id: UUID
    block_id: UUID
    block_code: str | None = None
    harvest_date: date
    ffb_weight_kg: Decimal
    bunch_count: int | None
    average_bunch_weight_kg: Decimal | None = None
    notes: str | None
    recorded_by: UUID


class ProductionSummary(BaseModel):
    block_id: UUID
    block_code: str
    days: int
    record_count: int
    total_ffb_kg: Decimal
    total_bunches: int
    average_ffb_kg_per_record: Decimal
