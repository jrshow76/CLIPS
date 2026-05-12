"""백테스트 도메인 ORM (tp_trade 스키마 내 분리).

DDL: `database/init/14_backtest_domain.sql`
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class BacktestRun(Base):
    """백테스트 잡 헤더."""

    __tablename__ = "backtest_runs"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    job_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_trade.strategies.id", ondelete="CASCADE"), nullable=False
    )
    universe: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    period_from: Mapped[date] = mapped_column(Date, nullable=False)
    period_to: Mapped[date] = mapped_column(Date, nullable=False)
    initial_capital: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    slippage: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False, default=Decimal("0.001"))
    fee_rate: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("0.00015")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="QUEUED")
    progress: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BacktestResult(Base):
    """백테스트 결과 (사용자 저장)."""

    __tablename__ = "backtest_results"
    __table_args__ = {"schema": "tp_trade"}

    run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_trade.backtest_runs.id", ondelete="CASCADE"), primary_key=True
    )
    label: Mapped[str | None] = mapped_column(String(100))
    cumulative_return: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    annualized_return: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    mdd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    sharpe: Mapped[Decimal | None] = mapped_column(Numeric(20, 8))
    win_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    trade_count: Mapped[int | None] = mapped_column(Integer)
    equity_curve: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    summary: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    saved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class BacktestTrade(Base):
    """백테스트 가상 거래 내역."""

    __tablename__ = "backtest_trades"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_trade.backtest_runs.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    entry_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    exit_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    pnl: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    entry_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    exit_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
