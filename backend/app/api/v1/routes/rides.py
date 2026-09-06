import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_ride_service
from app.domains.auth.dependencies import RoleChecker, get_current_user
from app.domains.rides.schemas import FareEstimateResponse, RideRequest, RideResponse
from app.domains.rides.service import RideService
from app.domains.users.models import User, UserRole

router = APIRouter(prefix="/rides")
require_rider = RoleChecker(UserRole.RIDER)
require_driver = RoleChecker(UserRole.DRIVER)


@router.post("/estimate", response_model=FareEstimateResponse)
async def estimate_ride(
    data: RideRequest,
    _rider: Annotated[User, Depends(require_rider)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> FareEstimateResponse:
    return await service.estimate(data)


@router.get("/available", response_model=list[RideResponse])
async def list_available_rides(
    driver: Annotated[User, Depends(require_driver)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> list[RideResponse]:
    return await service.list_available(driver.id)


@router.post("", response_model=RideResponse, status_code=status.HTTP_201_CREATED)
async def request_ride(
    data: RideRequest,
    rider: Annotated[User, Depends(require_rider)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.create(rider, data)


@router.get("", response_model=list[RideResponse])
async def list_my_rides(
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> list[RideResponse]:
    return await service.list_for_user(user)


@router.get("/{ride_id}", response_model=RideResponse)
async def get_ride(
    ride_id: uuid.UUID,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.get(user, ride_id)


@router.post("/{ride_id}/accept", response_model=RideResponse)
async def accept_ride(
    ride_id: uuid.UUID,
    driver: Annotated[User, Depends(require_driver)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.accept(driver.id, ride_id)


@router.post("/{ride_id}/cancel", response_model=RideResponse)
async def cancel_ride(
    ride_id: uuid.UUID,
    rider: Annotated[User, Depends(require_rider)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.cancel(rider.id, ride_id)


@router.post("/{ride_id}/arriving", response_model=RideResponse)
async def mark_driver_arriving(
    ride_id: uuid.UUID,
    driver: Annotated[User, Depends(require_driver)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.mark_arriving(driver.id, ride_id)


@router.post("/{ride_id}/arrive", response_model=RideResponse)
async def mark_driver_arrived(
    ride_id: uuid.UUID,
    driver: Annotated[User, Depends(require_driver)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.mark_arrived(driver.id, ride_id)


@router.post("/{ride_id}/start", response_model=RideResponse)
async def start_ride(
    ride_id: uuid.UUID,
    driver: Annotated[User, Depends(require_driver)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.start(driver.id, ride_id)


@router.post("/{ride_id}/complete", response_model=RideResponse)
async def complete_ride(
    ride_id: uuid.UUID,
    driver: Annotated[User, Depends(require_driver)],
    service: Annotated[RideService, Depends(get_ride_service)],
) -> RideResponse:
    return await service.complete(driver.id, ride_id)
