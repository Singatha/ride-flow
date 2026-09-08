from collections.abc import Mapping
from typing import Any


class ApplicationError(Exception):
    """A safe, expected failure that can cross the HTTP boundary."""

    code = "APPLICATION_ERROR"
    status_code = 400

    def __init__(self, message: str, details: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = dict(details or {})


class EmailAlreadyRegistered(ApplicationError):
    code = "EMAIL_ALREADY_REGISTERED"
    status_code = 409


class InvalidCredentials(ApplicationError):
    code = "INVALID_CREDENTIALS"
    status_code = 401


class InvalidToken(ApplicationError):
    code = "INVALID_TOKEN"
    status_code = 401


class InactiveUser(ApplicationError):
    code = "INACTIVE_USER"
    status_code = 403


class PermissionDenied(ApplicationError):
    code = "PERMISSION_DENIED"
    status_code = 403


class DriverProfileNotFound(ApplicationError):
    code = "DRIVER_PROFILE_NOT_FOUND"
    status_code = 404


class DriverProfileAlreadyExists(ApplicationError):
    code = "DRIVER_PROFILE_ALREADY_EXISTS"
    status_code = 409


class DriverNotVerified(ApplicationError):
    code = "DRIVER_NOT_VERIFIED"
    status_code = 409


class DriverStateConflict(ApplicationError):
    code = "DRIVER_STATE_CONFLICT"
    status_code = 409


class DriverMissingRequirements(ApplicationError):
    code = "DRIVER_MISSING_REQUIREMENTS"
    status_code = 409


class VehicleNotFound(ApplicationError):
    code = "VEHICLE_NOT_FOUND"
    status_code = 404


class VehicleAlreadyExists(ApplicationError):
    code = "VEHICLE_ALREADY_EXISTS"
    status_code = 409


class RideNotFound(ApplicationError):
    code = "RIDE_NOT_FOUND"
    status_code = 404


class PricingRuleNotFound(ApplicationError):
    code = "PRICING_RULE_NOT_FOUND"
    status_code = 409


class InvalidRideTransition(ApplicationError):
    code = "INVALID_RIDE_TRANSITION"
    status_code = 409


class RideAlreadyAccepted(ApplicationError):
    code = "RIDE_ALREADY_ACCEPTED"
    status_code = 409


class DriverUnavailable(ApplicationError):
    code = "DRIVER_UNAVAILABLE"
    status_code = 409


class ActiveRideExists(ApplicationError):
    code = "ACTIVE_RIDE_EXISTS"
    status_code = 409


class RideAccessDenied(ApplicationError):
    code = "RIDE_ACCESS_DENIED"
    status_code = 403


class RideOfferNotFound(ApplicationError):
    code = "RIDE_OFFER_NOT_FOUND"
    status_code = 409


class MatchingUnavailable(ApplicationError):
    code = "MATCHING_UNAVAILABLE"
    status_code = 503
