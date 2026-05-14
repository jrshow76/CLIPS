"""키움 LiveMarketData: MarketDataPort 구현 (키움 게이트웨이 경유)."""
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
from app.integrations.kiwoom.client import KiwoomGatewayClient, get_kiwoom_client

log = structlog.get_logger(__name__)


class KiwoomLiveMarketData(MarketDataPort):
    """키움 게이트웨이 기반 시세 어댑터."""

    def __init__(self, client: KiwoomGatewayClient | None = None) -> None:
        self._client = client or get_kiwoom_client()

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
            source="kiwoom",
        )

    async def get_orderbook(self, code: str) -> OrderbookSnapshot:
        # 키움 게이트웨이 v1 은 호가 별도 API 미제공 (현재가만 노출).
        # 추후 게이트웨이 보강 시 활성화.
        return OrderbookSnapshot(code=code, bids=[], asks=[], ts=datetime.utcnow())

    async def get_history(
        self,
        code: str,
        interval: str = "D",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[CandleBar]:
        # CREON 어댑터와 동일 정책: DB 우선 조회.
        return []

    async def subscribe_ticks(self, codes: list[str]) -> AsyncIterator[QuoteSnapshot]:
        """실시간 시세 구독 — 게이트웨이가 Redis 로 publish."""
        await self._client.subscribe_quote(codes)
        if False:
            yield  # type: ignore[unreachable]
