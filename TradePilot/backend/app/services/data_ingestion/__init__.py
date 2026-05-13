"""데이터 적재 파이프라인 패키지.

외부에서 사용 가능한 진입점:
- IngestionConfig, default_config: 적재 설정
- PyKrxSource, CreonSource: 데이터 소스
- 각 loader 함수
- backfill_daily: 과거 데이터 백필

사용 예:
    from app.services.data_ingestion import (
        PyKrxSource, upsert_stocks, upsert_price_daily,
    )

    src = PyKrxSource()
    rows = await src.fetch_stock_master()
    await upsert_stocks(db, rows)
"""
from app.services.data_ingestion.backfill import BackfillResult, backfill_daily
from app.services.data_ingestion.config import (
    INDEX_CODE_MAP,
    IngestionConfig,
    default_config,
)
from app.services.data_ingestion.loaders import (
    insert_price_minute,
    upsert_market_index_master,
    upsert_market_indices,
    upsert_price_daily,
    upsert_stock_sectors,
    upsert_stocks,
)
from app.services.data_ingestion.partitioner import (
    build_partition_ddl,
    ensure_partition,
    ensure_partitions_for_range,
    ensure_partitions_lookahead,
)
from app.services.data_ingestion.sources import (
    DailyBar,
    IndexBar,
    MarketDataSource,
    MinuteBar,
    StockMasterRow,
    StockSectorRow,
)
from app.services.data_ingestion.sources.creon_source import CreonSource
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

__all__ = [
    # config
    "INDEX_CODE_MAP",
    "IngestionConfig",
    "default_config",
    # sources
    "MarketDataSource",
    "PyKrxSource",
    "CreonSource",
    "DailyBar",
    "MinuteBar",
    "IndexBar",
    "StockMasterRow",
    "StockSectorRow",
    # loaders
    "upsert_stocks",
    "upsert_stock_sectors",
    "upsert_price_daily",
    "insert_price_minute",
    "upsert_market_index_master",
    "upsert_market_indices",
    # validator
    "ValidationError",
    "validate_daily",
    "validate_minute",
    "validate_index",
    "filter_valid_daily",
    "filter_valid_minute",
    "filter_valid_index",
    # partitioner
    "build_partition_ddl",
    "ensure_partition",
    "ensure_partitions_for_range",
    "ensure_partitions_lookahead",
    # backfill
    "backfill_daily",
    "BackfillResult",
]
