from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.exceptions import InactiveUser, InvalidToken, PermissionDenied
from app.database.session import get_db_session
from app.domains.auth.security import decode_access_token
from app.domains.users.models import User, UserRole
from app.domains.users.repository import UserRepository

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise InvalidToken("Bearer access token is required")
    user_id = decode_access_token(credentials.credentials, settings)
    user = await UserRepository(session).get_by_id(user_id)
    if user is None:
        raise InvalidToken("Access token subject does not exist")
    if not user.is_active:
        raise InactiveUser("User account is inactive")
    return user


class RoleChecker:
    def __init__(self, *allowed_roles: UserRole) -> None:
        self.allowed_roles = frozenset(allowed_roles)

    async def __call__(self, user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in self.allowed_roles:
            raise PermissionDenied("Your role does not permit this operation")
        return user
