"""종목/시세 도메인 서비스."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.integrations.factory import get_market_data
from app.models.market import PriceDaily, PriceMinute, Stock
from app.models.user import UserFavorite
from app.repositories.stock_repository import (
    StockExtRepository,
    UserFavoriteRepository,
)

log = structlog.get_logger(__name__)


INTERVAL_MAP_MINUTE = {"1m": 1, "5m": 5, "15m": 15, "30m": 30, "60m": 60}


class StockService:
    """종목/시세 조회 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.stocks = StockExtRepository(db)
        self.favs = UserFavoriteRepository(db)

    # ------------------------------------------------------------------
    # 종목 조회/검색
    # ------------------------------------------------------------------
    async def search(
        self, *, q: str | None, market: str | None, offset: int, limit: int
    ) -> tuple[list[Stock], int]:
        return await self.stocks.search(q=q, market=market, offset=offset, limit=limit)

    async def get_by_code(self, code: str) -> Stock:
        s = await self.stocks.find_by_code(code)
        if not s:
            raise AppException("E0062", message="종목을 찾을 수 없습니다.")
        return s

    async def get_quote(self, code: str) -> dict[str, Any]:
        """시세 스냅샷. SIM 어댑터(=DB 기반) 사용."""
        market = get_market_data("SIM")
        try:
            snap = await market.get_snapshot(code)
        except Exception as e:
            raise AppException("E0004", message="시세 데이터를 가져올 수 없습니다.") from e
        return {
            "code": code,
            "price": snap.price,
            "change": getattr(snap, "change", Decimal("0")),
            "change_pct": getattr(snap, "change_pct", Decimal("0")),
            "volume": int(getattr(snap, "volume", 0) or 0),
            "ts": getattr(snap, "ts", datetime.utcnow()),
        }

    async def get_orderbook(self, code: str) -> dict[str, Any]:
        """호가 10단계 스냅샷.

        흐름:
        1. Redis 캐시(``tp:cache:orderbook:<code>``, TTL=1초) 조회
        2. 캐시 미스 → CREON 게이트웨이 ``/market/orderbook/{code}`` 호출
        3. 게이트웨이 실패 → 최신 일봉 기반 mock 생성 (fallback)
        4. 결과를 ``OrderbookOut`` 스키마 형식(`bids`/`asks`는 `[{price, qty}]`)로 정규화

        - 게이트웨이 응답 페이로드는 ``bids/asks: [[price, qty], ...]``이므로 dict 형태로 변환.
        - 게이트웨이가 도달 불가능한 환경(테스트/오프라인)에서도 화면이 깨지지 않도록 mock fallback 유지.
        """
        from app.core.redis_client import cache_get_json, cache_set_json

        s = await self.get_by_code(code)
        cache_key = f"tp:cache:orderbook:{code}"
        cached = await cache_get_json(cache_key)
        if cached:
            return self._normalize_orderbook(code, cached)

        # 게이트웨이 호출 시도
        try:
            from app.integrations.creon.client import get_creon_client

            gw = get_creon_client()
            resp = await gw.get_orderbook(code)
            if isinstance(resp, dict) and resp.get("success") and resp.get("data"):
                data = resp["data"]
                # 1초 TTL 캐시
                await cache_set_json(cache_key, data, ttl_sec=1)
                return self._normalize_orderbook(code, data)
        except Exception as e:
            log.warning("orderbook_gateway_fallback", code=code, error=str(e))

        # Fallback: 최신 일봉 종가 기반 mock 호가
        last = await self.stocks.latest_daily(s.id)
        if not last:
            raise AppException("E0061", message="호가 정보를 사용할 수 없습니다.")
        base = float(last.close)
        tick = max(1.0, base * 0.001)
        asks = [
            {
                "price": Decimal(str(round(base + tick * (i + 1), 2))),
                "qty": 100 + i * 10,
            }
            for i in range(10)
        ]
        bids = [
            {
                "price": Decimal(str(round(base - tick * (i + 1), 2))),
                "qty": 100 + i * 10,
            }
            for i in range(10)
        ]
        return {
            "code": code,
            "asks": asks,
            "bids": bids,
            "ts": datetime.utcnow(),
        }

    @staticmethod
    def _normalize_orderbook(code: str, data: dict[str, Any]) -> dict[str, Any]:
        """게이트웨이/캐시 페이로드를 ``OrderbookOut`` 형식으로 정규화.

        게이트웨이 페이로드는 ``bids/asks: [[price, qty], ...]``로 오므로,
        ``[{price, qty}]`` (Pydantic ``OrderbookLevel``)로 변환한다.
        """
        def _conv(levels: list[Any]) -> list[dict[str, Any]]:
            out: list[dict[str, Any]] = []
            for level in levels or []:
                if isinstance(level, dict):
                    price = level.get("price", 0)
                    qty = level.get("qty", 0)
                elif isinstance(level, (list, tuple)) and len(level) >= 2:
                    price, qty = level[0], level[1]
                else:
                    continue
                out.append({"price": Decimal(str(price)), "qty": int(qty or 0)})
            return out

        ts_raw = data.get("ts")
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
            except ValueError:
                ts = datetime.utcnow()
        elif isinstance(ts_raw, datetime):
            ts = ts_raw
        else:
            ts = datetime.utcnow()

        return {
            "code": code,
            "bids": _conv(data.get("bids") or []),
            "asks": _conv(data.get("asks") or []),
            "ts": ts,
        }

    # ------------------------------------------------------------------
    # 캔들
    # ------------------------------------------------------------------
    async def get_candles(
        self,
        code: str,
        *,
        interval: str,
        from_: str | None,
        to: str | None,
    ) -> list[dict[str, Any]]:
        s = await self.get_by_code(code)
        if interval in ("D", "W", "M"):
            from_date = date.fromisoformat(from_) if from_ else None
            to_date = date.fromisoformat(to) if to else None
            rows = await self.stocks.list_daily(s.id, from_date=from_date, to_date=to_date)
            if interval == "D":
                return [self._daily_to_dict(r) for r in rows]
            return self._aggregate(rows, period=interval)
        elif interval in INTERVAL_MAP_MINUTE:
            from_ts = datetime.fromisoformat(from_) if from_ else None
            to_ts = datetime.fromisoformat(to) if to else None
            rows = await self.stocks.list_minute(
                s.id,
                interval_min=INTERVAL_MAP_MINUTE[interval],
                from_ts=from_ts,
                to_ts=to_ts,
            )
            return [self._minute_to_dict(r) for r in rows]
        raise AppException("E0003", details={"interval": ["허용되지 않은 봉 간격"]})

    def _daily_to_dict(self, r: PriceDaily) -> dict[str, Any]:
        return {
            "ts": datetime.combine(r.trade_date, datetime.min.time()),
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": int(r.volume),
        }

    def _minute_to_dict(self, r: PriceMinute) -> dict[str, Any]:
        return {
            "ts": r.ts,
            "open": r.open,
            "high": r.high,
            "low": r.low,
            "close": r.close,
            "volume": int(r.volume),
        }

    def _aggregate(self, rows: list[PriceDaily], *, period: str) -> list[dict[str, Any]]:
        """일봉을 주봉/월봉으로 단순 집계."""
        if not rows:
            return []
        from collections import OrderedDict

        groups: "OrderedDict[str, list[PriceDaily]]" = OrderedDict()
        for r in rows:
            key = (
                r.trade_date.strftime("%Y-%W") if period == "W" else r.trade_date.strftime("%Y-%m")
            )
            groups.setdefault(key, []).append(r)
        out: list[dict[str, Any]] = []
        for key, items in groups.items():
            items.sort(key=lambda x: x.trade_date)
            out.append(
                {
                    "ts": datetime.combine(items[0].trade_date, datetime.min.time()),
                    "open": items[0].open,
                    "high": max(i.high for i in items),
                    "low": min(i.low for i in items),
                    "close": items[-1].close,
                    "volume": sum(int(i.volume) for i in items),
                }
            )
        return out

    # ------------------------------------------------------------------
    # 즐겨찾기
    # ------------------------------------------------------------------
    async def add_favorite(self, user_id: int, code: str) -> None:
        s = await self.get_by_code(code)
        if await self.favs.exists(user_id, s.id):
            return  # 이미 있음
        fav = UserFavorite(user_id=user_id, stock_id=s.id)
        self.db.add(fav)
        await self.db.commit()
        log.info("favorite_added", user_id=user_id, code=code)

    async def remove_favorite(self, user_id: int, code: str) -> None:
        s = await self.get_by_code(code)
        await self.favs.remove(user_id, s.id)
        await self.db.commit()

    async def list_favorites(self, user_id: int) -> list[dict[str, Any]]:
        rows = await self.favs.list_for_user(user_id)
        return [
            {
                "code": stock.code,
                "name": stock.name,
                "market": stock.market,
                "created_at": fav.created_at,
            }
            for fav, stock in rows
        ]
