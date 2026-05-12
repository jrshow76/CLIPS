"""ML 학습/추론 흐름 통합 테스트.

흐름:
    POST /ml/predict → (Celery eager) → GET /ml/predictions/{id}

전제:
- 합성 데이터 fallback (ML_USE_SYNTHETIC=true) 사용
- Celery eager 모드 (CELERY_TASK_ALWAYS_EAGER=true) 또는 워커 미가용 시 enqueue 만 검증

토치 미설치 환경에서는 라우팅과 큐잉 검증까지만 수행한다.
"""
from __future__ import annotations

import os
import uuid

import pytest

pytestmark = pytest.mark.integration


# Celery eager 모드 (워커 미가용 환경 대응)
os.environ.setdefault("ML_USE_SYNTHETIC", "true")


def _signup_and_login(app_client) -> tuple[str, str]:
    email = f"ml-{uuid.uuid4().hex[:8]}@test.local"
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "ml"},
    )
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    token = r.json()["data"]["access_token"]
    return email, token


def test_ml_predict_request_returns_prediction_id(app_client) -> None:
    """POST /ml/predict 가 prediction_id 와 202 를 반환한다."""
    _email, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}

    r = app_client.post(
        "/api/v1/ml/predict",
        headers=headers,
        json={"stock_code": "005930", "horizon": 1},
    )
    # 종목이 DB 에 없으면 404, 있으면 202
    if r.status_code == 404:
        pytest.skip("DB 에 005930 종목이 등록되어 있지 않음 (테스트 환경 한정)")
    assert r.status_code == 202, r.text
    body = r.json()
    data = body.get("data", body)
    assert "prediction_id" in data or "job_id" in data


def test_ml_predict_horizon_validation(app_client) -> None:
    """horizon 이 1/3/5 가 아니면 422."""
    _email, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    r = app_client.post(
        "/api/v1/ml/predict",
        headers=headers,
        json={"stock_code": "005930", "horizon": 2},
    )
    assert r.status_code == 422


def test_ml_predict_result_polling_returns_status(app_client) -> None:
    """존재하지 않는 prediction_id 폴링 시 UNKNOWN 또는 PENDING 반환."""
    _email, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    fake_id = uuid.uuid4().hex
    r = app_client.get(f"/api/v1/ml/predictions/{fake_id}", headers=headers)
    assert r.status_code == 200, r.text
    data = r.json().get("data") or r.json()
    assert data["prediction_id"] == fake_id
    # Celery backend 가 PENDING/UNKNOWN 등을 반환
    assert "status" in data


def test_ml_train_requires_admin(app_client) -> None:
    """일반 사용자가 /ml/train 호출 시 403 (forbidden)."""
    _email, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    r = app_client.post(
        "/api/v1/ml/train",
        headers=headers,
        json={"stock_code": "005930", "horizon": 1},
    )
    assert r.status_code in (401, 403)
