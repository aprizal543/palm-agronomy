from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.telegram import TelegramUpdate
from app.services.telegram_agent import TelegramAgentService, safe_error_label


def test_location_update_preserves_horizontal_accuracy() -> None:
    update = TelegramUpdate.model_validate(
        {
            "update_id": 101,
            "message": {
                "message_id": 7,
                "chat": {"id": 55, "type": "private"},
                "from": {"id": 55, "is_bot": False, "first_name": "Petani"},
                "location": {
                    "longitude": 101.1992,
                    "latitude": 0.4992,
                    "horizontal_accuracy": 12.5,
                },
            },
        }
    )

    assert update.kind == "message"
    assert update.chat_id == 55
    assert update.telegram_user_id == 55
    assert update.message.location.horizontal_accuracy == 12.5
    assert TelegramAgentService._detect_intent(update) == "resolve_location"


def test_invalid_location_is_rejected_before_tool_call() -> None:
    with pytest.raises(ValidationError):
        TelegramUpdate.model_validate(
            {
                "update_id": 102,
                "message": {
                    "message_id": 8,
                    "chat": {"id": 55, "type": "private"},
                    "location": {"longitude": 201, "latitude": 0},
                },
            }
        )


def test_callback_payload_fits_telegram_limit() -> None:
    callback_data = f"loc:{uuid4()}:0"
    assert len(callback_data.encode("utf-8")) <= 64


def test_safe_error_label_does_not_include_exception_message() -> None:
    error = RuntimeError("postgresql://user:secret@example.invalid/database")

    assert safe_error_label(error) == "RuntimeError"


def test_safe_error_label_includes_sqlstate_only() -> None:
    class OriginalError:
        sqlstate = "08006"

    class WrappedError(RuntimeError):
        orig = OriginalError()

    assert safe_error_label(WrappedError("sensitive detail")) == (
        "WrappedError[sqlstate=08006]"
    )
