import uuid
from collections.abc import Sequence
from datetime import datetime

from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.drivers.models import (
    DriverLocation,
    DriverProfile,
    DriverStatus,
    DriverVerificationStatus,
    Vehicle,
)
from app.domains.drivers.schemas import DriverLocationUpdate, NearbyDriver
from app.domains.users.models import User


class DriverRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, profile: DriverProfile) -> None:
        self.session.add(profile)

    async def get_by_user_id(
        self, user_id: uuid.UUID, *, for_update: bool = False
    ) -> DriverProfile | None:
        statement = select(DriverProfile).where(DriverProfile.user_id == user_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_by_id(
        self, driver_id: uuid.UUID, *, for_update: bool = False
    ) -> DriverProfile | None:
        statement = select(DriverProfile).where(DriverProfile.id == driver_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()


class VehicleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, vehicle: Vehicle) -> None:
        self.session.add(vehicle)

    async def list_for_driver(self, driver_id: uuid.UUID) -> Sequence[Vehicle]:
        result = await self.session.execute(
            select(Vehicle)
            .where(Vehicle.driver_id == driver_id)
            .order_by(Vehicle.created_at.desc())
        )
        return result.scalars().all()

    async def get_for_driver(self, vehicle_id: uuid.UUID, driver_id: uuid.UUID) -> Vehicle | None:
        result = await self.session.execute(
            select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.driver_id == driver_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_driver(self, driver_id: uuid.UUID) -> Vehicle | None:
        result = await self.session.execute(
            select(Vehicle).where(Vehicle.driver_id == driver_id, Vehicle.is_active.is_(True))
        )
        return result.scalar_one_or_none()

    async def deactivate_for_driver(self, driver_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Vehicle).where(Vehicle.driver_id == driver_id).values(is_active=False)
        )


class DriverLocationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def exists_for_driver(self, driver_id: uuid.UUID) -> bool:
        result = await self.session.execute(
            select(DriverLocation.driver_id).where(DriverLocation.driver_id == driver_id)
        )
        return result.scalar_one_or_none() is not None

    async def upsert(
        self, driver_id: uuid.UUID, data: DriverLocationUpdate, recorded_at: datetime
    ) -> None:
        point = WKTElement(f"POINT({data.longitude} {data.latitude})", srid=4326)
        statement = insert(DriverLocation).values(
            driver_id=driver_id,
            location=point,
            heading=data.heading,
            speed_kph=data.speed_kph,
            accuracy_m=data.accuracy_m,
            recorded_at=recorded_at,
        )
        await self.session.execute(
            statement.on_conflict_do_update(
                index_elements=[DriverLocation.driver_id],
                set_={
                    "location": point,
                    "heading": data.heading,
                    "speed_kph": data.speed_kph,
                    "accuracy_m": data.accuracy_m,
                    "recorded_at": recorded_at,
                    "updated_at": func.now(),
                },
            )
        )

    async def find_available_nearby(
        self,
        latitude: float,
        longitude: float,
        *,
        radius_m: float = 5_000,
        limit: int = 20,
    ) -> list[NearbyDriver]:
        pickup = func.ST_GeogFromText(f"SRID=4326;POINT({longitude} {latitude})")
        distance = func.ST_Distance(DriverLocation.location, pickup)
        result = await self.session.execute(
            select(
                DriverProfile.id.label("driver_id"),
                DriverProfile.user_id,
                distance.label("distance_m"),
            )
            .join(DriverLocation, DriverLocation.driver_id == DriverProfile.id)
            .join(User, User.id == DriverProfile.user_id)
            .join(Vehicle, Vehicle.driver_id == DriverProfile.id)
            .where(
                DriverProfile.status == DriverStatus.AVAILABLE,
                DriverProfile.verification_status == DriverVerificationStatus.APPROVED,
                User.is_active.is_(True),
                Vehicle.is_active.is_(True),
                func.ST_DWithin(DriverLocation.location, pickup, radius_m),
            )
            .order_by(distance)
            .limit(limit)
        )
        return [
            NearbyDriver(
                driver_id=row.driver_id,
                user_id=row.user_id,
                distance_m=float(row.distance_m),
            )
            for row in result
        ]
