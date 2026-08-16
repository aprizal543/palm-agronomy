import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RecordStatus, UserRole
from app.models.farm import Farm, FarmMember
from app.models.user import User
from app.schemas.common import SpatialValidationDecision
from app.schemas.farm import FarmBoundaryUpdate, FarmCreate


class FarmRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: FarmCreate) -> Farm:
        values = data.model_dump(exclude={"boundary", "location_point"})
        farm = Farm(**values)
        if data.location_point:
            farm.location_point = func.ST_GeogFromText(
                f"SRID=4326;POINT({data.location_point.coordinates[0]} "
                f"{data.location_point.coordinates[1]})"
            )
        if data.boundary:
            geojson = json.dumps(data.boundary.model_dump(mode="json"))
            geometry = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geojson), 4326)
            farm.boundary = func.ST_Multi(geometry)
            farm.mapped_at = func.now()
        self.session.add(farm)
        await self.session.flush()
        return await self.get(farm.id)

    async def get(self, farm_id: UUID) -> Farm | None:
        statement = (
            select(
                Farm,
                func.ST_AsGeoJSON(Farm.boundary).label("boundary_geojson"),
                func.ST_AsGeoJSON(Farm.location_point).label("point_geojson"),
            )
            .where(Farm.id == farm_id)
            .execution_options(populate_existing=True)
        )
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        farm = row[0]
        farm.boundary_geojson = json.loads(row.boundary_geojson) if row.boundary_geojson else None
        farm.point_geojson = json.loads(row.point_geojson) if row.point_geojson else None
        return farm

    async def update_boundary(self, farm_id: UUID, data: FarmBoundaryUpdate) -> Farm | None:
        farm = await self.session.get(Farm, farm_id)
        if farm is None:
            return None
        geojson = json.dumps(data.boundary.model_dump(mode="json"))
        farm.boundary = func.ST_Multi(
            func.ST_SetSRID(func.ST_GeomFromGeoJSON(geojson), 4326)
        )
        farm.boundary_source = data.boundary_source
        farm.boundary_source_metadata = data.boundary_source_metadata
        farm.mapped_by = data.actor_user_id
        farm.mapped_at = func.now()
        await self.session.flush()
        return await self.get(farm_id)

    async def has_write_access(self, farm_id: UUID, user_id: UUID) -> bool:
        statement = select(
            select(Farm.id)
            .where(Farm.id == farm_id, Farm.owner_id == user_id)
            .exists()
            | select(FarmMember.farm_id)
            .where(
                FarmMember.farm_id == farm_id,
                FarmMember.user_id == user_id,
                FarmMember.access_role.in_(["editor", "validator"]),
            )
            .exists()
        )
        return bool(await self.session.scalar(statement))

    async def has_validation_access(self, farm_id: UUID, user_id: UUID) -> bool:
        role = await self.session.scalar(select(User.role).where(User.id == user_id, User.is_active))
        if role == UserRole.ADMIN:
            return True
        if role != UserRole.FIELD_OFFICER:
            return False
        return bool(
            await self.session.scalar(
                select(FarmMember.farm_id).where(
                    FarmMember.farm_id == farm_id,
                    FarmMember.user_id == user_id,
                    FarmMember.access_role == "validator",
                )
            )
        )

    async def validate_boundary(
        self, farm_id: UUID, data: SpatialValidationDecision
    ) -> Farm | None:
        farm = await self.session.get(Farm, farm_id)
        if farm is None:
            return None
        farm.status = RecordStatus(data.decision)
        farm.validation_notes = data.notes
        if data.decision == "confirmed":
            farm.confirmed_by = data.actor_user_id
            farm.confirmed_at = func.now()
        else:
            farm.confirmed_by = None
            farm.confirmed_at = None
        await self.session.flush()
        return await self.get(farm_id)
