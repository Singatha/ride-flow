import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.exceptions import EmailAlreadyRegistered, InvalidCredentials, InvalidToken
from app.domains.auth.models import RefreshToken
from app.domains.auth.repository import RefreshTokenRepository
from app.domains.auth.schemas import LoginRequest, TokenResponse
from app.domains.auth.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    digest_refresh_token,
    generate_refresh_token,
    hash_password,
    verify_password,
)
from app.domains.users.models import User
from app.domains.users.repository import UserRepository
from app.domains.users.schemas import RegisterRequest, UserResponse


@dataclass(frozen=True)
class IssuedRefreshToken:
    plaintext: str
    model: RefreshToken


class AuthService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self.users = UserRepository(session)
        self.refresh_tokens = RefreshTokenRepository(session)

    async def register(self, data: RegisterRequest) -> TokenResponse:
        email = str(data.email).strip().lower()
        try:
            async with self.session.begin():
                if await self.users.get_by_email(email) is not None:
                    raise EmailAlreadyRegistered("An account with this email already exists")
                user = User(
                    email=email,
                    password_hash=hash_password(data.password),
                    role=data.role,
                    first_name=data.first_name,
                    last_name=data.last_name,
                    phone_number=data.phone_number,
                )
                self.users.add(user)
                await self.session.flush()
                issued = self._issue_refresh_token(user.id)
                await self.session.flush()
        except IntegrityError as exc:
            raise EmailAlreadyRegistered("An account with this email already exists") from exc
        return self._token_response(user, issued.plaintext)

    async def login(self, data: LoginRequest) -> TokenResponse:
        email = str(data.email).strip().lower()
        user = await self.users.get_by_email(email)
        password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
        password_valid = verify_password(data.password, password_hash)
        if user is None or not password_valid or not user.is_active:
            raise InvalidCredentials("Email or password is incorrect")

        try:
            issued = self._issue_refresh_token(user.id)
            await self.session.flush()
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
        return self._token_response(user, issued.plaintext)

    async def refresh(self, plaintext_token: str) -> TokenResponse:
        now = datetime.now(UTC)
        replayed_family: uuid.UUID | None = None
        user: User | None = None
        issued: IssuedRefreshToken | None = None

        async with self.session.begin():
            current = await self.refresh_tokens.get_by_hash_for_update(
                digest_refresh_token(plaintext_token)
            )
            if current is None:
                raise InvalidToken("Refresh token is invalid or expired")
            if current.revoked_at is not None:
                replayed_family = current.family_id
                await self.refresh_tokens.revoke_family(current.family_id, now)
            elif current.expires_at <= now:
                current.revoked_at = now
            else:
                user = await self.users.get_by_id(current.user_id)
                if user is None or not user.is_active:
                    current.revoked_at = now
                else:
                    current.revoked_at = now
                    issued = self._issue_refresh_token(
                        user.id, family_id=current.family_id, parent_id=current.id
                    )
                    await self.session.flush()

        if replayed_family is not None:
            raise InvalidToken("Refresh token reuse detected; token family revoked")
        if user is None or issued is None:
            raise InvalidToken("Refresh token is invalid or expired")
        return self._token_response(user, issued.plaintext)

    async def logout(self, plaintext_token: str) -> None:
        now = datetime.now(UTC)
        async with self.session.begin():
            current = await self.refresh_tokens.get_by_hash_for_update(
                digest_refresh_token(plaintext_token)
            )
            if current is not None and current.revoked_at is None:
                current.revoked_at = now

    def _issue_refresh_token(
        self,
        user_id: uuid.UUID,
        *,
        family_id: uuid.UUID | None = None,
        parent_id: uuid.UUID | None = None,
    ) -> IssuedRefreshToken:
        plaintext = generate_refresh_token()
        model = RefreshToken(
            user_id=user_id,
            family_id=family_id or uuid.uuid4(),
            parent_id=parent_id,
            token_hash=digest_refresh_token(plaintext),
            expires_at=datetime.now(UTC) + timedelta(days=self.settings.refresh_token_ttl_days),
        )
        self.refresh_tokens.add(model)
        return IssuedRefreshToken(plaintext=plaintext, model=model)

    def _token_response(self, user: User, refresh_token: str) -> TokenResponse:
        return TokenResponse(
            access_token=create_access_token(user, self.settings),
            refresh_token=refresh_token,
            expires_in=self.settings.access_token_ttl_minutes * 60,
            user=UserResponse.model_validate(user),
        )
