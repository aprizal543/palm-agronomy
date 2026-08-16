"""Create confirmed block production records and database invariants."""

from alembic import op

revision = "0005_production_records"
down_revision = "0004_telegram_agent"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Keep one SQL command per op.execute: asyncpg rejects multi-command prepared statements.
    op.execute(
        """
        create table palm.production_records (
          id uuid primary key default gen_random_uuid(),
          farm_id uuid not null references palm.farms(id) on delete restrict,
          block_id uuid not null references palm.blocks(id) on delete restrict,
          harvest_date date not null,
          ffb_weight_kg numeric(14,2) not null check (ffb_weight_kg > 0),
          bunch_count integer check (bunch_count is null or bunch_count > 0),
          notes varchar(500),
          recorded_by uuid not null references palm.users(id) on delete restrict,
          confirmation_action_id uuid not null unique
            references palm.pending_actions(id) on delete restrict,
          source_update_id bigint not null
            references palm.telegram_updates(update_id) on delete restrict,
          status palm.record_status not null default 'confirmed',
          data_origin palm.data_origin not null default 'user_input',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint production_records_confirmed_only check (status = 'confirmed')
        )
        """
    )
    op.execute(
        "create index production_records_block_date_idx "
        "on palm.production_records(block_id,harvest_date desc)"
    )
    op.execute(
        "create index production_records_farm_date_idx "
        "on palm.production_records(farm_id,harvest_date desc)"
    )
    op.execute(
        """
        create function palm.validate_production_record() returns trigger
        language plpgsql as $$
        declare
          expected_farm_id uuid;
          allowed boolean;
        begin
          select farm_id into expected_farm_id
          from palm.blocks
          where id = new.block_id and status = 'confirmed';

          if expected_farm_id is null or expected_farm_id <> new.farm_id then
            raise exception 'Production block must be confirmed and belong to its farm';
          end if;

          select exists (
            select 1 from palm.farms f
            where f.id = new.farm_id and f.owner_id = new.recorded_by
            union all
            select 1 from palm.farm_members fm
            where fm.farm_id = new.farm_id
              and fm.user_id = new.recorded_by
              and fm.access_role in ('editor','validator')
          ) into allowed;

          if not allowed then
            raise exception 'Recorder has no write access to this farm';
          end if;

          if new.harvest_date > current_date then
            raise exception 'Harvest date cannot be in the future';
          end if;
          return new;
        end;
        $$
        """
    )
    op.execute(
        """
        create trigger production_records_validate before insert or update
        on palm.production_records for each row
        execute function palm.validate_production_record()
        """
    )
    op.execute(
        """
        create trigger production_records_set_updated_at before update
        on palm.production_records for each row
        execute function palm.set_updated_at()
        """
    )
    op.execute(
        "comment on table palm.production_records is "
        "'Human-confirmed FFB harvest records; Postgres enforces block, farm, and actor integrity'"
    )


def downgrade() -> None:
    op.execute(
        "drop trigger if exists production_records_set_updated_at on palm.production_records"
    )
    op.execute("drop trigger if exists production_records_validate on palm.production_records")
    op.execute("drop function if exists palm.validate_production_record()")
    op.execute("drop table if exists palm.production_records")
