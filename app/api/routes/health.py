import asyncio

from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.version import APP_VERSION

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "version": APP_VERSION}


@router.get("/health/live")
async def liveness() -> dict[str, str]:
    return {"status": "alive", "version": APP_VERSION}


async def _check_database(session: SessionDep) -> None:
    settings = get_settings()
    async with asyncio.timeout(settings.readiness_timeout_s):
        await session.execute(text("select 1"))


@router.get("/health/ready")
async def readiness(session: SessionDep) -> dict[str, str]:
    try:
        await _check_database(session)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Service belum siap") from exc
    return {"status": "ready", "database": "reachable", "version": APP_VERSION}


@router.get("/health/database")
async def database_health(session: SessionDep) -> dict[str, str]:
    try:
        await _check_database(session)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Database tidak tersedia") from exc
    return {"status": "ok", "database": "reachable"}
