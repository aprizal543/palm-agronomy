from pathlib import Path

ROOT = Path(__file__).parents[1]


def migration_text(name: str) -> str:
    return (ROOT / "migrations" / "versions" / name).read_text(encoding="utf-8").lower()


def test_three_sprint_one_revisions_exist() -> None:
    revisions = sorted((ROOT / "migrations" / "versions").glob("*.py"))
    assert [item.name for item in revisions] == [
        "0001_extensions_enums.py",
        "0002_users_farms.py",
        "0003_blocks_spatial.py",
    ]


def test_block_area_is_computed_in_postgis() -> None:
    sql = migration_text("0003_blocks_spatial.py")
    assert "st_area(new.boundary::extensions.geography)" in sql
    assert "new.area_m2 :=" in sql
    assert "new.area_ha :=" in sql


def test_overlap_and_farm_coverage_rules_exist() -> None:
    sql = migration_text("0003_blocks_spatial.py")
    assert "st_coveredby" in sql
    assert ">1.0" in sql
    assert "pg_advisory_xact_lock" in sql


def test_point_lookup_uses_st_covers() -> None:
    sql = migration_text("0003_blocks_spatial.py")
    assert "resolve_blocks_by_location" in sql
    assert "st_covers" in sql
    assert "st_dwithin" in sql
    assert "distance_to_boundary_m" in sql


def test_share_location_is_a_point_not_a_boundary() -> None:
    farms = migration_text("0002_users_farms.py")
    assert "location_point extensions.geography(point,4326)" in farms
    assert "declared_area_ha" in farms
    assert "verified_area_ha" in farms
    assert "boundary_source" in farms
