import asyncio
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.database.session import async_session_factory
from app.domains.auth.security import create_access_token
from app.domains.drivers.service import DriverService
from app.domains.users.models import User, UserRole

pytestmark = pytest.mark.asyncio(loop_scope="session")

PASSWORD = "correct-horse-battery-staple"


def registration_payload(email: str, role: str = "DRIVER") -> dict[str, str]:
    return {
        "email": email,
        "password": PASSWORD,
        "role": role,
        "first_name": "Amina",
        "last_name": "Dlamini",
        "phone_number": "+27111234567",
    }


def profile_payload(license_number: str = "GP-DRIVER-001") -> dict[str, str]:
    return {"license_number": license_number, "license_expiry": "2099-12-31"}


def vehicle_payload(license_plate: str = "CA 123-456") -> dict[str, object]:
    return {
        "make": "Toyota",
        "model": "Corolla Cross",
        "year": 2025,
        "color": "Silver",
        "license_plate": license_plate,
        "category": "STANDARD",
        "is_active": True,
    }


async def register(client: AsyncClient, email: str, role: str = "DRIVER") -> dict[str, object]:
    response = await client.post("/api/v1/auth/register", json=registration_payload(email, role))
    assert response.status_code == 201, response.text
    return response.json()


def auth_headers(session: dict[str, object]) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}


async def create_admin_headers() -> dict[str, str]:
    async with async_session_factory() as session:
        admin = User(
            email=f"admin-{uuid.uuid4()}@example.com",
            password_hash="not-used-by-this-test",
            role=UserRole.ADMIN,
            first_name="System",
            last_name="Administrator",
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        token = create_access_token(admin, get_settings())
    return {"Authorization": f"Bearer {token}"}


async def create_profile(
    client: AsyncClient,
    headers: dict[str, str],
    license_number: str = "GP-DRIVER-001",
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/drivers/profile",
        headers=headers,
        json=profile_payload(license_number),
    )
    assert response.status_code == 201, response.text
    return response.json()


async def approve_driver(
    client: AsyncClient, driver_id: object, admin_headers: dict[str, str]
) -> None:
    response = await client.put(
        f"/api/v1/drivers/{driver_id}/verification",
        headers=admin_headers,
        json={"status": "APPROVED"},
    )
    assert response.status_code == 200, response.text


async def prepare_available_driver(
    client: AsyncClient,
    *,
    email: str,
    license_number: str,
    license_plate: str,
    latitude: float,
    longitude: float,
    admin_headers: dict[str, str],
) -> tuple[dict[str, str], dict[str, object]]:
    registered = await register(client, email)
    headers = auth_headers(registered)
    profile = await create_profile(client, headers, license_number)
    await approve_driver(client, profile["id"], admin_headers)
    vehicle = await client.post(
        "/api/v1/vehicles", headers=headers, json=vehicle_payload(license_plate)
    )
    assert vehicle.status_code == 201, vehicle.text
    location = await client.put(
        "/api/v1/drivers/location",
        headers=headers,
        json={"latitude": latitude, "longitude": longitude, "accuracy_m": 8},
    )
    assert location.status_code == 200, location.text
    online = await client.put("/api/v1/drivers/status/online", headers=headers)
    assert online.status_code == 200, online.text
    return headers, profile


async def test_driver_profile_is_role_protected_and_unique(api_client: AsyncClient) -> None:
    rider = await register(api_client, "rider@example.com", "RIDER")
    forbidden = await api_client.post(
        "/api/v1/drivers/profile",
        headers=auth_headers(rider),
        json=profile_payload(),
    )

    driver = await register(api_client, "driver@example.com")
    headers = auth_headers(driver)
    created = await api_client.post(
        "/api/v1/drivers/profile", headers=headers, json=profile_payload()
    )
    duplicate = await api_client.post(
        "/api/v1/drivers/profile", headers=headers, json=profile_payload()
    )
    rider_cannot_approve = await api_client.put(
        f"/api/v1/drivers/{created.json()['id']}/verification",
        headers=auth_headers(rider),
        json={"status": "APPROVED"},
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "PERMISSION_DENIED"
    assert created.status_code == 201
    assert created.json()["license_number"] == "GP-DRIVER-001"
    assert created.json()["verification_status"] == "PENDING"
    assert created.json()["status"] == "OFFLINE"
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "DRIVER_PROFILE_ALREADY_EXISTS"
    assert rider_cannot_approve.status_code == 403


async def test_online_requires_approval_vehicle_and_location(api_client: AsyncClient) -> None:
    registered = await register(api_client, "driver@example.com")
    headers = auth_headers(registered)
    profile = await create_profile(api_client, headers)

    pending = await api_client.put("/api/v1/drivers/status/online", headers=headers)
    await approve_driver(api_client, profile["id"], await create_admin_headers())
    missing_both = await api_client.put("/api/v1/drivers/status/online", headers=headers)
    vehicle = await api_client.post("/api/v1/vehicles", headers=headers, json=vehicle_payload())
    missing_location = await api_client.put("/api/v1/drivers/status/online", headers=headers)
    location = await api_client.put(
        "/api/v1/drivers/location",
        headers=headers,
        json={
            "latitude": -26.2041,
            "longitude": 28.0473,
            "heading": 359.5,
            "speed_kph": 0,
            "accuracy_m": 7,
        },
    )
    online = await api_client.put("/api/v1/drivers/status/online", headers=headers)
    online_again = await api_client.put("/api/v1/drivers/status/online", headers=headers)
    offline = await api_client.put("/api/v1/drivers/status/offline", headers=headers)

    assert pending.status_code == 409
    assert pending.json()["error"]["code"] == "DRIVER_NOT_VERIFIED"
    assert missing_both.status_code == 409
    assert missing_both.json()["error"]["details"]["missing"] == [
        "active_vehicle",
        "location",
    ]
    assert vehicle.status_code == 201
    assert missing_location.json()["error"]["details"]["missing"] == ["location"]
    assert location.status_code == 200
    assert location.json()["latitude"] == -26.2041
    assert online.json()["status"] == "AVAILABLE"
    assert online_again.json()["status"] == "AVAILABLE"
    assert offline.json()["status"] == "OFFLINE"


async def test_vehicle_activation_is_owned_atomic_and_offline_only(
    api_client: AsyncClient,
) -> None:
    registered = await register(api_client, "driver@example.com")
    headers = auth_headers(registered)
    profile = await create_profile(api_client, headers)

    first, second = await asyncio.gather(
        api_client.post("/api/v1/vehicles", headers=headers, json=vehicle_payload("CA 111-111")),
        api_client.post("/api/v1/vehicles", headers=headers, json=vehicle_payload("CA 222-222")),
    )
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text

    vehicles = await api_client.get("/api/v1/vehicles/me", headers=headers)
    assert vehicles.status_code == 200
    assert sum(vehicle["is_active"] for vehicle in vehicles.json()) == 1

    other = await register(api_client, "other-driver@example.com")
    other_headers = auth_headers(other)
    await create_profile(api_client, other_headers, "GP-DRIVER-002")
    other_driver_update = await api_client.patch(
        f"/api/v1/vehicles/{first.json()['id']}",
        headers=other_headers,
        json={"color": "Black"},
    )
    assert other_driver_update.status_code == 404

    await approve_driver(api_client, profile["id"], await create_admin_headers())
    await api_client.put(
        "/api/v1/drivers/location",
        headers=headers,
        json={"latitude": -26.2041, "longitude": 28.0473},
    )
    await api_client.put("/api/v1/drivers/status/online", headers=headers)
    while_online = await api_client.patch(
        f"/api/v1/vehicles/{second.json()['id']}",
        headers=headers,
        json={"color": "Black"},
    )
    assert while_online.status_code == 409
    assert while_online.json()["error"]["code"] == "DRIVER_STATE_CONFLICT"


async def test_location_is_validated_and_upserted(api_client: AsyncClient) -> None:
    registered = await register(api_client, "driver@example.com")
    headers = auth_headers(registered)
    await create_profile(api_client, headers)

    invalid = await api_client.put(
        "/api/v1/drivers/location",
        headers=headers,
        json={"latitude": -91, "longitude": 28.0473},
    )
    first = await api_client.put(
        "/api/v1/drivers/location",
        headers=headers,
        json={"latitude": -26.2041, "longitude": 28.0473},
    )
    second = await api_client.put(
        "/api/v1/drivers/location",
        headers=headers,
        json={"latitude": -26.1076, "longitude": 28.0567},
    )

    assert invalid.status_code == 422
    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json()["latitude"] == -26.1076


async def test_nearby_query_orders_available_drivers_and_excludes_offline(
    api_client: AsyncClient,
) -> None:
    admin_headers = await create_admin_headers()
    _, nearest = await prepare_available_driver(
        api_client,
        email="near@example.com",
        license_number="GP-NEAR-001",
        license_plate="GP NEAR 1",
        latitude=-26.2042,
        longitude=28.0474,
        admin_headers=admin_headers,
    )
    _, farther = await prepare_available_driver(
        api_client,
        email="farther@example.com",
        license_number="GP-FAR-002",
        license_plate="GP FAR 2",
        latitude=-26.2141,
        longitude=28.0473,
        admin_headers=admin_headers,
    )
    offline_headers, offline = await prepare_available_driver(
        api_client,
        email="offline@example.com",
        license_number="GP-OFF-003",
        license_plate="GP OFF 3",
        latitude=-26.2051,
        longitude=28.0473,
        admin_headers=admin_headers,
    )
    _, outside = await prepare_available_driver(
        api_client,
        email="outside@example.com",
        license_number="GP-OUT-004",
        license_plate="GP OUT 4",
        latitude=-26.3041,
        longitude=28.0473,
        admin_headers=admin_headers,
    )
    await api_client.put("/api/v1/drivers/status/offline", headers=offline_headers)

    async with async_session_factory() as session:
        nearby = await DriverService(session).find_available_nearby(
            -26.2041, 28.0473, radius_m=5_000
        )

    assert [str(driver.driver_id) for driver in nearby] == [
        str(nearest["id"]),
        str(farther["id"]),
    ]
    assert nearby[0].distance_m < 50
    assert nearby[0].distance_m < nearby[1].distance_m
    assert str(offline["id"]) not in {str(driver.driver_id) for driver in nearby}
    assert str(outside["id"]) not in {str(driver.driver_id) for driver in nearby}


async def test_changing_credentials_resets_verification_and_availability(
    api_client: AsyncClient,
) -> None:
    headers, _ = await prepare_available_driver(
        api_client,
        email="driver@example.com",
        license_number="GP-DRIVER-001",
        license_plate="GP RESET 1",
        latitude=-26.2041,
        longitude=28.0473,
        admin_headers=await create_admin_headers(),
    )

    updated = await api_client.patch(
        "/api/v1/drivers/me",
        headers=headers,
        json={"license_number": "GP-DRIVER-NEW"},
    )

    assert updated.status_code == 200
    assert updated.json()["verification_status"] == "PENDING"
    assert updated.json()["status"] == "OFFLINE"
