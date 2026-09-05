from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.exceptions import ApplicationError


async def application_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Serialize expected domain/application errors without leaking internals."""

    if not isinstance(exc, ApplicationError):
        raise exc
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
            }
        },
        headers={"WWW-Authenticate": "Bearer"} if exc.status_code == 401 else None,
    )


async def request_validation_error_handler(_: Request, exc: Exception) -> JSONResponse:
    """Return useful validation failures without echoing credentials or other input."""

    if not isinstance(exc, RequestValidationError):
        raise exc
    errors = [
        {
            "field": ".".join(str(part) for part in error["loc"]),
            "type": error["type"],
            "message": error["msg"],
        }
        for error in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Request validation failed",
                "details": {"errors": errors},
            }
        },
    )
