import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.domains.drivers.models import (
    DriverStatus,
    DriverVerificationStatus,
    VehicleCategory,
)


def normalize_required(value: str) -> str:
    value = " ".join(value.split())
    if not value:
        raise ValueError("must not be blank")
    return value


def normalize_identifier(value: str) -> str:
    return normalize_required(value).upper()


class DriverProfileCreate(BaseModel):
    license_number: str = Field(min_length=3, max_length=64)
    license_expiry: date

    _normalize_license = field_validator("license_number")(normalize_identifier)

    @field_validator("license_expiry")
    @classmethod
    def require_future_expiry(cls, value: date) -> date:
        if value <= date.today():
            raise ValueError("driver license must not be expired")
        return value


class DriverProfileUpdate(BaseModel):
    license_number: str | None = Field(default=None, min_length=3, max_length=64)
    license_expiry: date | None = None

    @field_validator("license_number")
    @classmethod
    def normalize_optional_license(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return normalize_identifier(value)

    @field_validator("license_expiry")
    @classmethod
    def require_optional_future_expiry(cls, value: date | None) -> date:
        if value is None:
            raise ValueError("must not be null")
        if value <= date.today():
            raise ValueError("driver license must not be expired")
        return value


class DriverVerificationUpdate(BaseModel):
    status: DriverVerificationStatus


class DriverProfileResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    license_number: str
    license_expiry: date
    verification_status: DriverVerificationStatus
    status: DriverStatus
    created_at: datetime
    updated_at: datetime


class VehicleCreate(BaseModel):
    make: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=80)
    year: int = Field(ge=1980, le=2100)
    color: str = Field(min_length=1, max_length=40)
    license_plate: str = Field(min_length=2, max_length=32)
    category: VehicleCategory = VehicleCategory.STANDARD
    is_active: bool = True

    _normalize_make = field_validator("make")(normalize_required)
    _normalize_model = field_validator("model")(normalize_required)
    _normalize_color = field_validator("color")(normalize_required)
    _normalize_plate = field_validator("license_plate")(normalize_identifier)

    @field_validator("year")
    @classmethod
    def reject_implausible_future_year(cls, value: int) -> int:
        if value > date.today().year + 1:
            raise ValueError("vehicle year cannot be more than one year in the future")
        return value


class VehicleUpdate(BaseModel):
    make: str | None = Field(default=None, min_length=1, max_length=80)
    model: str | None = Field(default=None, min_length=1, max_length=80)
    year: int | None = Field(default=None, ge=1980, le=2100)
    color: str | None = Field(default=None, min_length=1, max_length=40)
    license_plate: str | None = Field(default=None, min_length=2, max_length=32)
    category: VehicleCategory | None = None
    is_active: bool | None = None

    @field_validator("make", "model", "color")
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return normalize_required(value)

    @field_validator("license_plate")
    @classmethod
    def normalize_optional_plate(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("must not be null")
        return normalize_identifier(value)

    @field_validator("year")
    @classmethod
    def validate_optional_year(cls, value: int | None) -> int:
        if value is None:
            raise ValueError("must not be null")
        if value > date.today().year + 1:
            raise ValueError("vehicle year cannot be more than one year in the future")
        return value

    @model_validator(mode="after")
    def reject_explicit_nulls(self) -> "VehicleUpdate":
        for field in self.model_fields_set:
            if getattr(self, field) is None:
                raise ValueError(f"{field} must not be null")
        return self


class VehicleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    driver_id: uuid.UUID
    make: str
    model: str
    year: int
    color: str
    license_plate: str
    category: VehicleCategory
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DriverLocationUpdate(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    heading: float | None = Field(default=None, ge=0, lt=360)
    speed_kph: float | None = Field(default=None, ge=0, le=300)
    accuracy_m: float | None = Field(default=None, ge=0, le=10_000)
    recorded_at: datetime | None = None

    @field_validator("recorded_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("recorded_at must include a timezone")
        return value


class DriverLocationResponse(BaseModel):
    driver_id: uuid.UUID
    latitude: float
    longitude: float
    heading: float | None
    speed_kph: float | None
    accuracy_m: float | None
    recorded_at: datetime


class NearbyDriver(BaseModel):
    driver_id: uuid.UUID
    user_id: uuid.UUID
    distance_m: float
