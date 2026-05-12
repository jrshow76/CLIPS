"""CREON 게이트웨이 FastAPI 메인.

엔드포인트 (docs/23_creon_gateway.md §5.1):
- GET  /healthz
- GET  /readyz
- GET  /system/status
- POST /system/reconnect
- POST /orders
- POST /orders/{id}/cancel
- GET  /account/balance
- GET  /account/positions
- GET  /market/quote/{code}
"""
from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from typing import Annotated, Any

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Path
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from creon_gateway.config import settings
from creon_gateway.creon_adapter import (
    CancelRequest,
    OrderSubmitRequest,
    get_adapter,
)
from creon_gateway.event_publisher import close_redis, publish_execution
from creon_gateway.healthbeat import get_healthbeat_task

# ---------------------------------------------------------------------------
# 로깅
# ---------------------------------------------------------------------------
logging.basicConfig(level=settings.LOG_LEVEL.upper(), format="%(message)s")
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)
log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------
@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    log.info("gateway_startup", id=settings.GATEWAY_ID, port=settings.GATEWAY_PORT)
    # 어댑터 초기화
    get_adapter()
    # 헬스비트 시작
    healthbeat = get_healthbeat_task()
    await healthbeat.start()
    yield
    await healthbeat.stop()
    await close_redis()
    log.info("gateway_shutdown")


# ---------------------------------------------------------------------------
# API Key 가드
# ---------------------------------------------------------------------------
async def require_api_key(
    x_gateway_api_key: Annotated[str | None, Header(alias="X-Gateway-Api-Key")] = None,
) -> None:
    if not x_gateway_api_key or x_gateway_api_key != settings.GATEWAY_API_KEY:
        raise HTTPException(status_code=401, detail="invalid api key")


# ---------------------------------------------------------------------------
# 응답 헬퍼
# ---------------------------------------------------------------------------
def ok(data: Any, raw: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"success": True, "data": data, "raw": raw or {"code": 0, "message": "정상"}}


def err(
    code: str, message: str, raw_code: int = 0, raw_msg: str = ""
) -> JSONResponse:
    return JSONResponse(
        status_code=200,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "raw_code": raw_code,
                "raw_msg": raw_msg,
            },
        },
    )


# ---------------------------------------------------------------------------
# 입출력 스키마
# ---------------------------------------------------------------------------
class OrderRequestBody(BaseModel):
    order_id: str | None = None
    code: str = Field(min_length=6, max_length=6)
    side: str  # BUY | SELL
    qty: int = Field(ge=1)
    order_type: str  # MARKET | LIMIT
    price: float | None = None
    user_id: str | None = None
    idempotency_key: str | None = None


class CancelRequestBody(BaseModel):
    broker_order_no: str
    code: str
    qty: int = 0


# ---------------------------------------------------------------------------
# 앱 정의
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TradePilot CREON Gateway",
    version="1.0.0",
    description="CREON Plus 어댑터 게이트웨이",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# 시스템
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["system"])
async def healthz() -> dict[str, Any]:
    return {"ok": True}


@app.get("/readyz", tags=["system"])
async def readyz() -> dict[str, Any]:
    adapter = get_adapter()
    adapter.ensure_connected()
    return {
        "ok": adapter.connected and adapter.account_loaded,
        "com_connected": adapter.connected,
        "account_loaded": adapter.account_loaded,
    }


@app.get("/system/status", tags=["system"])
async def system_status(_=Depends(require_api_key)) -> dict[str, Any]:
    adapter = get_adapter()
    return ok(adapter.system_status())


@app.post("/system/reconnect", tags=["system"])
async def system_reconnect(_=Depends(require_api_key)) -> dict[str, Any]:
    adapter = get_adapter()
    reconnected = adapter.reconnect()
    return ok({"reconnected": reconnected})


# ---------------------------------------------------------------------------
# 주문
# ---------------------------------------------------------------------------
@app.post("/orders", tags=["orders"])
async def submit_order(
    body: OrderRequestBody, _=Depends(require_api_key)
) -> dict[str, Any] | JSONResponse:
    adapter = get_adapter()
    req = OrderSubmitRequest(
        code=body.code,
        side=body.side,
        qty=body.qty,
        order_type=body.order_type,
        price=body.price,
        account_no=settings.CREON_ACCOUNT_NO,
        account_kind=settings.CREON_ACCOUNT_KIND,
    )
    resp = adapter.submit_order(req)
    if not resp.accepted:
        # 잔고부족 등 게이트웨이 에러 → G0010/G0011 등으로 변환
        g_code = "G0011" if "잔고" in resp.raw_msg else "G0010"
        return err(g_code, "주문 실패", resp.raw_code, resp.raw_msg)

    # 본체로 체결 이벤트 발행 (mock 어댑터는 즉시 체결)
    quote = adapter.get_quote(body.code)
    await publish_execution(
        {
            "order_id": body.order_id,
            "broker_order_no": resp.broker_order_no,
            "code": body.code,
            "side": body.side,
            "qty": body.qty,
            "price": body.price or quote.price,
            "fee": 0,
            "tax": 0,
            "ts": __import__("datetime").datetime.utcnow().isoformat() + "+00:00",
            "user_id": body.user_id,
        }
    )
    return ok(
        {
            "accepted": True,
            "broker_order_no": resp.broker_order_no,
            "raw_code": resp.raw_code,
            "raw_msg": resp.raw_msg,
        }
    )


@app.post("/orders/{order_id}/cancel", tags=["orders"])
async def cancel_order(
    order_id: Annotated[str, Path()],
    body: CancelRequestBody,
    _=Depends(require_api_key),
) -> dict[str, Any] | JSONResponse:
    adapter = get_adapter()
    resp = adapter.cancel_order(
        CancelRequest(broker_order_no=body.broker_order_no, code=body.code, qty=body.qty)
    )
    if not resp.accepted:
        return err("G0014", "주문 취소 실패", resp.raw_code, resp.raw_msg)
    return ok({"canceled": True, "broker_order_no": body.broker_order_no})


# ---------------------------------------------------------------------------
# 계좌
# ---------------------------------------------------------------------------
@app.get("/account/balance", tags=["account"])
async def account_balance(_=Depends(require_api_key)) -> dict[str, Any]:
    b = get_adapter().get_balance()
    return ok({"cash": b.cash, "equity": b.equity, "eval_amount": b.eval_amount})


@app.get("/account/positions", tags=["account"])
async def account_positions(_=Depends(require_api_key)) -> dict[str, Any]:
    items = [
        {
            "code": p.code,
            "qty": p.qty,
            "avg_price": p.avg_price,
            "eval_pnl": p.eval_pnl,
        }
        for p in get_adapter().get_positions()
    ]
    return ok(items)


# ---------------------------------------------------------------------------
# 시세
# ---------------------------------------------------------------------------
@app.get("/market/quote/{code}", tags=["market"])
async def market_quote(
    code: Annotated[str, Path(min_length=6, max_length=6)],
    _=Depends(require_api_key),
) -> dict[str, Any]:
    q = get_adapter().get_quote(code)
    return ok(
        {
            "price": q.price,
            "change": q.change,
            "change_pct": q.change_pct,
            "volume": q.volume,
            "ts": q.ts,
        }
    )


@app.get("/market/orderbook/{code}", tags=["market"])
async def market_orderbook(
    code: Annotated[str, Path(min_length=6, max_length=6)],
    _=Depends(require_api_key),
) -> dict[str, Any]:
    # mock: 현재가 ±호가 단위로 단순 생성
    q = get_adapter().get_quote(code)
    bids = [{"price": q.price - (i + 1) * 100, "qty": 100 * (i + 1)} for i in range(10)]
    asks = [{"price": q.price + (i + 1) * 100, "qty": 100 * (i + 1)} for i in range(10)]
    return ok({"bids": bids, "asks": asks})


@app.post("/subscribe/quote", tags=["market"])
async def subscribe_quote(
    body: dict[str, Any], _=Depends(require_api_key)
) -> dict[str, Any]:
    codes = body.get("codes", [])
    # mock 모드: 실제 구독 없이 수락만 응답. 운영 시에는 CpPbStockCur로 구독 등록.
    return ok({"subscribed": len(codes)})


@app.post("/unsubscribe/quote", tags=["market"])
async def unsubscribe_quote(
    body: dict[str, Any], _=Depends(require_api_key)
) -> dict[str, Any]:
    codes = body.get("codes", [])
    return ok({"unsubscribed": len(codes)})
