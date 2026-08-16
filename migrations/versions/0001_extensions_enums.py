"""Create PostGIS, private schema, shared enums, and timestamp function."""

from alembic import op

revision = "0001_extensions_enums"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("create schema if not exists extensions")
    op.execute("create extension if not exists postgis with schema extensions")
    op.execute("create schema if not exists palm")
    op.execute("create type palm.user_role as enum ('farmer','field_officer','admin')")
    op.execute("create type palm.farm_access_role as enum ('viewer','editor','validator')")
    op.execute(
        "create type palm.record_status as enum "
        "('draft','pending_validation','confirmed','rejected','archived')"
    )
    op.execute(
        "create type palm.data_origin as enum "
        "('synthetic','user_input','field_verified','public_api','system_generated')"
    )
    op.execute(
        "create type palm.boundary_source as enum "
        "('map_draw','gps_track','gis_import','ai_candidate')"
    )
    op.execute(
        """
        create function palm.set_updated_at() returns trigger language plpgsql as $$
        begin new.updated_at := now(); return new; end;
        $$
        """
    )


def downgrade() -> None:
    op.execute("drop function if exists palm.set_updated_at()")
    op.execute("drop type if exists palm.boundary_source")
    op.execute("drop type if exists palm.data_origin")
    op.execute("drop type if exists palm.record_status")
    op.execute("drop type if exists palm.farm_access_role")
    op.execute("drop type if exists palm.user_role")
    # The shared PostGIS extension/schema are intentionally preserved.
