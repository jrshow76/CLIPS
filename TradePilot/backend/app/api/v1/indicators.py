"""지표 API 라우터.

`docs/13_api_requirements.md` §4 명세 구현.
기존 `IndicatorService`(BackendSenior 작성)의 정적 계산 메서드를 활용한다.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.response import success_response
from app.schemas.indicator import (
    BollingerSeriesOut,
    IndicatorBatchIn,
    IndicatorBatchOut,
    MacdSeriesOut,
    MaSeriesOut,
    RsiSeriesOut,
    SimpleSeriesOut,
    StochasticSeriesOut,
)
from app.services.indicator_service import IndicatorService, to_dataframe
from app.services.stock_service import StockService

router = APIRouter(prefix="/indicators", tags=["indicators"])


async def _candles(
    db: AsyncSession, code: str, interval: str, from_: str | None, to: str | None
) -> list[dict[str, Any]]:
    """지표 계산 입력용 봉 데이터 로드."""
    svc = StockService(db)
    return await svc.get_candles(code, interval=interval, from_=from_, to=to)


@router.get("/ma", summary="이동평균선")
async def ma(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    period: list[int] = Query([5, 20, 60, 120]),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    out = IndicatorService.ma(df, period)
    return success_response(
        MaSeriesOut(
            code=code,
            interval=interval,
            periods={str(p): vals for p, vals in out.items()},
        )
    )


@router.get("/rsi", summary="RSI")
async def rsi(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    period: int = Query(14, ge=2, le=50),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    values = IndicatorService.rsi(df, period)
    return success_response(
        RsiSeriesOut(code=code, interval=interval, period=period, values=values)
    )


@router.get("/macd", summary="MACD")
async def macd(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    fast: int = Query(12, ge=2, le=100),
    slow: int = Query(26, ge=2, le=200),
    signal: int = Query(9, ge=2, le=50),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    if fast >= slow:
        raise AppException("E0003", details={"fast": ["fast는 slow보다 작아야 합니다."]})
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    out = IndicatorService.macd(df, fast=fast, slow=slow, signal=signal)
    return success_response(
        MacdSeriesOut(
            code=code,
            interval=interval,
            macd=out["macd"],
            signal=out["signal"],
            hist=out["hist"],
        )
    )


@router.get("/bollinger", summary="볼린저 밴드")
async def bollinger(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    period: int = Query(20, ge=2, le=200),
    k: float = Query(2.0, gt=0, le=5),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    out = IndicatorService.bollinger(df, period=period, k=k)
    return success_response(
        BollingerSeriesOut(
            code=code,
            interval=interval,
            mid=out["mid"],
            upper=out["upper"],
            lower=out["lower"],
        )
    )


@router.get("/obv", summary="OBV")
async def obv(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    return success_response(
        SimpleSeriesOut(code=code, interval=interval, values=IndicatorService.obv(df))
    )


@router.get("/vwap", summary="VWAP")
async def vwap(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    return success_response(
        SimpleSeriesOut(code=code, interval=interval, values=IndicatorService.vwap(df))
    )


@router.get("/stochastic", summary="Stochastic")
async def stochastic(
    db: AsyncSession = Depends(get_db),
    code: str = Query(..., min_length=6, max_length=6),
    k: int = Query(14, ge=2, le=50),
    d: int = Query(3, ge=2, le=20),
    smooth: int = Query(3, ge=1, le=20),
    interval: str = Query("D"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    df = to_dataframe(await _candles(db, code, interval, from_, to))
    out = IndicatorService.stochastic(df, k_period=k, d_period=d, smooth=smooth)
    return success_response(
        StochasticSeriesOut(code=code, interval=interval, k=out["k"], d=out["d"])
    )


@router.post("/batch", summary="다중 지표 한번에 조회")
async def batch(
    payload: IndicatorBatchIn,
    db: AsyncSession = Depends(get_db),
):
    df = to_dataframe(await _candles(db, payload.code, payload.interval, payload.from_, payload.to))
    results: dict[str, Any] = {}
    for spec in payload.indicators:
        name = (spec.get("name") or "").lower()
        params = spec.get("params") or {}
        try:
            if name == "ma":
                periods = params.get("periods") or [5, 20, 60]
                out = IndicatorService.ma(df, periods)
                results["ma"] = {str(p): v for p, v in out.items()}
            elif name == "rsi":
                results["rsi"] = IndicatorService.rsi(df, int(params.get("period", 14)))
            elif name == "macd":
                results["macd"] = IndicatorService.macd(
                    df,
                    fast=int(params.get("fast", 12)),
                    slow=int(params.get("slow", 26)),
                    signal=int(params.get("signal", 9)),
                )
            elif name == "bollinger":
                results["bollinger"] = IndicatorService.bollinger(
                    df,
                    period=int(params.get("period", 20)),
                    k=float(params.get("k", 2.0)),
                )
            elif name == "obv":
                results["obv"] = IndicatorService.obv(df)
            elif name == "vwap":
                results["vwap"] = IndicatorService.vwap(df)
            elif name == "stochastic":
                results["stochastic"] = IndicatorService.stochastic(
                    df,
                    k_period=int(params.get("k", 14)),
                    d_period=int(params.get("d", 3)),
                    smooth=int(params.get("smooth", 3)),
                )
            elif name == "atr":
                results["atr"] = IndicatorService.atr(df, int(params.get("period", 14)))
            else:
                results[name or "unknown"] = {"error": "unsupported_indicator"}
        except Exception as e:  # pragma: no cover
            results[name or "unknown"] = {"error": str(e)}
    return success_response(
        IndicatorBatchOut(code=payload.code, interval=payload.interval, results=results)
    )
