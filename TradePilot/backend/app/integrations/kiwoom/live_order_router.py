"""키움 LiveOrderRouter: OrderRouterPort 구현 (키움 게이트웨이 경유)."""
from __future__ import annotations

from typing import Any

import structlog

from app.domains.ports.order_router_port import (
    OrderRequest,
    OrderResult,
    OrderRouterPort,
)
from app.integrations.kiwoom.client import KiwoomGatewayClient, get_kiwoom_client

log = structlog.get_logger(__name__)


class KiwoomLiveOrderRouter(OrderRouterPort):
    """키움 게이트웨이를 통한 실거래 라우터."""

    def __init__(self, client: KiwoomGatewayClient | None = None) -> None:
        self._client = client or get_kiwoom_client()

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        payload: dict[str, Any] = {
            "order_id": str(request.order_id),
            "code": request.stock_code,
            "side": request.side,
            "qty": int(request.qty),
            "order_type": request.order_type,
            "price": float(request.price) if request.price is not None else None,
            "user_id": str(request.user_id),
        }
        if request.idempotency_key:
            payload["idempotency_key"] = request.idempotency_key

        log.info(
            "kiwoom_live_order_submit",
            order_id=request.order_id,
            code=request.stock_code,
            side=request.side,
            qty=str(request.qty),
        )
        resp = await self._client.submit_order(payload)
        data = resp.get("data", {}) or {}
        return OrderResult(
            accepted=bool(data.get("accepted", True)),
            status="ACCEPTED",
            broker_order_no=data.get("broker_order_no"),
            raw=data,
        )

    async def cancel_order(
        self,
        order_id: int,
        broker_order_no: str | None,
        stock_code: str,
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> OrderResult:
        if not broker_order_no:
            return OrderResult(
                accepted=False, status="REJECTED", reject_reason="broker_order_no 없음"
            )

        log.info(
            "kiwoom_live_order_cancel",
            order_id=order_id,
            broker_order_no=broker_order_no,
            timeout_sec=timeout_sec,
        )
        resp = await self._client.cancel_order(
            str(order_id),
            payload={"broker_order_no": broker_order_no, "code": stock_code},
            timeout_sec=timeout_sec,
            idempotency_key=idempotency_key,
        )
        data = resp.get("data", {}) or {}
        return OrderResult(
            accepted=bool(data.get("canceled", False)),
            status="CANCELED" if data.get("canceled") else "REJECTED",
            broker_order_no=broker_order_no,
            raw=data,
        )

    async def get_order_status(
        self, order_id: int, broker_order_no: str | None
    ) -> OrderResult:
        # 키움 게이트웨이 v1 은 별도 상태 조회 API 미제공 → DB 상태 기반
        return OrderResult(
            accepted=True, status="PENDING", broker_order_no=broker_order_no
        )
