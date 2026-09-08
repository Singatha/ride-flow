import uuid
from datetime import UTC, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from math import ceil

from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import (
    DriverProfileNotFound,
    DriverUnavailable,
    MatchingUnavailable,
    RideAccessDenied,
    RideNotFound,
    RideOfferNotFound,
)
from app.domains.drivers.models import DriverStatus, VehicleCategory
from app.domains.drivers.repository import (
    DriverLocationRepository,
    DriverRepository,
    VehicleRepository,
)
from app.domains.matching.repository import MatchAttemptRepository
from app.domains.matching.store import MatchingStore, OfferState
from app.domains.rides.models import MatchAttemptOutcome, RideMatchAttempt, RideStatus
from app.domains.rides.repository import RideRepository
from app.domains.rides.schemas import RideOfferResponse, RideRequest, RideResponse
from app.domains.rides.service import RideService
from app.domains.users.models import User

DISTANCE_QUANTUM = Decimal("0.01")


class MatchingService:
    def __init__(self, session: AsyncSession, redis: Redis, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.store = MatchingStore(
            redis,
            state_ttl_seconds=settings.matching_state_ttl_seconds,
            lock_ttl_seconds=settings.matching_lock_ttl_seconds,
        )
        self.rides = RideRepository(session)
        self.drivers = DriverRepository(session)
        self.vehicles = VehicleRepository(session)
        self.locations = DriverLocationRepository(session)
        self.attempts = MatchAttemptRepository(session)
        self.ride_service = RideService(session)

    async def create_ride(self, rider: User, data: RideRequest) -> RideResponse:
        ride = await self.ride_service.create(rider, data)
        try:
            await self.ensure_offer(ride.id)
        except MatchingUnavailable:
            pass
        return ride

    async def ensure_offer(
        self, ride_id: uuid.UUID, *, now: datetime | None = None
    ) -> OfferState | None:
        current_time = now or datetime.now(UTC)
        try:
            async with self.store.ride_lock(ride_id) as acquired:
                if not acquired:
                    return None
                return await self._ensure_offer_locked(ride_id, current_time)
        except RedisError as exc:
            await self.session.rollback()
            raise MatchingUnavailable("Driver matching is temporarily unavailable") from exc

    async def current_offer(self, user_id: uuid.UUID) -> RideOfferResponse | None:
        profile = await self.drivers.get_by_user_id(user_id)
        if profile is None:
            raise DriverProfileNotFound("Create a driver profile first")
        try:
            ride_id = await self.store.get_driver_ride_id(profile.id)
            if ride_id is None:
                return None
            offer = await self.store.get_ride_offer(ride_id)
            if offer is None or offer.driver_id != profile.id:
                await self.store.clear_driver_claim(profile.id, ride_id)
                return None
            if offer.expires_at <= datetime.now(UTC):
                await self.process_expired_offers()
                return None
            attempt = await self.attempts.get(ride_id, profile.id)
            if attempt is None or attempt.outcome is not MatchAttemptOutcome.OFFERED:
                await self.store.release_offer(offer)
                return None
            ride = await self.ride_service.response_for(ride_id)
            return RideOfferResponse(
                ride=ride,
                distance_m=attempt.distance_m,
                offered_at=offer.offered_at,
                expires_at=offer.expires_at,
            )
        except RedisError as exc:
            await self.session.rollback()
            raise MatchingUnavailable("Driver matching is temporarily unavailable") from exc

    async def accept_offer(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        now = datetime.now(UTC)
        try:
            async with self.store.ride_lock(ride_id) as acquired:
                if not acquired:
                    raise RideOfferNotFound("Ride offer is already being processed")
                offer = await self._require_offer(user_id, ride_id, now)
                ride = await self.rides.get_by_id(ride_id, for_update=True)
                if ride is None:
                    raise RideNotFound("Ride does not exist")
                driver = await self.drivers.get_by_user_id(user_id, for_update=True)
                if driver is None:
                    raise DriverProfileNotFound("Create a driver profile first")
                if driver.id != offer.driver_id or driver.status is not DriverStatus.AVAILABLE:
                    raise DriverUnavailable("Driver is no longer available")
                vehicle = await self.vehicles.get_active_for_driver(driver.id)
                if vehicle is None or vehicle.category.value != ride.ride_type.value:
                    raise DriverUnavailable("Active vehicle does not support this ride type")
                attempt = await self.attempts.get(ride_id, driver.id, for_update=True)
                if attempt is None or attempt.outcome is not MatchAttemptOutcome.OFFERED:
                    raise RideOfferNotFound("Ride offer is no longer active")

                ride.accept(driver.id, vehicle.id, now)
                driver.status = DriverStatus.RESERVED
                attempt.outcome = MatchAttemptOutcome.ACCEPTED
                attempt.responded_at = now
                await self._commit()
                try:
                    await self.store.release_offer(offer)
                except RedisError:
                    pass
            return await self.ride_service.response_for(ride_id)
        except RedisError as exc:
            await self.session.rollback()
            raise MatchingUnavailable("Driver matching is temporarily unavailable") from exc

    async def reject_offer(self, user_id: uuid.UUID, ride_id: uuid.UUID) -> None:
        now = datetime.now(UTC)
        try:
            async with self.store.ride_lock(ride_id) as acquired:
                if not acquired:
                    raise RideOfferNotFound("Ride offer is already being processed")
                offer = await self._require_offer(user_id, ride_id, now)
                attempt = await self.attempts.get(ride_id, offer.driver_id, for_update=True)
                if attempt is None or attempt.outcome is not MatchAttemptOutcome.OFFERED:
                    raise RideOfferNotFound("Ride offer is no longer active")
                attempt.outcome = MatchAttemptOutcome.REJECTED
                attempt.responded_at = now
                await self._commit()
                await self.store.release_offer(offer)
            await self.ensure_offer(ride_id, now=now)
        except RedisError as exc:
            await self.session.rollback()
            raise MatchingUnavailable("Driver matching is temporarily unavailable") from exc

    async def cancel_ride(self, rider_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        try:
            async with self.store.ride_lock(ride_id) as acquired:
                if not acquired:
                    raise RideOfferNotFound("Ride matching is already being processed")
                offer = await self.store.get_ride_offer(ride_id)
                response = await self._cancel_persisted(rider_id, ride_id)
                if offer is not None:
                    try:
                        await self.store.release_offer(offer)
                    except RedisError:
                        pass
                return response
        except RedisError:
            await self.session.rollback()
            return await self._cancel_persisted(rider_id, ride_id)

    async def process_expired_offers(self, *, now: datetime | None = None, limit: int = 100) -> int:
        current_time = now or datetime.now(UTC)
        processed = 0
        try:
            ride_ids = await self.store.due_ride_ids(current_time, limit=limit)
            for ride_id in ride_ids:
                expired = False
                async with self.store.ride_lock(ride_id) as acquired:
                    if not acquired:
                        continue
                    offer = await self.store.get_ride_offer(ride_id)
                    if offer is None:
                        await self.store.remove_deadline(ride_id)
                        continue
                    if offer.expires_at > current_time:
                        continue
                    await self._expire_locked(offer, current_time)
                    expired = True
                    processed += 1
                if expired:
                    await self.ensure_offer(ride_id, now=current_time)
            return processed
        except RedisError as exc:
            await self.session.rollback()
            raise MatchingUnavailable("Driver matching is temporarily unavailable") from exc

    async def recover_searching_rides(self, *, limit: int = 100) -> int:
        ride_ids = await self.rides.list_searching_ids(limit=limit)
        await self.session.rollback()
        created = 0
        for ride_id in ride_ids:
            if await self.ensure_offer(ride_id) is not None:
                created += 1
        return created

    async def _ensure_offer_locked(self, ride_id: uuid.UUID, now: datetime) -> OfferState | None:
        existing = await self.store.get_ride_offer(ride_id)
        ride = await self.rides.get_by_id(ride_id)
        if ride is None:
            if existing is not None:
                await self.store.release_offer(existing)
            await self.store.remove_deadline(ride_id)
            await self.session.rollback()
            return None
        if ride.status is not RideStatus.SEARCHING:
            if existing is not None:
                await self.store.release_offer(existing)
            await self.store.remove_deadline(ride_id)
            await self.session.rollback()
            return None

        offered_attempt = await self.attempts.get_offered_for_ride(ride_id)
        if existing is not None:
            if (
                offered_attempt is not None
                and existing.driver_id == offered_attempt.driver_id
                and existing.expires_at > now
            ):
                return existing
            await self.store.release_offer(existing)

        if offered_attempt is not None:
            durable_offer = OfferState(
                ride_id=ride_id,
                driver_id=offered_attempt.driver_id,
                offered_at=offered_attempt.offered_at,
                expires_at=offered_attempt.expires_at,
            )
            if durable_offer.expires_at <= now:
                await self._expire_locked(durable_offer, now)
            else:
                remaining_seconds = max(1, ceil((durable_offer.expires_at - now).total_seconds()))
                if await self.store.claim_offer(durable_offer, remaining_seconds):
                    await self.session.rollback()
                    return durable_offer
                await self.session.rollback()
                return None

        located = await self.rides.locate(ride_id)
        attempted = await self.attempts.attempted_driver_ids(ride_id)
        candidates = await self.locations.find_available_nearby(
            located.pickup_latitude,
            located.pickup_longitude,
            category=VehicleCategory(ride.ride_type.value),
            excluded_driver_ids=attempted,
            radius_m=5_000,
            limit=50,
        )
        for candidate in candidates:
            expires_at = now + timedelta(seconds=self.settings.ride_offer_ttl_seconds)
            offer = OfferState(
                ride_id=ride_id,
                driver_id=candidate.driver_id,
                offered_at=now,
                expires_at=expires_at,
            )
            if not await self.store.claim_offer(offer, self.settings.ride_offer_ttl_seconds):
                continue
            attempt = RideMatchAttempt(
                ride_id=ride_id,
                driver_id=candidate.driver_id,
                outcome=MatchAttemptOutcome.OFFERED,
                distance_m=Decimal(str(candidate.distance_m)).quantize(
                    DISTANCE_QUANTUM, ROUND_HALF_UP
                ),
                offered_at=now,
                expires_at=expires_at,
            )
            self.attempts.add(attempt)
            try:
                await self.session.commit()
                return offer
            except IntegrityError:
                await self.session.rollback()
                await self.store.release_offer(offer)
        await self.session.rollback()
        return None

    async def _expire_locked(self, offer: OfferState, now: datetime) -> None:
        attempt = await self.attempts.get(offer.ride_id, offer.driver_id, for_update=True)
        if attempt is not None and attempt.outcome is MatchAttemptOutcome.OFFERED:
            attempt.outcome = MatchAttemptOutcome.TIMED_OUT
            attempt.responded_at = now
            await self._commit()
        else:
            await self.session.rollback()
        await self.store.release_offer(offer)

    async def _require_offer(
        self, user_id: uuid.UUID, ride_id: uuid.UUID, now: datetime
    ) -> OfferState:
        driver = await self.drivers.get_by_user_id(user_id)
        if driver is None:
            raise DriverProfileNotFound("Create a driver profile first")
        offer = await self.store.get_ride_offer(ride_id)
        if offer is None:
            raise RideOfferNotFound("Ride offer is no longer active")
        if offer.driver_id != driver.id:
            raise RideAccessDenied("Ride is not offered to this driver")
        if offer.expires_at <= now:
            await self._expire_locked(offer, now)
            raise RideOfferNotFound("Ride offer has expired")
        return offer

    async def _cancel_persisted(self, rider_id: uuid.UUID, ride_id: uuid.UUID) -> RideResponse:
        ride = await self.rides.get_by_id(ride_id, for_update=True)
        if ride is None:
            raise RideNotFound("Ride does not exist")
        if ride.rider_id != rider_id:
            raise RideAccessDenied("Ride does not belong to this rider")
        driver = None
        if ride.driver_id is not None:
            driver = await self.drivers.get_by_id(ride.driver_id, for_update=True)
        ride.cancel()
        if driver is not None:
            driver.status = DriverStatus.AVAILABLE
        attempt = await self.attempts.get_offered_for_ride(ride_id, for_update=True)
        if attempt is not None:
            attempt.outcome = MatchAttemptOutcome.CANCELLED
            attempt.responded_at = datetime.now(UTC)
        await self._commit()
        return await self.ride_service.response_for(ride_id)

    async def _commit(self) -> None:
        try:
            await self.session.flush()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
