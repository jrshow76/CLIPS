"""알림 Repository."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, delete, func, select, update

from app.models.notification import (
    Notification,
    NotificationChannel,
    PushSubscription,
)
from app.repositories.base import BaseRepository


class NotificationRepository(BaseRepository[Notification]):
    model = Notification

    async def list_for_user(
        self,
        user_id: int,
        *,
        read: bool | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> tuple[list[Notification], int]:
        stmt = select(Notification).where(Notification.user_id == user_id)
        cnt = select(func.count(Notification.id)).where(Notification.user_id == user_id)
        if read is not None:
            stmt = stmt.where(Notification.read.is_(read))
            cnt = cnt.where(Notification.read.is_(read))
        stmt = stmt.order_by(Notification.created_at.desc()).offset(offset).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        total = int((await self.session.execute(cnt)).scalar_one() or 0)
        return list(rows), total

    async def mark_read(self, user_id: int, noti_id: int) -> int:
        stmt = (
            update(Notification)
            .where(and_(Notification.id == noti_id, Notification.user_id == user_id))
            .values(read=True, read_at=datetime.now(tz=timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def mark_read_all(self, user_id: int) -> int:
        stmt = (
            update(Notification)
            .where(and_(Notification.user_id == user_id, Notification.read.is_(False)))
            .values(read=True, read_at=datetime.now(tz=timezone.utc))
        )
        result = await self.session.execute(stmt)
        return result.rowcount or 0


class NotificationChannelRepository(BaseRepository[NotificationChannel]):
    model = NotificationChannel

    async def get_or_create(self, user_id: int) -> NotificationChannel:
        existing = await self.get(user_id)
        if existing:
            return existing
        ch = NotificationChannel(user_id=user_id)
        self.session.add(ch)
        await self.session.flush()
        return ch


class PushSubscriptionRepository(BaseRepository[PushSubscription]):
    """Web Push 구독 endpoint 저장소."""

    model = PushSubscription

    async def list_active_for_user(self, user_id: int) -> list[PushSubscription]:
        stmt = (
            select(PushSubscription)
            .where(
                and_(
                    PushSubscription.user_id == user_id,
                    PushSubscription.active.is_(True),
                )
            )
            .order_by(PushSubscription.last_used_at.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        return list(rows)

    async def upsert(
        self,
        *,
        user_id: int,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_agent: str | None = None,
        expires_at: datetime | None = None,
    ) -> PushSubscription:
        stmt = select(PushSubscription).where(
            and_(
                PushSubscription.user_id == user_id,
                PushSubscription.endpoint == endpoint,
            )
        )
        existing = (await self.session.execute(stmt)).scalar_one_or_none()
        now = datetime.now(tz=timezone.utc)
        if existing:
            existing.p256dh_key = p256dh_key
            existing.auth_key = auth_key
            existing.user_agent = user_agent or existing.user_agent
            existing.expires_at = expires_at
            existing.last_used_at = now
            existing.active = True
            await self.session.flush()
            return existing
        sub = PushSubscription(
            user_id=user_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            user_agent=user_agent,
            expires_at=expires_at,
            active=True,
            last_used_at=now,
        )
        self.session.add(sub)
        await self.session.flush()
        return sub

    async def remove_by_endpoint(self, *, user_id: int | None, endpoint: str) -> int:
        cond = [PushSubscription.endpoint == endpoint]
        if user_id is not None:
            cond.append(PushSubscription.user_id == user_id)
        stmt = delete(PushSubscription).where(and_(*cond))
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def remove_all_for_user(self, user_id: int) -> int:
        stmt = delete(PushSubscription).where(PushSubscription.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.rowcount or 0

    async def touch_last_used(self, sub_id: int) -> None:
        stmt = (
            update(PushSubscription)
            .where(PushSubscription.id == sub_id)
            .values(last_used_at=datetime.now(tz=timezone.utc))
        )
        await self.session.execute(stmt)
