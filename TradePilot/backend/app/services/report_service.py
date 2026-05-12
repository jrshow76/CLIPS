"""리포트 도메인 서비스.

손익/거래/전략별 성과 리포트 + CSV 익스포트.
실서비스에서는 Materialized View 와 OLAP 쿼리를 활용한다.
v1은 OrderRepository / DailyPnl 기반의 단순 집계 + mock export.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

import structlog
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.models.market import Stock
from app.models.trade import DailyPnl, Fill, Strategy
from app.repositories.order_repository import OrderRepository

log = structlog.get_logger(__name__)

EXPORT_TTL_SEC = 3600 * 24  # 24h


class ReportService:
    """리포트 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.orders = OrderRepository(db)

    # ------------------------------------------------------------------
    # 손익 리포트
    # ------------------------------------------------------------------
    async def pnl_report(
        self,
        user_id: int,
        *,
        from_date: date,
        to_date: date,
        granularity: str = "D",
    ) -> dict[str, Any]:
        stmt = (
            select(DailyPnl)
            .where(
                and_(
                    DailyPnl.user_id == user_id,
                    DailyPnl.trade_date >= from_date,
                    DailyPnl.trade_date <= to_date,
                )
            )
            .order_by(DailyPnl.trade_date.asc())
        )
        rows = list((await self.db.execute(stmt)).scalars().all())

        series = [
            {
                "ts": r.trade_date,
                "realized": r.realized_pnl or Decimal("0"),
                "unrealized": r.unrealized_pnl or Decimal("0"),
                "total": r.total_pnl or Decimal("0"),
            }
            for r in rows
        ]

        # 주/월 집계
        if granularity in ("W", "M") and series:
            from collections import OrderedDict

            buckets: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
            for item in series:
                ts: date = item["ts"]
                key = ts.strftime("%Y-%W") if granularity == "W" else ts.strftime("%Y-%m")
                if key not in buckets:
                    buckets[key] = {
                        "ts": ts,
                        "realized": Decimal("0"),
                        "unrealized": Decimal("0"),
                        "total": Decimal("0"),
                    }
                buckets[key]["realized"] += item["realized"]
                buckets[key]["unrealized"] += item["unrealized"]
                buckets[key]["total"] += item["total"]
            series = list(buckets.values())

        total_realized = sum((r.realized_pnl or 0) for r in rows)
        total_unrealized = sum((r.unrealized_pnl or 0) for r in rows)
        wins = sum((r.win_count or 0) for r in rows)
        losses = sum((r.loss_count or 0) for r in rows)
        summary = {
            "total_realized": Decimal(str(total_realized)),
            "total_unrealized": Decimal(str(total_unrealized)),
            "win_count": int(wins),
            "loss_count": int(losses),
            "win_rate": round(wins / (wins + losses), 4) if (wins + losses) else 0.0,
        }
        return {"granularity": granularity, "series": series, "summary": summary}

    # ------------------------------------------------------------------
    # 종목별 손익
    # ------------------------------------------------------------------
    async def positions_report(
        self,
        user_id: int,
        *,
        from_date: date,
        to_date: date,
    ) -> list[dict[str, Any]]:
        from_dt = datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
        to_dt = datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc)

        # 체결 기반 종목별 손익 집계 (간이)
        stmt = (
            select(
                Stock.code,
                Stock.name,
                func.sum(Fill.fill_qty * Fill.fill_price).label("amount"),
                func.count(Fill.id).label("trades"),
            )
            .join(Stock, Stock.id == Fill.stock_id)
            .where(
                and_(
                    Fill.user_id == user_id,
                    Fill.filled_at >= from_dt,
                    Fill.filled_at <= to_dt,
                )
            )
            .group_by(Stock.code, Stock.name)
        )
        rows = (await self.db.execute(stmt)).all()
        return [
            {
                "code": r.code,
                "name": r.name,
                "realized_pnl": Decimal(str(r.amount or 0)),
                "win_count": 0,
                "loss_count": 0,
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # 거래 리포트
    # ------------------------------------------------------------------
    async def trades_report(
        self,
        user_id: int,
        *,
        from_date: date,
        to_date: date,
        status: str | None = None,
        code: str | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> tuple[list[dict[str, Any]], int]:
        from_dt = datetime.combine(from_date, datetime.min.time(), tzinfo=timezone.utc)
        to_dt = datetime.combine(to_date, datetime.max.time(), tzinfo=timezone.utc)
        rows, total = await self.orders.list_for_user(
            user_id,
            status=status,
            code=code,
            from_dt=from_dt,
            to_dt=to_dt,
            offset=offset,
            limit=limit,
        )
        items: list[dict[str, Any]] = []
        for o in rows:
            stock = await self.db.get(Stock, o.stock_id)
            items.append(
                {
                    "id": str(o.public_id),
                    "code": stock.code if stock else "",
                    "side": o.side,
                    "qty": o.qty,
                    "price": o.price,
                    "status": o.status,
                    "created_at": o.created_at,
                    "filled_at": o.filled_at,
                }
            )
        return items, total

    # ------------------------------------------------------------------
    # 전략별 성과
    # ------------------------------------------------------------------
    async def strategies_report(
        self, user_id: int, *, strategy_ids: list[str]
    ) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for sid in strategy_ids:
            stmt = select(Strategy).where(
                and_(Strategy.public_id == sid, Strategy.user_id == user_id)
            )
            s = (await self.db.execute(stmt)).scalar_one_or_none()
            if not s:
                continue
            out.append(
                {
                    "strategy_id": str(s.public_id),
                    "name": s.name,
                    "trades": 0,
                    "win_rate": 0.0,
                    "cumulative_return": 0.0,
                }
            )
        return out

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    async def request_export(
        self,
        user_id: int,
        *,
        type_: str,
        from_date: date,
        to_date: date,
        fmt: str = "csv",
    ) -> str:
        """익스포트 잡 생성. (Redis 캐시로 즉시 완료 상태 저장.)"""
        export_id = uuid4().hex
        await get_redis().setex(
            f"export:{user_id}:{export_id}",
            EXPORT_TTL_SEC,
            f"{type_}|{from_date}|{to_date}|{fmt}|DONE",
        )
        log.info("export_requested", user_id=user_id, export_id=export_id, type=type_)
        return export_id

    async def get_export_status(self, user_id: int, export_id: str) -> dict[str, Any]:
        raw = await get_redis().get(f"export:{user_id}:{export_id}")
        if not raw:
            raise AppException("E0062", message="익스포트 잡을 찾을 수 없습니다.")
        if isinstance(raw, bytes):
            raw = raw.decode("utf-8")
        parts = raw.split("|")
        status = parts[-1] if parts else "UNKNOWN"
        # v1: 다운로드 URL은 정적 경로로 가정 (실제 구현 시 S3 Pre-signed URL)
        return {
            "export_id": export_id,
            "status": status,
            "download_url": f"/api/v1/reports/export/{export_id}/download"
            if status == "DONE"
            else None,
            "expires_at": None,
        }
