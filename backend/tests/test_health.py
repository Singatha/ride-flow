from collections.abc import AsyncIterator

from httpx import AsyncClient
from redis.exceptions import RedisError
from sqlalchemy.exc import SQLAlchemyError

from app.cache.redis import get_redis_client
from app.database.session import get_db_session
from app.main import app


async def test_health_reports_process_is_alive(client: AsyncClient) -> None:
    response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_ready_reports_database_is_reachable(client: AsyncClient) -> None:
    response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


async def test_ready_returns_503_without_exposing_database_details(client: AsyncClient) -> None:
    class UnhealthySession:
        async def execute(self, _statement: object) -> None:
            raise SQLAlchemyError("sensitive connection detail")

    async def unhealthy_session() -> AsyncIterator[UnhealthySession]:
        yield UnhealthySession()

    app.dependency_overrides[get_db_session] = unhealthy_session
    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "DATABASE_UNAVAILABLE",
            "message": "Database is unavailable",
        }
    }
    assert "sensitive" not in response.text


async def test_ready_returns_503_when_matching_redis_is_unavailable(
    client: AsyncClient,
) -> None:
    class UnhealthyRedis:
        async def ping(self) -> None:
            raise RedisError("sensitive redis detail")

    app.dependency_overrides[get_redis_client] = lambda: UnhealthyRedis()
    response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "code": "REDIS_UNAVAILABLE",
            "message": "Redis is unavailable",
        }
    }
    assert "sensitive" not in response.text


async def test_openapi_exposes_health_routes(client: AsyncClient) -> None:
    response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert "/health" in response.json()["paths"]
    assert "/ready" in response.json()["paths"]
