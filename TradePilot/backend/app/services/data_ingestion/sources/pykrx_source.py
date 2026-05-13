"""pykrx 기반 KRX 데이터 어댑터.

pykrx는 동기 라이브러리이므로 asyncio 환경에서는 `run_in_executor`로 감싼다.
또한 호출 실패 시 지수 백오프 재시도를 수행한다 (config.max_retries 기준).

테스트/로컬 환경(pykrx 미설치)에서는 deterministic 합성 데이터를 반환한다.
"""
from __future__ import annotations

import asyncio
import functools
import os
import random
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from app.services.data_ingestion.config import (
    INDEX_CODE_MAP,
    IngestionConfig,
    default_config,
)
from app.services.data_ingestion.sources.base import (
    DailyBar,
    IndexBar,
    MarketDataSource,
    MinuteBar,
    StockMasterRow,
    StockSectorRow,
)

log = structlog.get_logger(__name__)

_KST = ZoneInfo("Asia/Seoul")


def _is_pykrx_available() -> bool:
    """pykrx import 가능 여부 (지연 import)."""
    try:
        import pykrx.stock  # noqa: F401

        return True
    except Exception:  # noqa: BLE001 - import error 모두 흡수
        return False


def _force_synthetic() -> bool:
    """환경변수로 강제 합성 데이터 모드.

    - INGEST_USE_SYNTHETIC=true 일 때 항상 합성 데이터 반환 (테스트/CI 용).
    """
    return os.getenv("INGEST_USE_SYNTHETIC", "false").lower() == "true"


def _ymd(d: date) -> str:
    """pykrx가 요구하는 YYYYMMDD 문자열."""
    return d.strftime("%Y%m%d")


# ---------------------------------------------------------------------------
# 재시도 데코레이터 (지수 백오프)
# ---------------------------------------------------------------------------
async def _retry_async(
    func: Any,
    *args: Any,
    config: IngestionConfig,
    op_name: str,
    **kwargs: Any,
) -> Any:
    """지수 백오프 재시도 (최대 max_retries회).

    동기 함수를 executor에서 실행하며, 예외 발생 시 backoff 후 재시도한다.
    """
    loop = asyncio.get_event_loop()
    last_exc: Exception | None = None
    for attempt in range(config.max_retries + 1):
        try:
            partial = functools.partial(func, *args, **kwargs)
            return await loop.run_in_executor(None, partial)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt >= config.max_retries:
                break
            backoff = min(
                config.retry_backoff_base ** attempt + random.random(),
                config.retry_backoff_max,
            )
            log.warning(
                "pykrx_retry",
                op=op_name,
                attempt=attempt + 1,
                error=str(exc)[:200],
                backoff=backoff,
            )
            await asyncio.sleep(backoff)
    assert last_exc is not None
    log.error("pykrx_failed", op=op_name, error=str(last_exc)[:200])
    raise last_exc


# ---------------------------------------------------------------------------
# pykrx 어댑터
# ---------------------------------------------------------------------------
class PyKrxSource(MarketDataSource):
    """KRX 공식 데이터 어댑터 (pykrx 기반)."""

    name = "pykrx"

    def __init__(self, config: IngestionConfig | None = None) -> None:
        self.config = config or default_config
        self._available = _is_pykrx_available() and not _force_synthetic()

    # ------------------------------------------------------------------
    # 종목 마스터
    # ------------------------------------------------------------------
    async def fetch_stock_master(self, target_date: date | None = None) -> list[StockMasterRow]:
        """KOSPI + KOSDAQ 종목 마스터 조회."""
        target_date = target_date or _last_business_day()

        if not self._available:
            log.warning("pykrx_unavailable_synthetic_master")
            return _synthetic_master()

        from pykrx import stock as krx_stock

        rows: list[StockMasterRow] = []
        for market in ("KOSPI", "KOSDAQ"):
            tickers = await _retry_async(
                krx_stock.get_market_ticker_list,
                _ymd(target_date),
                market=market,
                config=self.config,
                op_name=f"get_market_ticker_list:{market}",
            )
            await asyncio.sleep(self.config.rate_limit_sleep_sec)

            # 시가총액/상장주식수 일괄 조회 (DataFrame)
            try:
                cap_df = await _retry_async(
                    krx_stock.get_market_cap_by_ticker,
                    _ymd(target_date),
                    market=market,
                    config=self.config,
                    op_name=f"get_market_cap:{market}",
                )
            except Exception:
                cap_df = None
            await asyncio.sleep(self.config.rate_limit_sleep_sec)

            for code in tickers:
                name = await _retry_async(
                    krx_stock.get_market_ticker_name,
                    code,
                    config=self.config,
                    op_name=f"get_market_ticker_name:{code}",
                )
                listing_shares: int | None = None
                market_cap: int | None = None
                if cap_df is not None and code in cap_df.index:
                    row = cap_df.loc[code]
                    listing_shares = int(row.get("상장주식수") or 0) or None
                    market_cap = int(row.get("시가총액") or 0) or None
                rows.append(
                    StockMasterRow(
                        code=str(code),
                        name=str(name),
                        market=market,
                        listing_shares=listing_shares,
                        market_cap=market_cap,
                    )
                )
        log.info("pykrx_stock_master_fetched", count=len(rows), date=str(target_date))
        return rows

    # ------------------------------------------------------------------
    # 섹터 (업종)
    # ------------------------------------------------------------------
    async def fetch_sectors(self, target_date: date | None = None) -> list[StockSectorRow]:
        """업종별 구성 종목 매핑.

        pykrx의 get_index_portfolio_deposit_file()를 활용.
        업종 코드 = KRX 업종지수 코드 (KOSPI: 1xxx, KOSDAQ: 2xxx).
        """
        target_date = target_date or _last_business_day()

        if not self._available:
            log.warning("pykrx_unavailable_synthetic_sectors")
            return _synthetic_sectors()

        from pykrx import stock as krx_stock

        rows: list[StockSectorRow] = []
        # KRX 업종지수 코드 + 이름 (대표 업종만; 전체는 운영 시 확장)
        sector_universe = await _retry_async(
            krx_stock.get_index_ticker_list,
            _ymd(target_date),
            market="KOSPI",
            config=self.config,
            op_name="get_index_ticker_list:KOSPI",
        )
        await asyncio.sleep(self.config.rate_limit_sleep_sec)
        sector_universe_kosdaq = await _retry_async(
            krx_stock.get_index_ticker_list,
            _ymd(target_date),
            market="KOSDAQ",
            config=self.config,
            op_name="get_index_ticker_list:KOSDAQ",
        )
        sector_universe_all = list(sector_universe) + list(sector_universe_kosdaq)
        await asyncio.sleep(self.config.rate_limit_sleep_sec)

        for sector_code in sector_universe_all:
            try:
                sector_name = await _retry_async(
                    krx_stock.get_index_ticker_name,
                    sector_code,
                    config=self.config,
                    op_name=f"get_index_ticker_name:{sector_code}",
                )
                stock_codes = await _retry_async(
                    krx_stock.get_index_portfolio_deposit_file,
                    sector_code,
                    _ymd(target_date),
                    config=self.config,
                    op_name=f"get_index_portfolio_deposit:{sector_code}",
                )
            except Exception as e:  # noqa: BLE001
                log.warning("pykrx_sector_skip", sector=sector_code, error=str(e)[:100])
                continue
            for code in stock_codes:
                rows.append(
                    StockSectorRow(
                        stock_code=str(code),
                        sector_code=str(sector_code),
                        sector_name=str(sector_name),
                        is_primary=True,
                    )
                )
            await asyncio.sleep(self.config.rate_limit_sleep_sec)

        log.info("pykrx_sectors_fetched", count=len(rows), date=str(target_date))
        return rows

    # ------------------------------------------------------------------
    # 일봉
    # ------------------------------------------------------------------
    async def fetch_daily(
        self,
        code: str,
        from_date: date,
        to_date: date,
    ) -> list[DailyBar]:
        """단일 종목 일봉 OHLCV 조회 (KRX)."""
        if not self._available:
            return _synthetic_daily(code, from_date, to_date)

        from pykrx import stock as krx_stock

        df = await _retry_async(
            krx_stock.get_market_ohlcv_by_date,
            _ymd(from_date),
            _ymd(to_date),
            code,
            config=self.config,
            op_name=f"get_market_ohlcv:{code}",
        )
        await asyncio.sleep(self.config.rate_limit_sleep_sec)

        bars: list[DailyBar] = []
        if df is None or df.empty:
            return bars

        # pykrx 컬럼: 시가/고가/저가/종가/거래량/거래대금/등락률
        for idx, row in df.iterrows():
            try:
                trade_date = _to_date(idx)
                open_ = Decimal(str(row.get("시가", 0)))
                high = Decimal(str(row.get("고가", 0)))
                low = Decimal(str(row.get("저가", 0)))
                close = Decimal(str(row.get("종가", 0)))
                volume = int(row.get("거래량", 0) or 0)
                volume_amount = Decimal(str(row.get("거래대금", 0) or 0))
                change_pct_raw = row.get("등락률")
                change_pct = (
                    Decimal(str(change_pct_raw)) if change_pct_raw is not None else None
                )
                bars.append(
                    DailyBar(
                        code=code,
                        trade_date=trade_date,
                        open=open_,
                        high=high,
                        low=low,
                        close=close,
                        volume=volume,
                        volume_amount=volume_amount,
                        change_pct=change_pct,
                    )
                )
            except Exception as e:  # noqa: BLE001
                log.warning("pykrx_daily_row_skip", code=code, error=str(e)[:100])
                continue
        return bars

    # ------------------------------------------------------------------
    # 지수
    # ------------------------------------------------------------------
    async def fetch_index(
        self,
        index_code: str,
        from_date: date,
        to_date: date,
    ) -> list[IndexBar]:
        """지수 일봉 조회.

        index_code: KOSPI/KOSDAQ/KOSPI200 (config.INDEX_CODE_MAP 키)
        """
        meta = INDEX_CODE_MAP.get(index_code.upper())
        if not meta:
            log.warning("unknown_index_code", code=index_code)
            return []

        if not self._available:
            return _synthetic_index(index_code, from_date, to_date)

        from pykrx import stock as krx_stock

        df = await _retry_async(
            krx_stock.get_index_ohlcv_by_date,
            _ymd(from_date),
            _ymd(to_date),
            meta["krx_code"],
            config=self.config,
            op_name=f"get_index_ohlcv:{index_code}",
        )
        await asyncio.sleep(self.config.rate_limit_sleep_sec)

        bars: list[IndexBar] = []
        if df is None or df.empty:
            return bars
        for idx, row in df.iterrows():
            try:
                trade_date = _to_date(idx)
                bars.append(
                    IndexBar(
                        code=index_code.upper(),
                        trade_date=trade_date,
                        open=Decimal(str(row.get("시가", 0))),
                        high=Decimal(str(row.get("고가", 0))),
                        low=Decimal(str(row.get("저가", 0))),
                        close=Decimal(str(row.get("종가", 0))),
                        volume=int(row.get("거래량", 0) or 0),
                        change_pct=(
                            Decimal(str(row.get("등락률")))
                            if row.get("등락률") is not None
                            else None
                        ),
                    )
                )
            except Exception as e:  # noqa: BLE001
                log.warning("pykrx_index_row_skip", code=index_code, error=str(e)[:100])
        return bars


# ---------------------------------------------------------------------------
# 보조 함수
# ---------------------------------------------------------------------------
def _to_date(idx: Any) -> date:
    """pykrx의 인덱스(Timestamp/문자열)를 date로 변환."""
    if isinstance(idx, date) and not isinstance(idx, datetime):
        return idx
    if isinstance(idx, datetime):
        return idx.date()
    # pandas Timestamp
    if hasattr(idx, "to_pydatetime"):
        return idx.to_pydatetime().date()
    if isinstance(idx, str):
        return datetime.strptime(idx[:10].replace("-", ""), "%Y%m%d").date()
    raise ValueError(f"unsupported index type: {type(idx)}")


def _last_business_day(reference: date | None = None) -> date:
    """직전 영업일 추정 (단순: 주말 제외).

    실제 휴장일 처리는 calendar_service 연동 시점에 강화한다.
    """
    d = reference or datetime.now(tz=_KST).date()
    while d.weekday() >= 5:  # 5=Sat, 6=Sun
        d -= timedelta(days=1)
    return d


# ---------------------------------------------------------------------------
# 합성 데이터 (pykrx 미가용 / 테스트 환경)
# ---------------------------------------------------------------------------
def _synthetic_master() -> list[StockMasterRow]:
    """테스트용 합성 종목 마스터 (10종목)."""
    samples = [
        ("005930", "삼성전자", "KOSPI"),
        ("000660", "SK하이닉스", "KOSPI"),
        ("035420", "NAVER", "KOSPI"),
        ("035720", "카카오", "KOSPI"),
        ("051910", "LG화학", "KOSPI"),
        ("005380", "현대차", "KOSPI"),
        ("207940", "삼성바이오로직스", "KOSPI"),
        ("068270", "셀트리온", "KOSPI"),
        ("247540", "에코프로비엠", "KOSDAQ"),
        ("086520", "에코프로", "KOSDAQ"),
    ]
    return [
        StockMasterRow(
            code=c, name=n, market=m, listing_shares=1_000_000, market_cap=10_000_000_000
        )
        for c, n, m in samples
    ]


def _synthetic_sectors() -> list[StockSectorRow]:
    """테스트용 합성 섹터 매핑."""
    return [
        StockSectorRow("005930", "G45", "전기전자", True),
        StockSectorRow("000660", "G45", "전기전자", True),
        StockSectorRow("035420", "G50", "서비스업", True),
        StockSectorRow("035720", "G50", "서비스업", True),
        StockSectorRow("051910", "G15", "화학", True),
        StockSectorRow("005380", "G25", "운수장비", True),
        StockSectorRow("207940", "G35", "의약품", True),
        StockSectorRow("068270", "G35", "의약품", True),
    ]


def _synthetic_daily(code: str, from_date: date, to_date: date) -> list[DailyBar]:
    """테스트용 합성 일봉 (deterministic seed: code 해시)."""
    rng = random.Random(abs(hash(code)) % (2**32))
    bars: list[DailyBar] = []
    base_price = float(rng.randint(50_000, 100_000))
    d = from_date
    prev_close = base_price
    while d <= to_date:
        if d.weekday() < 5:  # 평일만
            ret = rng.gauss(0.0003, 0.018)
            close = max(prev_close * (1 + ret), 100.0)
            open_ = prev_close
            high = max(open_, close) * (1 + abs(rng.gauss(0, 0.005)))
            low = min(open_, close) * (1 - abs(rng.gauss(0, 0.005)))
            volume = rng.randint(100_000, 5_000_000)
            bars.append(
                DailyBar(
                    code=code,
                    trade_date=d,
                    open=Decimal(f"{open_:.2f}"),
                    high=Decimal(f"{high:.2f}"),
                    low=Decimal(f"{low:.2f}"),
                    close=Decimal(f"{close:.2f}"),
                    volume=volume,
                    volume_amount=Decimal(f"{close * volume:.2f}"),
                    change_pct=Decimal(f"{ret * 100:.4f}"),
                )
            )
            prev_close = close
        d += timedelta(days=1)
    return bars


def _synthetic_index(code: str, from_date: date, to_date: date) -> list[IndexBar]:
    """테스트용 합성 지수 일봉."""
    rng = random.Random(abs(hash(f"index:{code}")) % (2**32))
    bars: list[IndexBar] = []
    base = {"KOSPI": 2700.0, "KOSDAQ": 850.0, "KOSPI200": 360.0}.get(code.upper(), 1000.0)
    d = from_date
    prev_close = base
    while d <= to_date:
        if d.weekday() < 5:
            ret = rng.gauss(0.0002, 0.010)
            close = max(prev_close * (1 + ret), 100.0)
            open_ = prev_close
            high = max(open_, close) * (1 + abs(rng.gauss(0, 0.003)))
            low = min(open_, close) * (1 - abs(rng.gauss(0, 0.003)))
            bars.append(
                IndexBar(
                    code=code.upper(),
                    trade_date=d,
                    open=Decimal(f"{open_:.4f}"),
                    high=Decimal(f"{high:.4f}"),
                    low=Decimal(f"{low:.4f}"),
                    close=Decimal(f"{close:.4f}"),
                    volume=rng.randint(100_000_000, 1_000_000_000),
                    change_pct=Decimal(f"{ret * 100:.4f}"),
                )
            )
            prev_close = close
        d += timedelta(days=1)
    return bars
