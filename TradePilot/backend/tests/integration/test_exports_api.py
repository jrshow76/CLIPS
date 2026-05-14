"""익스포트 API 통합 테스트.

흐름:
    1. POST /exports → public_id 수신 (202)
    2. GET /exports/{id} 폴링 → 진행률/상태 확인
    3. GET /exports/{id}/download → 사전서명 URL 발급
    4. DELETE /exports/{id} → 취소

전제:
    - boto3 S3 호출은 monkeypatch 로 fake 구현 주입.
    - Celery 워커가 없으므로 워커 수동 실행(`run_export`)으로 DONE 상태 강제.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

import pytest


pytestmark = pytest.mark.integration


def _signup_and_login(app_client) -> tuple[str, str]:
    email = f"exp-{uuid.uuid4().hex[:8]}@test.local"
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "exp"},
    )
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    token = r.json()["data"]["access_token"]
    return email, token


class _FakeS3Client:
    """boto3 S3 클라이언트 대용. 업로드/사전서명/삭제 모두 메모리에 기록."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put_object(self, **kwargs):
        self.objects[kwargs["Key"]] = kwargs["Body"]
        return {"ETag": '"fake-etag"'}

    def upload_fileobj(self, Fileobj, Bucket, Key, **kwargs):  # noqa: N803
        self.objects[Key] = Fileobj.read()

    def generate_presigned_url(self, _op, Params, ExpiresIn):  # noqa: N803
        return f"https://fake.s3/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"

    def delete_object(self, **kwargs):
        self.objects.pop(kwargs["Key"], None)


def test_export_request_status_download_flow(app_client, monkeypatch) -> None:
    """전체 익스포트 라이프사이클: 요청 → 워커 수동 실행 → 다운로드."""
    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. boto3 클라이언트 mock
    fake = _FakeS3Client()
    from app.services.export_engine import s3_uploader as s3_mod

    original_init = s3_mod.S3Uploader._get_client

    def _fake_get_client(self):
        # 동일 인스턴스가 항상 같은 fake 를 반환
        return fake

    monkeypatch.setattr(s3_mod.S3Uploader, "_get_client", _fake_get_client)

    # 2. POST /exports — PNL CSV 요청
    r = app_client.post(
        "/api/v1/exports",
        headers=headers,
        json={
            "job_type": "PNL",
            "format": "CSV",
            "filter_params": {
                "from": "2025-01-01",
                "to": "2025-12-31",
            },
        },
    )
    assert r.status_code == 202, r.text
    body = r.json()["data"]
    export_id = body["export_id"]
    assert export_id
    assert body["status"] == "PENDING"

    # 3. 워커 비가용 환경이므로 runner 를 동기 실행(inline) 으로 강제 처리.
    import asyncio

    from app.core.database import AsyncSessionLocal
    from app.models.trade import ExportJob
    from app.services.export_engine.runner import run_export
    from sqlalchemy import select

    async def _run_inline():
        async with AsyncSessionLocal() as db:
            stmt = select(ExportJob).where(ExportJob.public_id == uuid.UUID(export_id))
            job = (await db.execute(stmt)).scalar_one()
            await run_export(db, job.id)

    asyncio.run(_run_inline())

    # 4. GET /exports/{id} — 상태 DONE 확인
    r = app_client.get(f"/api/v1/exports/{export_id}", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["status"] == "DONE", data
    assert data["progress_percent"] == 100
    assert data["row_count"] is not None  # 0 이상

    # 5. GET /exports/{id}/download — 사전서명 URL 발급
    r = app_client.get(f"/api/v1/exports/{export_id}/download", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["download_url"].startswith("https://fake.s3/")
    assert export_id in data["download_url"] or "/" + export_id in data["download_url"]


def test_export_unauthorized_access_blocked(app_client, monkeypatch) -> None:
    """다른 사용자의 export_id 로 접근 시 E0062."""
    # 사용자 A 가 익스포트 생성
    _, token_a = _signup_and_login(app_client)
    fake = _FakeS3Client()
    from app.services.export_engine import s3_uploader as s3_mod

    monkeypatch.setattr(s3_mod.S3Uploader, "_get_client", lambda self: fake)

    r = app_client.post(
        "/api/v1/exports",
        headers={"Authorization": f"Bearer {token_a}"},
        json={"job_type": "POSITIONS", "format": "CSV", "filter_params": {}},
    )
    export_id = r.json()["data"]["export_id"]

    # 사용자 B 로 접근 시 차단
    _, token_b = _signup_and_login(app_client)
    r = app_client.get(
        f"/api/v1/exports/{export_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "E0062"


def test_export_invalid_job_type_rejected(app_client) -> None:
    _, token = _signup_and_login(app_client)
    r = app_client.post(
        "/api/v1/exports",
        headers={"Authorization": f"Bearer {token}"},
        json={"job_type": "INVALID", "format": "CSV"},
    )
    assert r.status_code == 400  # pydantic Literal 검증 실패
    body = r.json()
    assert body["success"] is False


def test_export_concurrent_limit_enforced(app_client, monkeypatch) -> None:
    """동시 PENDING/RUNNING 한도 초과 시 E0021."""
    monkeypatch.setenv("EXPORT_CONCURRENT_PER_USER", "1")
    # config 캐시 해제(매 호출시 ExportConfig 재로드 되므로 안전)

    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    # 1건 생성 (PENDING 으로 남아 있음)
    r1 = app_client.post(
        "/api/v1/exports",
        headers=headers,
        json={"job_type": "POSITIONS", "format": "CSV"},
    )
    assert r1.status_code == 202

    # 2건째: 한도 초과
    r2 = app_client.post(
        "/api/v1/exports",
        headers=headers,
        json={"job_type": "POSITIONS", "format": "CSV"},
    )
    assert r2.status_code == 422, r2.text
    assert r2.json()["error"]["code"] == "E0021"


def test_export_cancel(app_client, monkeypatch) -> None:
    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    r = app_client.post(
        "/api/v1/exports",
        headers=headers,
        json={"job_type": "POSITIONS", "format": "CSV"},
    )
    export_id = r.json()["data"]["export_id"]

    r = app_client.delete(f"/api/v1/exports/{export_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["data"]["status"] == "CANCELED"
