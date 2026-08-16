from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class TelegramUser(BaseModel):
    id: int
    is_bot: bool = False
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None

    @property
    def display_name(self) -> str:
        return " ".join(part for part in (self.first_name, self.last_name) if part).strip()


class TelegramChat(BaseModel):
    id: int
    type: str


class TelegramLocation(BaseModel):
    longitude: float = Field(ge=-180, le=180)
    latitude: float = Field(ge=-90, le=90)
    horizontal_accuracy: float | None = Field(default=None, ge=0, le=1500)


class TelegramMessage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message_id: int
    date: int | None = None
    chat: TelegramChat
    from_user: TelegramUser | None = Field(default=None, alias="from")
    text: str | None = None
    location: TelegramLocation | None = None


class TelegramCallbackQuery(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: str
    from_user: TelegramUser = Field(alias="from")
    message: TelegramMessage | None = None
    data: str | None = None


class TelegramUpdate(BaseModel):
    update_id: int
    message: TelegramMessage | None = None
    callback_query: TelegramCallbackQuery | None = None

    @property
    def kind(self) -> Literal["message", "callback_query", "unsupported"]:
        if self.message is not None:
            return "message"
        if self.callback_query is not None:
            return "callback_query"
        return "unsupported"

    @property
    def chat_id(self) -> int | None:
        if self.message is not None:
            return self.message.chat.id
        if self.callback_query and self.callback_query.message:
            return self.callback_query.message.chat.id
        return None

    @property
    def telegram_user_id(self) -> int | None:
        if self.message and self.message.from_user:
            return self.message.from_user.id
        if self.callback_query:
            return self.callback_query.from_user.id
        return None


class TelegramWebhookResult(BaseModel):
    status: Literal["processed", "duplicate", "ignored"]
    update_id: int


class InlineKeyboardButton(BaseModel):
    text: str
    callback_data: str


class InlineKeyboardMarkup(BaseModel):
    inline_keyboard: list[list[InlineKeyboardButton]]


class AgentToolResult(BaseModel):
    tool_name: str
    data: dict[str, Any]
