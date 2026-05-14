"""매매 시그널 서비스.

룰 기반 시그널 산출:
- 골든크로스 (MA5 > MA20 + 직전 봉 반전)
- 데드크로스
- RSI 과매수(70 이상) / 과매도(30 이하)
- MACD 시그널 교차
- 볼린저 밴드 하단 터치(매수) / 상단 터치(매도)

DSL 평가는 `app.domains.rules.evaluator` 로 확장 예정. v1.0은 단순 룰셋 위주.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

import pandas as pd
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Signal
from app.services.indicator_service import IndicatorService

log = structlog.get_logger(__name__)


# 룰 코드
SIGNAL_GOLDEN_CROSS = "GOLDEN_CROSS"
SIGNAL_DEAD_CROSS = "DEAD_CROSS"
SIGNAL_RSI_OVERSOLD = "RSI_OVERSOLD"
SIGNAL_RSI_OVERBOUGHT = "RSI_OVERBOUGHT"
SIGNAL_MACD_BULL = "MACD_BULL"
SIGNAL_MACD_BEAR = "MACD_BEAR"
SIGNAL_BB_LOWER_TOUCH = "BB_LOWER_TOUCH"
SIGNAL_BB_UPPER_TOUCH = "BB_UPPER_TOUCH"


class SignalService:
    """시그널 생성 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    def evaluate_rules(self, df: pd.DataFrame) -> list[dict[str, Any]]:
        """주어진 OHLCV DataFrame을 평가하여 시그널 후보 리스트를 반환한다.

        반환: [{action: BUY|SELL, code: RULE, confidence: HIGH|MID|LOW, trace: {...}}, ...]
        """
        if df.empty or len(df) < 30:
            return []

        signals: list[dict[str, Any]] = []

        # MA 교차
        ma5 = df["close"].rolling(window=5, min_periods=1).mean()
        ma20 = df["close"].rolling(window=20, min_periods=1).mean()
        if len(ma5) >= 2 and len(ma20) >= 2:
            if ma5.iloc[-2] <= ma20.iloc[-2] and ma5.iloc[-1] > ma20.iloc[-1]:
                signals.append({
                    "action": "BUY",
                    "code": SIGNAL_GOLDEN_CROSS,
                    "confidence": "HIGH",
                    "trace": {"ma5": float(ma5.iloc[-1]), "ma20": float(ma20.iloc[-1])},
                })
            elif ma5.iloc[-2] >= ma20.iloc[-2] and ma5.iloc[-1] < ma20.iloc[-1]:
                signals.append({
                    "action": "SELL",
                    "code": SIGNAL_DEAD_CROSS,
                    "confidence": "HIGH",
                    "trace": {"ma5": float(ma5.iloc[-1]), "ma20": float(ma20.iloc[-1])},
                })

        # RSI
        rsi_values = IndicatorService.rsi(df, 14)
        if rsi_values and rsi_values[-1] is not None:
            rsi_last = rsi_values[-1]
            if rsi_last <= 30:
                signals.append({
                    "action": "BUY",
                    "code": SIGNAL_RSI_OVERSOLD,
                    "confidence": "MID",
                    "trace": {"rsi14": rsi_last},
                })
            elif rsi_last >= 70:
                signals.append({
                    "action": "SELL",
                    "code": SIGNAL_RSI_OVERBOUGHT,
                    "confidence": "MID",
                    "trace": {"rsi14": rsi_last},
                })

        # MACD
        macd = IndicatorService.macd(df)
        m, s = macd["macd"], macd["signal"]
        if (
            len(m) >= 2 and len(s) >= 2
            and m[-2] is not None and s[-2] is not None
            and m[-1] is not None and s[-1] is not None
        ):
            if m[-2] <= s[-2] and m[-1] > s[-1]:
                signals.append({
                    "action": "BUY",
                    "code": SIGNAL_MACD_BULL,
                    "confidence": "MID",
                    "trace": {"macd": m[-1], "signal": s[-1]},
                })
            elif m[-2] >= s[-2] and m[-1] < s[-1]:
                signals.append({
                    "action": "SELL",
                    "code": SIGNAL_MACD_BEAR,
                    "confidence": "MID",
                    "trace": {"macd": m[-1], "signal": s[-1]},
                })

        # 볼린저 밴드
        bb = IndicatorService.bollinger(df)
        close_last = float(df["close"].iloc[-1])
        if bb["lower"] and bb["lower"][-1] is not None and close_last <= bb["lower"][-1]:
            signals.append({
                "action": "BUY",
                "code": SIGNAL_BB_LOWER_TOUCH,
                "confidence": "LOW",
                "trace": {"close": close_last, "bb_lower": bb["lower"][-1]},
            })
        if bb["upper"] and bb["upper"][-1] is not None and close_last >= bb["upper"][-1]:
            signals.append({
                "action": "SELL",
                "code": SIGNAL_BB_UPPER_TOUCH,
                "confidence": "LOW",
                "trace": {"close": close_last, "bb_upper": bb["upper"][-1]},
            })

        return signals

    async def persist_signal(
        self,
        *,
        user_id: int,
        strategy_id: int,
        stock_id: int,
        action: str,
        confidence: str,
        trigger_price: Decimal,
        condition_trace: dict[str, Any],
    ) -> Signal:
        """시그널을 DB에 저장하고 알림 발송 트리거."""
        sig = Signal(
            user_id=user_id,
            strategy_id=strategy_id,
            stock_id=stock_id,
            action=action,
            confidence=confidence,
            trigger_price=trigger_price,
            status="ACTIVE",
            condition_trace=condition_trace,
            generated_at=datetime.now(tz=timezone.utc),
        )
        self.db.add(sig)
        await self.db.flush()

        # 알림 발송 (실패해도 시그널 저장은 유지)
        try:
            from app.models.market import Stock as _Stock
            from app.models.trade import Strategy as _Strategy
            from app.models.user import User as _User
            from app.services.notification_service import NotificationService

            user = await self.db.get(_User, user_id)
            stock = await self.db.get(_Stock, stock_id)
            strategy = await self.db.get(_Strategy, strategy_id)
            if user is not None and stock is not None:
                await NotificationService(self.db).send_signal_alert(
                    user=user,
                    stock_code=stock.code,
                    stock_name=stock.name,
                    action=action,
                    rule_code=str(condition_trace.get("code", condition_trace.get("rule_code", ""))),
                    confidence=confidence,
                    trigger_price=str(trigger_price),
                    strategy_name=strategy.name if strategy else "사용자 전략",
                )
        except Exception as _e:  # noqa: BLE001
            log.warning("signal_notify_failed", user_id=user_id, error=str(_e)[:200])
        return sig
