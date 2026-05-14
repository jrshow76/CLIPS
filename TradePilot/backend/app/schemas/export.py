"""익스포트 도메인 스키마.

POST /exports
GET  /exports/{id}
GET  /exports/{id}/download
DELETE /exports/{id}
GET  /exports
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


JobType = Literal["ORDERS", "PNL", "BACKTEST", "SIGNALS", "POSITIONS"]
ExportFormat = Literal["CSV", "XLSX"]
ExportStatus = Literal["PENDING", "RUNNING", "DONE", "FAILED", "EXPIRED", "CANCELED"]


class ExportRequestIn(BaseModel):
    """POST /exports 입력.

    필터는 익스포트 종류에 따라 의미가 다르다.
        * ORDERS / PNL / SIGNALS: ``from`` / ``to`` (ISO date), ``code`` 등
        * BACKTEST: ``run_id`` 또는 ``run_id_list``
        * POSITIONS: ``trade_mode`` (SIM/LIVE)
    """

    model_config = ConfigDict(extra="forbid")

    job_type: JobType
    format: ExportFormat = "CSV"
    filter_params: dict[str, Any] = Field(default_factory=dict)


class ExportJobOut(BaseModel):
    """단일 익스포트 잡 응답."""

    export_id: str
    job_type: JobType
    format: ExportFormat
    status: ExportStatus
    progress_percent: int = 0
    row_count: int | None = None
    file_size_bytes: int | None = None
    download_url: str | None = None
    download_url_expires_at: datetime | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    expires_at: datetime | None = None


class ExportDownloadOut(BaseModel):
    """GET /exports/{id}/download 응답."""

    export_id: str
    download_url: str
    expires_at: datetime
