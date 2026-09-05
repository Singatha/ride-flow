from collections.abc import AsyncIterator

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.database.session import engine
from app.main import app


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def clean_database_tables() -> AsyncIterator[None]:
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE driver_locations, vehicles, driver_profiles, "
                "refresh_tokens, users CASCADE"
            )
        )
    yield
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE TABLE driver_locations, vehicles, driver_profiles, "
                "refresh_tokens, users CASCADE"
            )
        )


@pytest_asyncio.fixture(loop_scope="session")
async def api_client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        yield client
