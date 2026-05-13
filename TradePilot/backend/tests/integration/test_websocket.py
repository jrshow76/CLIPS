"""WebSocket 통합 테스트.

FastAPI TestClient + websocket_connect 컨텍스트로 ``/ws/market`` 라우터 동작을 검증한다.

시나리오:
- 인증 (query token) → subscribe → 시세 수신
- 미인증 차단 (close 1008)
- 잘못된 종목 코드 검증 실패 시 error 메시지
- ping/pong heartbeat
"""
from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

import orjson
import pytest
from fastapi.testclient import TestClient

from app.api.websocket.connection_manager import (
    get_market_manager,
    reset_managers,
)
from app.api.websocket.protocol import TickMessage
from app.core.security import create_jwt_token


@pytest.fixture
def app_client_no_lifespan(monkeypatch):
    """lifespan 비활성화 (Redis/DB 의존 회피) - 라우터만 테스트."""
    from app.main import create_app

    app = create_app()
    # lifespan을 비활성화한 상태로 TestClient 사용
    # FastAPI TestClient는 lifespan을 자동 실행하므로,
    # 여기서는 명시적으로 dispatcher/listener가 실패해도 통과하는 환경을 가정.
    with TestClient(app, raise_server_exceptions=True) as client:
        yield client
    reset_managers()


def _make_token(sub: str = "user-public-id") -> str:
    token, _ = create_jwt_token(subject=sub, token_type="access")
    return token


def test_ws_market_unauthenticated_close(app_client_no_lifespan: TestClient):
    """token 없이 + auth 메시지도 없이 끊으면 close 1008."""
    client = app_client_no_lifespan
    with pytest.raises(Exception):
        with client.websocket_connect("/ws/market") as ws:
            # auth 대신 잘못된 메시지 전송
            ws.send_text(orjson.dumps({"type": "subscribe"}).decode())
            # 서버가 auth 누락 → close 하므로 receive 시 예외
            ws.receive_text()


def test_ws_market_query_token_auth_and_subscribe(
    app_client_no_lifespan: TestClient,
):
    """query string 토큰으로 인증 → subscribe → ack 수신."""
    client = app_client_no_lifespan
    token = _make_token("user-1")
    with client.websocket_connect(f"/ws/market?token={token}") as ws:
        ws.send_text(
            orjson.dumps(
                {"type": "subscribe", "stock_codes": ["005930", "000660"]}
            ).decode()
        )
        ack_raw = ws.receive_bytes()
        ack = orjson.loads(ack_raw)
        assert ack["type"] == "subscribed"
        assert sorted(ack["stock_codes"]) == ["000660", "005930"]
        assert ack["total"] == 2


def test_ws_market_invalid_stock_code(app_client_no_lifespan: TestClient):
    """6자리 숫자가 아닌 종목 코드는 검증 실패 → error 메시지."""
    client = app_client_no_lifespan
    token = _make_token("user-2")
    with client.websocket_connect(f"/ws/market?token={token}") as ws:
        ws.send_text(
            orjson.dumps(
                {"type": "subscribe", "stock_codes": ["BAD", "0059AB"]}
            ).decode()
        )
        msg_raw = ws.receive_bytes()
        msg = orjson.loads(msg_raw)
        assert msg["type"] == "error"
        assert msg["code"] == "E0003"


def test_ws_market_ping_pong(app_client_no_lifespan: TestClient):
    client = app_client_no_lifespan
    token = _make_token("user-3")
    with client.websocket_connect(f"/ws/market?token={token}") as ws:
        ws.send_text(orjson.dumps({"type": "ping"}).decode())
        msg = orjson.loads(ws.receive_bytes())
        assert msg["type"] == "pong"


def test_ws_market_first_message_auth(app_client_no_lifespan: TestClient):
    """query string 토큰 없이 첫 메시지로 auth → 이후 subscribe."""
    client = app_client_no_lifespan
    token = _make_token("user-4")
    with client.websocket_connect("/ws/market") as ws:
        ws.send_text(orjson.dumps({"type": "auth", "token": token}).decode())
        ws.send_text(
            orjson.dumps(
                {"type": "subscribe", "stock_codes": ["035420"]}
            ).decode()
        )
        msg = orjson.loads(ws.receive_bytes())
        assert msg["type"] == "subscribed"
        assert msg["stock_codes"] == ["035420"]


def test_ws_market_receives_broadcast_tick(app_client_no_lifespan: TestClient):
    """매니저로 직접 broadcast → 구독자가 수신하는지 확인."""
    client = app_client_no_lifespan
    token = _make_token("user-5")
    manager = get_market_manager()
    manager.throttle_ms = 0  # 테스트 편의

    with client.websocket_connect(f"/ws/market?token={token}") as ws:
        ws.send_text(
            orjson.dumps(
                {"type": "subscribe", "stock_codes": ["005930"]}
            ).decode()
        )
        # subscribed ack 소비
        orjson.loads(ws.receive_bytes())

        # 서버측 manager로 직접 broadcast (Redis 우회)
        async def emit():
            await manager.broadcast_to_stock_subscribers(
                "005930",
                TickMessage(
                    stock_code="005930", price=71500, volume=120
                ).model_dump(),
            )

        asyncio.run(emit())

        msg = orjson.loads(ws.receive_bytes())
        assert msg["type"] == "tick"
        assert msg["stock_code"] == "005930"
        assert msg["price"] == 71500
