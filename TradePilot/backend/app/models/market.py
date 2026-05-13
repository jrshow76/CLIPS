"""시장 데이터 도메인 ORM (tp_market 스키마).

DDL: `database/init/11_market_domain.sql`
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Stock(Base):
    """종목 마스터."""

    __tablename__ = "stocks"
    __table_args__ = {"schema": "tp_market"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(6), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="LISTED")
    listing_shares: Mapped[int | None] = mapped_column(BigInteger)
    market_cap: Mapped[int | None] = mapped_column(BigInteger)
    par_value: Mapped[int | None] = mapped_column(Integer)
    listed_at: Mapped[date | None] = mapped_column(Date)
    delisted_at: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Sector(Base):
    """섹터/업종 마스터."""

    __tablename__ = "sectors"
    __table_args__ = {"schema": "tp_market"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    parent_code: Mapped[str | None] = mapped_column(String(20))
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class StockSector(Base):
    """종목-섹터 M:N 매핑."""

    __tablename__ = "stock_sectors"
    __table_args__ = {"schema": "tp_market"}

    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), primary_key=True
    )
    sector_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.sectors.id", ondelete="CASCADE"), primary_key=True
    )
    is_primary: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class CorporateAction(Base):
    """기업액션 (무상/유상증자, 액면분할, 배당)."""

    __tablename__ = "corporate_actions"
    __table_args__ = {"schema": "tp_market"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), nullable=False
    )
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    ratio: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    cash_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PriceDaily(Base):
    """일봉."""

    __tablename__ = "price_daily"
    __table_args__ = {"schema": "tp_market"}

    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    volume_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    adj_close: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class PriceMinute(Base):
    """분봉 (월별 RANGE 파티셔닝)."""

    __tablename__ = "price_minute"
    __table_args__ = {"schema": "tp_market"}

    stock_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    interval_min: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    volume_amount: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketIndex(Base):
    """시장 지수 마스터."""

    __tablename__ = "market_index"
    __table_args__ = {"schema": "tp_market"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(20), nullable=False, unique=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    market: Mapped[str] = mapped_column(String(10), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketIndexDaily(Base):
    """지수 일봉."""

    __tablename__ = "market_index_daily"
    __table_args__ = {"schema": "tp_market"}

    index_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.market_index.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    open: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    high: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    low: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    close: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class MarketCalendar(Base):
    """시장 휴장일 캘린더 (KRX/NYSE 등 확장 대비).

    DDL: `database/init/16_calendar_seed.sql`,
         `database/migrations/2026_05_add_market_calendar.sql`

    holiday_type:
        - REGULAR    : 법정/정기 공휴일 (신정, 설날, 추석, 광복절 등)
        - TEMPORARY  : 임시 휴장 (선거일, 임시 공휴일 등)
        - SUBSTITUTE : 대체 공휴일

    source:
        - pykrx  : pykrx 라이브러리에서 자동 동기화
        - manual : 운영자 수동 입력
        - seed   : 초기 시드 데이터
    """

    __tablename__ = "market_calendar"
    __table_args__ = {"schema": "tp_market"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    holiday_date: Mapped[date] = mapped_column(Date, nullable=False, unique=True)
    holiday_name: Mapped[str] = mapped_column(String(100), nullable=False)
    holiday_type: Mapped[str] = mapped_column(String(20), nullable=False, default="REGULAR")
    market: Mapped[str] = mapped_column(String(10), nullable=False, default="KRX")
    description: Mapped[str | None] = mapped_column(String)
    source: Mapped[str] = mapped_column(String(20), nullable=False, default="pykrx")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
