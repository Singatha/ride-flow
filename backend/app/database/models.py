"""Import persistent models so Alembic can discover their metadata."""

from app.domains.auth.models import RefreshToken
from app.domains.users.models import User

__all__ = ["RefreshToken", "User"]
