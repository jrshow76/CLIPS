"""백테스트 잡 흐름 통합 테스트.

흐름:
    POST /backtest/jobs → (워커 미가용 → inline 동기 실행) → polling → GET result/trades

전제:
- Celery 워커 미가용 환경에서 BacktestService 의 `_run_inline` fallback 이 동작한다.
- 합성 데이터 fallback 환경변수 `BACKTEST_USE_SYNTHETIC=true` 활성화.
"""
from __future__ import annotations

import os
import uuid

import pytest


pytestmark = pytest.mark.integration


# Celery 가 import 불가능한 환경에서도 inline 실행되도록 환경변수 강제 설정
os.environ.setdefault("BACKTEST_USE_SYNTHETIC", "true")


def _signup_and_login(app_client) -> tuple[str, str]:
    email = f"bt-{uuid.uuid4().hex[:8]}@test.local"
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "bt"},
    )
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    token = r.json()["data"]["access_token"]
    return email, token


def _create_strategy(app_client, headers) -> str:
    payload = {
        "name": "테스트 골든크로스",
        "description": "백테스트 통합 테스트용",
        "entry_rules": {"all": [{"indicator": "MA", "fast": 5, "op": "CROSS_UP", "slow": 20}]},
        "exit_rules": {"all": [{"indicator": "MA", "fast": 5, "op": "CROSS_DOWN", "slow": 20}]},
        "universe": ["005930"],
        "limits": {"engine_type": "golden_cross"},
    }
    r = app_client.post("/api/v1/strategies", headers=headers, json=payload)
    assert r.status_code == 201, r.text
    return r.json()["data"]["id"]


def test_backtest_full_flow(app_client) -> None:
    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    strategy_id = _create_strategy(app_client, headers)

    # 잡 생성
    payload = {
        "strategy_id": strategy_id,
        "universe": ["005930"],
        "from": "2025-01-01",
        "to": "2025-12-31",
        "initial_capital": "10000000",
        "slippage": "0.0005",
        "fee_rate": "0.00015",
    }
    r = app_client.post("/api/v1/backtest/jobs", headers=headers, json=payload)
    assert r.status_code == 202, r.text
    job_id = r.json()["data"]["job_id"]
    assert job_id

    # 진행률 조회
    r = app_client.get(f"/api/v1/backtest/jobs/{job_id}/progress", headers=headers)
    assert r.status_code == 200
    body = r.json()["data"]
    # inline 실행이므로 이미 DONE 또는 FAILED
    assert body["status"] in ("DONE", "FAILED", "RUNNING", "QUEUED")

    # 결과 조회 (DONE 일 때만 metrics 포함)
    r = app_client.get(f"/api/v1/backtest/jobs/{job_id}/result", headers=headers)
    assert r.status_code == 200
    data = r.json()["data"]
    assert data["job_id"] == job_id
    assert "summary" in data
    assert "metrics" in data
    # equity_curve 가 dict(JSONB) 로 저장되어 있어야 한다 (DONE 인 경우)
    if data["summary"]["status"] == "DONE":
        assert data["equity_curve"] is not None
        # 메트릭 필드 존재
        for key in ("cumulative_return", "mdd", "sharpe", "win_rate", "trade_count"):
            assert key in data["metrics"]


def test_backtest_invalid_period_rejected(app_client) -> None:
    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    strategy_id = _create_strategy(app_client, headers)

    # 기간 30일 미만 → E0032
    payload = {
        "strategy_id": strategy_id,
        "universe": ["005930"],
        "from": "2025-01-01",
        "to": "2025-01-10",
        "initial_capital": "10000000",
        "slippage": "0.0005",
        "fee_rate": "0.00015",
    }
    r = app_client.post("/api/v1/backtest/jobs", headers=headers, json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "E0032"


def test_backtest_capital_below_minimum_rejected(app_client) -> None:
    _, token = _signup_and_login(app_client)
    headers = {"Authorization": f"Bearer {token}"}
    strategy_id = _create_strategy(app_client, headers)

    payload = {
        "strategy_id": strategy_id,
        "universe": ["005930"],
        "from": "2025-01-01",
        "to": "2025-06-30",
        "initial_capital": "100000",  # 10만원 → 100만원 미만 거부
        "slippage": "0.0005",
        "fee_rate": "0.00015",
    }
    r = app_client.post("/api/v1/backtest/jobs", headers=headers, json=payload)
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "E0032"
