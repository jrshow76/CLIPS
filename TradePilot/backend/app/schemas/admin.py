"""관리자 API 스키마."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class HealthOut(BaseModel):
    db: bool
    redis: bool
    creon_gateway: bool
    ready: bool


class MaintenanceIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    message: str | None = None


class MaintenanceOut(BaseModel):
    enabled: bool
    message: str | None = None
    updated_at: datetime


class MasterRefreshOut(BaseModel):
    job_id: str
    status: Literal["QUEUED", "RUNNING", "DONE"] = "QUEUED"


class AuditLogItem(BaseModel):
    id: int
    user_id: int | None = None
    event: str
    result: str
    ip_address: str | None = None
    user_agent: str | None = None
    meta: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
