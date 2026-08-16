import json
from uuid import UUID

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.schemas.block import BlockCreate
from app.schemas.common import SpatialValidationDecision
from app.models.enums import RecordStatus


class BlockRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, data: BlockCreate) -> Block:
        values = data.model_dump(exclude={"boundary", "actor_user_id"})
        geojson = json.dumps(data.boundary.model_dump(mode="json"))
        block = Block(**values)
        block.mapped_by = data.actor_user_id
        block.mapped_at = func.now()
        block.boundary = func.ST_SetSRID(func.ST_GeomFromGeoJSON(geojson), 4326)
        # Placeholder values satisfy ORM typing; the database trigger overwrites both.
        block.area_m2 = 1
        block.area_ha = 0.0001
        self.session.add(block)
        await self.session.flush()
        return await self.get(block.id)

    async def get(self, block_id: UUID) -> Block | None:
        statement = (
            select(Block, func.ST_AsGeoJSON(Block.boundary).label("boundary_geojson"))
            .where(Block.id == block_id)
            .execution_options(populate_existing=True)
        )
        row = (await self.session.execute(statement)).first()
        if row is None:
            return None
        block = row[0]
        block.boundary_geojson = json.loads(row.boundary_geojson)
        return block

    async def find_by_location(
        self, longitude: float, latitude: float, accuracy_m: float
    ) -> list[dict]:
        result = await self.session.execute(
            text(
                "select block_id, farm_id, block_code, area_ha, contains_point, "
                "distance_to_boundary_m "
                "from palm.resolve_blocks_by_location(:longitude, :latitude, :accuracy_m)"
            ),
            {"longitude": longitude, "latitude": latitude, "accuracy_m": accuracy_m},
        )
        return [dict(row._mapping) for row in result]

    async def validate_boundary(
        self, block_id: UUID, data: SpatialValidationDecision
    ) -> Block | None:
        block = await self.session.get(Block, block_id)
        if block is None:
            return None
        block.status = RecordStatus(data.decision)
        block.validation_notes = data.notes
        if data.decision == "confirmed":
            block.confirmed_by = data.actor_user_id
            block.confirmed_at = func.now()
        else:
            block.confirmed_by = None
            block.confirmed_at = None
        await self.session.flush()
        return await self.get(block_id)
