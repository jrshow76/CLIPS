"""시장(지수) API 라우터.

`docs/13_api_requirements.md` §13 명세 + 시장 캘린더 자동화 확장.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import require_role
from app.core.response import accepted_response, success_response
from app.schemas.market import (
    BusinessDayOut,
    CalendarHolidayItem,
    CalendarItem,
    CalendarSyncOut,
    HolidayCreateIn,
    IndexCandle,
    IndexItem,
    MarketStatusOut,
)
from app.services.calendar_service import CalendarService
from app.services.market_service import MarketService

router = APIRouter(prefix="/market", tags=["market"])

# 관리자/운영자 가드
_ADMIN = require_role("ROLE_ADMIN")
_ADMIN_OR_OPERATOR = require_role("ROLE_ADMIN", "ROLE_OPERATOR")


@router.get("/indices", summary="시장 지수")
async def indices(db: AsyncSession = Depends(get_db)):
    svc = MarketService(db)
    data = await svc.list_indices()
    items = [IndexItem(**d) for d in data]
    return success_response([i.model_dump() for i in items])


@router.get("/indices/{code}/candles", summary="지수 OHLCV")
async def index_candles(
    code: str,
    db: AsyncSession = Depends(get_db),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    svc = MarketService(db)
    rows = await svc.candles(
        code,
        from_date=date.fromisoformat(from_) if from_ else None,
        to_date=date.fromisoformat(to) if to else None,
    )
    items = [IndexCandle(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/status", summary="장 운영 상태")
async def market_status(db: AsyncSession = Depends(get_db)):
    svc = MarketService(db)
    data = await svc.market_status()
    return success_response(MarketStatusOut(**data))


# ---------------------------------------------------------------------------
# 캘린더 (퍼블릭 조회)
# ---------------------------------------------------------------------------
@router.get("/calendar", summary="연간 휴장일(쿼리)")
async def calendar(
    db: AsyncSession = Depends(get_db),
    year: int = Query(..., ge=2020, le=2035),
):
    """레거시 호환 엔드포인트. `?year=YYYY` 쿼리로 호출."""
    svc = MarketService(db)
    rows = await svc.calendar(year)
    items = [CalendarItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/calendar/{year}", summary="연도별 휴장일 상세")
async def calendar_by_year(
    year: int,
    db: AsyncSession = Depends(get_db),
    market: str = Query("KRX", min_length=2, max_length=10),
):
    """연도 PathParam 기반 캘린더 조회 (캐시).

    - 응답: holiday_date / holiday_name / holiday_type / market / source
    """
    if year < 2020 or year > 2035:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="year 는 2020~2035 범위여야 합니다.")
    svc = CalendarService(db)
    holidays = await svc.get_holidays(year, market)
    items = [
        CalendarHolidayItem(
            holiday_date=h.date,
            holiday_name=h.name,
            holiday_type=h.type,
            market=h.market,
            source=h.source,
            description=h.description,
        )
        for h in holidays
    ]
    return success_response([i.model_dump() for i in items])


@router.get("/calendar/business-day/{target_date}", summary="영업일 여부 + 다음/이전 영업일")
async def calendar_business_day(
    target_date: str,
    db: AsyncSession = Depends(get_db),
    market: str = Query("KRX", min_length=2, max_length=10),
):
    """주어진 날짜의 영업일 여부, 다음 영업일, 이전 영업일을 반환."""
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="target_date 는 YYYY-MM-DD 형식이어야 합니다.")
    svc = CalendarService(db)
    is_biz = await svc.is_business_day(d, market)
    is_holi = await svc.is_holiday(d, market)
    nxt = await svc.next_business_day(d, market)
    prev = await svc.previous_business_day(d, market)
    return success_response(
        BusinessDayOut(
            date=d,
            is_business_day=is_biz,
            is_holiday=is_holi,
            is_weekend=d.weekday() >= 5,
            next_business_day=nxt,
            previous_business_day=prev,
        )
    )


# ---------------------------------------------------------------------------
# 관리자: 동기화 / 임시휴장 추가 / 삭제
#  prefix /admin 별도 라우터 (권한 가드)
# ---------------------------------------------------------------------------
admin_calendar_router = APIRouter(prefix="/admin/market/calendar", tags=["admin", "market"])


@admin_calendar_router.post(
    "/sync/{year}",
    summary="휴장일 수동 동기화 (관리자)",
    status_code=202,
)
async def admin_sync_calendar(
    year: int,
    _operator=Depends(_ADMIN_OR_OPERATOR),
):
    """Celery 태스크 `calendar.sync_for_year` 를 enqueue. 워커 미가용 시
    동기 실행으로 fallback (테스트/개발 편의)."""
    if year < 2020 or year > 2035:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="year 는 2020~2035 범위여야 합니다.")
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task(
            "calendar.sync_for_year",
            kwargs={"year": year},
            queue="default",
        )
        return accepted_response(status="QUEUED", extra={"year": year})
    except Exception:
        # 워커 미가용 환경 fallback: 인라인 실행
        from app.core.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            svc = CalendarService(session)
            result = await svc.sync_from_krx(year)
        return success_response(CalendarSyncOut(year=year, **result))


@admin_calendar_router.post(
    "/holidays",
    summary="임시휴장 추가 (관리자)",
    status_code=201,
)
async def admin_add_holiday(
    payload: HolidayCreateIn,
    db: AsyncSession = Depends(get_db),
    _operator=Depends(_ADMIN_OR_OPERATOR),
):
    svc = CalendarService(db)
    h = await svc.add_holiday(
        target=payload.holiday_date,
        name=payload.holiday_name,
        holiday_type=payload.holiday_type,
        market=payload.market,
        source="manual",
        description=payload.description,
    )
    return success_response(
        CalendarHolidayItem(
            holiday_date=h.date,
            holiday_name=h.name,
            holiday_type=h.type,
            market=h.market,
            source=h.source,
            description=h.description,
        )
    )


@admin_calendar_router.delete(
    "/holidays/{target_date}",
    summary="휴장일 삭제 (관리자)",
)
async def admin_delete_holiday(
    target_date: str,
    db: AsyncSession = Depends(get_db),
    market: str = Query("KRX", min_length=2, max_length=10),
    user=Depends(_ADMIN),
):
    try:
        d = date.fromisoformat(target_date)
    except ValueError:
        from fastapi import HTTPException

        raise HTTPException(status_code=400, detail="target_date 는 YYYY-MM-DD 형식이어야 합니다.")
    svc = CalendarService(db)
    removed = await svc.remove_holiday(d, market, actor_user_id=user.id)
    return success_response({"date": d.isoformat(), "removed": removed, "market": market})


# `admin_calendar_router` 는 prefix `/admin/...` 를 사용하므로
# 시장 라우터(`/market`)에 include 하지 않고 v1/__init__.py 에서 별도 등록한다.
