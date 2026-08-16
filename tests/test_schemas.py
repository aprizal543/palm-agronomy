from datetime import datetime

import pytest
from pydantic import ValidationError

from app.schemas.block import BlockCreate
from app.schemas.common import PolygonGeoJSON
from app.schemas.farm import FarmCreate
from app.schemas.user import UserCreate


def square() -> PolygonGeoJSON:
    return PolygonGeoJSON(
        coordinates=[
            [
                (101.20, 0.50),
                (101.21, 0.50),
                (101.21, 0.51),
                (101.20, 0.50),
            ]
        ]
    )


def test_user_requires_telegram_or_phone() -> None:
    with pytest.raises(ValidationError, match="telegram_user_id atau phone"):
        UserCreate(full_name="Petani Demo")


def test_polygon_ring_must_be_closed() -> None:
    with pytest.raises(ValidationError, match="harus tertutup"):
        PolygonGeoJSON(
            coordinates=[[(101.20, 0.50), (101.21, 0.50), (101.21, 0.51), (101.20, 0.51)]]
        )


def test_longitude_range_is_validated() -> None:
    with pytest.raises(ValidationError):
        PolygonGeoJSON(coordinates=[[(181, 0), (101, 0), (101, 1), (181, 0)]])


def test_future_planting_year_is_rejected() -> None:
    with pytest.raises(ValidationError, match="tahun berjalan"):
        BlockCreate(
            farm_id="11111111-1111-1111-1111-111111111111",
            actor_user_id="22222222-2222-2222-2222-222222222222",
            block_code="A01",
            boundary=square(),
            planting_year=datetime.now().year + 1,
        )


def test_farm_boundary_requires_auditable_source() -> None:
    with pytest.raises(ValidationError, match="boundary_source wajib"):
        FarmCreate(
            owner_id="11111111-1111-1111-1111-111111111111",
            name="Kebun Makmur",
            boundary=square(),
        )


def test_gps_accuracy_requires_location_point() -> None:
    with pytest.raises(ValidationError, match="bersama location_point"):
        FarmCreate(
            owner_id="11111111-1111-1111-1111-111111111111",
            name="Kebun Makmur",
            location_accuracy_m=15,
        )
