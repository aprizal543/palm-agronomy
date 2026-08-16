from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.observability import configure_logging
from app.core.version import APP_VERSION
from app.db.session import engine

settings = get_settings()
configure_logging(level=settings.log_level, json_logs=settings.json_logs)


@asynccontextmanager
async def lifespan(_: FastAPI):
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=APP_VERSION,
    description="Sprint 7: deployment readiness, observability, and conversational agronomy",
    lifespan=lifespan,
)
app.include_router(api_router, prefix=settings.api_v1_prefix)
