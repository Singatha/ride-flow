from functools import lru_cache

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="RIDEFLOW_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "RideFlow API"
    environment: str = "local"
    debug: bool = False
    database_url: str = "postgresql+asyncpg://rideflow:rideflow@localhost:5432/rideflow"
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    jwt_secret: SecretStr = SecretStr("local-development-secret-change-before-production")
    access_token_ttl_minutes: int = Field(default=15, ge=1, le=60)
    refresh_token_ttl_days: int = Field(default=30, ge=1, le=90)

    @field_validator("jwt_secret")
    @classmethod
    def validate_jwt_secret(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value()) < 32:
            raise ValueError("JWT secret must contain at least 32 characters")
        return value

    @model_validator(mode="after")
    def prevent_local_secret_outside_development(self) -> "Settings":
        if self.environment not in {
            "local",
            "test",
        } and self.jwt_secret.get_secret_value().startswith("local-development-secret"):
            raise ValueError("A non-development JWT secret is required")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
