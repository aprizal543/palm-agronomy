from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geography, Geometry
from sqlalchemy import DateTime, ForeignKey, Numeric, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BoundarySource, DataOrigin, FarmAccessRole, RecordStatus
from app.models.types import palm_enum


class Farm(Base):
    __tablename__ = "farms"
    __table_args__ = {"schema": "palm"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    owner_id: Mapped[UUID] = mapped_column(ForeignKey("palm.users.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120))
    village: Mapped[str | None] = mapped_column(String)
    district: Mapped[str | None] = mapped_column(String)
    regency: Mapped[str | None] = mapped_column(String)
    province: Mapped[str | None] = mapped_column(String)
    location_point: Mapped[object | None] = mapped_column(Geography("POINT", srid=4326))
    location_accuracy_m: Mapped[Decimal | None] = mapped_column(Numeric(8, 2))
    boundary: Mapped[object | None] = mapped_column(Geometry("MULTIPOLYGON", srid=4326))
    declared_area_ha: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    verified_area_m2: Mapped[Decimal | None] = mapped_column(Numeric(16, 2))
    verified_area_ha: Mapped[Decimal | None] = mapped_column(Numeric(12, 4))
    boundary_source: Mapped[BoundarySource | None] = mapped_column(
        palm_enum(BoundarySource, "boundary_source")
    )
    boundary_source_metadata: Mapped[dict | None] = mapped_column(JSONB)
    mapped_by: Mapped[UUID | None] = mapped_column(ForeignKey("palm.users.id"))
    mapped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[RecordStatus] = mapped_column(
        palm_enum(RecordStatus, "record_status"), default=RecordStatus.DRAFT
    )
    validation_notes: Mapped[str | None] = mapped_column(String)
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("palm.users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_origin: Mapped[DataOrigin] = mapped_column(
        palm_enum(DataOrigin, "data_origin"), default=DataOrigin.USER_INPUT
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class FarmMember(Base):
    __tablename__ = "farm_members"
    __table_args__ = {"schema": "palm"}

    farm_id: Mapped[UUID] = mapped_column(
        ForeignKey("palm.farms.id", ondelete="RESTRICT"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(
        ForeignKey("palm.users.id", ondelete="RESTRICT"), primary_key=True
    )
    access_role: Mapped[FarmAccessRole] = mapped_column(
        palm_enum(FarmAccessRole, "farm_access_role"), default=FarmAccessRole.VIEWER
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))
