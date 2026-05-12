"""SimMarketData: 시뮬레이션 시세 어댑터.

전략:
1) DB(price_daily/price_minute)의 최신 종가/현재 캔들을 가져온다.
2) DB도 없으면 Redis 캐시(`quote:{code}`)를 시도.
3) 둘 다 없으면 임의의 데모 가격(70,000원) 반환.

이 어댑터는 시뮬레이션 모드에서 SimOrderRouter가 호출하는 시세 소스이다.
"""
from __future__ import annotations

import random
from collections.abc import AsyncIterator
from datetime import date, datetime, timezone
from decimal import Decimal

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import AsyncSessionLocal
from app.core.redis_client import cache_get_json, cache_set_json
from app.domains.ports.market_data_port import (
    CandleBar,
    MarketDataPort,
    OrderbookSnapshot,
    QuoteSnapshot,
)
from app.models.market import PriceDaily, Stock

log = structlog.get_logger(__name__)

QUOTE_CACHE_TTL = 3  # 초


class SimMarketData(MarketDataPort):
    """DB + 캐시 + 데모 가격 fallback."""

    def __init__(
        self,
        session_factory: async_sessionmaker | None = None,
    ) -> None:
        self._sf = session_factory or AsyncSessionLocal

    async def get_snapshot(self, code: str) -> QuoteSnapshot:
        # 1) 캐시
        cached = await cache_get_json(f"quote:{code}")
        if cached:
            return QuoteSnapshot(
                code=code,
                price=Decimal(str(cached["price"])),
                change=Decimal(str(cached.get("change", 0))),
                change_pct=Decimal(str(cached.get("change_pct", 0))),
                volume=int(cached.get("volume", 0)),
                ts=datetime.fromisoformat(cached["ts"]) if cached.get("ts") else None,
                source="cache",
            )

        # 2) DB - 가장 최근 일봉
        async with self._sf() as session:
            stmt = (
                select(PriceDaily, Stock)
                .join(Stock, Stock.id == PriceDaily.stock_id)
                .where(Stock.code == code)
                .order_by(PriceDaily.trade_date.desc())
                .limit(1)
            )
            row = (await session.execute(stmt)).first()

        if row:
            pd, _stock = row
            snapshot = QuoteSnapshot(
                code=code,
                price=pd.close,
                change=(pd.close - pd.open) if pd.open else Decimal("0"),
                change_pct=pd.change_pct or Decimal("0"),
                volume=pd.volume,
                ts=datetime.now(tz=timezone.utc),
                source="db_daily",
            )
        else:
            # 3) 데모 가격 (테스트 환경에서 동작)
            log.debug("sim_demo_price_used", code=code)
            base = 70_000 + random.randint(-500, 500)
            snapshot = QuoteSnapshot(
                code=code,
                price=Decimal(str(base)),
                change=Decimal("0"),
                change_pct=Decimal("0"),
                volume=0,
                ts=datetime.now(tz=timezone.utc),
                source="sim_demo",
            )

        # 캐시 저장
        await cache_set_json(
            f"quote:{code}",
            {
                "price": str(snapshot.price),
                "change": str(snapshot.change or 0),
                "change_pct": str(snapshot.change_pct or 0),
                "volume": snapshot.volume,
                "ts": (snapshot.ts or datetime.now(tz=timezone.utc)).isoformat(),
            },
            ttl_sec=QUOTE_CACHE_TTL,
        )
        return snapshot

    async def get_orderbook(self, code: str) -> OrderbookSnapshot:
        """SIM 호가: 현재가 ±1호가 단위로 합성."""
        snap = await self.get_snapshot(code)
        price = snap.price
        tick = self._tick_size(price)
        bids = [(price - tick * (i + 1), 100 * (i + 1)) for i in range(10)]
        asks = [(price + tick * (i + 1), 100 * (i + 1)) for i in range(10)]
        return OrderbookSnapshot(code=code, bids=bids, asks=asks, ts=snap.ts)

    async def get_history(
        self,
        code: str,
        interval: str = "D",
        from_date: date | None = None,
        to_date: date | None = None,
    ) -> list[CandleBar]:
        """일봉 히스토리 (DB)."""
        async with self._sf() as session:
            stmt = (
                select(PriceDaily, Stock)
                .join(Stock, Stock.id == PriceDaily.stock_id)
                .where(Stock.code == code)
                .order_by(PriceDaily.trade_date.asc())
            )
            if from_date:
                stmt = stmt.where(PriceDaily.trade_date >= from_date)
            if to_date:
                stmt = stmt.where(PriceDaily.trade_date <= to_date)
            rows = (await session.execute(stmt)).all()

        return [
            CandleBar(
                ts=datetime.combine(pd.trade_date, datetime.min.time(), tzinfo=timezone.utc),
                open=pd.open,
                high=pd.high,
                low=pd.low,
                close=pd.close,
                volume=pd.volume,
                interval=interval,
            )
            for pd, _ in rows
        ]

    async def subscribe_ticks(self, codes: list[str]) -> AsyncIterator[QuoteSnapshot]:
        """SIM 모드는 실시간 구독 미지원 (빈 generator)."""
        if False:
            yield  # type: ignore[unreachable]

    @staticmethod
    def _tick_size(price: Decimal) -> Decimal:
        """KRX 호가 단위 (단순화)."""
        if price < 2000:
            return Decimal("1")
        if price < 5000:
            return Decimal("5")
        if price < 20000:
            return Decimal("10")
        if price < 50000:
            return Decimal("50")
        if price < 200000:
            return Decimal("100")
        if price < 500000:
            return Decimal("500")
        return Decimal("1000")
