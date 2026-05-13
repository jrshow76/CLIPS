#!/usr/bin/env python
"""TradePilot 초기 시장 데이터 적재 스크립트.

수행 단계:
    1. 종목 마스터 + 섹터 매핑 동기화
    2. KOSPI/KOSDAQ/KOSPI200 지수 마스터 + 5년 일봉
    3. 전 종목 일봉 5년 백필 (수십분~수 시간 소요)
    4. price_minute 월별 파티션 사전 생성

실행:
    python scripts/ingest_initial_data.py
    python scripts/ingest_initial_data.py --start 2021-01-01 --end 2026-05-13
    python scripts/ingest_initial_data.py --skip-backfill        # 마스터/지수만
    python scripts/ingest_initial_data.py --codes 005930,000660  # 일부 종목만

환경 변수:
    DATABASE_URL : PostgreSQL DSN
    INGEST_USE_SYNTHETIC=true : pykrx 미설치 환경에서 합성 데이터 사용
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

# 프로젝트 루트를 파이썬 경로에 추가 (스크립트 단독 실행 가능)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
BACKEND_PATH = PROJECT_ROOT / "backend"
if str(BACKEND_PATH) not in sys.path:
    sys.path.insert(0, str(BACKEND_PATH))


def _parse_date(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _default_start() -> date:
    return date.today() - timedelta(days=365 * 5)


async def _step_master() -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import (
        PyKrxSource,
        upsert_stock_sectors,
        upsert_stocks,
    )

    print("[1/4] 종목 마스터/섹터 동기화 시작 ...")
    src = PyKrxSource()
    masters = await src.fetch_stock_master()
    print(f"  - 종목 {len(masters)}개 수신")
    async with AsyncSessionLocal() as db:
        master_stat = await upsert_stocks(db, masters)
    print(f"  - UPSERT 완료: {master_stat}")

    sectors = await src.fetch_sectors()
    print(f"  - 섹터 매핑 {len(sectors)}건 수신")
    async with AsyncSessionLocal() as db:
        sector_stat = await upsert_stock_sectors(db, sectors)
    print(f"  - 섹터/매핑 UPSERT 완료: {sector_stat}")
    return {"master": master_stat, "sectors": sector_stat}


async def _step_indices(start: date, end: date) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import (
        INDEX_CODE_MAP,
        PyKrxSource,
        upsert_market_index_master,
        upsert_market_indices,
    )

    print(f"[2/4] 지수 일봉 적재 ({start} ~ {end}) ...")
    src = PyKrxSource()
    async with AsyncSessionLocal() as db:
        await upsert_market_index_master(db)

    all_bars = []
    for code in INDEX_CODE_MAP.keys():
        bars = await src.fetch_index(code, start, end)
        print(f"  - {code}: {len(bars)} 봉")
        all_bars.extend(bars)
    async with AsyncSessionLocal() as db:
        stat = await upsert_market_indices(db, all_bars)
    print(f"  - 지수 일봉 UPSERT 완료: {stat}")
    return stat


async def _step_backfill(
    start: date,
    end: date,
    codes: list[str] | None,
) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import backfill_daily

    print(f"[3/4] 일봉 백필 시작 ({start} ~ {end}) ...")

    try:
        from tqdm import tqdm

        bar = tqdm(unit="code", desc="backfill")

        async def _on_progress(pct: int, code: str | None) -> None:
            bar.update(1)
            if code:
                bar.set_postfix_str(code)

    except Exception:  # noqa: BLE001
        bar = None

        async def _on_progress(pct: int, code: str | None) -> None:
            if pct % 5 == 0:
                print(f"  - 진행률 {pct}% (code={code})")

    async with AsyncSessionLocal() as db:
        result = await backfill_daily(
            db,
            start_date=start,
            end_date=end,
            codes=codes,
            progress_cb=_on_progress,
        )
    if bar is not None:
        bar.close()

    payload = {
        "target_codes": result.target_codes,
        "processed": result.processed_codes,
        "upserted": result.upserted_bars,
        "invalid": result.invalid_bars,
        "failed": len(result.failed_codes),
    }
    print(f"  - 백필 완료: {payload}")
    if result.failed_codes:
        print(f"  - 실패 종목 (앞 20): {result.failed_codes[:20]}")
    return payload


async def _step_partitions(start: date, end: date) -> dict:
    from app.core.database import AsyncSessionLocal
    from app.services.data_ingestion import ensure_partitions_for_range

    print(f"[4/4] price_minute 파티션 보장 ({start} ~ {end}) ...")
    async with AsyncSessionLocal() as db:
        created = await ensure_partitions_for_range(db, start, end)
    print(f"  - 신규 파티션: {created}")
    return {"created": created}


async def main() -> int:
    parser = argparse.ArgumentParser(description="TradePilot 초기 시장 데이터 적재")
    parser.add_argument(
        "--start",
        type=_parse_date,
        default=_default_start(),
        help="백필 시작일 (기본: 5년 전)",
    )
    parser.add_argument(
        "--end",
        type=_parse_date,
        default=date.today(),
        help="백필 종료일 (기본: 오늘)",
    )
    parser.add_argument(
        "--codes",
        type=str,
        default=None,
        help="대상 종목 코드 콤마 구분 (생략 시 전 종목)",
    )
    parser.add_argument(
        "--skip-master",
        action="store_true",
        help="종목 마스터/섹터 동기화 건너뛰기",
    )
    parser.add_argument(
        "--skip-indices",
        action="store_true",
        help="지수 일봉 적재 건너뛰기",
    )
    parser.add_argument(
        "--skip-backfill",
        action="store_true",
        help="일봉 백필 건너뛰기",
    )
    parser.add_argument(
        "--skip-partitions",
        action="store_true",
        help="파티션 사전 생성 건너뛰기",
    )

    args = parser.parse_args()
    codes = (
        [c.strip() for c in args.codes.split(",") if c.strip()] if args.codes else None
    )

    print("=" * 60)
    print("TradePilot 초기 시장 데이터 적재")
    print(f"  기간: {args.start} ~ {args.end}")
    print(f"  종목: {len(codes) if codes else '전 종목'}")
    print("=" * 60)

    summary: dict = {}
    if not args.skip_master:
        summary["master"] = await _step_master()
    if not args.skip_indices:
        summary["indices"] = await _step_indices(args.start, args.end)
    if not args.skip_backfill:
        summary["backfill"] = await _step_backfill(args.start, args.end, codes)
    if not args.skip_partitions:
        summary["partitions"] = await _step_partitions(args.start, args.end)

    print("=" * 60)
    print("초기 적재 완료")
    print(summary)
    print("=" * 60)
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
