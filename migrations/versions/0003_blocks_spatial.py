"""Create spatial blocks, validation trigger, and point lookup function."""

from alembic import op

revision = "0003_blocks_spatial"
down_revision = "0002_users_farms"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        create table palm.blocks (
          id uuid primary key default gen_random_uuid(),
          farm_id uuid not null references palm.farms(id) on delete restrict,
          block_code text not null check (char_length(trim(block_code)) between 1 and 30),
          name text,
          boundary extensions.geometry(Polygon,4326) not null,
          area_m2 numeric(16,2) not null,
          area_ha numeric(12,4) not null,
          boundary_source palm.boundary_source not null default 'map_draw',
          boundary_source_metadata jsonb,
          mapped_by uuid references palm.users(id) on delete restrict,
          mapped_at timestamptz,
          planting_year smallint check (planting_year is null or planting_year between 1900 and 2100),
          soil_type text,
          status palm.record_status not null default 'pending_validation',
          validation_notes text,
          confirmed_by uuid references palm.users(id) on delete restrict,
          confirmed_at timestamptz,
          data_origin palm.data_origin not null default 'user_input',
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          archived_at timestamptz,
          constraint blocks_area_positive check (area_m2 > 0 and area_ha > 0),
          constraint blocks_confirmation_pair check (
            (confirmed_by is null and confirmed_at is null) or
            (confirmed_by is not null and confirmed_at is not null)
          )
        )
        """
    )
    op.execute("create unique index blocks_farm_code_uq on palm.blocks(farm_id,lower(block_code))")
    op.execute("create index blocks_farm_status_idx on palm.blocks(farm_id,status)")
    op.execute("create index blocks_boundary_gist on palm.blocks using gist(boundary)")
    op.execute(
        """
        create function palm.validate_and_measure_block() returns trigger language plpgsql as $$
        declare farm_geom extensions.geometry(MultiPolygon,4326); overlap_code text; measured numeric;
        begin
          if new.boundary is null or extensions.st_isempty(new.boundary) then
            raise exception 'Block boundary is required and cannot be empty';
          end if;
          if extensions.st_srid(new.boundary) <> 4326 then raise exception 'Block boundary SRID must be 4326'; end if;
          new.boundary := extensions.st_force2d(new.boundary);
          if not extensions.st_isvalid(new.boundary) then
            raise exception 'Block boundary is invalid: %', extensions.st_isvalidreason(new.boundary);
          end if;
          measured := extensions.st_area(new.boundary::extensions.geography);
          if measured <= 0 then raise exception 'Block area must be greater than zero'; end if;
          new.area_m2 := round(measured,2); new.area_ha := round(measured/10000.0,4);
          perform pg_advisory_xact_lock(hashtextextended(new.farm_id::text,0));
          select boundary into farm_geom from palm.farms where id=new.farm_id;
          if farm_geom is not null and not extensions.st_coveredby(new.boundary,farm_geom) then
            raise exception 'Block boundary must be covered by the farm boundary';
          end if;
          select b.block_code into overlap_code from palm.blocks b
          where b.farm_id=new.farm_id and b.id<>new.id and b.status<>'archived'
            and b.boundary && new.boundary
            and extensions.st_area(extensions.st_intersection(b.boundary,new.boundary)::extensions.geography)>1.0
          limit 1;
          if overlap_code is not null then
            raise exception 'Block boundary overlaps another active block by more than 1 m2';
          end if;
          if tg_op='UPDATE' and (
            not extensions.st_equals(old.boundary,new.boundary) or
            old.boundary_source is distinct from new.boundary_source
          ) then
            new.status:='pending_validation'; new.confirmed_by:=null; new.confirmed_at:=null;
          end if;
          new.updated_at:=now(); return new;
        end $$
        """
    )
    op.execute(
        """
        create trigger blocks_validate_measure before insert or update of boundary,farm_id,boundary_source on palm.blocks
          for each row execute function palm.validate_and_measure_block()
        """
    )
    op.execute(
        """
        create trigger blocks_set_updated_at before update on palm.blocks
          for each row execute function palm.set_updated_at()
        """
    )
    op.execute(
        """
        create function palm.resolve_blocks_by_location(
          input_longitude double precision,
          input_latitude double precision,
          input_accuracy_m double precision default 0
        )
        returns table(
          block_id uuid,farm_id uuid,block_code text,area_ha numeric,
          contains_point boolean,distance_to_boundary_m numeric
        )
        language sql stable as $$
          with point as (
            select extensions.st_setsrid(
              extensions.st_makepoint(input_longitude,input_latitude),4326
            ) as geom
          )
          select b.id,b.farm_id,b.block_code,b.area_ha,
            extensions.st_covers(b.boundary,p.geom),
            round(extensions.st_distance(
              extensions.st_boundary(b.boundary)::extensions.geography,
              p.geom::extensions.geography
            )::numeric,2)
          from palm.blocks b cross join point p
          where b.status='confirmed' and (
            extensions.st_covers(b.boundary,p.geom) or
            (input_accuracy_m > 0 and extensions.st_dwithin(
              b.boundary::extensions.geography,p.geom::extensions.geography,input_accuracy_m
            ))
          );
        $$
        """
    )
    op.execute("comment on schema palm is 'Private application schema for PalmAgronomy AI Agent'")
    op.execute(
        "comment on column palm.blocks.area_m2 is "
        "'Calculated by PostGIS; never supplied by Agent/client'"
    )


def downgrade() -> None:
    op.execute(
        "drop function if exists palm.resolve_blocks_by_location(double precision,double precision,double precision)"
    )
    op.execute("drop trigger if exists blocks_validate_measure on palm.blocks")
    op.execute("drop function if exists palm.validate_and_measure_block()")
    op.execute("drop table if exists palm.blocks")
