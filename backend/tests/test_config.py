import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_settings_have_safe_local_defaults() -> None:
    settings = Settings(_env_file=None)

    assert settings.environment == "local"
    assert settings.debug is False
    assert settings.cors_origins == ["http://localhost:5173"]


def test_short_jwt_secret_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, jwt_secret="too-short")


def test_local_jwt_secret_is_rejected_in_production() -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, environment="production")
