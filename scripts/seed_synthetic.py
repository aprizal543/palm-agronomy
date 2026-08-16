"""Small idempotent synthetic seed for Sprint 1 demos."""

import asyncio

from sqlalchemy import text

from app.db.session import SessionLocal

SEED_ADMIN_SQL = """
insert into palm.users (telegram_user_id,full_name,role,data_origin)
values (990000099,'Admin Demo PalmAgronomy','admin','synthetic')
on conflict (telegram_user_id) do update set full_name=excluded.full_name
"""

SEED_FARM_BLOCK_SQL = """
with farmer as (
  insert into palm.users (telegram_user_id,full_name,role,data_origin)
  values (990000001,'Petani Demo PalmAgronomy','farmer','synthetic')
  on conflict (telegram_user_id) do update set full_name=excluded.full_name
  returning id
), owner as (
  select id from farmer union all
  select id from palm.users where telegram_user_id=990000001 limit 1
), farm as (
  insert into palm.farms(
    owner_id,name,village,district,regency,province,boundary,boundary_source,status,data_origin
  )
  select id,'Kebun Demo Kampar','Desa Demo','Tapung','Kampar','Riau',
    extensions.st_multi(extensions.st_geomfromtext(
      'POLYGON((101.20 0.50,101.22 0.50,101.22 0.52,101.20 0.52,101.20 0.50))',4326
    )),'map_draw','confirmed','synthetic'
  from owner
  on conflict do nothing
  returning id
), target_farm as (
  select id from farm union all
  select f.id from palm.farms f join owner o on f.owner_id=o.id
  where lower(f.name)=lower('Kebun Demo Kampar') limit 1
)
insert into palm.blocks(farm_id,block_code,name,boundary,area_m2,area_ha,status,data_origin)
select tf.id,'A01','Blok Demo A01',extensions.st_geomfromtext(
  'POLYGON((101.201 0.501,101.209 0.501,101.209 0.509,101.201 0.509,101.201 0.501))',4326
),1,0.0001,'confirmed','synthetic'
from target_farm tf
where not exists (
  select 1 from palm.blocks b
  where b.farm_id=tf.id and lower(b.block_code)=lower('A01')
)
on conflict do nothing
"""

SEED_MEMBERSHIP_SQL = """
insert into palm.farm_members(farm_id,user_id,access_role)
select f.id,u.id,'validator'
from palm.farms f
join palm.users owner on owner.id=f.owner_id and owner.telegram_user_id=990000001
cross join palm.users u
where lower(f.name)=lower('Kebun Demo Kampar') and u.telegram_user_id=990000099
on conflict (farm_id,user_id) do update set access_role=excluded.access_role
"""


async def main() -> None:
    async with SessionLocal() as session:
        try:
            # asyncpg prepares one SQL command at a time. Keep the related seed
            # operations in one database transaction, but execute each command
            # separately so a failure rolls back the entire seed consistently.
            await session.execute(text(SEED_ADMIN_SQL))
            await session.execute(text(SEED_FARM_BLOCK_SQL))
            await session.execute(text(SEED_MEMBERSHIP_SQL))
            await session.commit()
        except Exception:
            await session.rollback()
            raise
    print("Synthetic/simulated data for academic prototype berhasil dibuat.")


if __name__ == "__main__":
    asyncio.run(main())
