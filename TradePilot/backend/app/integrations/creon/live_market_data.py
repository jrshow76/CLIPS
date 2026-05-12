"""LiveMarketData: MarketDataPort 실거래 구현 (게이트웨이 기반)."""
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
from app.integrations.creon.client import CreonGatewayClient, get_creon_client

log = structlog.get_logger(__name__)


class LiveMarketData(MarketDataPort):
    """크레온 게이트웨이 기반 시세 어댑터."""

    def __init__(self, client: CreonGatewayClient | None = None) -> None:
        self._client = client or get_creon_client()

    async def get_snapshot(self, code: str) -> QuoteSnapshot:
        resp = await self._client.get_quote(code)
        data = resp.get("data", {}) or {}
        return QuoteSnapshot(
            code=code,
            price=Decimal(str(data.get("price", 0))),
            change=Decimal(str(data["change"])) if data.get("change") is not None else None,
            change_pct=(
                Decimal(str(data["change_pct"])) if data.get("change_pct") is not None else None
            ),
            volume=int(data.get("volume", 0)),
            ts=datetime.fromisoformat(data["ts"]) if data.get("ts") else None,
            source="creon",
        )

    async def get_orderbook(self, code: str) -> OrderbookSnapshot:
        resp = await self._client.get_orderbook(code)
        data = resp.get("data", {}) or {}
        return OrderbookSnapshot(
            code=code,
            bids=[
                (Decimal(str(b["price"])), int(b["qty"]))
                for b in (data.get("bids") or [])
            ],
            asks=[
                (Decimal(str(a["price"])), int(a["qty"]))
                for a in (data.get("asks") or [])
            ],
            ts=datetime.fromisoformat(data["ts"]) if data.get("ts") else None,
        )

    async def get_history(
        self,
        code: str,
        interval: str = "D",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[CandleBar]:
        # LIVE 모드의 과거 캔들은 DB(price_daily/minute) 우선 조회하는 것이 일반적.
        # 게이트웨이 호출이 필요한 시점은 빈 캔들 백필 또는 백테스트 사전 데이터 적재.
        # v1.0 기본 구현은 빈 리스트(상위 서비스에서 DB 조회로 처리).
        return []

    async def subscribe_ticks(self, codes: list[str]) -> AsyncIterator[QuoteSnapshot]:
        """실시간 시세 구독.

        구현 노트: 본체 측에서는 게이트웨이의 Redis Pub/Sub 채널
        `tp:market.tick.{code}`를 직접 구독하는 것이 정석이다.
        (`app.integrations.creon.event_listener` 참고)
        본 메서드는 사용 편의를 위한 wrapper로 빈 generator 반환.
        """
        await self._client.subscribe_quote(codes)
        # 실제 tick stream은 event_listener에서 처리.
        if False:
            yield  # type: ignore[unreachable]
