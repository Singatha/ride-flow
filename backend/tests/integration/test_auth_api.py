import asyncio

import jwt
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.config import get_settings
from app.database.session import async_session_factory
from app.domains.auth.models import RefreshToken
from app.domains.auth.security import digest_refresh_token
from app.domains.users.models import User

pytestmark = pytest.mark.asyncio(loop_scope="session")


def registration_payload(email: str = "rider@example.com") -> dict[str, str]:
    return {
        "email": email,
        "password": "correct-horse-battery-staple",
        "role": "RIDER",
        "first_name": "Amina",
        "last_name": "Dlamini",
        "phone_number": "+27111234567",
    }


async def register(client: AsyncClient, email: str = "rider@example.com") -> dict[str, object]:
    response = await client.post("/api/v1/auth/register", json=registration_payload(email))
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_persists_a_hashed_password_and_token_digest(
    api_client: AsyncClient,
) -> None:
    body = await register(api_client, " Rider@Example.com ")

    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 900
    assert body["user"]["email"] == "rider@example.com"  # type: ignore[index]
    assert "password" not in body["user"]  # type: ignore[operator]

    async with async_session_factory() as session:
        user = (await session.execute(select(User))).scalar_one()
        stored_token = (await session.execute(select(RefreshToken))).scalar_one()

    assert user.password_hash != registration_payload()["password"]
    assert user.password_hash.startswith("$argon2")
    assert stored_token.token_hash == digest_refresh_token(body["refresh_token"])  # type: ignore[arg-type]
    assert body["refresh_token"] not in stored_token.token_hash


async def test_browser_can_refresh_using_httponly_cookie(api_client: AsyncClient) -> None:
    registration = await api_client.post("/api/v1/auth/register", json=registration_payload())

    response = await api_client.post("/api/v1/auth/refresh", json={})

    assert registration.status_code == 201
    assert "HttpOnly" in registration.headers["set-cookie"]
    assert "SameSite=lax" in registration.headers["set-cookie"]
    assert response.status_code == 200


async def test_duplicate_email_is_rejected_case_insensitively(api_client: AsyncClient) -> None:
    await register(api_client, "rider@example.com")

    response = await api_client.post(
        "/api/v1/auth/register", json=registration_payload("RIDER@EXAMPLE.COM")
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "EMAIL_ALREADY_REGISTERED"


async def test_concurrent_registration_allows_only_one_email(api_client: AsyncClient) -> None:
    first, second = await asyncio.gather(
        api_client.post("/api/v1/auth/register", json=registration_payload()),
        api_client.post("/api/v1/auth/register", json=registration_payload()),
    )

    assert sorted([first.status_code, second.status_code]) == [201, 409]


async def test_public_registration_cannot_create_admin(api_client: AsyncClient) -> None:
    payload = registration_payload()
    payload["role"] = "ADMIN"

    response = await api_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"
    assert registration_payload()["password"] not in response.text


async def test_validation_errors_do_not_echo_passwords(api_client: AsyncClient) -> None:
    payload = registration_payload()
    payload["password"] = "secret"

    response = await api_client.post("/api/v1/auth/register", json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["details"]["errors"][0]["field"] == "body.password"
    assert "secret" not in response.text


async def test_login_uses_generic_errors_and_issues_access_claims(api_client: AsyncClient) -> None:
    await register(api_client)

    wrong_password = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "rider@example.com", "password": "definitely-wrong"},
    )
    missing_user = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "missing@example.com", "password": "definitely-wrong"},
    )
    success = await api_client.post(
        "/api/v1/auth/login",
        json={"email": "RIDER@example.com", "password": registration_payload()["password"]},
    )

    assert wrong_password.status_code == 401
    assert missing_user.status_code == 401
    assert wrong_password.json() == missing_user.json()
    assert success.status_code == 200
    claims = jwt.decode(
        success.json()["access_token"],
        get_settings().jwt_secret.get_secret_value(),
        algorithms=["HS256"],
        issuer="rideflow",
        audience="rideflow-api",
    )
    assert claims["type"] == "access"
    assert claims["role"] == "RIDER"
    assert {"sub", "iss", "aud", "jti", "iat", "exp"}.issubset(claims)


async def test_profile_requires_authentication_and_updates_only_current_user(
    api_client: AsyncClient,
) -> None:
    token_body = await register(api_client)
    headers = {"Authorization": f"Bearer {token_body['access_token']}"}

    unauthenticated = await api_client.get("/api/v1/users/me")
    profile = await api_client.get("/api/v1/users/me", headers=headers)
    updated = await api_client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"first_name": "  Nomsa  ", "phone_number": "+27821234567"},
    )

    assert unauthenticated.status_code == 401
    assert unauthenticated.json()["error"]["code"] == "INVALID_TOKEN"
    assert profile.status_code == 200
    assert updated.status_code == 200
    assert updated.json()["first_name"] == "Nomsa"
    assert updated.json()["phone_number"] == "+27821234567"


async def test_refresh_rotates_token_and_reuse_revokes_the_family(api_client: AsyncClient) -> None:
    original = await register(api_client)

    rotated = await api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]}
    )
    replay = await api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": original["refresh_token"]}
    )
    child_after_replay = await api_client.post(
        "/api/v1/auth/refresh", json={"refresh_token": rotated.json()["refresh_token"]}
    )

    assert rotated.status_code == 200
    assert rotated.json()["refresh_token"] != original["refresh_token"]
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "INVALID_TOKEN"
    assert child_after_replay.status_code == 401


async def test_concurrent_refresh_allows_one_rotation_then_revokes_compromised_family(
    api_client: AsyncClient,
) -> None:
    original = await register(api_client)
    payload = {"refresh_token": original["refresh_token"]}

    first, second = await asyncio.gather(
        api_client.post("/api/v1/auth/refresh", json=payload),
        api_client.post("/api/v1/auth/refresh", json=payload),
    )

    assert sorted([first.status_code, second.status_code]) == [200, 401]
    successful = first if first.status_code == 200 else second
    family_check = await api_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": successful.json()["refresh_token"]},
    )
    assert family_check.status_code == 401


async def test_logout_is_idempotent_and_revokes_refresh_token(api_client: AsyncClient) -> None:
    token_body = await register(api_client)
    payload = {"refresh_token": token_body["refresh_token"]}

    first_logout = await api_client.post("/api/v1/auth/logout", json=payload)
    second_logout = await api_client.post("/api/v1/auth/logout", json=payload)
    refresh = await api_client.post("/api/v1/auth/refresh", json=payload)

    assert first_logout.status_code == 204
    assert second_logout.status_code == 204
    assert refresh.status_code == 401


async def test_inactive_user_cannot_use_existing_access_token(api_client: AsyncClient) -> None:
    token_body = await register(api_client)
    async with async_session_factory() as session:
        user = (await session.execute(select(User))).scalar_one()
        user.is_active = False
        await session.commit()

    response = await api_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token_body['access_token']}"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "INACTIVE_USER"
