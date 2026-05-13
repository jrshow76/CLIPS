"""적재 전 데이터 검증.

DB 제약(check constraint)에서도 한 번 더 검증되지만,
대량 적재 시 잘못된 1건이 트랜잭션 전체를 롤백시키지 않도록
사전 필터링을 수행한다.

검증 정책:
- 가격(open/high/low/close): 0 이상
- OHLC 관계: low ≤ open,close ≤ high
- 거래량/거래대금: 0 이상
- 같은 PK(code+date 또는 code+ts+interval) 중복 → 마지막 값 유지
"""
from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Iterable

import structlog

from app.services.data_ingestion.sources.base import DailyBar, IndexBar, MinuteBar

log = structlog.get_logger(__name__)


_ZERO = Decimal("0")


class ValidationError(Exception):
    """단건 검증 실패 (배치 전체는 계속 진행)."""


# ---------------------------------------------------------------------------
# 단건 검증
# ---------------------------------------------------------------------------
def _validate_ohlc(
    open_: Decimal, high: Decimal, low: Decimal, close: Decimal
) -> None:
    """OHLC 관계 검증."""
    if any(v < _ZERO for v in (open_, high, low, close)):
        raise ValidationError(f"음수 가격: o={open_} h={high} l={low} c={close}")
    if low > open_ or low > close or high < open_ or high < close:
        raise ValidationError(
            f"OHLC 관계 위반: o={open_} h={high} l={low} c={close}"
        )


def validate_daily(bar: DailyBar) -> DailyBar:
    """일봉 1건 검증. 실패 시 ValidationError."""
    _validate_ohlc(bar.open, bar.high, bar.low, bar.close)
    if bar.volume < 0:
        raise ValidationError(f"음수 거래량: {bar.volume}")
    if bar.volume_amount < _ZERO:
        raise ValidationError(f"음수 거래대금: {bar.volume_amount}")
    return bar


def validate_minute(bar: MinuteBar) -> MinuteBar:
    """분봉 1건 검증."""
    _validate_ohlc(bar.open, bar.high, bar.low, bar.close)
    if bar.volume < 0:
        raise ValidationError(f"음수 거래량: {bar.volume}")
    if bar.interval_min not in (1, 5, 15, 30):
        raise ValidationError(f"허용되지 않은 interval: {bar.interval_min}")
    if bar.ts.tzinfo is None:
        raise ValidationError("분봉 ts는 timezone-aware 여야 합니다")
    return bar


def validate_index(bar: IndexBar) -> IndexBar:
    """지수 1건 검증."""
    _validate_ohlc(bar.open, bar.high, bar.low, bar.close)
    if bar.volume < 0:
        raise ValidationError(f"음수 거래량: {bar.volume}")
    return bar


# ---------------------------------------------------------------------------
# 배치 필터링 + 중복 제거
# ---------------------------------------------------------------------------
def filter_valid_daily(bars: Iterable[DailyBar]) -> tuple[list[DailyBar], int]:
    """일봉 배치 필터링.

    Returns:
        (유효한 bars, 제외된 건수)
    """
    seen: dict[tuple[str, ], DailyBar] = {}
    invalid = 0
    for b in bars:
        try:
            validate_daily(b)
        except ValidationError as e:
            invalid += 1
            log.debug("invalid_daily_bar", code=b.code, date=str(b.trade_date), reason=str(e))
            continue
        # 중복은 마지막 값으로 덮어쓰기 (UPSERT 의미와 일치)
        key = (b.code, b.trade_date)  # type: ignore[assignment]
        seen[key] = b  # type: ignore[index]
    return list(seen.values()), invalid


def filter_valid_minute(bars: Iterable[MinuteBar]) -> tuple[list[MinuteBar], int]:
    """분봉 배치 필터링."""
    seen: dict[tuple, MinuteBar] = {}
    invalid = 0
    for b in bars:
        try:
            validate_minute(b)
        except ValidationError as e:
            invalid += 1
            log.debug("invalid_minute_bar", code=b.code, ts=str(b.ts), reason=str(e))
            continue
        key = (b.code, b.ts, b.interval_min)
        seen[key] = b
    return list(seen.values()), invalid


def filter_valid_index(bars: Iterable[IndexBar]) -> tuple[list[IndexBar], int]:
    """지수 배치 필터링."""
    seen: dict[tuple, IndexBar] = {}
    invalid = 0
    for b in bars:
        try:
            validate_index(b)
        except ValidationError as e:
            invalid += 1
            log.debug(
                "invalid_index_bar", code=b.code, date=str(b.trade_date), reason=str(e)
            )
            continue
        key = (b.code, b.trade_date)
        seen[key] = b
    return list(seen.values()), invalid


def summarize(bar: DailyBar | MinuteBar | IndexBar) -> dict:
    """디버깅용 dict 변환."""
    return {k: str(v) for k, v in asdict(bar).items()}
