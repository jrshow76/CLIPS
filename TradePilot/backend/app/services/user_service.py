"""사용자 도메인 서비스.

`/users/me`, `/users/me/settings`, 관리자용 목록/역할 변경을 담당한다.
"""
from __future__ import annotations

from typing import Any

import structlog
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.user import User, UserSettings
from app.repositories.user_repository import UserRepository

log = structlog.get_logger(__name__)


class UserService:
    """사용자 도메인 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    # ------------------------------------------------------------------
    # 내 정보
    # ------------------------------------------------------------------
    async def update_me(
        self, user: User, *, nickname: str | None, phone: str | None
    ) -> User:
        """프로필 부분 수정."""
        changed = False
        if nickname is not None:
            user.nickname = nickname
            changed = True
        if phone is not None:
            user.phone = phone
            # 휴대폰 번호가 바뀌면 인증 플래그 초기화
            user.phone_verified = False
            changed = True
        if changed:
            await self.db.commit()
            await self.db.refresh(user)
            log.info("user_profile_updated", user_id=user.id)
        return user

    # ------------------------------------------------------------------
    # 사용자 설정
    # ------------------------------------------------------------------
    async def get_settings(self, user_id: int) -> UserSettings:
        """사용자 설정 조회. 없으면 기본값 생성."""
        existing = await self.db.get(UserSettings, user_id)
        if existing:
            return existing
        settings_row = UserSettings(user_id=user_id)
        self.db.add(settings_row)
        await self.db.commit()
        await self.db.refresh(settings_row)
        return settings_row

    async def update_settings(
        self,
        user_id: int,
        *,
        theme: str | None = None,
        noti_inapp: bool | None = None,
        noti_email: bool | None = None,
        noti_telegram: bool | None = None,
        noti_rules: dict[str, Any] | None = None,
        schedule: dict[str, Any] | None = None,
    ) -> UserSettings:
        settings_row = await self.get_settings(user_id)
        if theme is not None:
            settings_row.theme = theme
        if noti_inapp is not None:
            settings_row.noti_inapp = noti_inapp
        if noti_email is not None:
            settings_row.noti_email = noti_email
        if noti_telegram is not None:
            settings_row.noti_telegram = noti_telegram
        if noti_rules is not None:
            settings_row.noti_rules = noti_rules
        if schedule is not None:
            settings_row.schedule = schedule
        await self.db.commit()
        await self.db.refresh(settings_row)
        log.info("user_settings_updated", user_id=user_id)
        return settings_row

    # ------------------------------------------------------------------
    # 관리자
    # ------------------------------------------------------------------
    async def list_users_admin(
        self,
        *,
        q: str | None = None,
        role: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[User], int]:
        """관리자용 사용자 목록."""
        stmt = select(User).where(User.deleted_at.is_(None))
        cnt = select(func.count(User.id)).where(User.deleted_at.is_(None))
        if q:
            like = f"%{q}%"
            stmt = stmt.where((User.email.ilike(like)) | (User.nickname.ilike(like)))
            cnt = cnt.where((User.email.ilike(like)) | (User.nickname.ilike(like)))
        if role:
            stmt = stmt.where(User.role == role)
            cnt = cnt.where(User.role == role)
        stmt = stmt.order_by(User.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.db.execute(stmt)).scalars().all()
        total = int((await self.db.execute(cnt)).scalar_one() or 0)
        return list(rows), total

    async def update_role_admin(self, target_public_id: str, role: str) -> User:
        """관리자: 사용자 역할 변경."""
        user = await self.users.find_by_public_id(target_public_id)
        if not user:
            raise AppException("E0062", message="대상 사용자를 찾을 수 없습니다.")
        user.role = role
        await self.db.commit()
        await self.db.refresh(user)
        log.info("user_role_changed", user_id=user.id, new_role=role)
        return user
