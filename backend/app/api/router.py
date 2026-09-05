from fastapi import APIRouter

from app.api.v1.router import router as v1_router
from app.api.v1.routes.health import router as health_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["health"])
api_router.include_router(v1_router, prefix="/api/v1")
