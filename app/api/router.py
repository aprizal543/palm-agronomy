from fastapi import APIRouter

from app.api.routes import blocks, farms, health, knowledge, telegram, users

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(farms.router, prefix="/farms", tags=["farms"])
api_router.include_router(blocks.router, prefix="/blocks", tags=["blocks"])
api_router.include_router(telegram.router, prefix="/telegram", tags=["telegram"])
api_router.include_router(knowledge.router, prefix="/knowledge", tags=["knowledge"])
