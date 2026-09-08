import uuid
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.domains.rides.models import Ride, RideStatus, RideType


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class RideRequest(BaseModel):
    pickup: Coordinates
    destination: Coordinates
    ride_type: RideType = RideType.STANDARD

    @model_validator(mode="after")
    def require_distinct_locations(self) -> "RideRequest":
        if self.pickup == self.destination:
            raise ValueError("pickup and destination must be different")
        return self


class FareEstimateResponse(BaseModel):
    ride_type: RideType
    estimated_distance_km: Decimal
    estimated_duration_minutes: Decimal
    estimated_fare: Decimal
    currency: str
    available_driver_count: int


class AssignedDriverResponse(BaseModel):
    id: uuid.UUID
    first_name: str
    last_name: str
    phone_number: str | None


class AssignedVehicleResponse(BaseModel):
    id: uuid.UUID
    make: str
    model: str
    color: str
    license_plate: str
    category: str


class RideResponse(BaseModel):
    id: uuid.UUID
    rider_id: uuid.UUID
    driver_id: uuid.UUID | None
    vehicle_id: uuid.UUID | None
    driver: AssignedDriverResponse | None
    vehicle: AssignedVehicleResponse | None
    status: RideStatus
    ride_type: RideType
    pickup: Coordinates
    destination: Coordinates
    estimated_distance_km: Decimal
    estimated_duration_minutes: Decimal
    estimated_fare: Decimal
    final_fare: Decimal | None
    currency: str
    requested_at: datetime
    accepted_at: datetime | None
    arriving_at: datetime | None
    arrived_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_ride(
        cls,
        ride: Ride,
        *,
        pickup_latitude: float,
        pickup_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
        currency: str,
    ) -> "RideResponse":
        return cls(
            id=ride.id,
            rider_id=ride.rider_id,
            driver_id=ride.driver_id,
            vehicle_id=ride.vehicle_id,
            driver=(
                AssignedDriverResponse(
                    id=ride.driver.id,
                    first_name=ride.driver.user.first_name,
                    last_name=ride.driver.user.last_name,
                    phone_number=ride.driver.user.phone_number,
                )
                if ride.driver is not None
                else None
            ),
            vehicle=(
                AssignedVehicleResponse(
                    id=ride.vehicle.id,
                    make=ride.vehicle.make,
                    model=ride.vehicle.model,
                    color=ride.vehicle.color,
                    license_plate=ride.vehicle.license_plate,
                    category=ride.vehicle.category.value,
                )
                if ride.vehicle is not None
                else None
            ),
            status=ride.status,
            ride_type=ride.ride_type,
            pickup=Coordinates(latitude=pickup_latitude, longitude=pickup_longitude),
            destination=Coordinates(latitude=destination_latitude, longitude=destination_longitude),
            estimated_distance_km=ride.estimated_distance_km,
            estimated_duration_minutes=ride.estimated_duration_minutes,
            estimated_fare=ride.estimated_fare,
            final_fare=ride.final_fare,
            currency=currency,
            requested_at=ride.requested_at,
            accepted_at=ride.accepted_at,
            arriving_at=ride.arriving_at,
            arrived_at=ride.arrived_at,
            started_at=ride.started_at,
            completed_at=ride.completed_at,
            cancelled_at=ride.cancelled_at,
            created_at=ride.created_at,
            updated_at=ride.updated_at,
        )


class RideOfferResponse(BaseModel):
    ride: RideResponse
    distance_m: Decimal
    offered_at: datetime
    expires_at: datetime
