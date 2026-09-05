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
