from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import BoundarySource, DataOrigin, RecordStatus
from app.schemas.common import FarmBoundary, PointGeoJSON


class FarmCreate(BaseModel):
    owner_id: UUID
    name: str = Field(min_length=2, max_length=120)
    village: str | None = None
    district: str | None = None
    regency: str | None = None
    province: str | None = None
    location_point: PointGeoJSON | None = None
    location_accuracy_m: Decimal | None = Field(default=None, ge=0, le=10000)
    boundary: FarmBoundary | None = None
    declared_area_ha: Decimal | None = Field(default=None, gt=0)
    boundary_source: BoundarySource | None = None
    boundary_source_metadata: dict | None = None
    mapped_by: UUID | None = None
    data_origin: DataOrigin = DataOrigin.USER_INPUT

    @model_validator(mode="after")
    def validate_spatial_provenance(self):
        if self.location_accuracy_m is not None and self.location_point is None:
            raise ValueError("location_accuracy_m hanya boleh diisi bersama location_point")
        if self.boundary is not None and self.boundary_source is None:
            raise ValueError("boundary_source wajib diisi ketika boundary tersedia")
        if self.boundary is None and self.boundary_source is not None:
            raise ValueError("boundary_source tidak boleh diisi tanpa boundary")
        return self


class FarmRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    village: str | None
    district: str | None
    regency: str | None
    province: str | None
    boundary: dict | None = None
    location_point: dict | None = None
    location_accuracy_m: Decimal | None
    declared_area_ha: Decimal | None
    verified_area_m2: Decimal | None
    verified_area_ha: Decimal | None
    boundary_source: BoundarySource | None
    mapped_by: UUID | None
    status: RecordStatus
    data_origin: DataOrigin
    created_at: datetime
    updated_at: datetime


class FarmBoundaryUpdate(BaseModel):
    actor_user_id: UUID
    boundary: FarmBoundary
    boundary_source: BoundarySource
    boundary_source_metadata: dict | None = None
