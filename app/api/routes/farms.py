from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.api.deps import SessionDep
from app.repositories.farms import FarmRepository
from app.schemas.common import SpatialValidationDecision
from app.schemas.farm import FarmBoundaryUpdate, FarmCreate, FarmRead
from app.services.farms import FarmService

router = APIRouter()


def serialize_farm(farm) -> FarmRead:
    return FarmRead.model_validate(
        {
            **farm.__dict__,
            "boundary": getattr(farm, "boundary_geojson", None),
            "location_point": getattr(farm, "point_geojson", None),
        }
    )


@router.post("", response_model=FarmRead, status_code=status.HTTP_201_CREATED)
async def create_farm(payload: FarmCreate, session: SessionDep):
    return serialize_farm(await FarmService(session).create(payload))


@router.get("/{farm_id}", response_model=FarmRead)
async def get_farm(farm_id: UUID, session: SessionDep):
    farm = await FarmRepository(session).get(farm_id)
    if farm is None:
        raise HTTPException(status_code=404, detail="Kebun tidak ditemukan")
    return serialize_farm(farm)


@router.patch("/{farm_id}/boundary", response_model=FarmRead)
async def update_farm_boundary(farm_id: UUID, payload: FarmBoundaryUpdate, session: SessionDep):
    return serialize_farm(await FarmService(session).update_boundary(farm_id, payload))


@router.patch("/{farm_id}/validation", response_model=FarmRead)
async def validate_farm_boundary(
    farm_id: UUID, payload: SpatialValidationDecision, session: SessionDep
):
    return serialize_farm(await FarmService(session).validate_boundary(farm_id, payload))
