"""크레온 게이트웨이 기반 분봉 어댑터.

게이트웨이는 Linux 본체와 별도(Windows)에 위치하므로
HTTP 클라이언트를 통해 분봉 차트(StockChart) API를 호출한다.

게이트웨이가 비활성/미가용 환경(Linux only)에서는 빈 리스트를 반환하고
경고 로그만 남긴다 (적재 파이프라인 자체는 계속 동작).
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

import structlog

from app.core.exceptions import AppException
from app.integrations.creon.client import CreonGatewayClient, get_creon_client
from app.services.data_ingestion.config import IngestionConfig, default_config
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


class CreonSource(MarketDataSource):
    """크레온 게이트웨이 어댑터 (분봉 전용).

    종목 마스터/일봉/지수는 PyKrxSource가 우선이며,
    본 어댑터는 분봉 적재만 담당한다.
    """

    name = "creon"

    def __init__(
        self,
        client: CreonGatewayClient | None = None,
        config: IngestionConfig | None = None,
    ) -> None:
        self._client = client or get_creon_client()
        self.config = config or default_config

    # ------------------------------------------------------------------
    # MarketDataSource: 미지원 메서드는 빈 결과 반환 (책임 분리)
    # ------------------------------------------------------------------
    async def fetch_stock_master(self, target_date: date | None = None) -> list[StockMasterRow]:
        log.debug("creon_source_master_unsupported")
        return []

    async def fetch_sectors(self, target_date: date | None = None) -> list[StockSectorRow]:
        log.debug("creon_source_sectors_unsupported")
        return []

    async def fetch_daily(
        self,
        code: str,
        from_date: date,
        to_date: date,
    ) -> list[DailyBar]:
        log.debug("creon_source_daily_unsupported", code=code)
        return []

    async def fetch_index(
        self,
        index_code: str,
        from_date: date,
        to_date: date,
    ) -> list[IndexBar]:
        return []

    # ------------------------------------------------------------------
    # 분봉
    # ------------------------------------------------------------------
    async def fetch_minute(
        self,
        code: str,
        target_date: date,
        interval_min: int = 1,
    ) -> list[MinuteBar]:
        """단일 종목 분봉 조회 (게이트웨이 호출).

        게이트웨이 응답 포맷 가정 (docs/23_creon_gateway.md §5.5):
            GET /market/chart/minute/{code}?date=YYYYMMDD&interval=1
            → {success: true, data: {bars: [{ts, open, high, low, close, volume, amount}, ...]}}

        게이트웨이 미가용 시 빈 리스트.
        """
        try:
            resp = await self._request_chart(code, target_date, interval_min)
        except AppException as e:
            # 게이트웨이 다운/타임아웃 → 분봉 적재는 best-effort
            log.warning(
                "creon_minute_unavailable",
                code=code,
                date=str(target_date),
                error_code=e.code,
                error=e.message,
            )
            return []
        except Exception as e:  # noqa: BLE001
            log.warning("creon_minute_unexpected", code=code, error=str(e)[:200])
            return []

        bars_raw = (resp.get("data") or {}).get("bars") or []
        bars: list[MinuteBar] = []
        for raw in bars_raw:
            try:
                ts = _parse_ts_kst(raw.get("ts"))
                bars.append(
                    MinuteBar(
                        code=code,
                        ts=ts,
                        interval_min=interval_min,
                        open=Decimal(str(raw.get("open", 0))),
                        high=Decimal(str(raw.get("high", 0))),
                        low=Decimal(str(raw.get("low", 0))),
                        close=Decimal(str(raw.get("close", 0))),
                        volume=int(raw.get("volume", 0) or 0),
                        volume_amount=Decimal(str(raw.get("amount", 0) or 0)),
                    )
                )
            except Exception as e:  # noqa: BLE001
                log.warning("creon_minute_row_skip", code=code, error=str(e)[:200])
        return bars

    async def _request_chart(
        self,
        code: str,
        target_date: date,
        interval_min: int,
    ) -> dict[str, Any]:
        """게이트웨이 분봉 차트 호출 (저수준)."""
        path = f"/market/chart/minute/{code}"
        # client._request은 GET에 query 미지원 → 임시로 직접 호출
        client = await self._client._get_client()  # type: ignore[attr-defined]
        params = {"date": target_date.strftime("%Y%m%d"), "interval": str(interval_min)}
        resp = await client.get(path, params=params)
        if resp.status_code >= 500:
            raise AppException(
                "E0004",
                message="크레온 게이트웨이 분봉 차트 조회 실패",
                details={"status": resp.status_code},
            )
        try:
            data = resp.json()
        except Exception as e:
            raise AppException("E0004", message="게이트웨이 분봉 응답 파싱 실패") from e
        if not data.get("success", True):
            err = data.get("error", {}) or {}
            raise AppException(
                "E0061",
                message=err.get("message", "분봉 데이터 미수신"),
                details={"gateway_code": err.get("code")},
            )
        return data


def _parse_ts_kst(raw: Any) -> datetime:
    """게이트웨이 ts(문자열/숫자)를 KST timezone-aware datetime으로 변환."""
    if raw is None:
        return datetime.now(tz=_KST)
    if isinstance(raw, (int, float)):
        # epoch seconds 가정
        return datetime.fromtimestamp(float(raw), tz=_KST)
    if isinstance(raw, str):
        # ISO 8601 또는 YYYYMMDDHHMMSS
        try:
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=_KST)
            return dt.astimezone(_KST)
        except ValueError:
            pass
        if len(raw) == 14 and raw.isdigit():
            dt = datetime.strptime(raw, "%Y%m%d%H%M%S").replace(tzinfo=_KST)
            return dt
        if len(raw) == 12 and raw.isdigit():
            dt = datetime.strptime(raw, "%Y%m%d%H%M").replace(tzinfo=_KST)
            return dt
    raise ValueError(f"unsupported ts format: {raw!r}")
