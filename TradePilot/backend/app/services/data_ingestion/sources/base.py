"""데이터 소스 어댑터 추상 클래스.

각 외부 데이터 소스(pykrx, CREON 등)는 본 추상을 구현한다.
- 모든 메서드는 동기/비동기 혼용 가능 (호출 측은 await 우선).
- DTO는 dataclass로 단순화하여 ORM 의존성을 분리한다.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal


# ---------------------------------------------------------------------------
# DTO: 데이터 소스가 반환하는 표준 레코드
# ---------------------------------------------------------------------------
@dataclass(slots=True)
class StockMasterRow:
    """종목 마스터 1행."""

    code: str
    name: str
    market: str  # KOSPI/KOSDAQ/KONEX/ETF
    listing_shares: int | None = None
    market_cap: int | None = None
    par_value: int | None = None
    listed_at: date | None = None
    status: str = "LISTED"


@dataclass(slots=True)
class StockSectorRow:
    """종목-섹터 매핑 1행."""

    stock_code: str
    sector_code: str
    sector_name: str
    is_primary: bool = True


@dataclass(slots=True)
class DailyBar:
    """일봉 1행."""

    code: str
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    volume_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    change_pct: Decimal | None = None
    adj_close: Decimal | None = None


@dataclass(slots=True)
class MinuteBar:
    """분봉 1행."""

    code: str
    ts: datetime  # KST timezone-aware
    interval_min: int
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    volume_amount: Decimal = field(default_factory=lambda: Decimal("0"))


@dataclass(slots=True)
class IndexBar:
    """지수 일봉 1행."""

    code: str  # KOSPI/KOSDAQ/KOSPI200
    trade_date: date
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: int = 0
    change_pct: Decimal | None = None


# ---------------------------------------------------------------------------
# 추상 베이스
# ---------------------------------------------------------------------------
class MarketDataSource(ABC):
    """시장 데이터 소스 어댑터 인터페이스."""

    name: str = "unknown"

    @abstractmethod
    async def fetch_stock_master(self, target_date: date | None = None) -> list[StockMasterRow]:
        """종목 마스터 전체 조회."""

    @abstractmethod
    async def fetch_sectors(self, target_date: date | None = None) -> list[StockSectorRow]:
        """종목-섹터 매핑 조회."""

    @abstractmethod
    async def fetch_daily(
        self,
        code: str,
        from_date: date,
        to_date: date,
    ) -> list[DailyBar]:
        """단일 종목 일봉 조회."""

    @abstractmethod
    async def fetch_index(
        self,
        index_code: str,
        from_date: date,
        to_date: date,
    ) -> list[IndexBar]:
        """지수 일봉 조회."""

    async def fetch_minute(
        self,
        code: str,
        target_date: date,
        interval_min: int = 1,
    ) -> list[MinuteBar]:
        """분봉 조회 (선택 구현; 기본은 빈 리스트)."""
        return []
