"""게이트웨이 테스트 공통 픽스처.

- mock COM 객체 픽스처 (pythoncom/win32com 미설치 환경 대응)
- 어댑터 싱글톤 리셋
- FastAPI TestClient
- Redis 모킹 (가벼운 in-memory 대체)
"""
from __future__ import annotations

import asyncio
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

# 테스트 환경 강제: mock 모드
os.environ.setdefault("CREON_FORCE_MOCK", "true")
os.environ.setdefault("CREON_TRADE_ENV", "SIM")
os.environ.setdefault("CREON_USE_MOCK", "true")
os.environ.setdefault("GATEWAY_API_KEY", "test-api-key-test-api-key-test-key")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("RATE_LIMIT_PER_SEC", "12")
os.environ.setdefault("RATE_LIMIT_PER_4SEC", "48")


@pytest.fixture(autouse=True)
def reset_adapter_singleton():
    """각 테스트마다 어댑터 싱글톤 리셋."""
    from creon_gateway import creon_adapter, healthbeat, config

    config.get_settings.cache_clear()
    creon_adapter.reset_adapter()
    healthbeat.reset_healthbeat_task()
    yield
    creon_adapter.reset_adapter()
    healthbeat.reset_healthbeat_task()


@pytest.fixture
def mock_com():
    """가짜 win32com.client Dispatch 객체.

    pythoncom/win32com 없이도 RealCreonAdapter 코드 경로를 시뮬레이션할 수 있게 한다.
    """
    com = MagicMock()

    # CpCybos
    cybos = MagicMock()
    cybos.IsConnect = 1

    # CpTdUtil
    tdutil = MagicMock()
    tdutil.TradeInit.return_value = 0
    tdutil.AccountNumber = ["5512345678"]  # 모의투자 접두사
    tdutil.GoodsList.return_value = ["01"]

    # CpTd0311 (주문)
    td0311 = MagicMock()
    td0311.BlockRequest.return_value = 0
    td0311.GetHeaderValue.return_value = "99999999"
    td0311.GetDibStatus.return_value = 0
    td0311.GetDibMsg1.return_value = "정상"

    # CpTd0314 (취소)
    td0314 = MagicMock()
    td0314.BlockRequest.return_value = 0

    # StockMst (시세)
    stockmst = MagicMock()
    stockmst.BlockRequest.return_value = 0
    # GetHeaderValue 분기: 11=현재가, 12=변동, 18=거래량
    stockmst.GetHeaderValue.side_effect = lambda i: {
        11: 71200.0,
        12: 300.0,
        18: 12345678,
    }.get(i, 0)

    # CpCodeMgr
    codemgr = MagicMock()
    codemgr.CodeToName.return_value = "삼성전자"
    codemgr.GetStockMarketKind.return_value = 1  # KOSPI
    codemgr.GetStockSectionKind.return_value = 1
    codemgr.GetStockMaxPrice.return_value = 90000.0
    codemgr.GetStockMinPrice.return_value = 50000.0
    codemgr.GetStockStatusKind.return_value = 0

    # CpTd6033 (잔고)
    td6033 = MagicMock()
    td6033.BlockRequest.return_value = 0
    td6033.GetHeaderValue.side_effect = lambda i: {
        7: 0,           # 종목 수
        9: 1_000_000.0, # 추정예수금
        10: 1_000_000.0,
    }.get(i, 0)

    # StockCur (구독)
    stockcur = MagicMock()
    stockcur.Subscribe.return_value = None
    stockcur.Unsubscribe.return_value = None

    def dispatch(prog_id: str) -> Any:
        return {
            "CpUtil.CpCybos": cybos,
            "CpTrade.CpTdUtil": tdutil,
            "CpTrade.CpTd0311": td0311,
            "CpTrade.CpTd0314": td0314,
            "Dscbo1.StockMst": stockmst,
            "CpUtil.CpCodeMgr": codemgr,
            "CpTrade.CpTd6033": td6033,
            "Dscbo1.StockCur": stockcur,
        }[prog_id]

    com.Dispatch.side_effect = dispatch
    return com


@pytest.fixture
def fake_redis():
    """간단한 in-memory Redis 더블 (publish 메시지 수집 + setex/get 지원)."""

    class _FakeRedis:
        def __init__(self) -> None:
            self.published: list[tuple[str, bytes]] = []
            self.store: dict[str, bytes] = {}

        async def publish(self, channel: str, payload: bytes) -> int:
            self.published.append((channel, payload))
            return 1

        async def get(self, key: str) -> bytes | None:
            return self.store.get(key)

        async def setex(self, key: str, ttl: int, val: bytes) -> bool:
            self.store[key] = val
            return True

        async def aclose(self) -> None:
            pass

    return _FakeRedis()


@pytest.fixture
def app_client(fake_redis):
    """게이트웨이 FastAPI TestClient.

    Redis는 fake_redis로 패치.
    """
    from fastapi.testclient import TestClient
    from creon_gateway import event_publisher
    from creon_gateway.main import app

    event_publisher._redis = fake_redis  # type: ignore[assignment]
    # 동기적으로 lifespan 실행되게 TestClient with-구문
    with TestClient(app) as client:
        client.headers.update({"X-Gateway-Api-Key": os.environ["GATEWAY_API_KEY"]})
        yield client


@pytest.fixture
def anyio_backend():
    """anyio 비동기 픽스처."""
    return "asyncio"
