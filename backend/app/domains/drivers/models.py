import uuid
from datetime import date, datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    String,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domains.rides.models import Ride
    from app.domains.users.models import User


class DriverVerificationStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    SUSPENDED = "SUSPENDED"


class DriverStatus(StrEnum):
    OFFLINE = "OFFLINE"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    ON_TRIP = "ON_TRIP"


class VehicleCategory(StrEnum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    XL = "XL"


class DriverProfile(TimestampMixin, Base):
    __tablename__ = "driver_profiles"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    license_number: Mapped[str] = mapped_column(String(64), unique=True)
    license_expiry: Mapped[date] = mapped_column(Date)
    verification_status: Mapped[DriverVerificationStatus] = mapped_column(
        Enum(
            DriverVerificationStatus,
            name="driver_verification_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=DriverVerificationStatus.PENDING,
        server_default=DriverVerificationStatus.PENDING.value,
        index=True,
    )
    status: Mapped[DriverStatus] = mapped_column(
        Enum(
            DriverStatus,
            name="driver_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=DriverStatus.OFFLINE,
        server_default=DriverStatus.OFFLINE.value,
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="driver_profile")
    vehicles: Mapped[list["Vehicle"]] = relationship(
        back_populates="driver", cascade="all, delete-orphan"
    )
    location: Mapped["DriverLocation | None"] = relationship(
        back_populates="driver", cascade="all, delete-orphan", uselist=False
    )
    rides: Mapped[list["Ride"]] = relationship(back_populates="driver")


class Vehicle(TimestampMixin, Base):
    __tablename__ = "vehicles"
    __table_args__ = (
        CheckConstraint("year BETWEEN 1980 AND 2100", name="valid_year"),
        Index(
            "uq_vehicles_one_active_per_driver",
            "driver_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="CASCADE"), index=True
    )
    make: Mapped[str] = mapped_column(String(80))
    model: Mapped[str] = mapped_column(String(80))
    year: Mapped[int]
    color: Mapped[str] = mapped_column(String(40))
    license_plate: Mapped[str] = mapped_column(String(32), unique=True)
    category: Mapped[VehicleCategory] = mapped_column(
        Enum(
            VehicleCategory,
            name="vehicle_category",
            values_callable=lambda categories: [category.value for category in categories],
        )
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    driver: Mapped[DriverProfile] = relationship(back_populates="vehicles")
    rides: Mapped[list["Ride"]] = relationship(back_populates="vehicle")


class DriverLocation(TimestampMixin, Base):
    __tablename__ = "driver_locations"
    __table_args__ = (
        CheckConstraint(
            "heading IS NULL OR (heading >= 0 AND heading < 360)", name="valid_heading"
        ),
        CheckConstraint("speed_kph IS NULL OR speed_kph >= 0", name="nonnegative_speed"),
        CheckConstraint("accuracy_m IS NULL OR accuracy_m >= 0", name="nonnegative_accuracy"),
    )

    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="CASCADE"), primary_key=True
    )
    location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    heading: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed_kph: Mapped[float | None] = mapped_column(Float, nullable=True)
    accuracy_m: Mapped[float | None] = mapped_column(Float, nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)

    driver: Mapped[DriverProfile] = relationship(back_populates="location")


Index("ix_driver_locations_location_gist", DriverLocation.location, postgresql_using="gist")
