import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from pwdlib import PasswordHash

from app.core.config import Settings
from app.core.exceptions import InvalidToken
from app.domains.users.models import User

ALGORITHM = "HS256"
password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user: User, settings: Settings, now: datetime | None = None) -> str:
    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_ttl_minutes)
    payload: dict[str, Any] = {
        "sub": str(user.id),
        "role": user.role.value,
        "type": "access",
        "iss": "rideflow",
        "aud": "rideflow-api",
        "jti": str(uuid.uuid4()),
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(payload, settings.jwt_secret.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings) -> uuid.UUID:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[ALGORITHM],
            issuer="rideflow",
            audience="rideflow-api",
            options={"require": ["sub", "type", "iss", "aud", "jti", "iat", "exp"]},
        )
        if payload["type"] != "access":
            raise InvalidToken("Token is not an access token")
        return uuid.UUID(payload["sub"])
    except InvalidToken:
        raise
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise InvalidToken("Access token is invalid or expired") from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(64)


def digest_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
