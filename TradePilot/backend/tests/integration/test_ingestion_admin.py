"""데이터 적재 관리자 API 통합 테스트.

DB와 Redis가 동작 중이어야 한다 (CI는 docker compose up 후 실행).

검증 흐름:
- ROLE_ADMIN 사용자로 로그인 → 관리자 API 호출
- POST /admin/ingestion/* → 202 Accepted + job_id 반환
- GET /admin/ingestion/jobs/{id} → Redis에 진행률 키가 있을 때만 200,
  없으면 404 (E0062)
- POST /admin/ingestion/backfill → 입력 검증 (E0003/E0063)

Celery는 eager 모드 또는 워커 미가용 환경에서도 응답이 정상이어야 한다 (큐잉만 검증).
"""
from __future__ import annotations

import json
import os
import uuid

import pytest

# Celery 워커 미가용 환경에서도 동작하도록 합성 모드
os.environ["INGEST_USE_SYNTHETIC"] = "true"

pytestmark = pytest.mark.integration


def _unique_email() -> str:
    return f"admin-{uuid.uuid4().hex[:8]}@test.local"


def _make_admin_token(app_client) -> str:
    """ADMIN 사용자 생성 후 토큰 반환.

    User.role 컬럼을 직접 ADMIN으로 변경.
    """
    from sqlalchemy import update

    from app.core.database import AsyncSessionLocal
    from app.models.user import User

    email = _unique_email()
    pw = "Abcd1234!"
    r = app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "admin"},
    )
    assert r.status_code == 201, r.text

    # role을 ADMIN으로 승격
    import asyncio

    async def _promote() -> None:
        async with AsyncSessionLocal() as db:
            await db.execute(
                update(User).where(User.email == email).values(role="ROLE_ADMIN")
            )
            await db.commit()

    asyncio.run(_promote())

    r = app_client.post(
        "/api/v1/auth/login", json={"email": email, "password": pw}
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["access_token"]


# ---------------------------------------------------------------------------
# 종목 마스터 트리거
# ---------------------------------------------------------------------------
def test_ingestion_stock_master_returns_accepted(app_client) -> None:
    token = _make_admin_token(app_client)
    r = app_client.post(
        "/api/v1/admin/ingestion/stock-master",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 202, r.text
    body = r.json()
    assert body["success"] is True
    assert "job_id" in body["data"]
    assert body["data"]["status"] == "QUEUED"


# ---------------------------------------------------------------------------
# 일봉 적재 트리거
# ---------------------------------------------------------------------------
def test_ingestion_daily_returns_accepted(app_client) -> None:
    token = _make_admin_token(app_client)
    r = app_client.post(
        "/api/v1/admin/ingestion/daily/2026-05-13",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 202, r.text
    data = r.json()["data"]
    assert data["job_id"]
    assert data["trade_date"] == "2026-05-13"


# ---------------------------------------------------------------------------
# 백필 입력 검증
# ---------------------------------------------------------------------------
def test_backfill_rejects_inverted_range(app_client) -> None:
    token = _make_admin_token(app_client)
    r = app_client.post(
        "/api/v1/admin/ingestion/backfill",
        headers={"Authorization": f"Bearer {token}"},
        json={"start": "2026-05-13", "end": "2026-01-01"},
    )
    assert r.status_code == 400, r.text
    assert r.json()["error"]["code"] == "E0003"


def test_backfill_rejects_excessive_range(app_client) -> None:
    token = _make_admin_token(app_client)
    r = app_client.post(
        "/api/v1/admin/ingestion/backfill",
        headers={"Authorization": f"Bearer {token}"},
        json={"start": "2010-01-01", "end": "2026-05-13"},
    )
    # 10년 초과 → E0063
    assert r.status_code == 422, r.text
    assert r.json()["error"]["code"] == "E0063"


def test_backfill_accepts_valid_payload(app_client) -> None:
    token = _make_admin_token(app_client)
    r = app_client.post(
        "/api/v1/admin/ingestion/backfill",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "start": "2026-04-01",
            "end": "2026-05-01",
            "codes": ["005930", "000660"],
        },
    )
    assert r.status_code == 202, r.text
    data = r.json()["data"]
    assert data["job_id"]
    assert data["codes_count"] == 2


# ---------------------------------------------------------------------------
# 진행률 조회
# ---------------------------------------------------------------------------
def test_job_detail_404_when_missing(app_client) -> None:
    token = _make_admin_token(app_client)
    r = app_client.get(
        "/api/v1/admin/ingestion/jobs/nonexistentjob1234",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "E0062"


def test_job_detail_returns_redis_payload(app_client) -> None:
    """Redis에 진행률 데이터가 있을 때 정상 조회."""
    import asyncio

    from app.core.redis_client import get_redis

    token = _make_admin_token(app_client)
    job_id = "testjob" + uuid.uuid4().hex[:8]
    payload = {
        "job_id": job_id,
        "pct": 42,
        "status": "RUNNING",
        "detail": {"current_code": "005930"},
        "ts": "2026-05-13T16:30:00Z",
    }

    async def _set() -> None:
        redis = get_redis()
        await redis.set("ingest:job:" + job_id, json.dumps(payload), ex=3600)

    asyncio.run(_set())

    r = app_client.get(
        f"/api/v1/admin/ingestion/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()["data"]
    assert body["job_id"] == job_id
    assert body["pct"] == 42
    assert body["status"] == "RUNNING"


# ---------------------------------------------------------------------------
# 작업 취소
# ---------------------------------------------------------------------------
def test_job_cancel_marks_canceled(app_client) -> None:
    import asyncio

    from app.core.redis_client import get_redis

    token = _make_admin_token(app_client)
    job_id = "canceljob" + uuid.uuid4().hex[:8]

    async def _set() -> None:
        redis = get_redis()
        await redis.set(
            "ingest:job:" + job_id,
            json.dumps({"job_id": job_id, "pct": 30, "status": "RUNNING"}),
            ex=3600,
        )

    asyncio.run(_set())

    r = app_client.post(
        f"/api/v1/admin/ingestion/jobs/{job_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["status"] == "CANCELED"


# ---------------------------------------------------------------------------
# 권한 가드
# ---------------------------------------------------------------------------
def test_ingestion_endpoints_require_admin(app_client) -> None:
    """일반 사용자(ROLE_USER)는 401/403."""
    email = _unique_email()
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "x"},
    )
    r = app_client.post(
        "/api/v1/auth/login", json={"email": email, "password": pw}
    )
    token = r.json()["data"]["access_token"]

    # 일반 사용자 → 권한 부족
    r = app_client.post(
        "/api/v1/admin/ingestion/stock-master",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code in (401, 403), r.text


def test_ingestion_endpoints_require_auth(app_client) -> None:
    """인증 없이 호출 시 401."""
    r = app_client.post("/api/v1/admin/ingestion/stock-master")
    assert r.status_code == 401
