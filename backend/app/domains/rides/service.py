import uuid
from decimal import ROUND_HALF_UP, Decimal

from geoalchemy2.elements import WKTElement
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ActiveRideExists,
    DriverProfileNotFound,
    DriverUnavailable,
    PricingRuleNotFound,
    RideAccessDenied,
    RideNotFound,
)
from app.domains.drivers.models import DriverProfile, DriverStatus, VehicleCategory
from app.domains.drivers.repository import (
    DriverLocationRepository,
    DriverRepository,
    VehicleRepository,
)
from app.domains.rides.models import PricingRule, Ride, RideStatus, RideType
from app.domains.rides.repository import LocatedRide, PricingRuleRepository, RideRepository
from app.domains.rides.schemas import FareEstimateResponse, RideRequest, RideResponse
from app.domains.users.models import User, UserRole

MONEY_QUANTUM = Decimal("0.01")
DISTANCE_QUANTUM = Decimal("0.001")
DURATION_QUANTUM = Decimal("0.01")


class RideService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.rides = RideRepository(session)
        self.pricing = PricingRuleRepository(session)
        self.drivers = DriverRepository(session)
        self.locations = DriverLocationRepository(session)
        self.vehicles = VehicleRepository(session)

    async def estimate(self, data: RideRequest) -> FareEstimateResponse:
        rule, distance_km, duration_minutes, fare = await self._calculate(data)
        available_count = await self.locations.count_available_nearby(
            data.pickup.latitude,
            data.pickup.longitude,
            category=VehicleCategory(data.ride_type.value),
        )
        return FareEstimateResponse(
            ride_type=data.ride_type,
            estimated_distance_km=distance_km,
            estimated_duration_minutes=duration_minutes,
            estimated_fare=fare,
            currency=rule.currency,
            available_driver_count=available_count,
        )

    async def create(self, rider: User, data: RideRequest) -> RideResponse:
        rule, distance_km, duration_minutes, fare = await self._calculate(data)
        ride = Ride(
            rider_id=rider.id,
            pricing_rule_id=rule.id,
            status=RideStatus.REQUESTED,
            ride_type=data.ride_type,
            pickup_location=self._point(data.pickup.longitude, data.pickup.latitude),
            destination_location=self._point(data.destination.longitude, data.destination.latitude),
            estimated_distance_km=distance_km,
            estimated_duration_minutes=duration_minutes,
            estimated_fare=fare,
        )
        ride.begin_search()
        self.rides.add(ride)
        try:
            await self.session.flush()
            await self.session.refresh(ride)
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ActiveRideExists("Rider already has an active ride") from exc
        return await self._response_for(ride.id)

    async def list_for_user(self, user: User) -> list[RideResponse]:
        if user.role is UserRole.RIDER:
            rides = await self.rides.list_for_rider(user.id)
        elif user.role is UserRole.DRIVER:
            profile = await self.drivers.get_by_user_id(user.id)
            if profile is None:
                raise DriverProfileNotFound("Create a driver profile first")
            rides = await self.rides.list_for_driver(profile.id)
        else:
            raise RideAccessDenied("Administrators do not have a personal ride history")
        return [self._response(located) for located in rides]

    async def list_available(self, user_id: uuid.UUID) -> list[RideResponse]:
        profile = await self.drivers.get_by_user_id(user_id)
        if profile is None:
            raise DriverProfileNotFound("Create a driver profile first")
        if profile.status is not DriverStatus.AVAILABLE:
            raise DriverUnavailable("Driver must be available to view open ride requests")
        vehicle = await self.vehicles.get_active_for_driver(profile.id)
        if vehicle is None:
            raise DriverUnavailable("Driver requires an active vehicle")
        return [
            self._response(located)
            for located in await self.rides.list_searching(RideType(vehicle.category.value))
        ]

    async def get(self, user: User, ride_id: uuid.UUID) -> RideResponse:
        ride = await self._ride(ride_id)
        if user.role is UserRole.RIDER and ride.rider_id != user.id:
            raise RideAccessDenied("Ride does not belong to this rider")
        if user.role is UserRole.DRIVER:
            profile = await self.drivers.get_by_user_id(user.id)
            if profile is None or ride.driver_id != profile.id:
                raise RideAccessDenied("Ride is not assigned to this driver")
        return await self._response_for(ride.id)

    async def accept(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride = await self._locked_ride(ride_id)
        profile = await self.drivers.get_by_user_id(user_id, for_update=True)
        if profile is None:
            raise DriverProfileNotFound("Create a driver profile first")
        if profile.status is not DriverStatus.AVAILABLE:
            raise DriverUnavailable("Driver must be available to accept a ride")
        vehicle = await self.vehicles.get_active_for_driver(profile.id)
        if vehicle is None or vehicle.category.value != ride.ride_type.value:
            raise DriverUnavailable("Active vehicle does not support this ride type")
        ride.accept(profile.id, vehicle.id)
        profile.status = DriverStatus.RESERVED
        await self._commit()
        return await self._response_for(ride.id)

    async def cancel(self, rider_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride = await self._locked_ride(ride_id)
        if ride.rider_id != rider_id:
            raise RideAccessDenied("Ride does not belong to this rider")
        driver = None
        if ride.driver_id is not None:
            driver = await self.drivers.get_by_id(ride.driver_id, for_update=True)
        ride.cancel()
        if driver is not None:
            driver.status = DriverStatus.AVAILABLE
        await self._commit()
        return await self._response_for(ride.id)

    async def mark_arriving(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride, _ = await self._assigned_ride(user_id, ride_id)
        ride.mark_arriving()
        await self._commit()
        return await self._response_for(ride.id)

    async def mark_arrived(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride, _ = await self._assigned_ride(user_id, ride_id)
        ride.mark_arrived()
        await self._commit()
        return await self._response_for(ride.id)

    async def start(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride, driver = await self._assigned_ride(user_id, ride_id)
        ride.start()
        driver.status = DriverStatus.ON_TRIP
        await self._commit()
        return await self._response_for(ride.id)

    async def complete(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride, driver = await self._assigned_ride(user_id, ride_id)
        ride.complete(ride.estimated_fare)
        driver.status = DriverStatus.AVAILABLE
        await self._commit()
        return await self._response_for(ride.id)

    async def _calculate(self, data: RideRequest) -> tuple[PricingRule, Decimal, Decimal, Decimal]:
        rule = await self.pricing.get_active(data.ride_type)
        if rule is None:
            raise PricingRuleNotFound(f"No active pricing rule exists for {data.ride_type.value}")
        distance_metres = await self.rides.distance_metres(
            data.pickup.latitude,
            data.pickup.longitude,
            data.destination.latitude,
            data.destination.longitude,
        )
        raw_distance_km = Decimal(str(distance_metres)) / Decimal(1000)
        distance_km = raw_distance_km.quantize(DISTANCE_QUANTUM, ROUND_HALF_UP)
        duration_minutes = (distance_km / rule.average_speed_kph * Decimal(60)).quantize(
            DURATION_QUANTUM, ROUND_HALF_UP
        )
        fare = (
            rule.base_fare
            + distance_km * rule.cost_per_km
            + duration_minutes * rule.cost_per_minute
        ).quantize(MONEY_QUANTUM, ROUND_HALF_UP)
        return rule, distance_km, duration_minutes, fare

    async def _ride(self, ride_id: uuid.UUID) -> Ride:
        ride = await self.rides.get_by_id(ride_id)
        if ride is None:
            raise RideNotFound("Ride does not exist")
        return ride

    async def _locked_ride(self, ride_id: uuid.UUID) -> Ride:
        ride = await self.rides.get_by_id(ride_id, for_update=True)
        if ride is None:
            raise RideNotFound("Ride does not exist")
        return ride

    async def _assigned_ride(
        self, user_id: uuid.UUID, ride_id: uuid.UUID
    ) -> tuple[Ride, DriverProfile]:
        ride = await self._locked_ride(ride_id)
        driver = await self.drivers.get_by_user_id(user_id, for_update=True)
        if driver is None:
            raise DriverProfileNotFound("Create a driver profile first")
        if ride.driver_id != driver.id:
            raise RideAccessDenied("Ride is not assigned to this driver")
        return ride, driver

    async def _commit(self) -> None:
        try:
            await self.session.flush()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise

    async def _response_for(self, ride_id: uuid.UUID) -> RideResponse:
        return self._response(await self.rides.locate(ride_id))

    @staticmethod
    def _response(located: LocatedRide) -> RideResponse:
        return RideResponse.from_ride(
            located.ride,
            pickup_latitude=located.pickup_latitude,
            pickup_longitude=located.pickup_longitude,
            destination_latitude=located.destination_latitude,
            destination_longitude=located.destination_longitude,
            currency=located.currency,
        )

    @staticmethod
    def _point(longitude: float, latitude: float) -> WKTElement:
        return WKTElement(f"POINT({longitude} {latitude})", srid=4326)
