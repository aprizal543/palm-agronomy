"""Create users, farms, memberships, and farm spatial validation."""

from alembic import op

revision = "0002_users_farms"
down_revision = "0001_extensions_enums"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        create table palm.users (
          id uuid primary key default gen_random_uuid(),
          telegram_user_id bigint unique,
          phone text,
          full_name text not null check (char_length(trim(full_name)) between 2 and 120),
          role palm.user_role not null default 'farmer',
          preferred_language text not null default 'id',
          timezone text not null default 'Asia/Jakarta',
          is_active boolean not null default true,
          data_origin palm.data_origin not null default 'user_input',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          constraint users_identity_required check (telegram_user_id is not null or phone is not null)
        )
        """
    )
    op.execute("create index users_role_active_idx on palm.users (role, is_active)")
    op.execute(
        """
        create trigger users_set_updated_at before update on palm.users
          for each row execute function palm.set_updated_at()
        """
    )
    op.execute(
        """
        create table palm.farms (
          id uuid primary key default gen_random_uuid(),
          owner_id uuid not null references palm.users(id) on delete restrict,
          name text not null check (char_length(trim(name)) between 2 and 120),
          village text, district text, regency text, province text,
          location_point extensions.geography(Point,4326),
          location_accuracy_m numeric(8,2) check (location_accuracy_m is null or location_accuracy_m >= 0),
          boundary extensions.geometry(MultiPolygon,4326),
          declared_area_ha numeric(12,4) check (declared_area_ha > 0),
          verified_area_m2 numeric(16,2) check (verified_area_m2 > 0),
          verified_area_ha numeric(12,4) check (verified_area_ha > 0),
          boundary_source palm.boundary_source,
          boundary_source_metadata jsonb,
          mapped_by uuid references palm.users(id) on delete restrict,
          mapped_at timestamptz,
          status palm.record_status not null default 'draft',
          validation_notes text,
          confirmed_by uuid references palm.users(id) on delete restrict,
          confirmed_at timestamptz,
          data_origin palm.data_origin not null default 'user_input',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          archived_at timestamptz,
          constraint farms_confirmation_pair check (
            (confirmed_by is null and confirmed_at is null) or
            (confirmed_by is not null and confirmed_at is not null)
          ),
          constraint farms_boundary_provenance check (
            (boundary is null and boundary_source is null) or
            (boundary is not null and boundary_source is not null)
          ),
          constraint farms_confirmed_requires_boundary check (
            status <> 'confirmed' or boundary is not null
          )
        )
        """
    )
    op.execute("create unique index farms_owner_name_uq on palm.farms (owner_id, lower(name))")
    op.execute("create index farms_owner_idx on palm.farms(owner_id)")
    op.execute("create index farms_boundary_gist on palm.farms using gist(boundary)")
    op.execute("create index farms_location_gist on palm.farms using gist(location_point)")
    op.execute(
        """
        create table palm.farm_members (
          farm_id uuid not null references palm.farms(id) on delete restrict,
          user_id uuid not null references palm.users(id) on delete restrict,
          access_role palm.farm_access_role not null default 'viewer',
          created_at timestamptz not null default now(),
          primary key (farm_id,user_id)
        )
        """
    )
    op.execute("create index farm_members_user_idx on palm.farm_members(user_id)")
    op.execute(
        """
        create function palm.validate_and_measure_farm() returns trigger language plpgsql as $$
        declare measured numeric;
        begin
          if new.boundary is null then
            new.verified_area_m2 := null; new.verified_area_ha := null;
            if tg_op = 'UPDATE' and old.boundary is not null then
              new.status := 'pending_validation'; new.confirmed_by := null; new.confirmed_at := null;
            end if;
            return new;
          end if;
          if extensions.st_isempty(new.boundary) then raise exception 'Farm boundary cannot be empty'; end if;
          if extensions.st_srid(new.boundary) <> 4326 then raise exception 'Farm boundary SRID must be 4326'; end if;
          new.boundary := extensions.st_force2d(new.boundary);
          if not extensions.st_isvalid(new.boundary) then
            raise exception 'Invalid farm boundary: %', extensions.st_isvalidreason(new.boundary);
          end if;
          measured := extensions.st_area(new.boundary::extensions.geography);
          if measured <= 0 then raise exception 'Farm area must be greater than zero'; end if;
          new.verified_area_m2 := round(measured,2);
          new.verified_area_ha := round(measured/10000.0,4);
          if tg_op = 'INSERT' or (
             tg_op = 'UPDATE' and old.boundary is distinct from new.boundary
             and (
               old.boundary is null or
               not extensions.st_equals(old.boundary,new.boundary) or
               old.boundary_source is distinct from new.boundary_source
             )
          ) then
            new.status := 'pending_validation'; new.confirmed_by := null; new.confirmed_at := null;
          end if;
          return new;
        end $$
        """
    )
    op.execute(
        """
        create trigger farms_validate_measure before insert or update of boundary,boundary_source on palm.farms
          for each row execute function palm.validate_and_measure_farm()
        """
    )
    op.execute(
        """
        create trigger farms_set_updated_at before update on palm.farms
          for each row execute function palm.set_updated_at()
        """
    )


def downgrade() -> None:
    op.execute("drop table if exists palm.farm_members")
    op.execute("drop trigger if exists farms_validate_measure on palm.farms")
    op.execute("drop function if exists palm.validate_and_measure_farm()")
    op.execute("drop table if exists palm.farms")
    op.execute("drop table if exists palm.users")
