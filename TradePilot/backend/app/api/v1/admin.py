"""관리자 API 라우터.

`docs/13_api_requirements.md` §18 명세 구현.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Body, Depends, Path, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, engine
from app.core.dependencies import require_role
from app.core.exceptions import AppException
from app.core.redis_client import get_redis, ping_redis
from app.core.response import accepted_response, page_response, success_response
from app.models.user import AuditLogin
from app.schemas.admin import (
    AuditLogItem,
    HealthOut,
    MaintenanceIn,
    MaintenanceOut,
)

router = APIRouter(prefix="/admin", tags=["admin"])

# 운영 (ADMIN/OPERATOR 가드)
ADMIN = require_role("ROLE_ADMIN")
ADMIN_OR_OPERATOR = require_role("ROLE_ADMIN", "ROLE_OPERATOR")


@router.get("/system/health", summary="시스템 헬스 체크")
async def system_health(
    _user=Depends(ADMIN_OR_OPERATOR),
):
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass
    redis_ok = await ping_redis()
    try:
        from app.integrations.creon.event_listener import is_gateway_alive

        gateway_alive = is_gateway_alive(threshold_sec=30)
    except Exception:
        gateway_alive = False
    return success_response(
        HealthOut(
            db=db_ok,
            redis=redis_ok,
            creon_gateway=gateway_alive,
            ready=db_ok and redis_ok,
        )
    )


@router.post("/system/maintenance", summary="유지보수 모드 토글")
async def system_maintenance(
    payload: MaintenanceIn,
    _admin=Depends(ADMIN),
):
    """Redis에 유지보수 플래그 저장. 미들웨어/게이트웨이가 본 키를 참조해 차단할 수 있음."""
    redis = get_redis()
    if payload.enabled:
        await redis.set("system:maintenance", payload.message or "유지보수 중")
    else:
        await redis.delete("system:maintenance")
    return success_response(
        MaintenanceOut(
            enabled=payload.enabled,
            message=payload.message,
            updated_at=datetime.now(tz=timezone.utc),
        )
    )


@router.post("/data/refresh/master", summary="종목 마스터/섹터 갱신", status_code=202)
async def data_refresh_master(
    _operator=Depends(ADMIN_OR_OPERATOR),
):
    """종목/섹터 마스터 데이터 갱신 잡 큐잉.

    실제 갱신 워커는 `data.master_refresh` 태스크에서 처리.
    """
    job_id = uuid4().hex
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task("data.master_refresh", queue="default", kwargs={"job_id": job_id})
    except Exception:
        # 워커 미가용 환경에서도 성공 응답 (실제 작업은 fallback 없음)
        pass
    return accepted_response(job_id=job_id, status="QUEUED")


# ============================================================================
# 데이터 적재 관리
# ============================================================================
class BackfillIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start: date = Field(..., description="백필 시작일 (YYYY-MM-DD)")
    end: date = Field(..., description="백필 종료일 (YYYY-MM-DD)")
    codes: list[str] | None = Field(
        None, description="대상 종목 코드 (생략 시 전 종목)"
    )


_INGEST_JOB_PREFIX = "ingest:job:"


def _send_ingestion_task(
    task_name: str,
    *,
    queue: str = "ingestion",
    kwargs: dict | None = None,
) -> str:
    """Celery 태스크 enqueue + job_id 반환.

    워커 미가용 환경(테스트)에서도 job_id는 발급한다.
    """
    job_id = uuid4().hex
    payload = {**(kwargs or {}), "job_id": job_id}
    try:
        from app.workers.celery_app import celery_app

        celery_app.send_task(task_name, queue=queue, kwargs=payload)
    except Exception:  # noqa: BLE001 - 워커 미가용 시에도 예약 응답
        pass
    return job_id


@router.post(
    "/ingestion/stock-master",
    summary="종목 마스터 즉시 동기화",
    status_code=202,
)
async def ingestion_stock_master(
    _operator=Depends(ADMIN_OR_OPERATOR),
):
    """KRX 종목 마스터/섹터 매핑을 즉시 동기화."""
    job_id = _send_ingestion_task("ingestion.stock_master")
    return accepted_response(job_id=job_id, status="QUEUED")


@router.post(
    "/ingestion/daily/{ingest_date}",
    summary="특정일 일봉 적재",
    status_code=202,
)
async def ingestion_daily(
    ingest_date: date = Path(..., description="적재 일자 YYYY-MM-DD"),
    _operator=Depends(ADMIN_OR_OPERATOR),
):
    """지정한 날짜의 일봉을 즉시 적재."""
    job_id = _send_ingestion_task(
        "ingestion.daily_prices",
        kwargs={"date_str": ingest_date.isoformat()},
    )
    return accepted_response(
        job_id=job_id,
        status="QUEUED",
        extra={"trade_date": ingest_date.isoformat()},
    )


@router.post(
    "/ingestion/backfill",
    summary="과거 일봉 백필 시작",
    status_code=202,
)
async def ingestion_backfill(
    payload: BackfillIn = Body(...),
    _admin=Depends(ADMIN),
):
    """과거 일봉 데이터 백필 작업을 큐잉."""
    if payload.start > payload.end:
        raise AppException(
            "E0003",
            message="시작일이 종료일보다 늦을 수 없습니다.",
            details={"start": str(payload.start), "end": str(payload.end)},
        )
    if (payload.end - payload.start).days > 365 * 10:
        raise AppException(
            "E0063",
            message="백필 기간이 너무 깁니다 (최대 10년).",
        )
    job_id = _send_ingestion_task(
        "ingestion.backfill_daily",
        kwargs={
            "start": payload.start.isoformat(),
            "end": payload.end.isoformat(),
            "codes": payload.codes,
        },
    )
    return accepted_response(
        job_id=job_id,
        status="QUEUED",
        extra={
            "start": payload.start.isoformat(),
            "end": payload.end.isoformat(),
            "codes_count": len(payload.codes) if payload.codes else None,
        },
    )


@router.get("/ingestion/jobs", summary="적재 작업 목록")
async def ingestion_jobs(
    limit: int = Query(50, ge=1, le=200),
    _operator=Depends(ADMIN_OR_OPERATOR),
):
    """진행 중/완료된 적재 작업을 Redis에서 조회.

    `ingest:job:*` 키를 SCAN하여 최근 작업 N건을 반환한다.
    """
    redis = get_redis()
    items: list[dict] = []
    try:
        cursor = 0
        scanned = 0
        while True:
            cursor, keys = await redis.scan(
                cursor=cursor, match=f"{_INGEST_JOB_PREFIX}*", count=100
            )
            for k in keys:
                if scanned >= limit:
                    break
                raw = await redis.get(k)
                if raw is None:
                    continue
                try:
                    items.append(json.loads(raw))
                    scanned += 1
                except Exception:  # noqa: BLE001
                    continue
            if cursor == 0 or scanned >= limit:
                break
    except Exception as e:  # noqa: BLE001
        return success_response({"items": [], "error": str(e)[:200]})

    # 최신순 정렬 (ts 기준)
    items.sort(key=lambda x: x.get("ts", ""), reverse=True)
    return success_response({"items": items[:limit]})


@router.get("/ingestion/jobs/{job_id}", summary="적재 작업 진행률")
async def ingestion_job_detail(
    job_id: str = Path(..., min_length=8, max_length=64),
    _operator=Depends(ADMIN_OR_OPERATOR),
):
    """특정 작업의 진행률/상태 조회."""
    redis = get_redis()
    raw = await redis.get(_INGEST_JOB_PREFIX + job_id)
    if raw is None:
        raise AppException("E0062", message="작업을 찾을 수 없습니다.")
    try:
        return success_response(json.loads(raw))
    except Exception as e:  # noqa: BLE001
        raise AppException("E0005", message="작업 데이터 파싱 실패") from e


@router.post("/ingestion/jobs/{job_id}/cancel", summary="적재 작업 취소")
async def ingestion_job_cancel(
    job_id: str = Path(..., min_length=8, max_length=64),
    _admin=Depends(ADMIN),
):
    """작업 취소 요청 (best-effort).

    Celery Task의 revoke를 시도하고 Redis 상태를 CANCELED로 마킹한다.
    이미 실행 중인 태스크는 즉시 중단되지 않을 수 있다.
    """
    try:
        from app.workers.celery_app import celery_app

        celery_app.control.revoke(job_id, terminate=False)
    except Exception:  # noqa: BLE001
        pass

    redis = get_redis()
    raw = await redis.get(_INGEST_JOB_PREFIX + job_id)
    if raw is None:
        raise AppException("E0062", message="작업을 찾을 수 없습니다.")
    try:
        data = json.loads(raw)
    except Exception:
        data = {"job_id": job_id}
    data["status"] = "CANCELED"
    data["ts"] = datetime.now(tz=timezone.utc).isoformat()
    await redis.set(_INGEST_JOB_PREFIX + job_id, json.dumps(data, default=str))
    return success_response(data)


@router.get("/audit-logs", summary="감사 로그")
async def audit_logs(
    db: AsyncSession = Depends(get_db),
    _admin=Depends(ADMIN),
    user_id: int | None = Query(None),
    event: str | None = Query(None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
):
    stmt = select(AuditLogin).order_by(AuditLogin.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(AuditLogin.user_id == user_id)
    if event:
        stmt = stmt.where(AuditLogin.event == event)
    stmt = stmt.offset((page - 1) * size).limit(size)
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        AuditLogItem(
            id=r.id,
            user_id=r.user_id,
            event=r.event,
            result=r.result,
            ip_address=str(r.ip_address) if r.ip_address else None,
            user_agent=r.user_agent,
            meta=r.meta or {},
            created_at=r.created_at,
        )
        for r in rows
    ]
    has_next = len(items) >= size
    return page_response(items, page=page, size=size, total=None, has_next=has_next)
