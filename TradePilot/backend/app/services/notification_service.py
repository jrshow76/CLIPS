"""알림 서비스."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.notification import Notification, NotificationChannel
from app.repositories.notification_repository import (
    NotificationChannelRepository,
    NotificationRepository,
)

log = structlog.get_logger(__name__)


class NotificationService:
    """알림 도메인 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notis = NotificationRepository(db)
        self.channels = NotificationChannelRepository(db)

    async def list_for_user(
        self, user_id: int, *, read: bool | None, offset: int, limit: int
    ) -> tuple[list[Notification], int]:
        return await self.notis.list_for_user(
            user_id, read=read, offset=offset, limit=limit
        )

    async def mark_read(self, user_id: int, noti_id: int) -> None:
        updated = await self.notis.mark_read(user_id, noti_id)
        if not updated:
            raise AppException("E0062", message="알림을 찾을 수 없습니다.")
        await self.db.commit()

    async def mark_read_all(self, user_id: int) -> int:
        updated = await self.notis.mark_read_all(user_id)
        await self.db.commit()
        return updated

    async def get_channels(self, user_id: int) -> NotificationChannel:
        ch = await self.channels.get_or_create(user_id)
        await self.db.commit()
        return ch

    async def update_channels(
        self,
        user_id: int,
        *,
        inapp_enabled: bool | None = None,
        email_enabled: bool | None = None,
        telegram_enabled: bool | None = None,
        telegram_chat_id: str | None = None,
    ) -> NotificationChannel:
        ch = await self.channels.get_or_create(user_id)
        if inapp_enabled is not None:
            ch.inapp_enabled = inapp_enabled
        if email_enabled is not None:
            ch.email_enabled = email_enabled
        if telegram_enabled is not None:
            ch.telegram_enabled = telegram_enabled
        if telegram_chat_id is not None:
            ch.telegram_chat_id = telegram_chat_id
        await self.db.commit()
        await self.db.refresh(ch)
        return ch

    async def send_test(self, user_id: int, *, channel: str) -> dict[str, Any]:
        """테스트 알림 발송 (인앱은 DB 행 생성, EMAIL/TELEGRAM은 mock)."""
        ch = await self.channels.get_or_create(user_id)
        enabled_map = {
            "INAPP": ch.inapp_enabled,
            "EMAIL": ch.email_enabled,
            "TELEGRAM": ch.telegram_enabled,
        }
        if not enabled_map.get(channel, False):
            raise AppException(
                "E0082",
                message=f"{channel} 채널이 활성화되어 있지 않습니다.",
            )
        if channel == "INAPP":
            noti = Notification(
                user_id=user_id,
                event_type="TEST",
                priority="LOW",
                channel="INAPP",
                title="테스트 알림",
                body="알림 시스템 테스트입니다.",
                payload={"test": True},
                sent_at=datetime.now(tz=timezone.utc),
            )
            self.db.add(noti)
            await self.db.commit()
            log.info("test_notification_sent_inapp", user_id=user_id)
            return {"sent": True, "channel": channel}
        # EMAIL / TELEGRAM 은 mock (실제 전송은 별도 워커)
        log.info("test_notification_mock", user_id=user_id, channel=channel)
        return {"sent": True, "channel": channel, "mock": True}
