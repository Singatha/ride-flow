import uuid
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING, ClassVar

from geoalchemy2 import Geography
from geoalchemy2.elements import WKBElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.exceptions import InvalidRideTransition, RideAlreadyAccepted
from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.domains.drivers.models import DriverProfile, Vehicle
    from app.domains.users.models import User


class RideType(StrEnum):
    STANDARD = "STANDARD"
    PREMIUM = "PREMIUM"
    XL = "XL"


class RideStatus(StrEnum):
    REQUESTED = "REQUESTED"
    SEARCHING = "SEARCHING"
    DRIVER_ASSIGNED = "DRIVER_ASSIGNED"
    DRIVER_ARRIVING = "DRIVER_ARRIVING"
    DRIVER_ARRIVED = "DRIVER_ARRIVED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class MatchAttemptOutcome(StrEnum):
    OFFERED = "OFFERED"
    REJECTED = "REJECTED"
    TIMED_OUT = "TIMED_OUT"
    ACCEPTED = "ACCEPTED"
    CANCELLED = "CANCELLED"


class PricingRule(TimestampMixin, Base):
    __tablename__ = "pricing_rules"
    __table_args__ = (
        CheckConstraint("base_fare >= 0", name="nonnegative_base_fare"),
        CheckConstraint("cost_per_km >= 0", name="nonnegative_cost_per_km"),
        CheckConstraint("cost_per_minute >= 0", name="nonnegative_cost_per_minute"),
        CheckConstraint("average_speed_kph > 0", name="positive_average_speed"),
        Index(
            "uq_pricing_rules_one_active_per_type",
            "ride_type",
            unique=True,
            postgresql_where=text("is_active"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ride_type: Mapped[RideType] = mapped_column(
        Enum(
            RideType,
            name="ride_type",
            values_callable=lambda ride_types: [ride_type.value for ride_type in ride_types],
        ),
        index=True,
    )
    currency: Mapped[str] = mapped_column(String(3), default="ZAR", server_default="ZAR")
    base_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cost_per_km: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    cost_per_minute: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    average_speed_kph: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")

    rides: Mapped[list["Ride"]] = relationship(back_populates="pricing_rule")


class Ride(TimestampMixin, Base):
    __tablename__ = "rides"
    __table_args__ = (
        CheckConstraint("estimated_distance_km >= 0", name="nonnegative_distance"),
        CheckConstraint("estimated_duration_minutes >= 0", name="nonnegative_duration"),
        CheckConstraint("estimated_fare >= 0", name="nonnegative_estimated_fare"),
        CheckConstraint("final_fare IS NULL OR final_fare >= 0", name="nonnegative_final_fare"),
        Index("ix_rides_rider_requested", "rider_id", "requested_at"),
        Index("ix_rides_driver_status", "driver_id", "status"),
        Index("ix_rides_status_requested", "status", "requested_at"),
        Index(
            "uq_rides_one_active_per_rider",
            "rider_id",
            unique=True,
            postgresql_where=text("status NOT IN ('COMPLETED', 'CANCELLED')"),
        ),
        Index(
            "uq_rides_one_active_per_driver",
            "driver_id",
            unique=True,
            postgresql_where=text(
                "driver_id IS NOT NULL AND status NOT IN ('COMPLETED', 'CANCELLED')"
            ),
        ),
    )

    _transitions: ClassVar[dict[RideStatus, frozenset[RideStatus]]] = {
        RideStatus.REQUESTED: frozenset({RideStatus.SEARCHING, RideStatus.CANCELLED}),
        RideStatus.SEARCHING: frozenset({RideStatus.DRIVER_ASSIGNED, RideStatus.CANCELLED}),
        RideStatus.DRIVER_ASSIGNED: frozenset({RideStatus.DRIVER_ARRIVING, RideStatus.CANCELLED}),
        RideStatus.DRIVER_ARRIVING: frozenset({RideStatus.DRIVER_ARRIVED, RideStatus.CANCELLED}),
        RideStatus.DRIVER_ARRIVED: frozenset({RideStatus.IN_PROGRESS, RideStatus.CANCELLED}),
        RideStatus.IN_PROGRESS: frozenset({RideStatus.COMPLETED}),
        RideStatus.COMPLETED: frozenset(),
        RideStatus.CANCELLED: frozenset(),
    }

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    rider_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="RESTRICT"), nullable=True
    )
    vehicle_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vehicles.id", ondelete="RESTRICT"), nullable=True
    )
    pricing_rule_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pricing_rules.id", ondelete="RESTRICT")
    )
    status: Mapped[RideStatus] = mapped_column(
        Enum(
            RideStatus,
            name="ride_status",
            values_callable=lambda statuses: [status.value for status in statuses],
        ),
        default=RideStatus.REQUESTED,
        server_default=RideStatus.REQUESTED.value,
    )
    ride_type: Mapped[RideType] = mapped_column(
        Enum(
            RideType,
            name="ride_type",
            values_callable=lambda ride_types: [ride_type.value for ride_type in ride_types],
        )
    )
    pickup_location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    destination_location: Mapped[WKBElement] = mapped_column(
        Geography(geometry_type="POINT", srid=4326, spatial_index=False)
    )
    estimated_distance_km: Mapped[Decimal] = mapped_column(Numeric(10, 3))
    estimated_duration_minutes: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    estimated_fare: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    final_fare: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    requested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), server_default=text("now()")
    )
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arriving_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    arrived_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rider: Mapped["User"] = relationship(back_populates="rides_as_rider")
    driver: Mapped["DriverProfile | None"] = relationship(back_populates="rides")
    vehicle: Mapped["Vehicle | None"] = relationship(back_populates="rides")
    pricing_rule: Mapped[PricingRule] = relationship(back_populates="rides")
    match_attempts: Mapped[list["RideMatchAttempt"]] = relationship(
        back_populates="ride", cascade="all, delete-orphan"
    )

    def begin_search(self) -> None:
        self._transition(RideStatus.SEARCHING)

    def accept(
        self, driver_id: uuid.UUID, vehicle_id: uuid.UUID, now: datetime | None = None
    ) -> None:
        if self.driver_id is not None:
            raise RideAlreadyAccepted("Ride is no longer available for acceptance")
        self._transition(RideStatus.DRIVER_ASSIGNED)
        self.driver_id = driver_id
        self.vehicle_id = vehicle_id
        self.accepted_at = now or datetime.now(UTC)

    def mark_arriving(self, now: datetime | None = None) -> None:
        transition_time = now or datetime.now(UTC)
        self._transition(RideStatus.DRIVER_ARRIVING)
        self.arriving_at = transition_time

    def mark_arrived(self, now: datetime | None = None) -> None:
        transition_time = now or datetime.now(UTC)
        self._transition(RideStatus.DRIVER_ARRIVED)
        self.arrived_at = transition_time

    def start(self, now: datetime | None = None) -> None:
        transition_time = now or datetime.now(UTC)
        self._transition(RideStatus.IN_PROGRESS)
        self.started_at = transition_time

    def complete(self, final_fare: Decimal, now: datetime | None = None) -> None:
        transition_time = now or datetime.now(UTC)
        self._transition(RideStatus.COMPLETED)
        self.final_fare = final_fare
        self.completed_at = transition_time

    def cancel(self, now: datetime | None = None) -> None:
        transition_time = now or datetime.now(UTC)
        self._transition(RideStatus.CANCELLED)
        self.cancelled_at = transition_time

    def _transition(self, target: RideStatus) -> None:
        if target not in self._transitions[self.status]:
            raise InvalidRideTransition(
                f"Ride cannot transition from {self.status.value} to {target.value}",
                {"current_status": self.status.value, "requested_status": target.value},
            )
        self.status = target


Index("ix_rides_pickup_location_gist", Ride.pickup_location, postgresql_using="gist")


class RideMatchAttempt(TimestampMixin, Base):
    __tablename__ = "ride_match_attempts"
    __table_args__ = (
        CheckConstraint("distance_m >= 0", name="nonnegative_distance"),
        UniqueConstraint("ride_id", "driver_id"),
        Index("ix_ride_match_attempts_ride_outcome", "ride_id", "outcome"),
        Index(
            "uq_ride_match_attempts_one_offered_per_ride",
            "ride_id",
            unique=True,
            postgresql_where=text("outcome = 'OFFERED'"),
        ),
        Index(
            "uq_ride_match_attempts_one_offer_per_driver",
            "driver_id",
            unique=True,
            postgresql_where=text("outcome = 'OFFERED'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    ride_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("rides.id", ondelete="CASCADE"), index=True
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("driver_profiles.id", ondelete="RESTRICT"), index=True
    )
    outcome: Mapped[MatchAttemptOutcome] = mapped_column(
        Enum(
            MatchAttemptOutcome,
            name="match_attempt_outcome",
            values_callable=lambda outcomes: [outcome.value for outcome in outcomes],
        ),
        default=MatchAttemptOutcome.OFFERED,
        server_default=MatchAttemptOutcome.OFFERED.value,
    )
    distance_m: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    offered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ride: Mapped[Ride] = relationship(back_populates="match_attempts")
    driver: Mapped["DriverProfile"] = relationship(back_populates="match_attempts")
