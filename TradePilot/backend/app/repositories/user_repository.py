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
    """Refresh Token 세션 Repository.

    SEC-004(GATE-3) 보강:
    - jti 기반 조회/회전(rotate)/replay 탐지 메서드 추가.
    - find_by_jti는 폐기/만료 여부와 무관하게 조회하여 호출자가 상태를 검사할 수 있게 한다.
    """

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

    async def find_by_jti(self, jti: Any) -> Session | None:
        """jti 기반 조회 (폐기/만료 여부 무관).

        replay 탐지(이미 폐기된 jti가 다시 사용됨)를 위해 ``revoked_at``를
        WHERE 조건에 포함하지 않는다.
        """
        from uuid import UUID

        if isinstance(jti, str):
            try:
                jti = UUID(jti)
            except ValueError:
                return None
        stmt = select(Session).where(Session.jti == jti).limit(1)
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

    async def rotate(self, old_session: Session, new_jti: Any) -> None:
        """기존 세션을 즉시 폐기하고 새 jti로의 회전 체인을 기록한다.

        SEC-004(GATE-3): 호출자가 새 session 행을 ``add()``로 삽입한 직후/직전에
        본 메서드를 호출하면 동일 트랜잭션 내에서 회전이 원자적으로 처리된다.
        """
        from uuid import UUID

        if isinstance(new_jti, str):
            new_jti = UUID(new_jti)
        stmt = (
            update(Session)
            .where(Session.id == old_session.id)
            .values(
                revoked_at=datetime.now(tz=timezone.utc),
                replaced_by_jti=new_jti,
            )
        )
        await self.session.execute(stmt)

    async def delete_expired(self, cutoff: datetime) -> int:
        """expires_at < cutoff 인 행을 일괄 삭제.

        주기적 정리(cleanup) 작업에서 호출. 반환값은 삭제된 행 수.
        """
        from sqlalchemy import delete as sql_delete

        stmt = sql_delete(Session).where(Session.expires_at < cutoff)
        result = await self.session.execute(stmt)
        return int(result.rowcount or 0)
