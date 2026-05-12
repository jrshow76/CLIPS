"""헬스비트 태스크 단위 테스트.

- 30초 주기 발행 (테스트는 짧은 인터벌로 단축)
- 단절 시 재연결 카운터 증가, 3회 초과 시 CRITICAL alert
- trade_env, account 마스킹 포함된 페이로드
"""
from __future__ import annotations

import asyncio
import json

import pytest


@pytest.mark.anyio
async def test_healthbeat_publishes_payload(monkeypatch, fake_redis):
    """헬스비트 1회 실행 → fake_redis에 메시지 발행."""
    monkeypatch.setenv("HEALTHBEAT_INTERVAL_SEC", "1")
    monkeypatch.setenv("CREON_TRADE_ENV", "SIM")
    monkeypatch.setenv("CREON_ACCOUNT_NO", "5512345678")
    from creon_gateway.config import reload_settings
    reload_settings()

    # event_publisher의 _redis를 fake_redis로 패치
    from creon_gateway import event_publisher
    event_publisher._redis = fake_redis

    from creon_gateway.healthbeat import HealthbeatTask

    task = HealthbeatTask()
    task._interval_sec = 0.1  # 빠른 반복
    await task.start()
    await asyncio.sleep(0.3)
    await task.stop()

    # 최소 1건 이상 발행
    channels = [c for c, _ in fake_redis.published]
    assert any(c == "tp:gateway.healthbeat" for c in channels)

    # 페이로드 검증
    last = next(
        (json.loads(p) for c, p in fake_redis.published if c == "tp:gateway.healthbeat")
    )
    assert last["trade_env"] == "SIM"
    assert last["com_connected"] is True
    assert last["account_loaded"] is True
    # 계좌 번호 마스킹: 5512345678 → 55******78
    assert last["account_no_masked"].startswith("55")
    assert "*" in last["account_no_masked"]
    assert last["account_no_masked"].endswith("78")


@pytest.mark.anyio
async def test_healthbeat_reconnect_failure_alert(monkeypatch, fake_redis):
    """COM 단절 + 재연결 3회 실패 시 CRITICAL alert 발행."""
    monkeypatch.setenv("CREON_AUTO_RECONNECT_MAX", "3")
    from creon_gateway.config import reload_settings
    reload_settings()

    from creon_gateway import event_publisher
    event_publisher._redis = fake_redis

    from creon_gateway.creon_adapter import MockCreonAdapter
    from creon_gateway import creon_adapter

    # 어댑터를 단절 상태로 강제
    adapter = MockCreonAdapter()
    adapter.connected = False

    # ensure_connected 가 항상 단절 유지하도록 패치
    def _disconnected():
        adapter.connected = False
    adapter.ensure_connected = _disconnected  # type: ignore[method-assign]

    creon_adapter._adapter = adapter

    from creon_gateway.healthbeat import HealthbeatTask
    task = HealthbeatTask()
    task._interval_sec = 0.05
    await task.start()
    await asyncio.sleep(0.4)  # 0.05 * 8 = 0.4 → 3회 이상 실행
    await task.stop()

    # alert 채널에 CRITICAL 발행 확인
    alerts = [
        json.loads(p)
        for c, p in fake_redis.published
        if c == "tp:gateway.alert"
    ]
    assert any(a.get("level") == "CRITICAL" for a in alerts)
    assert any(a.get("code") == "G0002" for a in alerts)


@pytest.mark.anyio
async def test_healthbeat_request_counters_included(monkeypatch, fake_redis):
    """헬스비트에 request_count_1s / request_count_4s 가 포함."""
    monkeypatch.setenv("HEALTHBEAT_INTERVAL_SEC", "1")
    from creon_gateway.config import reload_settings
    reload_settings()

    from creon_gateway import event_publisher
    event_publisher._redis = fake_redis

    # 어댑터에 요청 몇 건 발생시켜 카운터 누적
    from creon_gateway.creon_adapter import (
        MockCreonAdapter,
        OrderSubmitRequest,
    )
    from creon_gateway import creon_adapter

    adapter = MockCreonAdapter()
    for _ in range(3):
        adapter.submit_order(
            OrderSubmitRequest(
                code="005930",
                side="BUY",
                qty=1,
                order_type="LIMIT",
                price=70000,
            )
        )
    creon_adapter._adapter = adapter

    from creon_gateway.healthbeat import HealthbeatTask
    task = HealthbeatTask()
    task._interval_sec = 0.05
    await task.start()
    await asyncio.sleep(0.15)
    await task.stop()

    healthbeats = [
        json.loads(p)
        for c, p in fake_redis.published
        if c == "tp:gateway.healthbeat"
    ]
    assert healthbeats
    # 최소 1건은 request_count_4s >= 3
    assert any(hb.get("request_count_4s", 0) >= 3 for hb in healthbeats)
