from fastapi import HTTPException, status
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.blocks import BlockRepository
from app.repositories.farms import FarmRepository
from app.schemas.block import BlockCreate
from app.schemas.common import SpatialValidationDecision


class BlockService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.blocks = BlockRepository(session)
        self.farms = FarmRepository(session)

    async def create(self, data: BlockCreate):
        if not await self.farms.has_write_access(data.farm_id, data.actor_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tidak memiliki akses edit")
        try:
            block = await self.blocks.create(data)
            await self.session.commit()
            return block
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Kode blok sudah digunakan atau referensi data tidak valid",
            ) from exc
        except DBAPIError as exc:
            await self.session.rollback()
            message = str(exc.orig)
            safe_detail = next(
                (
                    item
                    for item in (
                        "Block boundary must be covered by the farm boundary",
                        "Block boundary overlaps another active block by more than 1 m2",
                        "Block boundary is invalid",
                    )
                    if item.lower() in message.lower()
                ),
                "Polygon blok ditolak oleh validasi spasial",
            )
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=safe_detail) from exc

    async def validate_boundary(self, block_id, data: SpatialValidationDecision):
        block = await self.blocks.get(block_id)
        if block is None:
            raise HTTPException(status_code=404, detail="Blok tidak ditemukan")
        if not await self.farms.has_validation_access(block.farm_id, data.actor_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Akses validator diperlukan")
        block = await self.blocks.validate_boundary(block_id, data)
        await self.session.commit()
        return block
