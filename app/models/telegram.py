from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class TelegramUpdate(Base):
    __tablename__ = "telegram_updates"
    __table_args__ = {"schema": "palm"}

    update_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    update_kind: Mapped[str] = mapped_column(String)
    raw_update: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, default="processing")
    attempts: Mapped[int] = mapped_column(Integer, default=1)
    error_message: Mapped[str | None] = mapped_column(Text)
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = {"schema": "palm"}

    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    telegram_user_id: Mapped[int] = mapped_column(BigInteger)
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("palm.users.id", ondelete="SET NULL"))
    state: Mapped[str] = mapped_column(String, default="idle")
    context: Mapped[dict] = mapped_column(JSONB, default=dict)
    current_farm_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("palm.farms.id", ondelete="SET NULL")
    )
    current_block_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("palm.blocks.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class PendingAction(Base):
    __tablename__ = "pending_actions"
    __table_args__ = {"schema": "palm"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    chat_id: Mapped[int] = mapped_column(
        ForeignKey("palm.conversations.chat_id", ondelete="CASCADE")
    )
    telegram_user_id: Mapped[int] = mapped_column(BigInteger)
    action_type: Mapped[str] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )


class AgentAuditLog(Base):
    __tablename__ = "agent_audit_logs"
    __table_args__ = {"schema": "palm"}

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    trace_id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True))
    update_id: Mapped[int | None] = mapped_column(
        ForeignKey("palm.telegram_updates.update_id", ondelete="SET NULL")
    )
    chat_id: Mapped[int | None] = mapped_column(BigInteger)
    telegram_user_id: Mapped[int | None] = mapped_column(BigInteger)
    event_type: Mapped[str] = mapped_column(String)
    intent: Mapped[str | None] = mapped_column(String)
    tool_name: Mapped[str | None] = mapped_column(String)
    input_data: Mapped[dict | None] = mapped_column(JSONB)
    output_data: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String)
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
