"""분석 도메인 ORM (tp_analysis 스키마).

DDL: `database/init/12_analysis_domain.sql`
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
    Numeric,
    SmallInteger,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class IndicatorDaily(Base):
    """일봉 기반 기술적 지표 캐시."""

    __tablename__ = "indicators_daily"
    __table_args__ = {"schema": "tp_analysis"}

    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    ma5: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    ma20: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    ma60: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    ma120: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    rsi14: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    macd: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    macd_signal: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    macd_hist: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    bb_mid: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    bb_upper: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    bb_lower: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    obv: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    vwap: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    stoch_k: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    stoch_d: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    atr14: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class SectorMetricsDaily(Base):
    """섹터 일별 메트릭."""

    __tablename__ = "sector_metrics_daily"
    __table_args__ = {"schema": "tp_analysis"}

    sector_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.sectors.id", ondelete="CASCADE"), primary_key=True
    )
    trade_date: Mapped[date] = mapped_column(Date, primary_key=True)
    change_pct: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    volume_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    inflow_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    outflow_amount: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    net_flow: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    correlation: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Recommendation(Base):
    """일별 추천 종목."""

    __tablename__ = "recommendations"
    __table_args__ = {"schema": "tp_analysis"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[int | None] = mapped_column(BigInteger)
    trade_date: Mapped[date] = mapped_column(Date, nullable=False)
    score: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    reason_code: Mapped[str | None] = mapped_column(String(50))
    reason_text: Mapped[str | None] = mapped_column(Text)
    features: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )


class Signal(Base):
    """매매 시그널."""

    __tablename__ = "signals"
    __table_args__ = {"schema": "tp_analysis"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    public_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), nullable=False, unique=True, server_default=func.gen_random_uuid()
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_user.users.id", ondelete="CASCADE"), nullable=False
    )
    strategy_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(10), nullable=False)  # BUY/SELL
    confidence: Mapped[str] = mapped_column(String(10), nullable=False, default="MID")
    trigger_price: Mapped[Decimal | None] = mapped_column(Numeric(20, 4))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="ACTIVE")
    condition_trace: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ignored_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )


class MLPrediction(Base):
    """LSTM 예측 결과."""

    __tablename__ = "ml_predictions"
    __table_args__ = {"schema": "tp_analysis"}

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    stock_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tp_market.stocks.id", ondelete="CASCADE"), nullable=False
    )
    base_date: Mapped[date] = mapped_column(Date, nullable=False)
    horizon: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    pred_mean: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    pred_lower: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    pred_upper: Mapped[Decimal] = mapped_column(Numeric(20, 4), nullable=False)
    model_version: Mapped[str] = mapped_column(String(50), nullable=False)
    mape: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    direction_acc: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
