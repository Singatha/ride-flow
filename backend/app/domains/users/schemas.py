import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.domains.users.models import UserRole


def normalize_name(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("must not be blank")
    return value


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)
    role: UserRole
    first_name: str = Field(min_length=1, max_length=100)
    last_name: str = Field(min_length=1, max_length=100)
    phone_number: str | None = Field(default=None, min_length=7, max_length=32)

    _normalize_first_name = field_validator("first_name")(normalize_name)
    _normalize_last_name = field_validator("last_name")(normalize_name)

    @field_validator("role")
    @classmethod
    def prevent_public_admin_registration(cls, value: UserRole) -> UserRole:
        if value is UserRole.ADMIN:
            raise ValueError("ADMIN cannot be selected during public registration")
        return value


class UserUpdateRequest(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=100)
    last_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone_number: str | None = Field(default=None, min_length=7, max_length=32)

    @field_validator("first_name", "last_name")
    @classmethod
    def normalize_optional_name(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return normalize_name(value)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr
    role: UserRole
    first_name: str
    last_name: str
    phone_number: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
