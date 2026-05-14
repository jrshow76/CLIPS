"""KIS LiveOrderRouter: OrderRouterPort 구현 (한국투자증권).

CREON LiveOrderRouter와 동일한 시그니처를 유지한다 (포트 추상 일관성).
체결 이벤트는 KIS WebSocket에서 별도 수신되며 본 모듈은 ACCEPTED만 반환.
"""
from __future__ import annotations

from decimal import Decimal

import structlog

from app.core.exceptions import AppException
from app.domains.ports.order_router_port import (
    OrderRequest,
    OrderResult,
    OrderRouterPort,
)
from app.integrations.kis.client import KisClient, get_kis_client

log = structlog.get_logger(__name__)


class KisLiveOrderRouter(OrderRouterPort):
    """KIS REST 기반 실거래 라우터."""

    def __init__(self, client: KisClient | None = None) -> None:
        self._client = client or get_kis_client()

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        log.info(
            "kis_order_submit",
            order_id=request.order_id,
            code=request.stock_code,
            side=request.side,
            qty=str(request.qty),
            order_type=request.order_type,
        )
        try:
            resp = await self._client.submit_order(
                code=request.stock_code,
                side=request.side,
                qty=int(request.qty),
                order_type=request.order_type,
                price=float(request.price) if request.price is not None else None,
                idempotency_key=request.idempotency_key,
            )
        except AppException as e:
            # 비즈니스 거부 → REJECTED 로 표시 (서비스 계층이 status 처리)
            log.warning(
                "kis_order_rejected", code=e.code, order_id=request.order_id
            )
            return OrderResult(
                accepted=False,
                status="REJECTED",
                reject_reason=str(e.message)[:500] if hasattr(e, "message") else str(e),
                raw={"app_code": e.code},
            )

        output = resp.get("output") or {}
        # KIS 응답: KRX_FWDG_ORD_ORGNO + ODNO 조합으로 주문번호 식별.
        # 우리는 단일 문자열로 broker_order_no 를 사용하므로 ODNO 만 사용.
        broker_order_no = str(output.get("ODNO") or output.get("KRX_FWDG_ORD_ORGNO") or "")
        return OrderResult(
            accepted=True,
            status="ACCEPTED",
            broker_order_no=broker_order_no or None,
            raw=output,
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
            "kis_order_cancel",
            order_id=order_id,
            broker_order_no=broker_order_no,
            timeout_sec=timeout_sec,
            idem=bool(idempotency_key),
        )
        try:
            resp = await self._client.cancel_order(
                broker_order_no=broker_order_no,
                code=stock_code,
                qty=0,
                timeout_sec=timeout_sec,
                idempotency_key=idempotency_key,
            )
        except AppException as e:
            return OrderResult(
                accepted=False,
                status="REJECTED",
                reject_reason=getattr(e, "message", str(e))[:500],
                raw={"app_code": e.code},
            )
        return OrderResult(
            accepted=True,
            status="CANCELED",
            broker_order_no=broker_order_no,
            raw=resp.get("output") or {},
        )

    async def get_order_status(
        self, order_id: int, broker_order_no: str | None
    ) -> OrderResult:
        """주문 상태 조회.

        KIS는 일별 체결 조회 API로 단일 주문번호 조회가 가능하나
        본 v1 구현은 DB 기반 상태를 우선하므로 PENDING 반환.
        """
        return OrderResult(
            accepted=True,
            status="PENDING",
            broker_order_no=broker_order_no,
        )
