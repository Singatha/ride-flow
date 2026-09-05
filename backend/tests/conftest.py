from collections.abc import AsyncIterator
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from app.database.session import get_db_session
from app.main import app


class HealthySession:
    async def execute(self, _statement: object) -> None:
        return None


async def healthy_session() -> AsyncIterator[Any]:
    yield HealthySession()


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    app.dependency_overrides[get_db_session] = healthy_session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://testserver"
    ) as test_client:
        yield test_client
    app.dependency_overrides.clear()
