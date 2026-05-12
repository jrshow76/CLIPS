"""추천주 점수 산정 서비스.

점수 산정 알고리즘 (v1.0 단순화):
- 기술적 점수: RSI(과매도 가산), MACD 양전환, MA 정배열
- 모멘텀 점수: 최근 5일 수익률
- 거래대금 점수: 60일 평균 대비 비율
- 변동성 페널티: ATR 너무 클 경우 감점

총점 0~100 범위. 룰 결합은 가중 평균.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any

import numpy as np
import pandas as pd
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Recommendation
from app.services.indicator_service import IndicatorService

log = structlog.get_logger(__name__)


# 가중치 (합계 1.0)
WEIGHTS: dict[str, float] = {
    "technical": 0.40,
    "momentum": 0.30,
    "volume": 0.20,
    "volatility": 0.10,
}


class RecommendationService:
    """추천 점수 산정."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def compute_score(self, df: pd.DataFrame) -> tuple[float, dict[str, Any]]:
        """OHLCV → (총점 0~100, features 딕셔너리)."""
        if df.empty or len(df) < 20:
            return 0.0, {"reason": "insufficient_data"}

        features: dict[str, Any] = {}

        # 1) 기술적 점수
        rsi = IndicatorService.rsi(df, 14)
        rsi_last = rsi[-1] if rsi and rsi[-1] is not None else 50
        macd = IndicatorService.macd(df)
        macd_last = macd["macd"][-1] or 0
        macd_signal_last = macd["signal"][-1] or 0

        ma5 = df["close"].rolling(window=5, min_periods=1).mean().iloc[-1]
        ma20 = df["close"].rolling(window=20, min_periods=1).mean().iloc[-1]
        ma60 = df["close"].rolling(window=60, min_periods=1).mean().iloc[-1]

        technical_score = 0.0
        # RSI: 과매도 가산
        if rsi_last <= 30:
            technical_score += 35
        elif rsi_last <= 45:
            technical_score += 20
        elif rsi_last >= 70:
            technical_score -= 20  # 과매수 감점

        # MACD: 양전환 시 가점
        if macd_last > macd_signal_last and macd_last > 0:
            technical_score += 25

        # MA 정배열 (단기>중기>장기)
        if ma5 > ma20 > ma60:
            technical_score += 40
        elif ma5 > ma20:
            technical_score += 20

        technical_score = max(0, min(100, technical_score))
        features["technical"] = technical_score

        # 2) 모멘텀 점수 - 최근 5일 수익률
        recent_return = (df["close"].iloc[-1] / df["close"].iloc[-min(5, len(df) - 1)] - 1) * 100
        # -10% ~ +10% → 0 ~ 100 매핑
        momentum_score = max(0, min(100, (float(recent_return) + 10) * 5))
        features["momentum"] = momentum_score
        features["recent_return_pct"] = float(recent_return)

        # 3) 거래대금 점수
        if "volume" in df.columns:
            recent_vol = float(df["volume"].iloc[-1])
            avg_vol = float(df["volume"].rolling(window=min(60, len(df))).mean().iloc[-1])
            ratio = (recent_vol / avg_vol) if avg_vol else 1.0
            volume_score = min(100.0, ratio * 50)  # 평균의 2배면 100점
            features["volume_ratio"] = ratio
        else:
            volume_score = 50.0
        features["volume"] = volume_score

        # 4) 변동성 페널티 (ATR 기반)
        atr = IndicatorService.atr(df, 14)
        atr_last = atr[-1] if atr and atr[-1] is not None else 0
        price_last = float(df["close"].iloc[-1])
        atr_pct = (atr_last / price_last) * 100 if price_last else 0
        # 변동성 작을수록 좋음 (역점수): 0~5% → 100~0
        volatility_score = max(0, min(100, 100 - atr_pct * 20))
        features["volatility"] = volatility_score
        features["atr_pct"] = atr_pct

        # 가중 평균
        total = (
            technical_score * WEIGHTS["technical"]
            + momentum_score * WEIGHTS["momentum"]
            + volume_score * WEIGHTS["volume"]
            + volatility_score * WEIGHTS["volatility"]
        )
        return round(total, 2), features

    def explain(self, features: dict[str, Any]) -> tuple[str, str]:
        """점수 사유 텍스트.

        반환: (reason_code, reason_text)
        """
        rec_return = features.get("recent_return_pct", 0)
        if features.get("technical", 0) >= 70 and rec_return > 0:
            return ("STRONG_TECHNICAL_UPTREND", "기술적 강세 + 양호한 모멘텀")
        if features.get("technical", 0) >= 60:
            return ("BULLISH_TECHNICAL", "기술적 매수 신호 발생")
        if features.get("momentum", 0) >= 70:
            return ("STRONG_MOMENTUM", "최근 강한 상승 모멘텀")
        if features.get("volume", 0) >= 70:
            return ("VOLUME_SURGE", "평균 대비 거래 급증")
        return ("NEUTRAL", "일반적 점수 수준")

    async def save_recommendation(
        self,
        *,
        stock_id: int,
        strategy_id: int | None,
        trade_date: date,
        score: float,
        features: dict[str, Any],
    ) -> Recommendation:
        code, text = self.explain(features)
        reco = Recommendation(
            stock_id=stock_id,
            strategy_id=strategy_id,
            trade_date=trade_date,
            score=Decimal(str(score)),
            reason_code=code,
            reason_text=text,
            features=features,
        )
        self.db.add(reco)
        await self.db.flush()
        return reco
