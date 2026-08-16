from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from geoalchemy2 import Geometry
from sqlalchemy import DateTime, ForeignKey, Numeric, SmallInteger, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import BoundarySource, DataOrigin, RecordStatus
from app.models.types import palm_enum


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = {"schema": "palm"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    farm_id: Mapped[UUID] = mapped_column(ForeignKey("palm.farms.id", ondelete="RESTRICT"))
    block_code: Mapped[str] = mapped_column(String(30))
    name: Mapped[str | None] = mapped_column(String)
    boundary: Mapped[object] = mapped_column(Geometry("POLYGON", srid=4326))
    area_m2: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    area_ha: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    boundary_source: Mapped[BoundarySource] = mapped_column(
        palm_enum(BoundarySource, "boundary_source"), default=BoundarySource.MAP_DRAW
    )
    boundary_source_metadata: Mapped[dict | None] = mapped_column(JSONB)
    mapped_by: Mapped[UUID | None] = mapped_column(ForeignKey("palm.users.id"))
    mapped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    planting_year: Mapped[int | None] = mapped_column(SmallInteger)
    soil_type: Mapped[str | None] = mapped_column(String)
    status: Mapped[RecordStatus] = mapped_column(
        palm_enum(RecordStatus, "record_status"), default=RecordStatus.PENDING_VALIDATION
    )
    validation_notes: Mapped[str | None] = mapped_column(String)
    confirmed_by: Mapped[UUID | None] = mapped_column(ForeignKey("palm.users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    data_origin: Mapped[DataOrigin] = mapped_column(
        palm_enum(DataOrigin, "data_origin"), default=DataOrigin.USER_INPUT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    archived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
