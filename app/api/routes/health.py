from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.deps import SessionDep

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/database")
async def database_health(session: SessionDep) -> dict[str, str]:
    try:
        await session.execute(text("select 1"))
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database tidak tersedia") from exc
    return {"status": "ok", "database": "reachable"}

