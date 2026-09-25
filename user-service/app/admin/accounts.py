"""Safe exact-identity lookup for authorised User Service administrators."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.models import User
from app.registration.validation import normalize_email, normalize_username


class AdminAccountService:
    """Read one existing account without touching credentials or session state."""

    async def find_by_identity(
        self,
        session: AsyncSession,
        *,
        username: str | None,
        email: str | None,
    ) -> User:
        """Find the exact account identified by the validated username or email."""

        if username is not None:
            criterion = User.normalized_username == normalize_username(username)
        elif email is not None:
            criterion = User.normalized_email == normalize_email(email)
        else:
            raise ValueError("A validated identity criterion is required.")

        async with session.begin():
            user = (await session.execute(select(User).where(criterion))).scalar_one_or_none()
        if user is None:
            raise ApiError(404, "USER_NOT_FOUND", "No user account matches that identifier.")
        return user
