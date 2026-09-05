import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.v1.dependencies import get_vehicle_service
from app.domains.auth.dependencies import RoleChecker
from app.domains.drivers.schemas import VehicleCreate, VehicleResponse, VehicleUpdate
from app.domains.drivers.service import VehicleService
from app.domains.users.models import User, UserRole

router = APIRouter(prefix="/vehicles")
require_driver = RoleChecker(UserRole.DRIVER)


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    data: VehicleCreate,
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> VehicleResponse:
    return VehicleResponse.model_validate(await service.create(user.id, data))


@router.get("/me", response_model=list[VehicleResponse])
async def list_my_vehicles(
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> list[VehicleResponse]:
    vehicles = await service.list_for_driver(user.id)
    return [VehicleResponse.model_validate(vehicle) for vehicle in vehicles]


@router.patch("/{vehicle_id}", response_model=VehicleResponse)
async def update_vehicle(
    vehicle_id: uuid.UUID,
    data: VehicleUpdate,
    user: Annotated[User, Depends(require_driver)],
    service: Annotated[VehicleService, Depends(get_vehicle_service)],
) -> VehicleResponse:
    return VehicleResponse.model_validate(await service.update(user.id, vehicle_id, data))
