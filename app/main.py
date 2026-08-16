from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version="0.6.0",
    description="Sprint 5: contextual production analysis and verified agronomy retrieval",
    lifespan=lifespan,
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
