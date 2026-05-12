"""LiveOrderRouter: OrderRouterPort 실거래 구현.

게이트웨이 HTTP API를 호출하여 주문을 발주한다.
체결은 비동기 (Pub/Sub `tp:account.execution`)로 수신되며, 본 라우터는 ACCEPTED만 반환.
"""
from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog

from app.domains.ports.order_router_port import (
    OrderRequest,
    OrderResult,
    OrderRouterPort,
)
from app.integrations.creon.client import CreonGatewayClient, get_creon_client

log = structlog.get_logger(__name__)


class LiveOrderRouter(OrderRouterPort):
    """크레온 게이트웨이를 통한 실거래 라우터."""

    def __init__(self, client: CreonGatewayClient | None = None) -> None:
        self._client = client or get_creon_client()

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
            "live_order_submit",
            order_id=request.order_id,
            code=request.stock_code,
            side=request.side,
            qty=str(request.qty),
        )

        resp = await self._client.submit_order(payload)
        data = resp.get("data", {}) or {}

        # 게이트웨이 수락 → 체결은 비동기 이벤트로 수신
        return OrderResult(
            accepted=bool(data.get("accepted", True)),
            status="ACCEPTED",
            broker_order_no=data.get("broker_order_no"),
            raw=data,
        )

    async def cancel_order(
        self, order_id: int, broker_order_no: str | None, stock_code: str
    ) -> OrderResult:
        if not broker_order_no:
            return OrderResult(
                accepted=False, status="REJECTED", reject_reason="broker_order_no 없음"
            )

        log.info(
            "live_order_cancel",
            order_id=order_id,
            broker_order_no=broker_order_no,
        )

        resp = await self._client.cancel_order(
            str(order_id),
            payload={"broker_order_no": broker_order_no, "code": stock_code},
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
        # 게이트웨이가 별도 조회 API를 제공하지 않으므로 DB 기반 status를 사용해야 한다.
        # 본 메서드는 이후 v1.1에서 확장 예정.
        return OrderResult(
            accepted=True,
            status="PENDING",
            broker_order_no=broker_order_no,
        )
