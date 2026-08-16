from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import DataOrigin, UserRole


class UserCreate(BaseModel):
    telegram_user_id: int | None = None
    phone: str | None = None
    full_name: str = Field(min_length=2, max_length=120)
    role: UserRole = UserRole.FARMER
    preferred_language: str = "id"
    timezone: str = "Asia/Jakarta"
    data_origin: DataOrigin = DataOrigin.USER_INPUT

    @model_validator(mode="after")
    def identity_required(self):
        if self.telegram_user_id is None and not self.phone:
            raise ValueError("telegram_user_id atau phone wajib diisi")
        return self


class UserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    telegram_user_id: int | None
    phone: str | None
    full_name: str
    role: UserRole
    preferred_language: str
    timezone: str
    is_active: bool
    data_origin: DataOrigin
    created_at: datetime
