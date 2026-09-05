import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_driver_service
from app.domains.auth.dependencies import RoleChecker
from app.domains.drivers.models import DriverVerificationStatus
from app.domains.drivers.schemas import (
    DriverLocationResponse,
    DriverLocationUpdate,
    DriverProfileCreate,
    DriverProfileResponse,
    DriverProfileUpdate,
    DriverVerificationUpdate,
)
from app.domains.drivers.service import DriverService
from app.domains.users.models import User, UserRole

router = APIRouter(prefix="/drivers")
require_driver = RoleChecker(UserRole.DRIVER)
require_admin = RoleChecker(UserRole.ADMIN)


@router.post("/profile", response_model=DriverProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    data: DriverProfileCreate,
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverProfileResponse:
    return DriverProfileResponse.model_validate(await service.create_profile(user, data))


@router.get("/me", response_model=DriverProfileResponse)
async def get_me(
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverProfileResponse:
    return DriverProfileResponse.model_validate(await service.get_profile(user.id))


@router.patch("/me", response_model=DriverProfileResponse)
async def update_me(
    data: DriverProfileUpdate,
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverProfileResponse:
    return DriverProfileResponse.model_validate(await service.update_profile(user.id, data))


@router.put("/status/online", response_model=DriverProfileResponse)
async def go_online(
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverProfileResponse:
    return DriverProfileResponse.model_validate(await service.go_online(user.id))


@router.put("/status/offline", response_model=DriverProfileResponse)
async def go_offline(
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverProfileResponse:
    return DriverProfileResponse.model_validate(await service.go_offline(user.id))


@router.put("/location", response_model=DriverLocationResponse)
async def update_location(
    data: DriverLocationUpdate,
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverLocationResponse:
    return await service.update_location(user.id, data)


@router.put("/{driver_id}/verification", response_model=DriverProfileResponse)
async def set_verification(
    driver_id: uuid.UUID,
    data: DriverVerificationUpdate,
    _admin: Annotated[User, Depends(require_admin)],
    service: Annotated[DriverService, Depends(get_driver_service)],
) -> DriverProfileResponse:
    profile = await service.set_verification(driver_id, DriverVerificationStatus(data.status))
    return DriverProfileResponse.model_validate(profile)
