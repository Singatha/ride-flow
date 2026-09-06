import asyncio
import uuid
from decimal import ROUND_HALF_UP, Decimal

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.database.session import async_session_factory
from app.domains.auth.security import create_access_token
from app.domains.users.models import User, UserRole

pytestmark = pytest.mark.asyncio(loop_scope="session")

PASSWORD = "correct-horse-battery-staple"
RIDE_REQUEST = {
    "pickup": {"latitude": -26.2041, "longitude": 28.0473},
    "destination": {"latitude": -26.1076, "longitude": 28.0567},
    "ride_type": "STANDARD",
}


async def register(client: AsyncClient, email: str, role: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": PASSWORD,
            "role": role,
            "first_name": "Ride",
            "last_name": "Tester",
            "phone_number": "+27111234567",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def headers(session: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def admin_headers() -> dict[str, str]:
    async with async_session_factory() as session:
        admin = User(
            email=f"admin-{uuid.uuid4()}@example.com",
            password_hash="not-used",
            role=UserRole.ADMIN,
            first_name="System",
            last_name="Administrator",
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(admin, get_settings())
    return {"Authorization": f"Bearer {token}"}


async def prepare_driver(
    client: AsyncClient,
    *,
    suffix: str,
    category: str = "STANDARD",
) -> tuple[dict[str, str], str]:
    driver_session = await register(client, f"driver-{suffix}@example.com", "DRIVER")
    driver_headers = headers(driver_session)
    profile_response = await client.post(
        "/api/v1/drivers/profile",
        headers=driver_headers,
        json={
            "license_number": f"LIC-{suffix}",
            "license_expiry": "2099-12-31",
        },
    )
    assert profile_response.status_code == 201, profile_response.text
    profile = profile_response.json()
    approval = await client.put(
        f"/api/v1/drivers/{profile['id']}/verification",
        headers=await admin_headers(),
        json={"status": "APPROVED"},
    )
    assert approval.status_code == 200, approval.text
    vehicle = await client.post(
        "/api/v1/vehicles",
        headers=driver_headers,
        json={
            "make": "Toyota",
            "model": "Corolla",
            "year": 2025,
            "color": "Silver",
            "license_plate": f"GP {suffix}",
            "category": category,
            "is_active": True,
        },
    )
    assert vehicle.status_code == 201, vehicle.text
    location = await client.put(
        "/api/v1/drivers/location",
        headers=driver_headers,
        json={"latitude": -26.2042, "longitude": 28.0474},
    )
    assert location.status_code == 200, location.text
    online = await client.put("/api/v1/drivers/status/online", headers=driver_headers)
    assert online.status_code == 200, online.text
    return driver_headers, str(profile["id"])


async def request_ride(client: AsyncClient, rider_headers: dict[str, str]) -> dict[str, object]:
    response = await client.post("/api/v1/rides", headers=rider_headers, json=RIDE_REQUEST)
    assert response.status_code == 201, response.text
    return response.json()


async def test_estimate_uses_postgis_pricing_rules_and_matching_vehicle_type(
    api_client: AsyncClient,
) -> None:
    rider = await register(api_client, "rider@example.com", "RIDER")
    rider_headers = headers(rider)
    standard_headers, _ = await prepare_driver(api_client, suffix="STANDARD", category="STANDARD")
    premium_headers, _ = await prepare_driver(api_client, suffix="PREMIUM", category="PREMIUM")

    estimate = await api_client.post(
        "/api/v1/rides/estimate", headers=rider_headers, json=RIDE_REQUEST
    )

    assert estimate.status_code == 200
    body = estimate.json()
    assert body["ride_type"] == "STANDARD"
    assert body["currency"] == "ZAR"
    assert body["available_driver_count"] == 1
    assert float(body["estimated_distance_km"]) > 10
    assert float(body["estimated_duration_minutes"]) > 0
    expected_fare = (
        Decimal("20.00")
        + Decimal(body["estimated_distance_km"]) * Decimal("12.00")
        + Decimal(body["estimated_duration_minutes"]) * Decimal("1.50")
    ).quantize(Decimal("0.01"), ROUND_HALF_UP)
    assert Decimal(body["estimated_fare"]) == expected_fare

    ride = await request_ride(api_client, rider_headers)
    standard_requests = await api_client.get("/api/v1/rides/available", headers=standard_headers)
    premium_requests = await api_client.get("/api/v1/rides/available", headers=premium_headers)
    incompatible_acceptance = await api_client.post(
        f"/api/v1/rides/{ride['id']}/accept", headers=premium_headers
    )
    assert [request["id"] for request in standard_requests.json()] == [ride["id"]]
    assert premium_requests.json() == []
    assert incompatible_acceptance.status_code == 409
    assert incompatible_acceptance.json()["error"]["code"] == "DRIVER_UNAVAILABLE"


async def test_request_is_searching_private_and_one_active_per_rider(
    api_client: AsyncClient,
) -> None:
    rider = await register(api_client, "rider@example.com", "RIDER")
    rider_headers = headers(rider)
    other_rider = await register(api_client, "other-rider@example.com", "RIDER")
    other_headers = headers(other_rider)

    first, second = await asyncio.gather(
        api_client.post("/api/v1/rides", headers=rider_headers, json=RIDE_REQUEST),
        api_client.post("/api/v1/rides", headers=rider_headers, json=RIDE_REQUEST),
    )
    responses = sorted([first, second], key=lambda response: response.status_code)
    created = responses[0]
    rejected = responses[1]

    assert created.status_code == 201
    assert created.json()["status"] == "SEARCHING"
    assert created.json()["pickup"] == RIDE_REQUEST["pickup"]
    assert rejected.status_code == 409
    assert rejected.json()["error"]["code"] == "ACTIVE_RIDE_EXISTS"

    hidden = await api_client.get(f"/api/v1/rides/{created.json()['id']}", headers=other_headers)
    history = await api_client.get("/api/v1/rides", headers=rider_headers)
    assert hidden.status_code == 403
    assert len(history.json()) == 1


async def test_concurrent_acceptance_reserves_exactly_one_driver(
    api_client: AsyncClient,
) -> None:
    rider = await register(api_client, "rider@example.com", "RIDER")
    ride = await request_ride(api_client, headers(rider))
    first_headers, _ = await prepare_driver(api_client, suffix="ONE")
    second_headers, _ = await prepare_driver(api_client, suffix="TWO")

    first, second = await asyncio.gather(
        api_client.post(f"/api/v1/rides/{ride['id']}/accept", headers=first_headers),
        api_client.post(f"/api/v1/rides/{ride['id']}/accept", headers=second_headers),
    )

    assert sorted([first.status_code, second.status_code]) == [200, 409]
    failed = first if first.status_code == 409 else second
    assert failed.json()["error"]["code"] == "RIDE_ALREADY_ACCEPTED"
    statuses = [
        (await api_client.get("/api/v1/drivers/me", headers=driver_headers)).json()["status"]
        for driver_headers in (first_headers, second_headers)
    ]
    assert sorted(statuses) == ["AVAILABLE", "RESERVED"]


async def test_driver_completes_valid_lifecycle_and_invalid_jump_is_rejected(
    api_client: AsyncClient,
) -> None:
    rider = await register(api_client, "rider@example.com", "RIDER")
    rider_headers = headers(rider)
    ride = await request_ride(api_client, rider_headers)
    driver_headers, _ = await prepare_driver(api_client, suffix="LIFECYCLE")
    other_headers, _ = await prepare_driver(api_client, suffix="UNASSIGNED")

    accepted = await api_client.post(f"/api/v1/rides/{ride['id']}/accept", headers=driver_headers)
    unauthorized = await api_client.post(
        f"/api/v1/rides/{ride['id']}/arriving", headers=other_headers
    )
    invalid = await api_client.post(f"/api/v1/rides/{ride['id']}/start", headers=driver_headers)
    arriving = await api_client.post(f"/api/v1/rides/{ride['id']}/arriving", headers=driver_headers)
    arrived = await api_client.post(f"/api/v1/rides/{ride['id']}/arrive", headers=driver_headers)
    started = await api_client.post(f"/api/v1/rides/{ride['id']}/start", headers=driver_headers)
    first_completion, second_completion = await asyncio.gather(
        api_client.post(f"/api/v1/rides/{ride['id']}/complete", headers=driver_headers),
        api_client.post(f"/api/v1/rides/{ride['id']}/complete", headers=driver_headers),
    )
    completed = first_completion if first_completion.status_code == 200 else second_completion
    repeated = first_completion if first_completion.status_code == 409 else second_completion

    assert sorted([first_completion.status_code, second_completion.status_code]) == [200, 409]
    assert accepted.json()["status"] == "DRIVER_ASSIGNED"
    assert accepted.json()["driver"]["first_name"] == "Ride"
    assert accepted.json()["vehicle"]["license_plate"] == "GP LIFECYCLE"
    assert unauthorized.status_code == 403
    assert invalid.status_code == 409
    assert invalid.json()["error"]["code"] == "INVALID_RIDE_TRANSITION"
    assert arriving.json()["status"] == "DRIVER_ARRIVING"
    assert arrived.json()["status"] == "DRIVER_ARRIVED"
    assert started.json()["status"] == "IN_PROGRESS"
    assert completed.json()["status"] == "COMPLETED"
    assert completed.json()["final_fare"] == completed.json()["estimated_fare"]
    assert repeated.status_code == 409

    driver = await api_client.get("/api/v1/drivers/me", headers=driver_headers)
    assert driver.json()["status"] == "AVAILABLE"


async def test_rider_cancellation_releases_driver_but_cannot_cancel_active_trip(
    api_client: AsyncClient,
) -> None:
    rider = await register(api_client, "rider@example.com", "RIDER")
    rider_headers = headers(rider)
    ride = await request_ride(api_client, rider_headers)
    driver_headers, _ = await prepare_driver(api_client, suffix="CANCEL")
    await api_client.post(f"/api/v1/rides/{ride['id']}/accept", headers=driver_headers)

    cancelled = await api_client.post(f"/api/v1/rides/{ride['id']}/cancel", headers=rider_headers)
    driver = await api_client.get("/api/v1/drivers/me", headers=driver_headers)

    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "CANCELLED"
    assert driver.json()["status"] == "AVAILABLE"

    second_ride = await request_ride(api_client, rider_headers)
    await api_client.post(f"/api/v1/rides/{second_ride['id']}/accept", headers=driver_headers)
    await api_client.post(f"/api/v1/rides/{second_ride['id']}/arriving", headers=driver_headers)
    await api_client.post(f"/api/v1/rides/{second_ride['id']}/arrive", headers=driver_headers)
    await api_client.post(f"/api/v1/rides/{second_ride['id']}/start", headers=driver_headers)
    too_late = await api_client.post(
        f"/api/v1/rides/{second_ride['id']}/cancel", headers=rider_headers
    )
    assert too_late.status_code == 409
    assert too_late.json()["error"]["code"] == "INVALID_RIDE_TRANSITION"
