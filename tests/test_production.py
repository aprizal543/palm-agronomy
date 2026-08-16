from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.repositories.production import format_decimal_2
from app.schemas.production import ProductionDraft
from app.services.telegram_agent import parse_production_command


def test_production_command_uses_today_and_accepts_decimal_comma() -> None:
    today = date(2026, 8, 16)
    draft = parse_production_command("/produksi 1250,50 80", today=today)

    assert draft.ffb_weight_kg == Decimal("1250.50")
    assert draft.bunch_count == 80
    assert draft.harvest_date == today


def test_production_command_accepts_explicit_date_without_bunch_count() -> None:
    draft = parse_production_command("/produksi 900 - 2026-08-15")

    assert draft.ffb_weight_kg == Decimal(900)
    assert draft.bunch_count is None
    assert draft.harvest_date == date(2026, 8, 15)


@pytest.mark.parametrize(
    "command",
    [
        "/produksi",
        "/produksi nol",
        "/produksi -5",
        "/produksi 100 0",
        "/produksi 100 20 16-08-2026",
        "/produksi 100 20 2026-08-16 extra",
    ],
)
def test_invalid_production_commands_are_rejected(command: str) -> None:
    with pytest.raises(ValueError, match="Format"):
        parse_production_command(command)


def test_future_harvest_date_is_rejected() -> None:
    with pytest.raises(ValidationError, match="masa depan"):
        ProductionDraft(
            ffb_weight_kg=100,
            harvest_date=datetime.now(UTC).date() + timedelta(days=1),
        )


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("1250.0000000000000000"), "1250.00"),
        (Decimal("12.345"), "12.34"),
        (None, "0.00"),
    ],
)
def test_decimal_output_is_formatted_to_two_places(
    value: Decimal | None, expected: str
) -> None:
    assert format_decimal_2(value) == expected
