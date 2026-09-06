import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.core.exceptions import InvalidRideTransition, RideAlreadyAccepted
from app.domains.rides.models import Ride, RideStatus, RideType


def ride_in(status: RideStatus) -> Ride:
    return Ride(
        rider_id=uuid.uuid4(),
        pricing_rule_id=uuid.uuid4(),
        status=status,
        ride_type=RideType.STANDARD,
        estimated_distance_km=Decimal("5.000"),
        estimated_duration_minutes=Decimal("10.00"),
        estimated_fare=Decimal("95.00"),
    )


def test_full_ride_lifecycle_uses_explicit_operations() -> None:
    now = datetime(2026, 9, 6, tzinfo=UTC)
    ride = ride_in(RideStatus.REQUESTED)
    driver_id = uuid.uuid4()
    vehicle_id = uuid.uuid4()

    ride.begin_search()
    ride.accept(driver_id, vehicle_id, now)
    ride.mark_arriving(now)
    ride.mark_arrived(now)
    ride.start(now)
    ride.complete(Decimal("95.00"), now)

    assert ride.status is RideStatus.COMPLETED
    assert ride.driver_id == driver_id
    assert ride.vehicle_id == vehicle_id
    assert ride.accepted_at == now
    assert ride.arriving_at == now
    assert ride.arrived_at == now
    assert ride.started_at == now
    assert ride.completed_at == now
    assert ride.final_fare == Decimal("95.00")


def test_invalid_transition_reports_both_states() -> None:
    ride = ride_in(RideStatus.DRIVER_ASSIGNED)

    with pytest.raises(InvalidRideTransition) as exc_info:
        ride.start()

    assert exc_info.value.details == {
        "current_status": "DRIVER_ASSIGNED",
        "requested_status": "IN_PROGRESS",
    }


def test_only_pre_trip_rides_can_be_cancelled() -> None:
    cancellable = ride_in(RideStatus.DRIVER_ARRIVED)
    active = ride_in(RideStatus.IN_PROGRESS)

    cancellable.cancel()

    assert cancellable.status is RideStatus.CANCELLED
    with pytest.raises(InvalidRideTransition):
        active.cancel()


def test_only_searching_ride_can_be_accepted() -> None:
    cancelled = ride_in(RideStatus.CANCELLED)
    assigned = ride_in(RideStatus.SEARCHING)
    assigned.accept(uuid.uuid4(), uuid.uuid4())

    with pytest.raises(InvalidRideTransition):
        cancelled.accept(uuid.uuid4(), uuid.uuid4())
    with pytest.raises(RideAlreadyAccepted):
        assigned.accept(uuid.uuid4(), uuid.uuid4())
