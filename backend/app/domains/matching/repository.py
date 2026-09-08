import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.rides.models import MatchAttemptOutcome, RideMatchAttempt


class MatchAttemptRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    def add(self, attempt: RideMatchAttempt) -> None:
        self.session.add(attempt)

    async def attempted_driver_ids(self, ride_id: uuid.UUID) -> set[uuid.UUID]:
        result = await self.session.execute(
            select(RideMatchAttempt.driver_id).where(RideMatchAttempt.ride_id == ride_id)
        )
        return set(result.scalars().all())

    async def get(
        self,
        ride_id: uuid.UUID,
        driver_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> RideMatchAttempt | None:
        statement = select(RideMatchAttempt).where(
            RideMatchAttempt.ride_id == ride_id,
            RideMatchAttempt.driver_id == driver_id,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def get_offered_for_ride(
        self, ride_id: uuid.UUID, *, for_update: bool = False
    ) -> RideMatchAttempt | None:
        statement = select(RideMatchAttempt).where(
            RideMatchAttempt.ride_id == ride_id,
            RideMatchAttempt.outcome == MatchAttemptOutcome.OFFERED,
        )
        if for_update:
            statement = statement.with_for_update()
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()

    async def list_for_ride(self, ride_id: uuid.UUID) -> Sequence[RideMatchAttempt]:
        result = await self.session.execute(
            select(RideMatchAttempt)
            .where(RideMatchAttempt.ride_id == ride_id)
            .order_by(RideMatchAttempt.offered_at)
        )
        return result.scalars().all()
