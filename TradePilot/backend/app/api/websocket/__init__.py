"""실시간 WebSocket 라우터 패키지.

엔드포인트 (모두 ``/ws`` prefix):
- ``GET /ws/market``        - 실시간 시세
- ``GET /ws/orderbook``     - 실시간 호가창 (Level 2, 10단계)
- ``GET /ws/account``       - 체결/잔고
- ``GET /ws/notifications`` - 알림

설계 문서:
- ``docs/33_realtime_websocket_guide.md`` (전체)
- ``docs/47_orderbook_guide.md`` (호가창 전용)
"""
from __future__ import annotations

from fastapi import APIRouter, FastAPI

from app.api.websocket.account_ws import router as account_router
from app.api.websocket.market_ws import router as market_router
from app.api.websocket.notifications_ws import router as notifications_router
from app.api.websocket.orderbook_ws import router as orderbook_router


def register_websocket_routes(app: FastAPI) -> None:
    """앱에 ``/ws/*`` 라우터 등록."""
    parent = APIRouter(prefix="/ws")
    parent.include_router(market_router)
    parent.include_router(orderbook_router)
    parent.include_router(account_router)
    parent.include_router(notifications_router)
    app.include_router(parent)


__all__ = ["register_websocket_routes"]
