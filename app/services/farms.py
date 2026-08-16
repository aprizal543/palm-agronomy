from fastapi import HTTPException, status
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.farms import FarmRepository
from app.schemas.common import SpatialValidationDecision
from app.schemas.farm import FarmBoundaryUpdate, FarmCreate


class FarmService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repository = FarmRepository(session)

    async def create(self, data: FarmCreate):
        try:
            farm = await self.repository.create(data)
            await self.session.commit()
            return farm
        except IntegrityError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Nama kebun sudah digunakan oleh pemilik ini atau referensi tidak valid",
            ) from exc

    async def update_boundary(self, farm_id, data: FarmBoundaryUpdate):
        if not await self.repository.has_write_access(farm_id, data.actor_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Tidak memiliki akses edit"
            )
        try:
            farm = await self.repository.update_boundary(farm_id, data)
            if farm is None:
                raise HTTPException(status_code=404, detail="Kebun tidak ditemukan")
            await self.session.commit()
            return farm
        except DBAPIError as exc:
            await self.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Farm polygon ditolak oleh validasi PostGIS",
            ) from exc

    async def validate_boundary(self, farm_id, data: SpatialValidationDecision):
        if not await self.repository.has_validation_access(farm_id, data.actor_user_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail="Akses validator diperlukan"
            )
        current = await self.repository.get(farm_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Kebun tidak ditemukan")
        if data.decision == "confirmed" and current.boundary is None:
            raise HTTPException(
                status_code=422, detail="Farm belum memiliki polygon untuk divalidasi"
            )
        farm = await self.repository.validate_boundary(farm_id, data)
        if farm is None:
            raise HTTPException(status_code=404, detail="Kebun tidak ditemukan")
        await self.session.commit()
        return farm
