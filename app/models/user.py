from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Boolean, DateTime, String, text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.models.enums import DataOrigin, UserRole
from app.models.types import palm_enum


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "palm"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger, unique=True)
    phone: Mapped[str | None] = mapped_column(String)
    full_name: Mapped[str] = mapped_column(String(120))
    role: Mapped[UserRole] = mapped_column(
        palm_enum(UserRole, "user_role"), default=UserRole.FARMER
    )
    preferred_language: Mapped[str] = mapped_column(String, default="id")
    timezone: Mapped[str] = mapped_column(String, default="Asia/Jakarta")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    data_origin: Mapped[DataOrigin] = mapped_column(
        palm_enum(DataOrigin, "data_origin"), default=DataOrigin.USER_INPUT
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )

