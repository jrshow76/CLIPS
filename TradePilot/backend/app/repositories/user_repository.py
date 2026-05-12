"""사용자 도메인 Repository."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import OtpCode, Session, User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """사용자 Repository."""

    model = User

    async def find_by_email(self, email: str, include_deleted: bool = False) -> User | None:
        stmt = select(User).where(User.email == email)
        if not include_deleted:
            stmt = stmt.where(User.deleted_at.is_(None))
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_by_public_id(self, public_id: str) -> User | None:
        stmt = select(User).where(
            and_(User.public_id == public_id, User.deleted_at.is_(None))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def increment_login_fail(self, user_id: int, lock_until: datetime | None = None) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                login_fail_count=User.login_fail_count + 1,
                locked_until=lock_until,
            )
        )
        await self.session.execute(stmt)

    async def reset_login_fail(self, user_id: int) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(
                login_fail_count=0,
                locked_until=None,
                last_login_at=datetime.now(tz=timezone.utc),
            )
        )
        await self.session.execute(stmt)

    async def update_password(self, user_id: int, new_hash: str) -> None:
        stmt = update(User).where(User.id == user_id).values(password_hash=new_hash)
        await self.session.execute(stmt)


class OtpRepository(BaseRepository[OtpCode]):
    model = OtpCode

    async def create(
        self,
        *,
        user_id: int,
        otp_id: Any,
        purpose: str,
        code_hash: str,
        channel: str,
        expires_at: datetime,
    ) -> OtpCode:
        otp = OtpCode(
            user_id=user_id,
            otp_id=otp_id,
            purpose=purpose,
            code_hash=code_hash,
            channel=channel,
            expires_at=expires_at,
        )
        return await self.add(otp)

    async def find_active(self, otp_id: Any) -> OtpCode | None:
        stmt = select(OtpCode).where(
            and_(OtpCode.otp_id == otp_id, OtpCode.consumed_at.is_(None))
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def consume(self, otp_id: int) -> None:
        stmt = (
            update(OtpCode)
            .where(OtpCode.id == otp_id)
            .values(consumed_at=datetime.now(tz=timezone.utc))
        )
        await self.session.execute(stmt)

    async def increment_attempt(self, otp_id: int) -> None:
        stmt = (
            update(OtpCode)
            .where(OtpCode.id == otp_id)
            .values(attempt_count=OtpCode.attempt_count + 1)
        )
        await self.session.execute(stmt)


class SessionRepository(BaseRepository[Session]):
    model = Session

    async def find_by_hash(self, token_hash: str) -> Session | None:
        stmt = select(Session).where(
            and_(
                Session.refresh_token_hash == token_hash,
                Session.revoked_at.is_(None),
                Session.expires_at > datetime.now(tz=timezone.utc),
            )
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def revoke(self, session_id: int) -> None:
        stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(revoked_at=datetime.now(tz=timezone.utc))
        )
        await self.session.execute(stmt)

    async def revoke_all_for_user(self, user_id: int) -> None:
        stmt = (
            update(Session)
            .where(and_(Session.user_id == user_id, Session.revoked_at.is_(None)))
            .values(revoked_at=datetime.now(tz=timezone.utc))
        )
        await self.session.execute(stmt)
