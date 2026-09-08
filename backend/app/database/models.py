"""Import persistent models so Alembic can discover their metadata."""

from app.domains.auth.models import RefreshToken
from app.domains.drivers.models import DriverLocation, DriverProfile, Vehicle
from app.domains.rides.models import PricingRule, Ride, RideMatchAttempt
from app.domains.users.models import User

__all__ = [
    "DriverLocation",
    "DriverProfile",
    "PricingRule",
    "RefreshToken",
    "Ride",
    "RideMatchAttempt",
    "User",
    "Vehicle",
]
