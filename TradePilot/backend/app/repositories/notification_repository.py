"""알림 Repository."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import and_, func, select, update

from app.models.notification import Notification, NotificationChannel
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
