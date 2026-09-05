from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users.models import User
from app.domains.users.schemas import UserUpdateRequest


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def update_profile(self, user: User, data: UserUpdateRequest) -> User:
        changes = data.model_dump(exclude_unset=True)
        try:
            for field, value in changes.items():
                setattr(user, field, value)
            await self.session.flush()
            await self.session.refresh(user)
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return user
