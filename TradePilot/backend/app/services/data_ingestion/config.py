"""데이터 적재 파이프라인 설정.

- 시작일/종료일, 배치 크기, 재시도 정책, rate limit 등 적재 동작에 영향을 주는 정적 파라미터를 단일 객체로 관리한다.
- 운영 환경에서는 환경변수로 일부 값 override 가능.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date, timedelta


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except ValueError:
        return default


def _default_backfill_start() -> date:
    """기본 백필 시작일 = 오늘로부터 5년 전."""
    return date.today() - timedelta(days=365 * 5)


@dataclass(slots=True)
class IngestionConfig:
    """데이터 적재 설정.

    Attributes:
        backfill_start: 일봉 백필 기본 시작일 (5년 전)
        chunk_size: DB 일괄 UPSERT 청크 크기
        rate_limit_sleep_sec: pykrx 호출 간 sleep (rate limit 회피)
        max_retries: pykrx 호출 실패 시 최대 재시도 횟수
        retry_backoff_base: 지수 백오프 베이스 (sec)
        retry_backoff_max: 지수 백오프 상한 (sec)
        minute_retention_days: 분봉 보관 일수 (기본 90)
        active_codes_limit: 장중 분봉 적재 대상 종목 상한
        creon_minute_intervals: 적재할 분봉 인터벌 (분)
        partition_lookahead_months: price_minute 파티션 사전 생성 개월 수
    """

    backfill_start: date = field(default_factory=_default_backfill_start)
    chunk_size: int = field(default_factory=lambda: _env_int("INGEST_CHUNK_SIZE", 1000))
    rate_limit_sleep_sec: float = field(
        default_factory=lambda: _env_float("INGEST_PYKRX_SLEEP_SEC", 0.2)
    )
    max_retries: int = field(default_factory=lambda: _env_int("INGEST_MAX_RETRIES", 3))
    retry_backoff_base: float = field(
        default_factory=lambda: _env_float("INGEST_RETRY_BACKOFF_BASE", 2.0)
    )
    retry_backoff_max: float = field(
        default_factory=lambda: _env_float("INGEST_RETRY_BACKOFF_MAX", 30.0)
    )
    minute_retention_days: int = field(
        default_factory=lambda: _env_int("INGEST_MINUTE_RETENTION_DAYS", 90)
    )
    active_codes_limit: int = field(
        default_factory=lambda: _env_int("INGEST_ACTIVE_CODES_LIMIT", 500)
    )
    creon_minute_intervals: tuple[int, ...] = (1, 5)
    partition_lookahead_months: int = field(
        default_factory=lambda: _env_int("INGEST_PARTITION_LOOKAHEAD_MONTHS", 2)
    )


# ---------------------------------------------------------------------------
# 시장 지수 매핑 (KRX 코드)
# ---------------------------------------------------------------------------
# pykrx 의 index 코드 체계:
#   1001 = KOSPI
#   2001 = KOSDAQ
#   1028 = KOSPI200
INDEX_CODE_MAP: dict[str, dict[str, str]] = {
    "KOSPI": {"krx_code": "1001", "name": "코스피", "market": "KOSPI"},
    "KOSDAQ": {"krx_code": "2001", "name": "코스닥", "market": "KOSDAQ"},
    "KOSPI200": {"krx_code": "1028", "name": "코스피200", "market": "KOSPI"},
}


# 모듈 싱글톤 (테스트에서는 재바인딩하지 말 것)
default_config = IngestionConfig()
