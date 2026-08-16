from pathlib import Path

ROOT = Path(__file__).parents[1]


def migration_text(name: str) -> str:
    return (ROOT / "migrations" / "versions" / name).read_text(encoding="utf-8").lower()


def test_six_revisions_exist() -> None:
    revisions = sorted((ROOT / "migrations" / "versions").glob("*.py"))
    assert [item.name for item in revisions] == [
        "0001_extensions_enums.py",
        "0002_users_farms.py",
        "0003_blocks_spatial.py",
        "0004_telegram_agent.py",
        "0005_production_records.py",
        "0006_rag_knowledge.py",
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


def test_telegram_update_idempotency_and_audit_contract() -> None:
    sql = migration_text("0004_telegram_agent.py")
    assert "update_id bigint primary key" in sql
    assert "create table palm.conversations" in sql
    assert "create table palm.pending_actions" in sql
    assert "create table palm.agent_audit_logs" in sql
    assert "trace_id uuid not null" in sql


def test_production_requires_confirmation_and_database_invariants() -> None:
    sql = migration_text("0005_production_records.py")
    assert "create table palm.production_records" in sql
    assert "confirmation_action_id uuid not null unique" in sql
    assert "source_update_id bigint not null" in sql
    assert "validate_production_record" in sql
    assert "expected_farm_id <> new.farm_id" in sql
    assert "access_role in ('editor','validator')" in sql
    assert "new.harvest_date > current_date" in sql


def test_rag_requires_verified_sources_and_keeps_evidence_trace() -> None:
    sql = migration_text("0006_rag_knowledge.py")
    assert "create extension if not exists vector" in sql
    assert "create table palm.knowledge_sources" in sql
    assert "verification_status" in sql
    assert "verified_source_has_timestamp" in sql
    assert "create table palm.knowledge_chunks" in sql
    assert "embedding extensions.vector(1536)" in sql
    assert "using gin(search_vector)" in sql
    assert "create table palm.rag_query_logs" in sql
    assert "retrieved_chunk_ids uuid[]" in sql
