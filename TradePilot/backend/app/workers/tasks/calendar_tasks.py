"""시장 캘린더 동기화 태스크.

스케줄
------
- `calendar.sync_yearly`     : 매년 1월 2일 09:00 KST (당해/익년 일괄 동기화)
- `calendar.sync_for_year`   : 운영자 수동 트리거용 (특정 연도)

동기화 결과는 알림(`notifications` 큐)으로 발송한다.
"""
from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import structlog
from celery import shared_task

from app.core.database import AsyncSessionLocal
from app.services.calendar_service import CalendarService

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# 내부 코루틴
# ---------------------------------------------------------------------------
async def _sync_one_year(year: int) -> dict[str, int]:
    """단일 연도 동기화. CalendarService 호출."""
    async with AsyncSessionLocal() as session:
        svc = CalendarService(session)
        return await svc.sync_from_krx(year)


async def _sync_years(years: list[int]) -> dict[str, dict[str, int]]:
    """여러 연도 동기화."""
    out: dict[str, dict[str, int]] = {}
    for y in years:
        try:
            out[str(y)] = await _sync_one_year(y)
        except Exception:
            log.exception("calendar_sync_year_failed", year=y)
            out[str(y)] = {"fetched": 0, "upserted": 0, "skipped": 0, "error": 1}
    return out


def _send_notify(title: str, body: str) -> None:
    """동기화 결과 알림 발송 (운영자 채널). 실패는 무시."""
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task(
            "notifications.send",
            kwargs={
                "channel": "INAPP",
                "title": title,
                "body": body,
                "event_type": "CALENDAR_SYNC",
                "priority": "NORMAL",
            },
            queue="notifications",
        )
    except Exception:
        log.warning("calendar_sync_notify_failed", title=title)


# ---------------------------------------------------------------------------
# 태스크
# ---------------------------------------------------------------------------
@shared_task(
    name="calendar.sync_yearly",
    bind=True,
    max_retries=3,
    queue="default",
)
def sync_holidays_yearly(self: Any) -> dict[str, Any]:
    """매년 1월 2일 09:00 KST 실행.

    당해 + 익년 휴장일을 일괄 동기화한다.
    """
    today = date.today()
    years = [today.year, today.year + 1]
    log.info("calendar_sync_yearly_start", years=years)
    try:
        result = asyncio.run(_sync_years(years))
        body_lines = [
            f"{y}: fetched={r.get('fetched')}, upserted={r.get('upserted')}, skipped={r.get('skipped')}"
            for y, r in result.items()
        ]
        _send_notify(
            title="[캘린더] 연간 휴장일 자동 동기화 완료",
            body="\n".join(body_lines),
        )
        return {"years": years, "result": result}
    except Exception as e:
        log.exception("calendar_sync_yearly_failed")
        _send_notify(
            title="[캘린더] 연간 휴장일 자동 동기화 실패",
            body=f"오류: {e}",
        )
        raise self.retry(exc=e, countdown=300)


@shared_task(
    name="calendar.sync_for_year",
    bind=True,
    max_retries=3,
    queue="default",
)
def sync_holidays_for_year(self: Any, year: int) -> dict[str, Any]:
    """수동 트리거: 특정 연도 휴장일 동기화."""
    log.info("calendar_sync_year_start", year=year)
    try:
        result = asyncio.run(_sync_one_year(year))
        _send_notify(
            title=f"[캘린더] {year}년 휴장일 동기화 완료",
            body=f"fetched={result.get('fetched')}, upserted={result.get('upserted')}, skipped={result.get('skipped')}",
        )
        return {"year": year, **result}
    except Exception as e:
        log.exception("calendar_sync_year_failed", year=year)
        _send_notify(
            title=f"[캘린더] {year}년 휴장일 동기화 실패",
            body=f"오류: {e}",
        )
        raise self.retry(exc=e, countdown=120)
