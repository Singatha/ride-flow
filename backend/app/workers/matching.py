import asyncio
import logging

from sqlalchemy.exc import DBAPIError

from app.cache.redis import redis_client
from app.core.config import get_settings
from app.core.exceptions import MatchingUnavailable
from app.database import models as _models  # noqa: F401 -- initialize all ORM relationships
from app.database.session import async_session_factory, engine
from app.domains.matching.service import MatchingService

logger = logging.getLogger(__name__)


async def run() -> None:
    settings = get_settings()
    try:
        while True:
            try:
                async with async_session_factory() as session:
                    service = MatchingService(session, redis_client, settings)
                    await service.process_expired_offers()
                    await service.recover_searching_rides()
            except (MatchingUnavailable, DBAPIError, OSError):
                logger.exception("Matching worker iteration failed")
            await asyncio.sleep(settings.matching_worker_interval_seconds)
    finally:
        await redis_client.aclose()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run())
