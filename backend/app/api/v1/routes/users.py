from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.v1.dependencies import get_user_service
from app.domains.auth.dependencies import get_current_user
from app.domains.users.models import User
from app.domains.users.schemas import UserResponse, UserUpdateRequest
from app.domains.users.service import UserService

router = APIRouter(prefix="/users")


@router.get("/me", response_model=UserResponse)
async def get_me(user: Annotated[User, Depends(get_current_user)]) -> User:
    return user


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdateRequest,
    user: Annotated[User, Depends(get_current_user)],
    service: Annotated[UserService, Depends(get_user_service)],
) -> User:
    return await service.update_profile(user, data)
