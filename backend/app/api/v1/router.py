from fastapi import APIRouter

from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.drivers import router as drivers_router
from app.api.v1.routes.rides import router as rides_router
from app.api.v1.routes.users import router as users_router
from app.api.v1.routes.vehicles import router as vehicles_router

router = APIRouter()
router.include_router(auth_router, tags=["authentication"])
router.include_router(users_router, tags=["users"])
router.include_router(drivers_router, tags=["drivers"])
router.include_router(vehicles_router, tags=["vehicles"])
router.include_router(rides_router, tags=["rides"])
