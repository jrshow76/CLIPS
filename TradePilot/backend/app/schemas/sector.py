"""섹터 도메인 스키마."""
from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

SectorPeriod = Literal["D", "W", "M"]


class SectorOut(BaseModel):
    code: str
    name: str
    parent_code: str | None = None
    sort_order: int = 0


class SectorRankingItem(BaseModel):
    code: str
    name: str
    change_pct: Decimal | None = None
    volume_amount: Decimal | None = None


class SectorFlowItem(BaseModel):
    code: str
    name: str
    inflow_amount: Decimal | None = None
    outflow_amount: Decimal | None = None
    net_flow: Decimal | None = None


class SectorHeatmapOut(BaseModel):
    labels: list[str] = Field(default_factory=list)
    matrix: list[list[float]] = Field(default_factory=list)


class SectorStockItem(BaseModel):
    code: str
    name: str
    market: str
    is_primary: bool = False
