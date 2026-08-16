from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import BoundarySource, DataOrigin, RecordStatus
from app.schemas.common import PolygonGeoJSON


class BlockCreate(BaseModel):
    farm_id: UUID
    actor_user_id: UUID
    block_code: str = Field(min_length=1, max_length=30)
    name: str | None = None
    boundary: PolygonGeoJSON
    boundary_source: BoundarySource = BoundarySource.MAP_DRAW
    boundary_source_metadata: dict | None = None
    planting_year: int | None = Field(default=None, ge=1900, le=2100)
    soil_type: str | None = None
    data_origin: DataOrigin = DataOrigin.USER_INPUT

    @field_validator("planting_year")
    @classmethod
    def reject_future_year(cls, value: int | None) -> int | None:
        if value is not None and value > datetime.now().year:
            raise ValueError("planting_year tidak boleh melebihi tahun berjalan")
        return value


class BlockRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    farm_id: UUID
    block_code: str
    name: str | None
    boundary: dict
    area_m2: Decimal
    area_ha: Decimal
    boundary_source: BoundarySource
    mapped_by: UUID | None
    planting_year: int | None
    soil_type: str | None
    status: RecordStatus
    data_origin: DataOrigin
    created_at: datetime
    updated_at: datetime


class BlockLocationResult(BaseModel):
    block_id: UUID
    farm_id: UUID
    block_code: str
    area_ha: Decimal
    contains_point: bool
    distance_to_boundary_m: Decimal


class LocationResolution(BaseModel):
    status: Literal["matched", "confirmation_required", "ambiguous", "not_found"]
    accuracy_m: Decimal
    candidates: list[BlockLocationResult]


class GeometryValidationResult(BaseModel):
    valid: bool
    reason: str
    area_m2: Decimal | None = None
    area_ha: Decimal | None = None
