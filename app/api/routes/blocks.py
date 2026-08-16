from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import SessionDep
from app.repositories.blocks import BlockRepository
from app.schemas.block import BlockCreate, BlockRead, GeometryValidationResult, LocationResolution
from app.schemas.common import PolygonGeoJSON, SpatialValidationDecision
from app.services.blocks import BlockService
from app.services.gis import GISService

router = APIRouter()


def serialize_block(block) -> BlockRead:
    return BlockRead.model_validate({**block.__dict__, "boundary": block.boundary_geojson})


@router.post("", response_model=BlockRead, status_code=status.HTTP_201_CREATED)
async def create_block(payload: BlockCreate, session: SessionDep):
    return serialize_block(await BlockService(session).create(payload))


@router.post("/validate-geometry", response_model=GeometryValidationResult)
async def validate_geometry(payload: PolygonGeoJSON, session: SessionDep):
    return await GISService(session).validate_polygon(payload)


@router.get("/by-location", response_model=LocationResolution)
async def find_by_location(
    session: SessionDep,
    longitude: float = Query(ge=-180, le=180),
    latitude: float = Query(ge=-90, le=90),
    accuracy_m: float = Query(default=0, ge=0, le=10000),
):
    matches = await BlockRepository(session).find_by_location(longitude, latitude, accuracy_m)
    if not matches:
        resolution_status = "not_found"
    elif len(matches) > 1:
        resolution_status = "ambiguous"
    elif not matches[0]["contains_point"] or matches[0]["distance_to_boundary_m"] <= accuracy_m:
        resolution_status = "confirmation_required"
    else:
        resolution_status = "matched"
    return LocationResolution(
        status=resolution_status,
        accuracy_m=accuracy_m,
        candidates=matches,
    )


@router.get("/{block_id}", response_model=BlockRead)
async def get_block(block_id: UUID, session: SessionDep):
    block = await BlockRepository(session).get(block_id)
    if block is None:
        raise HTTPException(status_code=404, detail="Blok tidak ditemukan")
    return serialize_block(block)


@router.patch("/{block_id}/validation", response_model=BlockRead)
async def validate_block_boundary(
    block_id: UUID, payload: SpatialValidationDecision, session: SessionDep
):
    return serialize_block(await BlockService(session).validate_boundary(block_id, payload))
