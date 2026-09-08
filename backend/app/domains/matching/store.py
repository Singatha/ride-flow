import json
import secrets
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import cast

from redis.asyncio import Redis
from redis.exceptions import RedisError


def _decode(value: bytes | str) -> str:
    return value.decode() if isinstance(value, bytes) else value


CLAIM_OFFER_SCRIPT = """
if redis.call('EXISTS', KEYS[1]) == 1 then
  return 0
end
if not redis.call('SET', KEYS[2], ARGV[1], 'NX', 'EX', ARGV[2]) then
  return -1
end
redis.call('SET', KEYS[1], ARGV[3], 'EX', ARGV[4])
redis.call('ZADD', KEYS[3], ARGV[5], ARGV[1])
return 1
"""

RELEASE_OFFER_SCRIPT = """
if redis.call('GET', KEYS[2]) == ARGV[1] then
  redis.call('DEL', KEYS[2])
end
redis.call('DEL', KEYS[1])
redis.call('ZREM', KEYS[3], ARGV[1])
return 1
"""

RELEASE_LOCK_SCRIPT = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
  return redis.call('DEL', KEYS[1])
end
return 0
"""


@dataclass(frozen=True)
class OfferState:
    ride_id: uuid.UUID
    driver_id: uuid.UUID
    offered_at: datetime
    expires_at: datetime

    def serialize(self) -> str:
        values = asdict(self)
        values["ride_id"] = str(self.ride_id)
        values["driver_id"] = str(self.driver_id)
        values["offered_at"] = self.offered_at.isoformat()
        values["expires_at"] = self.expires_at.isoformat()
        return json.dumps(values, separators=(",", ":"))

    @classmethod
    def deserialize(cls, value: str) -> "OfferState":
        data = json.loads(value)
        return cls(
            ride_id=uuid.UUID(data["ride_id"]),
            driver_id=uuid.UUID(data["driver_id"]),
            offered_at=datetime.fromisoformat(data["offered_at"]).astimezone(UTC),
            expires_at=datetime.fromisoformat(data["expires_at"]).astimezone(UTC),
        )


class MatchingStore:
    deadlines_key = "matching:offer_deadlines"

    def __init__(
        self,
        redis: Redis,
        *,
        state_ttl_seconds: int,
        lock_ttl_seconds: int,
    ) -> None:
        self.redis = redis
        self.state_ttl_seconds = state_ttl_seconds
        self.lock_ttl_seconds = lock_ttl_seconds

    async def claim_offer(self, offer: OfferState, offer_ttl_seconds: int) -> bool:
        claim_ttl = offer_ttl_seconds + (self.lock_ttl_seconds * 2)
        result = await self.redis.eval(
            CLAIM_OFFER_SCRIPT,
            3,
            self._ride_offer_key(offer.ride_id),
            self._driver_offer_key(offer.driver_id),
            self.deadlines_key,
            str(offer.ride_id),
            claim_ttl,
            offer.serialize(),
            self.state_ttl_seconds,
            offer.expires_at.timestamp(),
        )
        return int(result) == 1

    async def get_ride_offer(self, ride_id: uuid.UUID) -> OfferState | None:
        value = await self.redis.get(self._ride_offer_key(ride_id))
        return OfferState.deserialize(_decode(value)) if value else None

    async def get_driver_ride_id(self, driver_id: uuid.UUID) -> uuid.UUID | None:
        value = await self.redis.get(self._driver_offer_key(driver_id))
        return uuid.UUID(_decode(value)) if value else None

    async def release_offer(self, offer: OfferState) -> None:
        await self.redis.eval(
            RELEASE_OFFER_SCRIPT,
            3,
            self._ride_offer_key(offer.ride_id),
            self._driver_offer_key(offer.driver_id),
            self.deadlines_key,
            str(offer.ride_id),
        )

    async def clear_driver_claim(self, driver_id: uuid.UUID, ride_id: uuid.UUID) -> None:
        await self.redis.eval(
            RELEASE_LOCK_SCRIPT,
            1,
            self._driver_offer_key(driver_id),
            str(ride_id),
        )

    async def remove_deadline(self, ride_id: uuid.UUID) -> None:
        await self.redis.zrem(self.deadlines_key, str(ride_id))

    async def due_ride_ids(self, now: datetime, *, limit: int = 100) -> list[uuid.UUID]:
        values = cast(
            list[bytes | str],
            await self.redis.zrangebyscore(
                self.deadlines_key,
                min="-inf",
                max=now.timestamp(),
                start=0,
                num=limit,
            ),
        )
        return [uuid.UUID(_decode(value)) for value in values]

    @asynccontextmanager
    async def ride_lock(self, ride_id: uuid.UUID) -> AsyncIterator[bool]:
        key = f"ride:{ride_id}:matching_lock"
        token = secrets.token_urlsafe(24)
        acquired = bool(await self.redis.set(key, token, nx=True, ex=self.lock_ttl_seconds))
        try:
            yield acquired
        finally:
            if acquired:
                try:
                    await self.redis.eval(RELEASE_LOCK_SCRIPT, 1, key, token)
                except RedisError:
                    pass

    @staticmethod
    def _ride_offer_key(ride_id: uuid.UUID) -> str:
        return f"ride:{ride_id}:offer"

    @staticmethod
    def _driver_offer_key(driver_id: uuid.UUID) -> str:
        return f"driver:{driver_id}:offer"
