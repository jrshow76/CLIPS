"""알림 워커 태스크.

- ``notifications.send``: 단일 알림(이벤트 + 사용자) 발송
- ``notifications.send_bulk``: 일괄 발송
- ``notifications.dispatch``: DB의 notification 행을 채널로 dispatch
- ``notifications.daily_report_all``: 매일 18:00 KST 전체 사용자 일일 리포트

재시도 정책:
- 외부 채널 실패는 지수 백오프(max=3회)
- 최종 실패 시 ``notifications`` 행의 ``payload.delivery`` 에 마지막 오류 누적
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
from typing import Any

import structlog
from celery import shared_task

log = structlog.get_logger(__name__)


# 재시도 백오프 (초): 30, 120, 300
_BACKOFF_SCHEDULE = (30, 120, 300)


@shared_task(
    name="notifications.send",
    queue="notifications",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_notification(
    self,  # type: ignore[no-untyped-def]
    *,
    user_id: int,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """단일 알림 발송 태스크.

    ``event_type`` 에 따라 NotificationService 의 적절한 send_* 메서드를 호출.
    """
    async def _run() -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal
        from app.services.notification_service import NotificationService
        from app.models.user import User

        async with AsyncSessionLocal() as db:
            user = await db.get(User, user_id)
            if user is None:
                log.warning("send_notification_user_missing", user_id=user_id)
                return {"sent": False, "error": "user_not_found"}
            svc = NotificationService(db)

            if event_type == "SIGNAL":
                noti = await svc.send_signal_alert(user=user, **payload)
            elif event_type == "ORDER_FILLED":
                noti = await svc.send_execution_alert(user=user, **payload)
            elif event_type == "KILL_SWITCH":
                noti = await svc.send_kill_switch_alert(user=user, **payload)
            elif event_type == "SECURITY":
                noti = await svc.send_security_alert(user=user, **payload)
            elif event_type == "DAILY_REPORT":
                noti = await svc.send_daily_report(user=user, **payload)
            else:
                # 사용자 정의: notify_user 직호출
                noti = await svc.notify_user(
                    user_id=user.id,
                    user_public_id=str(user.public_id),
                    title=str(payload.get("title", "알림")),
                    body=payload.get("body"),
                    event_type=event_type,
                    severity=payload.get("severity", "INFO"),
                    payload=payload.get("payload") or {},
                )
            return {"sent": noti is not None, "notification_id": noti.id if noti else None}

    try:
        result = asyncio.run(_run())
        log.info("notification_sent", event_type=event_type, user_id=user_id, **result)
        return result
    except Exception as e:  # noqa: BLE001
        log.warning(
            "notification_send_error",
            event_type=event_type,
            user_id=user_id,
            error=str(e)[:200],
            attempt=self.request.retries + 1 if hasattr(self, "request") else 1,
        )
        raise


@shared_task(name="notifications.send_bulk", queue="notifications")
def send_bulk(events: list[dict[str, Any]]) -> dict[str, Any]:
    """일괄 발송 (각 이벤트마다 send_notification 태스크 enqueue)."""
    enqueued = 0
    for ev in events:
        send_notification.delay(  # type: ignore[attr-defined]
            user_id=int(ev["user_id"]),
            event_type=str(ev["event_type"]),
            payload=dict(ev.get("payload") or {}),
        )
        enqueued += 1
    log.info("notifications_bulk_enqueued", count=enqueued)
    return {"enqueued": enqueued}


@shared_task(
    name="notifications.dispatch",
    queue="notifications",
    bind=True,
    max_retries=3,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
)
def dispatch_notification(self, notification_id: int) -> dict[str, Any]:  # type: ignore[no-untyped-def]
    """notifications 테이블 행을 채널 어댑터로 dispatch.

    실패 시 ``notifications.payload.delivery`` 에 결과가 누적된다.
    """
    async def _run() -> dict[str, Any]:
        from app.core.database import AsyncSessionLocal
        from app.services.notification_service import NotificationService

        async with AsyncSessionLocal() as db:
            svc = NotificationService(db)
            results = await svc.dispatch(notification_id)
            ok = sum(1 for r in results if r.ok)
            failed = sum(1 for r in results if not r.ok)
            return {"dispatched": len(results), "ok": ok, "failed": failed}

    try:
        result = asyncio.run(_run())
        log.info("notification_dispatched", id=notification_id, **result)
        return result
    except Exception as e:  # noqa: BLE001
        log.warning(
            "notification_dispatch_error",
            id=notification_id,
            error=str(e)[:200],
            attempt=self.request.retries + 1 if hasattr(self, "request") else 1,
        )
        raise


@shared_task(name="notifications.daily_report_all", queue="notifications")
def daily_report_all() -> dict[str, Any]:
    """전체 사용자 대상 일일 리포트 발송 (매일 18:00 KST Beat).

    1. 활성 사용자 조회
    2. 각 사용자별 ReportService로 당일 손익 집계
    3. NotificationService.send_daily_report 호출
    """
    async def _run() -> dict[str, Any]:
        from sqlalchemy import select

        from app.core.database import AsyncSessionLocal
        from app.models.user import User
        from app.services.notification_service import NotificationService
        from app.services.report_service import ReportService

        today = date.today()
        async with AsyncSessionLocal() as db:
            stmt = select(User).where(User.deleted_at.is_(None))
            users = list((await db.execute(stmt)).scalars().all())
            sent = 0
            failed = 0
            report_svc = ReportService(db)
            noti_svc = NotificationService(db)
            for u in users:
                try:
                    pnl = await report_svc.pnl_report(
                        u.id, from_date=today, to_date=today, granularity="D"
                    )
                    summary = pnl.get("summary", {})
                    positions = await report_svc.positions_report(
                        u.id, from_date=today, to_date=today
                    )
                    top_stocks = sorted(
                        positions,
                        key=lambda p: float(p.get("realized_pnl") or 0),
                        reverse=True,
                    )[:5]
                    report_data: dict[str, Any] = {
                        "realized_pnl": str(summary.get("total_realized", 0)),
                        "unrealized_pnl": str(summary.get("total_unrealized", 0)),
                        "buy_count": summary.get("win_count", 0),
                        "sell_count": summary.get("loss_count", 0),
                        "win_rate": float(summary.get("win_rate", 0.0)),
                        "total_amount": "0",
                        "top_pnl_stocks": [
                            {
                                "code": s.get("code"),
                                "name": s.get("name"),
                                "realized_pnl": str(s.get("realized_pnl", 0)),
                                "trades": s.get("win_count", 0) + s.get("loss_count", 0),
                            }
                            for s in top_stocks
                        ],
                    }
                    await noti_svc.send_daily_report(
                        user=u,
                        report_date=today.isoformat(),
                        report_data=report_data,
                    )
                    sent += 1
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    log.warning(
                        "daily_report_user_failed",
                        user_id=u.id,
                        error=str(e)[:200],
                    )
            return {"users_total": len(users), "sent": sent, "failed": failed}

    try:
        result = asyncio.run(_run())
        log.info("daily_report_all_done", **result)
        return result
    except Exception as e:  # noqa: BLE001
        log.exception("daily_report_all_error", error=str(e))
        return {"users_total": 0, "sent": 0, "failed": 0, "error": str(e)[:200]}


# 백오프 시간 노출 (테스트용)
__all__ = [
    "send_notification",
    "send_bulk",
    "dispatch_notification",
    "daily_report_all",
    "_BACKOFF_SCHEDULE",
]
