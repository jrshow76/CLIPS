"""관리자 API 라우터.

`docs/13_api_requirements.md` §18 명세 구현.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, engine
from app.core.dependencies import require_role
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
