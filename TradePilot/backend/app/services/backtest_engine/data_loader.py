"""백테스트용 시계열 데이터 로더.

- DB의 `tp_market.price_daily` 에서 OHLCV 를 DataFrame 으로 로드한다.
- 휴장일은 거래일 기준 시퀀스만 유지(달력 fill 미수행).
- 데이터가 없을 경우 합성 데이터 fallback 을 지원한다.
  환경변수: `BACKTEST_USE_SYNTHETIC=true` 일 때 활성화.
"""
from __future__ import annotations

import os
from datetime import date, timedelta
from decimal import Decimal

import numpy as np
import pandas as pd
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.market import PriceDaily, Stock

log = structlog.get_logger(__name__)


# 컬럼 표준: [open, high, low, close, volume]  Index: DatetimeIndex (KST 일자)


async def load_daily_prices(
    db: AsyncSession,
    codes: list[str],
    period_from: date,
    period_to: date,
) -> dict[str, pd.DataFrame]:
    """다종목 일봉을 DataFrame dict 로 로드.

    Returns:
        {code: DataFrame(index=DatetimeIndex, columns=[open, high, low, close, volume])}
    """
    use_synthetic = os.getenv("BACKTEST_USE_SYNTHETIC", "false").lower() == "true"

    # 1) 종목 ID 조회
    stocks = await _resolve_stocks(db, codes)
    code_to_id = {s.code: s.id for s in stocks}

    out: dict[str, pd.DataFrame] = {}
    for code in codes:
        stock_id = code_to_id.get(code)
        if stock_id is None:
            if use_synthetic:
                out[code] = _synthetic_series(code, period_from, period_to)
            else:
                log.warning("backtest_data_loader_missing_stock", code=code)
            continue

        df = await _load_one(db, stock_id, period_from, period_to)
        if df.empty and use_synthetic:
            df = _synthetic_series(code, period_from, period_to)
        if not df.empty:
            out[code] = df

    if not out and use_synthetic:
        # 모든 코드가 누락된 극단적 fallback: 첫 코드로 합성
        if codes:
            out[codes[0]] = _synthetic_series(codes[0], period_from, period_to)

    return out


async def _resolve_stocks(db: AsyncSession, codes: list[str]) -> list[Stock]:
    if not codes:
        return []
    stmt = select(Stock).where(Stock.code.in_(codes))
    return list((await db.execute(stmt)).scalars().all())


async def _load_one(
    db: AsyncSession,
    stock_id: int,
    period_from: date,
    period_to: date,
) -> pd.DataFrame:
    stmt = (
        select(
            PriceDaily.trade_date,
            PriceDaily.open,
            PriceDaily.high,
            PriceDaily.low,
            PriceDaily.close,
            PriceDaily.volume,
        )
        .where(
            PriceDaily.stock_id == stock_id,
            PriceDaily.trade_date >= period_from,
            PriceDaily.trade_date <= period_to,
        )
        .order_by(PriceDaily.trade_date.asc())
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(
        rows, columns=["trade_date", "open", "high", "low", "close", "volume"]
    )
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.set_index("trade_date").sort_index()
    # Decimal -> float (백테스트 계산용)
    for col in ("open", "high", "low", "close"):
        df[col] = df[col].astype(float)
    df["volume"] = df["volume"].astype("int64")
    return df


def _synthetic_series(code: str, period_from: date, period_to: date) -> pd.DataFrame:
    """합성 OHLCV 생성 (개발/테스트 fallback).

    한국 평일(월~금)만 채우고 GBM 형태로 close 를 생성한다.
    """
    rng = np.random.default_rng(seed=abs(hash(code)) % (2**32))

    days: list[date] = []
    d = period_from
    while d <= period_to:
        if d.weekday() < 5:  # 평일만
            days.append(d)
        d += timedelta(days=1)
    if not days:
        return pd.DataFrame()

    n = len(days)
    # 시작가 5만원 ~ 10만원
    base = float(rng.integers(50_000, 100_000))
    drift = 0.0003
    vol = 0.018
    returns = rng.normal(loc=drift, scale=vol, size=n)
    close = base * np.exp(np.cumsum(returns))
    open_ = np.concatenate([[base], close[:-1]])
    high = np.maximum(open_, close) * (1 + np.abs(rng.normal(0, 0.005, n)))
    low = np.minimum(open_, close) * (1 - np.abs(rng.normal(0, 0.005, n)))
    volume = rng.integers(100_000, 5_000_000, size=n)

    df = pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
        },
        index=pd.to_datetime(days),
    )
    df.index.name = "trade_date"
    return df


def align_calendar(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """다종목 close 시리즈를 공통 거래일자 인덱스로 정렬한 DataFrame 반환.

    columns = 종목 코드. NaN 은 직전 값으로 forward fill 하지 않는다(상장 전/거래정지 구간 보존).
    """
    if not frames:
        return pd.DataFrame()
    closes = {code: df["close"] for code, df in frames.items()}
    aligned = pd.concat(closes, axis=1).sort_index()
    aligned.columns = list(frames.keys())
    return aligned


def to_decimal(value: float) -> Decimal:
    """float → Decimal 안전 변환 (DB 저장용)."""
    return Decimal(f"{value:.4f}")
