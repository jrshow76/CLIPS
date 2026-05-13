"""CREON 게이트웨이 FastAPI 메인.

엔드포인트 (`docs/23_creon_gateway.md` §5.1):
- GET  /healthz                       - liveness
- GET  /readyz                        - COM 세션 readiness
- GET  /system/status                 - 상세 상태 (SIM/REAL, 카운터)
- POST /system/reconnect              - COM 강제 재연결
- GET  /metrics                       - Prometheus 호환 메트릭
- POST /orders                        - 주문 발주 (idempotency-key 지원)
- POST /orders/{id}/cancel            - 주문 취소
- GET  /account                       - SIM/REAL 계좌 목록
- GET  /account/balance               - 예수금/평가
- GET  /account/positions             - 보유 종목
- GET  /market/quote/{code}           - 현재가
- GET  /market/orderbook/{code}       - 호가
- GET  /stocks/master/{code}          - 종목 마스터
- POST /subscribe/quote               - 실시간 시세 구독 요청
- POST /unsubscribe/quote             - 구독 해제

응답 envelope: {success, data, raw} 또는 {success: false, error}
인증: 모든 비공개 엔드포인트는 `X-Gateway-Api-Key` 헤더 필수.
"""
from __future__ import annotations

import contextlib
import logging
from collections.abc import AsyncIterator
from datetime import datetime, timezone
from typing import Annotated, Any

import orjson
import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Path
from fastapi.responses import JSONResponse, PlainTextResponse
from pydantic import BaseModel, Field

from creon_gateway.config import get_settings, settings as _initial_settings


def _settings():
    """호출 시점의 settings (테스트 reload 대응)."""
    return get_settings()


settings = _initial_settings  # 모듈 import 시점 캐시 (logging 등 1회성 용도)
from creon_gateway.creon_adapter import (
    CancelRequest,
    OrderSubmitRequest,
    get_adapter,
    map_creon_code,
)
from creon_gateway.event_publisher import (
    close_redis,
    get_redis,
    publish_execution,
)
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
    log.info(
        "gateway_startup",
        id=_settings().GATEWAY_ID,
        port=_settings().GATEWAY_PORT,
        trade_env=_settings().CREON_TRADE_ENV,
    )
    get_adapter()  # 어댑터 초기화
    healthbeat = get_healthbeat_task()
    await healthbeat.start()

    # Mock tick worker (mock 어댑터 + MOCK_TICK_ENABLED 시)
    mock_tick = None
    if _settings().MOCK_TICK_ENABLED:
        try:
            from creon_gateway.mock_tick_worker import get_mock_tick_worker
            mock_tick = get_mock_tick_worker()
            await mock_tick.start()
        except Exception as e:
            log.warning("mock_tick_start_failed", error=str(e))

    yield

    if mock_tick:
        try:
            await mock_tick.stop()
        except Exception:
            pass
    await healthbeat.stop()
    await close_redis()
    log.info("gateway_shutdown")


# ---------------------------------------------------------------------------
# API Key 가드
# ---------------------------------------------------------------------------
async def require_api_key(
    x_gateway_api_key: Annotated[str | None, Header(alias="X-Gateway-Api-Key")] = None,
) -> None:
    if not x_gateway_api_key or x_gateway_api_key != _settings().GATEWAY_API_KEY:
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
    side: str = Field(pattern=r"^(BUY|SELL)$")
    qty: int = Field(ge=1)
    order_type: str = Field(pattern=r"^(MARKET|LIMIT)$")
    price: float | None = None
    user_id: str | None = None
    idempotency_key: str | None = None


class CancelRequestBody(BaseModel):
    broker_order_no: str
    code: str
    qty: int = 0


class SubscribeBody(BaseModel):
    codes: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# 앱 정의
# ---------------------------------------------------------------------------
app = FastAPI(
    title="TradePilot CREON Gateway",
    version="1.0.0",
    description="CREON Plus 어댑터 게이트웨이 (모의/실거래)",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# 시스템 / 헬스
# ---------------------------------------------------------------------------
@app.get("/healthz", tags=["system"])
async def healthz() -> dict[str, Any]:
    """liveness: 프로세스가 살아있는지만 확인 (인증 불필요)."""
    return {
        "ok": True,
        "trade_env": _settings().CREON_TRADE_ENV,
        "gateway_id": _settings().GATEWAY_ID,
    }


@app.get("/readyz", tags=["system"])
async def readyz() -> dict[str, Any]:
    """readiness: COM 연결 + 계좌 로드 여부 (인증 불필요)."""
    adapter = get_adapter()
    adapter.ensure_connected()
    return {
        "ok": adapter.connected and adapter.account_loaded,
        "com_connected": adapter.connected,
        "account_loaded": adapter.account_loaded,
        "trade_env": _settings().CREON_TRADE_ENV,
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


@app.get("/metrics", tags=["system"], response_class=PlainTextResponse)
async def metrics() -> str:
    """Prometheus 호환 메트릭 (텍스트 포맷).

    노출 지표:
    - tradepilot_gateway_connected (gauge)
    - tradepilot_gateway_account_loaded (gauge)
    - tradepilot_gateway_request_count_1s (gauge)
    - tradepilot_gateway_request_count_4s (gauge)
    - tradepilot_gateway_trade_env (gauge, 1=SIM, 2=REAL)
    """
    adapter = get_adapter()
    status = adapter.system_status()
    env_val = 1 if _settings().CREON_TRADE_ENV == "SIM" else 2
    lines = [
        "# HELP tradepilot_gateway_connected CREON COM 연결 상태",
        "# TYPE tradepilot_gateway_connected gauge",
        f"tradepilot_gateway_connected {1 if status['connected'] else 0}",
        "# HELP tradepilot_gateway_account_loaded 거래 계좌 초기화 상태",
        "# TYPE tradepilot_gateway_account_loaded gauge",
        f"tradepilot_gateway_account_loaded {1 if status['account_loaded'] else 0}",
        "# HELP tradepilot_gateway_request_count_1s 직전 1초 요청 수",
        "# TYPE tradepilot_gateway_request_count_1s gauge",
        f"tradepilot_gateway_request_count_1s {status['request_count_1s']}",
        "# HELP tradepilot_gateway_request_count_4s 직전 4초 요청 수",
        "# TYPE tradepilot_gateway_request_count_4s gauge",
        f"tradepilot_gateway_request_count_4s {status['request_count_4s']}",
        "# HELP tradepilot_gateway_trade_env 거래 모드 (1=SIM, 2=REAL)",
        "# TYPE tradepilot_gateway_trade_env gauge",
        f"tradepilot_gateway_trade_env {env_val}",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 주문 (idempotency-key 처리)
# ---------------------------------------------------------------------------
async def _idempotency_get(key: str) -> dict[str, Any] | None:
    """Redis에서 멱등성 응답 조회."""
    try:
        raw = await get_redis().get(f"tp:gw:idem:{key}")
        if not raw:
            return None
        return orjson.loads(raw)
    except Exception:
        log.exception("idempotency_get_failed")
        return None


async def _idempotency_set(key: str, payload: dict[str, Any]) -> None:
    try:
        await get_redis().setex(
            f"tp:gw:idem:{key}",
            _settings().IDEMPOTENCY_TTL_SEC,
            orjson.dumps(payload),
        )
    except Exception:
        log.exception("idempotency_set_failed")


@app.post("/orders", tags=["orders"], response_model=None)
async def submit_order(
    body: OrderRequestBody, _=Depends(require_api_key)
) -> dict[str, Any] | JSONResponse:
    # 멱등성 키 확인
    if body.idempotency_key:
        cached = await _idempotency_get(body.idempotency_key)
        if cached is not None:
            log.info(
                "idempotency_hit",
                key=body.idempotency_key,
                order_id=body.order_id,
            )
            return cached

    adapter = get_adapter()
    req = OrderSubmitRequest(
        code=body.code,
        side=body.side,
        qty=body.qty,
        order_type=body.order_type,
        price=body.price,
        account_no=_settings().CREON_ACCOUNT_NO,
        account_kind=_settings().CREON_ACCOUNT_KIND,
    )

    # LIMIT 주문은 price 필수
    if body.order_type == "LIMIT" and (body.price is None or body.price <= 0):
        return err("G0012", "지정가 주문은 price 필수", -310, "호가단위 오류")

    resp = adapter.submit_order(req)
    if not resp.accepted:
        g_code = map_creon_code(resp.raw_code)
        response = {
            "success": False,
            "error": {
                "code": g_code,
                "message": "주문 실패",
                "raw_code": resp.raw_code,
                "raw_msg": resp.raw_msg,
            },
        }
        if body.idempotency_key:
            await _idempotency_set(body.idempotency_key, response)
        return JSONResponse(status_code=200, content=response)

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
            "trade_env": _settings().CREON_TRADE_ENV,
            "ts": datetime.now(tz=timezone.utc).isoformat(),
            "user_id": body.user_id,
        }
    )

    success_response = ok(
        {
            "accepted": True,
            "broker_order_no": resp.broker_order_no,
            "raw_code": resp.raw_code,
            "raw_msg": resp.raw_msg,
            "trade_env": _settings().CREON_TRADE_ENV,
        }
    )
    if body.idempotency_key:
        await _idempotency_set(body.idempotency_key, success_response)
    return success_response


@app.post("/orders/{order_id}/cancel", tags=["orders"], response_model=None)
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
        return err(
            map_creon_code(resp.raw_code),
            "주문 취소 실패",
            resp.raw_code,
            resp.raw_msg,
        )
    return ok({"canceled": True, "broker_order_no": body.broker_order_no})


# ---------------------------------------------------------------------------
# 계좌
# ---------------------------------------------------------------------------
@app.get("/account", tags=["account"])
async def account_list(_=Depends(require_api_key)) -> dict[str, Any]:
    """현재 모드(SIM/REAL)에 매칭되는 계좌 목록 반환."""
    accounts = get_adapter().get_accounts()
    return ok(
        {
            "trade_env": _settings().CREON_TRADE_ENV,
            "expected_prefix": _settings().expected_account_prefix(),
            "accounts": accounts,
        }
    )


@app.get("/account/balance", tags=["account"])
async def account_balance(_=Depends(require_api_key)) -> dict[str, Any]:
    b = get_adapter().get_balance()
    return ok(
        {
            "cash": b.cash,
            "equity": b.equity,
            "eval_amount": b.eval_amount,
            "trade_env": _settings().CREON_TRADE_ENV,
        }
    )


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
            "code": q.code,
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
    q = get_adapter().get_quote(code)
    bids = [
        {"price": q.price - (i + 1) * 100, "qty": 100 * (i + 1)} for i in range(10)
    ]
    asks = [
        {"price": q.price + (i + 1) * 100, "qty": 100 * (i + 1)} for i in range(10)
    ]
    return ok({"code": code, "bids": bids, "asks": asks})


@app.get("/stocks/master/{code}", tags=["market"])
async def stock_master(
    code: Annotated[str, Path(min_length=6, max_length=6)],
    _=Depends(require_api_key),
) -> dict[str, Any]:
    m = get_adapter().get_stock_master(code)
    return ok(
        {
            "code": m.code,
            "name": m.name,
            "market": m.market,
            "sector": m.sector,
            "is_etf": m.is_etf,
            "is_suspended": m.is_suspended,
            "upper_limit": m.upper_limit,
            "lower_limit": m.lower_limit,
        }
    )


@app.post("/subscribe/quote", tags=["market"])
async def subscribe_quote(
    body: SubscribeBody, _=Depends(require_api_key)
) -> dict[str, Any]:
    cnt = get_adapter().subscribe_realtime(body.codes)
    return ok({"subscribed": cnt})


@app.post("/unsubscribe/quote", tags=["market"])
async def unsubscribe_quote(
    body: SubscribeBody, _=Depends(require_api_key)
) -> dict[str, Any]:
    cnt = get_adapter().unsubscribe_realtime(body.codes)
    return ok({"unsubscribed": cnt})
