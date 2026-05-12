"""SimOrderRouter: 시뮬레이션 주문 라우터.

`docs/15_trading_policy.md` §7 가정:
- 슬리피지: 시장가 ±0.1%
- 수수료: 0.015%
- 거래세: 매도 0.18% (코스피/코스닥 공통, 정책 변경 가능)
- 시장가는 즉시 체결, 지정가는 현재가가 호가에 닿는 경우 체결로 가정.
- 체결지연: 50~200ms (랜덤) → asyncio.sleep으로 시뮬레이션
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from decimal import Decimal

import structlog

from app.domains.ports.market_data_port import MarketDataPort
from app.domains.ports.order_router_port import (
    OrderRequest,
    OrderResult,
    OrderRouterPort,
)

log = structlog.get_logger(__name__)

# 정책 상수
SIM_SLIPPAGE_RATE = Decimal("0.001")  # 0.1%
SIM_FEE_RATE = Decimal("0.00015")     # 0.015%
SIM_TAX_RATE_SELL = Decimal("0.0018") # 0.18% (매도 시)
SIM_FILL_DELAY_MIN_MS = 50
SIM_FILL_DELAY_MAX_MS = 200


class SimOrderRouter(OrderRouterPort):
    """시뮬레이션 주문 라우터.

    market_data 포트를 주입받아 현재가 기반으로 가상 체결을 만든다.
    """

    def __init__(
        self,
        market_data: MarketDataPort,
        slippage_rate: Decimal = SIM_SLIPPAGE_RATE,
        fee_rate: Decimal = SIM_FEE_RATE,
        tax_rate_sell: Decimal = SIM_TAX_RATE_SELL,
        enable_random_delay: bool = True,
    ) -> None:
        self._market = market_data
        self._slippage = slippage_rate
        self._fee = fee_rate
        self._tax_sell = tax_rate_sell
        self._delay = enable_random_delay

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        """가상 체결."""
        # 체결 지연 시뮬레이션
        if self._delay:
            await asyncio.sleep(
                random.randint(SIM_FILL_DELAY_MIN_MS, SIM_FILL_DELAY_MAX_MS) / 1000
            )

        # 현재가 조회
        try:
            snapshot = await self._market.get_snapshot(request.stock_code)
            ref_price = snapshot.price
        except Exception as e:
            log.warning("sim_quote_unavailable", code=request.stock_code, error=str(e))
            # 시세 미수신 → 지정가가 있으면 사용, 없으면 거부
            if request.price is None:
                return OrderResult(
                    accepted=False,
                    status="REJECTED",
                    reject_reason="시세 조회 실패 (E0061)",
                )
            ref_price = request.price

        # 체결가 산정
        if request.order_type == "MARKET":
            # 매수: +슬리피지, 매도: -슬리피지
            sign = Decimal("1") if request.side == "BUY" else Decimal("-1")
            fill_price = ref_price * (Decimal("1") + sign * self._slippage)
        else:  # LIMIT
            # 단순화: 지정가가 현재가에 도달했다고 가정
            if request.side == "BUY" and request.price is not None and request.price < ref_price:
                # 매수 지정가가 현재가보다 낮으면 미체결 처리
                return OrderResult(
                    accepted=True,
                    status="NEW",  # 미체결 상태로 대기
                    reject_reason=None,
                )
            if request.side == "SELL" and request.price is not None and request.price > ref_price:
                return OrderResult(accepted=True, status="NEW")
            fill_price = request.price or ref_price

        # 호가 단위 보정 (한국 시장 일반 정책: 천원 단위 등은 단순화로 4자리 반올림)
        fill_price = fill_price.quantize(Decimal("0.01"))

        # 수수료/세금
        gross = fill_price * request.qty
        fee = (gross * self._fee).quantize(Decimal("0.01"))
        tax = (
            (gross * self._tax_sell).quantize(Decimal("0.01"))
            if request.side == "SELL"
            else Decimal("0.00")
        )

        slippage = (fill_price - ref_price) / ref_price if ref_price > 0 else Decimal("0")
        result = OrderResult(
            accepted=True,
            status="FILLED",
            broker_order_no=None,
            filled_qty=request.qty,
            avg_fill_price=fill_price,
            fee=fee,
            tax=tax,
            slippage=slippage.quantize(Decimal("0.0001")),
            filled_at=datetime.now(tz=timezone.utc),
        )
        log.info(
            "sim_order_filled",
            order_id=request.order_id,
            code=request.stock_code,
            side=request.side,
            qty=str(request.qty),
            fill_price=str(fill_price),
            fee=str(fee),
            tax=str(tax),
        )
        return result

    async def cancel_order(
        self, order_id: int, broker_order_no: str | None, stock_code: str
    ) -> OrderResult:
        """SIM 모드 취소는 즉시 성공."""
        return OrderResult(
            accepted=True,
            status="CANCELED",
            broker_order_no=broker_order_no,
        )

    async def get_order_status(
        self, order_id: int, broker_order_no: str | None
    ) -> OrderResult:
        return OrderResult(accepted=True, status="FILLED", broker_order_no=broker_order_no)
