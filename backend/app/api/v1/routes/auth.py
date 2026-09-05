from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from app.api.v1.dependencies import get_auth_service
from app.core.exceptions import InvalidToken
from app.domains.auth.schemas import LoginRequest, LogoutRequest, RefreshRequest, TokenResponse
from app.domains.auth.service import AuthService
from app.domains.users.schemas import RegisterRequest

router = APIRouter(prefix="/auth")
REFRESH_COOKIE_NAME = "rideflow_refresh"


def set_refresh_cookie(response: Response, token: str, service: AuthService) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=token,
        max_age=service.settings.refresh_token_ttl_days * 24 * 60 * 60,
        httponly=True,
        secure=service.settings.environment not in {"local", "test"},
        samesite="lax",
        path="/api/v1/auth",
    )


def resolve_refresh_token(value: str | None, request: Request) -> str:
    token = value or request.cookies.get(REFRESH_COOKIE_NAME)
    if token is None:
        raise InvalidToken("Refresh token is required")
    return token


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: RegisterRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    tokens = await service.register(data)
    set_refresh_cookie(response, tokens.refresh_token, service)
    return tokens


@router.post("/login", response_model=TokenResponse)
async def login(
    data: LoginRequest,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    tokens = await service.login(data)
    set_refresh_cookie(response, tokens.refresh_token, service)
    return tokens


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    data: RefreshRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> TokenResponse:
    tokens = await service.refresh(resolve_refresh_token(data.refresh_token, request))
    set_refresh_cookie(response, tokens.refresh_token, service)
    return tokens


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    data: LogoutRequest,
    request: Request,
    response: Response,
    service: Annotated[AuthService, Depends(get_auth_service)],
) -> Response:
    await service.logout(resolve_refresh_token(data.refresh_token, request))
    response.delete_cookie(key=REFRESH_COOKIE_NAME, path="/api/v1/auth")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
