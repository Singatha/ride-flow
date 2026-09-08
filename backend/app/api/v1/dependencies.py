from typing import Annotated

from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.cache.redis import get_redis_client
from app.core.config import Settings, get_settings
from app.database.session import get_db_session
from app.domains.auth.service import AuthService
from app.domains.drivers.service import DriverService, VehicleService
from app.domains.matching.service import MatchingService
from app.domains.rides.service import RideService
from app.domains.users.service import UserService


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> AuthService:
    return AuthService(session, settings)


def get_user_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> UserService:
    return UserService(session)


def get_driver_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DriverService:
    return DriverService(session)


def get_vehicle_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> VehicleService:
    return VehicleService(session)


def get_ride_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RideService:
    return RideService(session)


def get_matching_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    redis: Annotated[Redis, Depends(get_redis_client)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MatchingService:
    return MatchingService(session, redis, settings)
