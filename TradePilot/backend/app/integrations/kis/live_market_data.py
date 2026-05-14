"""KIS LiveMarketData: MarketDataPort 구현 (한국투자증권).

- 현재가/호가: REST 직접 호출
- 실시간 시세: WebSocket 구독 → Redis publish (`tp:market.tick.<code>`)
  구독 워커는 별도 백그라운드 태스크에서 실행 (event_subscriber)
- 과거 캔들: KIS ``inquire-daily-itemchartprice`` API 사용 가능
  본 v1에서는 DB 우선 조회 정책에 맞춰 빈 리스트 반환.
"""
from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import date, datetime
from decimal import Decimal

import structlog

from app.domains.ports.market_data_port import (
    CandleBar,
    MarketDataPort,
    OrderbookSnapshot,
    QuoteSnapshot,
)
from app.integrations.kis.client import KisClient, get_kis_client

log = structlog.get_logger(__name__)


def _decimal(value: object, default: str = "0") -> Decimal:
    """KIS 응답은 문자열 숫자(예: '71200') 기반 — Decimal 안전 변환."""
    if value is None or value == "":
        return Decimal(default)
    try:
        return Decimal(str(value))
    except Exception:  # noqa: BLE001
        return Decimal(default)


class KisLiveMarketData(MarketDataPort):
    """KIS 시세 어댑터."""

    def __init__(self, client: KisClient | None = None) -> None:
        self._client = client or get_kis_client()

    async def get_snapshot(self, code: str) -> QuoteSnapshot:
        resp = await self._client.get_quote(code)
        out = resp.get("output") or {}
        # KIS 현재가 필드: stck_prpr(현재가), prdy_vrss(전일대비), prdy_ctrt(등락률%), acml_vol(거래량)
        return QuoteSnapshot(
            code=code,
            price=_decimal(out.get("stck_prpr")),
            change=_decimal(out.get("prdy_vrss")) if out.get("prdy_vrss") else None,
            change_pct=(
                _decimal(out.get("prdy_ctrt")) if out.get("prdy_ctrt") else None
            ),
            volume=int(_decimal(out.get("acml_vol"))),
            ts=datetime.utcnow(),
            source="kis",
        )

    async def get_orderbook(self, code: str) -> OrderbookSnapshot:
        resp = await self._client.get_orderbook(code)
        out = resp.get("output1") or resp.get("output") or {}
        bids: list[tuple[Decimal, int]] = []
        asks: list[tuple[Decimal, int]] = []
        # KIS 호가: ASKP1~ASKP10 (매도1~10), BIDP1~BIDP10 (매수1~10)
        # 잔량: ASKP_RSQN1~10, BIDP_RSQN1~10
        for i in range(1, 11):
            ask_p = out.get(f"askp{i}")
            ask_q = out.get(f"askp_rsqn{i}")
            bid_p = out.get(f"bidp{i}")
            bid_q = out.get(f"bidp_rsqn{i}")
            if ask_p and ask_q:
                asks.append((_decimal(ask_p), int(_decimal(ask_q))))
            if bid_p and bid_q:
                bids.append((_decimal(bid_p), int(_decimal(bid_q))))
        return OrderbookSnapshot(code=code, bids=bids, asks=asks, ts=datetime.utcnow())

    async def get_history(
        self,
        code: str,
        interval: str = "D",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[CandleBar]:
        """과거 캔들.

        v1.0: DB 우선 정책에 맞춰 빈 리스트.
        후속 작업: ``/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice``
        호출로 ML 백필 데이터 적재.
        """
        return []

    async def subscribe_ticks(self, codes: list[str]) -> AsyncIterator[QuoteSnapshot]:
        """실시간 시세 구독 (WebSocket).

        구현 노트:
        - 실제 구독 워커는 별도 ``event_subscriber.py`` (후속 작업)에서 관리.
        - WebSocket 채널 ``H0STCNT0`` 구독 → Redis ``tp:market.tick.<code>`` 발행.
        - 본 메서드는 사용 편의를 위한 stub. 즉시 빈 async generator 반환.
        """
        log.info("kis_ws_subscribe_request", codes=len(codes))
        # 실제 tick stream 은 event_subscriber 에서 처리.
        if False:
            yield  # type: ignore[unreachable]
