"""섹터 도메인 서비스."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AppException
from app.models.market import Sector
from app.repositories.sector_repository import SectorRepository

log = structlog.get_logger(__name__)


PERIOD_DAYS = {"D": 1, "W": 7, "M": 30}


class SectorService:
    """섹터 조회 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = SectorRepository(db)

    async def list_all(self) -> list[Sector]:
        return await self.repo.list_all()

    async def get_by_code(self, code: str) -> Sector:
        s = await self.repo.find_by_code(code)
        if not s:
            raise AppException("E0062", message="섹터를 찾을 수 없습니다.")
        return s

    # ------------------------------------------------------------------
    # 랭킹
    # ------------------------------------------------------------------
    async def ranking(self, *, period: str, sort: str = "change_pct,desc") -> list[dict[str, Any]]:
        """기간별 섹터 랭킹.

        period: D/W/M (최근 N일의 평균 change_pct, volume_amount 합)
        """
        days = PERIOD_DAYS.get(period.upper(), 1)
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        latest = await self.repo.latest_metrics_all()
        items: list[dict[str, Any]] = []
        for sec, _ in latest:
            metrics = await self.repo.metrics_for_period(
                sec.id, from_date=from_date, to_date=to_date
            )
            if not metrics:
                items.append(
                    {
                        "code": sec.code,
                        "name": sec.name,
                        "change_pct": None,
                        "volume_amount": None,
                    }
                )
                continue
            avg_chg = sum((m.change_pct or 0) for m in metrics) / len(metrics)
            total_vol = sum((m.volume_amount or 0) for m in metrics)
            items.append(
                {
                    "code": sec.code,
                    "name": sec.name,
                    "change_pct": Decimal(str(round(float(avg_chg), 4))),
                    "volume_amount": Decimal(str(total_vol)),
                }
            )
        # 정렬
        field, _, direction = sort.partition(",")
        direction = direction or "desc"
        reverse = direction.lower() == "desc"
        if field in ("change_pct", "volume_amount"):
            items.sort(key=lambda x: (x.get(field) is None, x.get(field) or 0), reverse=reverse)
        return items

    async def flow(self, *, period: str) -> list[dict[str, Any]]:
        days = PERIOD_DAYS.get(period.upper(), 1)
        to_date = date.today()
        from_date = to_date - timedelta(days=days)
        sectors = await self.repo.list_all()
        out: list[dict[str, Any]] = []
        for sec in sectors:
            metrics = await self.repo.metrics_for_period(
                sec.id, from_date=from_date, to_date=to_date
            )
            inflow = sum((m.inflow_amount or 0) for m in metrics)
            outflow = sum((m.outflow_amount or 0) for m in metrics)
            net = inflow - outflow
            out.append(
                {
                    "code": sec.code,
                    "name": sec.name,
                    "inflow_amount": Decimal(str(inflow)),
                    "outflow_amount": Decimal(str(outflow)),
                    "net_flow": Decimal(str(net)),
                }
            )
        out.sort(key=lambda x: float(x["net_flow"]), reverse=True)
        return out

    async def heatmap(self, *, window: int = 30) -> dict[str, Any]:
        """섹터 상관계수 매트릭스.

        v1: SectorMetricsDaily.change_pct 시계열로 단순 상관 계산.
        """
        sectors = await self.repo.list_all()
        if not sectors:
            return {"labels": [], "matrix": []}
        to_date = date.today()
        from_date = to_date - timedelta(days=window)

        # change_pct 벡터 수집
        series_map: dict[str, list[float]] = {}
        for s in sectors:
            ms = await self.repo.metrics_for_period(
                s.id, from_date=from_date, to_date=to_date
            )
            series_map[s.code] = [float(m.change_pct or 0) for m in ms]

        labels = [s.code for s in sectors]

        # 상관계수 (간이)
        def _corr(a: list[float], b: list[float]) -> float:
            n = min(len(a), len(b))
            if n < 2:
                return 0.0
            a = a[-n:]
            b = b[-n:]
            mean_a = sum(a) / n
            mean_b = sum(b) / n
            num = sum((a[i] - mean_a) * (b[i] - mean_b) for i in range(n))
            den_a = (sum((x - mean_a) ** 2 for x in a)) ** 0.5
            den_b = (sum((x - mean_b) ** 2 for x in b)) ** 0.5
            if den_a == 0 or den_b == 0:
                return 0.0
            return round(num / (den_a * den_b), 4)

        matrix = [[_corr(series_map[a], series_map[b]) for b in labels] for a in labels]
        return {"labels": labels, "matrix": matrix}

    async def list_stocks(
        self, code: str, *, offset: int, limit: int
    ) -> tuple[list[dict[str, Any]], int]:
        sec = await self.get_by_code(code)
        rows, total = await self.repo.list_stocks(sec.id, offset=offset, limit=limit)
        items = [
            {
                "code": s.code,
                "name": s.name,
                "market": s.market,
                "is_primary": is_primary,
            }
            for s, is_primary in rows
        ]
        return items, total
