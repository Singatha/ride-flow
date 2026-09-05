import uuid
from datetime import UTC, datetime, timedelta

import pytest

from app.core.config import Settings
from app.core.exceptions import InvalidToken, PermissionDenied
from app.domains.auth.dependencies import RoleChecker
from app.domains.auth.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from app.domains.users.models import User, UserRole


def make_user(role: UserRole = UserRole.RIDER) -> User:
    return User(
        id=uuid.uuid4(),
        email="user@example.com",
        password_hash="unused",
        role=role,
        first_name="Test",
        last_name="User",
    )


def test_passwords_are_hashed_and_verified() -> None:
    encoded = hash_password("correct-horse-battery-staple")

    assert encoded != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", encoded)
    assert not verify_password("wrong-password", encoded)


def test_expired_access_token_is_rejected() -> None:
    settings = Settings(_env_file=None)
    token = create_access_token(make_user(), settings, now=datetime.now(UTC) - timedelta(hours=1))

    with pytest.raises(InvalidToken):
        decode_access_token(token, settings)


async def test_role_checker_denies_unlisted_role() -> None:
    checker = RoleChecker(UserRole.ADMIN)

    with pytest.raises(PermissionDenied):
        await checker(make_user(UserRole.RIDER))
