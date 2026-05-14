"""매매 도메인 ORM (tp_trade 스키마).

DDL: `database/init/13_trade_domain.sql`
주의: orders/fills 는 월별 RANGE 파티셔닝이므로 PK가 복합키이다.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Strategy(Base):
    """사용자 전략."""

    __tablename__ = "strategies"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    entry_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    exit_rules: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    universe: Mapped[list[Any]] = mapped_column(JSONB, nullable=False, default=list)
    limits: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deactivated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class StrategyRule(Base):
    """전략 룰 정규화 (보조 검색용)."""

    __tablename__ = "strategy_rules"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    strategy_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_trade.strategies.id", ondelete="CASCADE"), nullable=False
    )
    rule_type: Mapped[str] = mapped_column(String(10), nullable=False)
    indicator: Mapped[str] = mapped_column(String(50), nullable=False)
    op: Mapped[str] = mapped_column(String(10), nullable=False)
    value: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Order(Base):
    """주문 (월별 RANGE 파티셔닝). PK=(id, ordered_at)."""

    __tablename__ = "orders"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    strategy_id: Mapped[int | None] = mapped_column(BigInteger)
    signal_id: Mapped[int | None] = mapped_column(BigInteger)
    stock_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trade_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    side: Mapped[str] = mapped_column(String(10), nullable=False)
    order_type: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="NEW")
    broker_order_no: Mapped[str | None] = mapped_column(String(50))
    idempotency_key: Mapped[str | None] = mapped_column(String(64))
    reject_reason: Mapped[str | None] = mapped_column(Text)
    ordered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    canceled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # SEC-003(GATE-1) — Kill Switch 게이트웨이 cancel_order 부분 실패 재시도용
    last_kill_switch_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    kill_switch_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Fill(Base):
    """체결. PK=(id, filled_at) 파티셔닝."""

    __tablename__ = "fills"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    user_id: Mapped[int | None] = mapped_column(BigInteger)
    stock_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trade_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    fill_qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    fill_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    fee: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    tax: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    slippage: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    filled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), primary_key=True, server_default=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Position(Base):
    """현재 보유 포지션 (user × stock × mode 1행)."""

    __tablename__ = "positions"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    stock_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    trade_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    qty: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    avg_price: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class Portfolio(Base):
    """일별 자산 스냅샷."""

    __tablename__ = "portfolios"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    trade_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    cash: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    equity: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    total_value: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    snapshot_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class DailyPnl(Base):
    """일별 손익 집계."""

    __tablename__ = "daily_pnl"
    __table_args__ = {"schema": "tp_trade"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    trade_mode: Mapped[str] = mapped_column(String(10), primary_key=True)
    realized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    unrealized_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    total_pnl: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False, default=0)
    mdd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    win_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    loss_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class TradeLimit(Base):
    """사용자 매매 한도."""

    __tablename__ = "trade_limits"
    __table_args__ = {"schema": "tp_trade"}

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), primary_key=True
    )
    daily_buy_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), nullable=False, default=Decimal("5000000")
    )
    daily_buy_count: Mapped[int] = mapped_column(Integer, nullable=False, default=20)
    per_stock_amount: Mapped[Decimal] = mapped_column(
        Numeric(20, 4), nullable=False, default=Decimal("1000000")
    )
    max_positions: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    stop_loss_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("-3.0")
    )
    take_profit_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("5.0")
    )
    daily_loss_limit_pct: Mapped[Decimal] = mapped_column(
        Numeric(10, 4), nullable=False, default=Decimal("-5.0")
    )
    single_order_max_qty: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class KillSwitchLog(Base):
    """비상정지 이력."""

    __tablename__ = "kill_switch_log"
    __table_args__ = {"schema": "tp_trade"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)
    canceled_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    detail: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
