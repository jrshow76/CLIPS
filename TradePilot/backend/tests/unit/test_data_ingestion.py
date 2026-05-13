"""data_ingestion 패키지 단위 테스트.

DB 의존성 없이 검증 가능한 항목:
- validator: 가격/거래량/OHLC/중복 검증
- partitioner: DDL SQL 정확성
- pykrx_source: 합성 데이터 모드(INGEST_USE_SYNTHETIC=true) 동작
- loaders: AsyncMock으로 SQL 페이로드 검증
"""
from __future__ import annotations

import os
from datetime import date, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest

# 합성 데이터 모드 강제 (테스트 환경)
os.environ["INGEST_USE_SYNTHETIC"] = "true"

from app.services.data_ingestion.config import IngestionConfig, default_config
from app.services.data_ingestion.partitioner import (
    build_partition_ddl,
    build_partition_index_ddl,
)
from app.services.data_ingestion.sources.base import (
    DailyBar,
    IndexBar,
    MinuteBar,
    StockMasterRow,
)
from app.services.data_ingestion.sources.pykrx_source import PyKrxSource
from app.services.data_ingestion.validator import (
    ValidationError,
    filter_valid_daily,
    filter_valid_index,
    filter_valid_minute,
    validate_daily,
    validate_index,
    validate_minute,
)


_KST = ZoneInfo("Asia/Seoul")


# ===========================================================================
# Validator
# ===========================================================================
class TestValidator:
    """가격 검증 단위 테스트."""

    @pytest.mark.unit
    def test_valid_daily_passes(self) -> None:
        bar = DailyBar(
            code="005930",
            trade_date=date(2026, 5, 13),
            open=Decimal("70000"),
            high=Decimal("71000"),
            low=Decimal("69000"),
            close=Decimal("70500"),
            volume=1_000_000,
            volume_amount=Decimal("70500000000"),
        )
        assert validate_daily(bar) is bar

    @pytest.mark.unit
    def test_negative_price_rejected(self) -> None:
        bar = DailyBar(
            code="005930",
            trade_date=date(2026, 5, 13),
            open=Decimal("-1"),
            high=Decimal("71000"),
            low=Decimal("69000"),
            close=Decimal("70500"),
        )
        with pytest.raises(ValidationError):
            validate_daily(bar)

    @pytest.mark.unit
    def test_ohlc_violation_rejected(self) -> None:
        # high < close 위반
        bar = DailyBar(
            code="005930",
            trade_date=date(2026, 5, 13),
            open=Decimal("70000"),
            high=Decimal("70100"),  # close보다 작음
            low=Decimal("69000"),
            close=Decimal("70500"),
        )
        with pytest.raises(ValidationError):
            validate_daily(bar)

    @pytest.mark.unit
    def test_negative_volume_rejected(self) -> None:
        bar = DailyBar(
            code="005930",
            trade_date=date(2026, 5, 13),
            open=Decimal("70000"),
            high=Decimal("71000"),
            low=Decimal("69000"),
            close=Decimal("70500"),
            volume=-1,
        )
        with pytest.raises(ValidationError):
            validate_daily(bar)

    @pytest.mark.unit
    def test_minute_requires_tz_aware(self) -> None:
        bar = MinuteBar(
            code="005930",
            ts=datetime(2026, 5, 13, 10, 0, 0),  # naive
            interval_min=1,
            open=Decimal("70000"),
            high=Decimal("71000"),
            low=Decimal("69000"),
            close=Decimal("70500"),
        )
        with pytest.raises(ValidationError):
            validate_minute(bar)

    @pytest.mark.unit
    def test_minute_invalid_interval(self) -> None:
        bar = MinuteBar(
            code="005930",
            ts=datetime(2026, 5, 13, 10, 0, 0, tzinfo=_KST),
            interval_min=2,  # 허용되지 않음
            open=Decimal("70000"),
            high=Decimal("71000"),
            low=Decimal("69000"),
            close=Decimal("70500"),
        )
        with pytest.raises(ValidationError):
            validate_minute(bar)

    @pytest.mark.unit
    def test_filter_dedups_keep_last(self) -> None:
        """동일 (code, date) 중복은 마지막 값만 유지 (UPSERT 의미)."""
        bars = [
            DailyBar(
                code="005930",
                trade_date=date(2026, 5, 13),
                open=Decimal("70000"),
                high=Decimal("71000"),
                low=Decimal("69000"),
                close=Decimal("70500"),
            ),
            DailyBar(
                code="005930",
                trade_date=date(2026, 5, 13),
                open=Decimal("70100"),
                high=Decimal("71500"),
                low=Decimal("69500"),
                close=Decimal("71000"),  # ← 마지막 값
            ),
        ]
        valid, invalid = filter_valid_daily(bars)
        assert invalid == 0
        assert len(valid) == 1
        assert valid[0].close == Decimal("71000")

    @pytest.mark.unit
    def test_filter_invalid_count(self) -> None:
        bars = [
            DailyBar(
                code="005930",
                trade_date=date(2026, 5, 13),
                open=Decimal("70000"),
                high=Decimal("71000"),
                low=Decimal("69000"),
                close=Decimal("70500"),
            ),
            DailyBar(
                code="005930",
                trade_date=date(2026, 5, 14),
                open=Decimal("-1"),
                high=Decimal("0"),
                low=Decimal("0"),
                close=Decimal("0"),
            ),
        ]
        valid, invalid = filter_valid_daily(bars)
        assert len(valid) == 1
        assert invalid == 1

    @pytest.mark.unit
    def test_index_validator(self) -> None:
        bar = IndexBar(
            code="KOSPI",
            trade_date=date(2026, 5, 13),
            open=Decimal("2700"),
            high=Decimal("2710"),
            low=Decimal("2690"),
            close=Decimal("2705"),
        )
        assert validate_index(bar) is bar


# ===========================================================================
# Partitioner
# ===========================================================================
class TestPartitioner:
    """월별 파티션 DDL 생성 테스트."""

    @pytest.mark.unit
    def test_ddl_format(self) -> None:
        ddl = build_partition_ddl(2026, 5)
        assert "tp_market.price_minute_y2026m05" in ddl
        assert "PARTITION OF tp_market.price_minute" in ddl
        assert "FROM ('2026-05-01')" in ddl
        assert "TO ('2026-06-01')" in ddl
        assert "IF NOT EXISTS" in ddl

    @pytest.mark.unit
    def test_year_boundary(self) -> None:
        """12월은 다음 해 1월 1일이 end."""
        ddl = build_partition_ddl(2026, 12)
        assert "FROM ('2026-12-01')" in ddl
        assert "TO ('2027-01-01')" in ddl

    @pytest.mark.unit
    def test_zero_padded_month(self) -> None:
        ddl = build_partition_ddl(2026, 1)
        assert "y2026m01" in ddl
        assert "FROM ('2026-01-01')" in ddl
        assert "TO ('2026-02-01')" in ddl

    @pytest.mark.unit
    def test_index_ddl(self) -> None:
        ddls = build_partition_index_ddl(2026, 5)
        assert len(ddls) == 1
        assert "ix_price_minute_y2026m05_stock_ts" in ddls[0]
        assert "(stock_id, ts)" in ddls[0]


# ===========================================================================
# PyKrxSource (synthetic mode)
# ===========================================================================
class TestPyKrxSourceSynthetic:
    """합성 데이터 모드의 deterministic 동작 검증."""

    @pytest.fixture
    def src(self) -> PyKrxSource:
        return PyKrxSource(config=IngestionConfig())

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_master_returns_samples(self, src: PyKrxSource) -> None:
        rows = await src.fetch_stock_master()
        assert len(rows) >= 5
        assert all(isinstance(r, StockMasterRow) for r in rows)
        # 005930 (삼성전자) 포함
        codes = {r.code for r in rows}
        assert "005930" in codes

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_daily_deterministic(self, src: PyKrxSource) -> None:
        """동일 code + 기간 → 동일 결과 (deterministic seed)."""
        from_d = date(2026, 1, 1)
        to_d = date(2026, 1, 31)
        bars1 = await src.fetch_daily("005930", from_d, to_d)
        bars2 = await src.fetch_daily("005930", from_d, to_d)
        assert len(bars1) == len(bars2)
        assert bars1[0].close == bars2[0].close

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_daily_excludes_weekends(self, src: PyKrxSource) -> None:
        """합성 데이터는 평일만 생성."""
        from_d = date(2026, 1, 1)
        to_d = date(2026, 1, 31)
        bars = await src.fetch_daily("005930", from_d, to_d)
        for b in bars:
            assert b.trade_date.weekday() < 5

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_daily_ohlc_valid(self, src: PyKrxSource) -> None:
        """합성 데이터도 OHLC 관계를 만족해야 함."""
        bars = await src.fetch_daily("005930", date(2026, 1, 1), date(2026, 1, 31))
        for b in bars:
            assert b.low <= b.open
            assert b.low <= b.close
            assert b.high >= b.open
            assert b.high >= b.close
            assert b.volume >= 0

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_index_returns_bars(self, src: PyKrxSource) -> None:
        bars = await src.fetch_index("KOSPI", date(2026, 1, 1), date(2026, 1, 31))
        assert len(bars) > 0
        assert all(b.code == "KOSPI" for b in bars)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_unknown_index_returns_empty(self, src: PyKrxSource) -> None:
        bars = await src.fetch_index("UNKNOWN", date(2026, 1, 1), date(2026, 1, 31))
        assert bars == []


# ===========================================================================
# Loaders (Mock 기반 SQL 페이로드 검증)
# ===========================================================================
class TestStockLoaderMock:
    """upsert_stocks의 SQL 페이로드 검증."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_stocks_chunks(self) -> None:
        from app.services.data_ingestion.loaders.stock_loader import upsert_stocks

        rows = [
            StockMasterRow(code=f"00{i:04d}", name=f"종목{i}", market="KOSPI")
            for i in range(5)
        ]
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        result = await upsert_stocks(db, rows)
        assert result["upserted"] == 5
        # 청크 사이즈 1000 → 1회 호출
        assert db.execute.await_count == 1
        assert db.commit.await_count == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_stocks_empty(self) -> None:
        from app.services.data_ingestion.loaders.stock_loader import upsert_stocks

        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        result = await upsert_stocks(db, [])
        assert result["upserted"] == 0
        assert db.execute.await_count == 0


class TestPriceDailyLoaderMock:
    """upsert_price_daily의 invalid 필터링과 missing_stock 처리 검증."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_filters_invalid(self) -> None:
        from app.services.data_ingestion.loaders.price_daily_loader import (
            upsert_price_daily,
        )

        bars = [
            DailyBar(
                code="005930",
                trade_date=date(2026, 5, 13),
                open=Decimal("-1"),  # invalid
                high=Decimal("0"),
                low=Decimal("0"),
                close=Decimal("0"),
            ),
        ]
        db = MagicMock()
        db.execute = AsyncMock()
        db.commit = AsyncMock()

        result = await upsert_price_daily(db, bars)
        assert result["upserted"] == 0
        assert result["invalid"] == 1

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_upsert_missing_stock(self) -> None:
        """code → stock_id 매핑 실패 시 missing_stock에 카운트."""
        from app.services.data_ingestion.loaders.price_daily_loader import (
            upsert_price_daily,
        )

        bars = [
            DailyBar(
                code="999999",  # DB에 없는 코드
                trade_date=date(2026, 5, 13),
                open=Decimal("70000"),
                high=Decimal("71000"),
                low=Decimal("69000"),
                close=Decimal("70500"),
                volume=1000,
            ),
        ]

        # _code_to_id_map → 빈 dict 반환하는 mock
        # SELECT 쿼리 결과를 빈 list로 mock
        select_result = MagicMock()
        select_result.all = MagicMock(return_value=[])

        db = MagicMock()
        db.execute = AsyncMock(return_value=select_result)
        db.commit = AsyncMock()

        result = await upsert_price_daily(db, bars)
        assert result["upserted"] == 0
        assert result["missing_stock"] == 1


# ===========================================================================
# Backfill (Mock 기반)
# ===========================================================================
class TestBackfillMock:
    """backfill_daily 진행률 콜백 + 실패 누적 검증."""

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_backfill_progress_callback(self) -> None:
        from app.services.data_ingestion.backfill import backfill_daily
        from app.services.data_ingestion.sources.base import MarketDataSource

        class _StubSource(MarketDataSource):
            name = "stub"

            async def fetch_stock_master(self, target_date=None):
                return []

            async def fetch_sectors(self, target_date=None):
                return []

            async def fetch_daily(self, code, from_date, to_date):
                return []

            async def fetch_index(self, index_code, from_date, to_date):
                return []

        progress_log: list[tuple[int, str | None]] = []

        async def cb(pct, code):
            progress_log.append((pct, code))

        # DB 호출은 일어나지 않도록 (fetch_daily가 빈 리스트 → upsert가 빈 결과)
        db = MagicMock()
        select_result = MagicMock()
        select_result.all = MagicMock(return_value=[])
        db.execute = AsyncMock(return_value=select_result)
        db.commit = AsyncMock()

        result = await backfill_daily(
            db,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 13),
            codes=["005930", "000660", "035420"],
            source=_StubSource(),
            progress_cb=cb,
        )
        assert result.target_codes == 3
        assert result.processed_codes == 3
        # 콜백 3회 (각 종목 처리 후)
        assert len(progress_log) == 3
        assert progress_log[-1][0] == 100  # 마지막은 100%

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_backfill_records_failed_codes(self) -> None:
        from app.services.data_ingestion.backfill import backfill_daily
        from app.services.data_ingestion.sources.base import MarketDataSource

        class _FlakeySource(MarketDataSource):
            name = "flakey"

            async def fetch_stock_master(self, target_date=None):
                return []

            async def fetch_sectors(self, target_date=None):
                return []

            async def fetch_daily(self, code, from_date, to_date):
                if code == "FAIL":
                    raise RuntimeError("simulated network error")
                return []

            async def fetch_index(self, index_code, from_date, to_date):
                return []

        db = MagicMock()
        select_result = MagicMock()
        select_result.all = MagicMock(return_value=[])
        db.execute = AsyncMock(return_value=select_result)
        db.commit = AsyncMock()

        result = await backfill_daily(
            db,
            start_date=date(2026, 5, 1),
            end_date=date(2026, 5, 13),
            codes=["005930", "FAIL", "000660"],
            source=_FlakeySource(),
        )
        assert result.target_codes == 3
        assert result.processed_codes == 3
        assert result.failed_codes == ["FAIL"]


# ===========================================================================
# IngestionConfig
# ===========================================================================
class TestConfig:
    @pytest.mark.unit
    def test_default_backfill_start_is_5y_ago(self) -> None:
        cfg = IngestionConfig()
        days_diff = (date.today() - cfg.backfill_start).days
        # 5년 ± 1일 허용
        assert 365 * 5 - 1 <= days_diff <= 365 * 5 + 1

    @pytest.mark.unit
    def test_default_chunk_size(self) -> None:
        assert default_config.chunk_size > 0
