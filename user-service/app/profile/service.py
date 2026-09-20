"""Transactional mutations for the authenticated caller's own profile."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import bcrypt
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.errors import ApiError
from app.api.schemas import ProfileUpdateRequest
from app.models import AccountStatus, Credential, ParticipationMode, User, UserSession

_DELETED_DISPLAY_NAME = "Deleted User"


class ProfileService:
    """Apply the Phase 3 allow-list without trusting request identity fields."""

    async def update_profile(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        changes: ProfileUpdateRequest,
    ) -> User:
        """Persist only display name and participation-mode preferences."""

        async with session.begin():
            user = await self._locked_user(session, user_id=user_id)
            if changes.display_name is not None:
                user.display_name = changes.display_name
            if changes.active_participation_mode is not None:
                user.active_participation_mode = changes.active_participation_mode
        return user

    async def delete_account(
        self,
        session: AsyncSession,
        *,
        user_id: UUID,
        current_password: str,
    ) -> None:
        """Anonymize the caller and remove their authentication material atomically.

        The stable User Service ID remains for de-identified history owned by
        other services. No request can revive this terminal account state.
        """

        now = datetime.now(UTC)
        async with session.begin():
            row = (
                await session.execute(
                    select(User, Credential)
                    .join(Credential, Credential.user_id == User.id)
                    .where(User.id == user_id)
                    .with_for_update()
                )
            ).one_or_none()
            if row is None:
                raise self._invalid_access_error()
            user, credential = row
            if not self._password_matches(current_password, credential.password_hash):
                raise ApiError(
                    403,
                    "INVALID_CURRENT_PASSWORD",
                    "The current password is not valid.",
                )
            await session.execute(delete(UserSession).where(UserSession.user_id == user_id))
            await session.delete(credential)
            user.username = None
            user.normalized_username = None
            user.email = None
            user.normalized_email = None
            user.email_verified_at = None
            user.display_name = _DELETED_DISPLAY_NAME
            user.active_participation_mode = ParticipationMode.REQUESTER
            user.role_version += 1
            user.account_status = AccountStatus.DELETED
            user.deleted_at = now

    @staticmethod
    async def _locked_user(session: AsyncSession, *, user_id: UUID) -> User:
        user = (
            await session.execute(select(User).where(User.id == user_id).with_for_update())
        ).scalar_one_or_none()
        if user is None:
            raise ProfileService._invalid_access_error()
        return user

    @staticmethod
    def _password_matches(password: str, password_hash: str) -> bool:
        try:
            return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("ascii"))
        except ValueError:
            return False

    @staticmethod
    def _invalid_access_error() -> ApiError:
        return ApiError(401, "INVALID_ACCESS_TOKEN", "Authentication is required.")
