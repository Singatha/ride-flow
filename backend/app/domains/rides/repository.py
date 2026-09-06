import uuid
from dataclasses import dataclass
from typing import Any

from geoalchemy2 import Geometry
from sqlalchemy import Select, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.domains.drivers.models import DriverProfile
from app.domains.rides.models import PricingRule, Ride, RideStatus, RideType


@dataclass(frozen=True)
class LocatedRide:
    ride: Ride
    currency: str
    pickup_latitude: float
    pickup_longitude: float
    destination_latitude: float
    destination_longitude: float


class PricingRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active(self, ride_type: RideType) -> PricingRule | None:
        result = await self.session.execute(
            select(PricingRule).where(
                PricingRule.ride_type == ride_type,
                PricingRule.is_active.is_(True),
            )
        )
        return result.scalar_one_or_none()


class RideRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, ride: Ride) -> None:
        self.session.add(ride)

    async def get_by_id(self, ride_id: uuid.UUID, *, for_update: bool = False) -> Ride | None:
        statement = select(Ride).where(Ride.id == ride_id)
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_rider(self, rider_id: uuid.UUID) -> list[LocatedRide]:
        statement = self._located_statement().where(Ride.rider_id == rider_id)
        return await self._located_results(statement.order_by(Ride.requested_at.desc()))

    async def list_for_driver(self, driver_id: uuid.UUID) -> list[LocatedRide]:
        statement = self._located_statement().where(Ride.driver_id == driver_id)
        return await self._located_results(statement.order_by(Ride.requested_at.desc()))

    async def list_searching(self, ride_type: RideType, *, limit: int = 25) -> list[LocatedRide]:
        statement = (
            self._located_statement()
            .where(Ride.status == RideStatus.SEARCHING, Ride.ride_type == ride_type)
            .order_by(Ride.requested_at)
            .limit(limit)
        )
        return await self._located_results(statement)

    async def locate(self, ride_id: uuid.UUID) -> LocatedRide:
        result = await self._located_results(self._located_statement().where(Ride.id == ride_id))
        return result[0]

    async def distance_metres(
        self,
        pickup_latitude: float,
        pickup_longitude: float,
        destination_latitude: float,
        destination_longitude: float,
    ) -> float:
        pickup = func.ST_GeogFromText(f"SRID=4326;POINT({pickup_longitude} {pickup_latitude})")
        destination = func.ST_GeogFromText(
            f"SRID=4326;POINT({destination_longitude} {destination_latitude})"
        )
        result = await self.session.execute(select(func.ST_Distance(pickup, destination)))
        return float(result.scalar_one())

    @staticmethod
    def _located_statement() -> Select[tuple[Any, ...]]:
        pickup_geometry = cast(Ride.pickup_location, Geometry(geometry_type="POINT", srid=4326))
        destination_geometry = cast(
            Ride.destination_location, Geometry(geometry_type="POINT", srid=4326)
        )
        return (
            select(
                Ride,
                PricingRule.currency.label("currency"),
                func.ST_Y(pickup_geometry).label("pickup_latitude"),
                func.ST_X(pickup_geometry).label("pickup_longitude"),
                func.ST_Y(destination_geometry).label("destination_latitude"),
                func.ST_X(destination_geometry).label("destination_longitude"),
            )
            .join(PricingRule, PricingRule.id == Ride.pricing_rule_id)
            .options(
                selectinload(Ride.driver).selectinload(DriverProfile.user),
                selectinload(Ride.vehicle),
            )
        )

    async def _located_results(self, statement: Select[tuple[Any, ...]]) -> list[LocatedRide]:
        result = await self.session.execute(statement)
        return [
            LocatedRide(
                ride=row[0],
                currency=str(row.currency),
                pickup_latitude=float(row.pickup_latitude),
                pickup_longitude=float(row.pickup_longitude),
                destination_latitude=float(row.destination_latitude),
                destination_longitude=float(row.destination_longitude),
            )
            for row in result
        ]
