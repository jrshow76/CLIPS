"""알림 API 라우터.

`docs/13_api_requirements.md` §14 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.schemas.notification import (
    ChannelOut,
    ChannelUpdateIn,
    NotificationItem,
    PushSubscribeIn,
    PushTestResult,
    PushUnsubscribeIn,
    PushVapidKeyOut,
    TestSendIn,
)
from app.services.notification_service import NotificationService

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", summary="알림 목록")
async def list_notifications(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    read: bool | None = Query(None),
):
    svc = NotificationService(db)
    rows, total = await svc.list_for_user(
        user.id, read=read, offset=page.offset, limit=page.limit
    )
    items = [
        NotificationItem(
            id=n.id,
            event_type=n.event_type,
            priority=n.priority,  # type: ignore[arg-type]
            channel=n.channel,
            title=n.title,
            body=n.body,
            read=n.read,
            read_at=n.read_at,
            created_at=n.created_at,
            payload=n.payload or {},
        )
        for n in rows
    ]
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.patch("/{noti_id}/read", summary="단건 읽음 처리")
async def read_one(
    noti_id: int,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    await svc.mark_read(user.id, noti_id)
    return success_response({"read": True, "id": noti_id})


@router.post("/read-all", summary="전체 읽음 처리")
async def read_all(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = NotificationService(db)
    updated = await svc.mark_read_all(user.id)
    return success_response({"read": True, "updated": updated})


@router.get("/channels", summary="알림 채널 조회")
async def get_channels(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = NotificationService(db)
    ch = await svc.get_channels(user.id)
    return success_response(
        ChannelOut(
            inapp_enabled=ch.inapp_enabled,
            email_enabled=ch.email_enabled,
            telegram_enabled=ch.telegram_enabled,
            telegram_chat_id=ch.telegram_chat_id,
        )
    )


@router.patch("/channels", summary="알림 채널 수정")
async def update_channels(
    payload: ChannelUpdateIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    ch = await svc.update_channels(
        user.id,
        inapp_enabled=payload.inapp_enabled,
        email_enabled=payload.email_enabled,
        telegram_enabled=payload.telegram_enabled,
        telegram_chat_id=payload.telegram_chat_id,
    )
    return success_response(
        ChannelOut(
            inapp_enabled=ch.inapp_enabled,
            email_enabled=ch.email_enabled,
            telegram_enabled=ch.telegram_enabled,
            telegram_chat_id=ch.telegram_chat_id,
        )
    )


@router.post("/test", summary="테스트 발송")
async def test_send(
    payload: TestSendIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    data = await svc.send_test(user.id, channel=payload.channel)
    return success_response(data)


# ==========================================================
# Web Push (PWA)
# ==========================================================
@router.get("/push/vapid-public-key", summary="VAPID 공개키 조회")
async def get_vapid_public_key(
    _user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    """클라이언트가 pushManager.subscribe 에 사용할 P-256 공개키.

    환경에 VAPID_PUBLIC_KEY 가 설정되지 않은 경우 ``public_key=null`` 반환.
    """
    svc = NotificationService(db)
    return success_response(PushVapidKeyOut(public_key=svc.webpush_public_key()))


@router.post("/push/subscribe", summary="Web Push 구독 등록")
async def subscribe_push(
    payload: PushSubscribeIn,
    user: CurrentUser,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    ua = payload.user_agent or request.headers.get("user-agent")
    sub = await svc.register_push_subscription(
        user_id=user.id,
        endpoint=payload.endpoint,
        p256dh_key=payload.p256dh_key,
        auth_key=payload.auth_key,
        user_agent=ua,
        expires_at=payload.expires_at,
    )
    return success_response(
        {
            "id": sub.id,
            "endpoint": sub.endpoint,
            "active": sub.active,
            "last_used_at": sub.last_used_at,
        }
    )


@router.delete("/push/unsubscribe", summary="Web Push 구독 해제")
async def unsubscribe_push(
    user: CurrentUser,
    payload: PushUnsubscribeIn | None = None,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    endpoint = payload.endpoint if payload else None
    removed = await svc.unregister_push_subscription(
        user_id=user.id, endpoint=endpoint
    )
    return success_response({"removed": removed})


@router.post("/push/test", summary="Web Push 테스트 발송")
async def test_push(
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = NotificationService(db)
    result = await svc.send_test_webpush(user.id)
    return success_response(PushTestResult(**result))
