"""키움 게이트웨이 환경설정.

CREON 게이트웨이와 거의 동일한 구조를 따른다 (운영자가 변수명만 KIS/KIWOOM 구분).

핵심 토글:
- ``KIWOOM_TRADE_ENV``: SIM(모의투자) / REAL(실거래). 기본 SIM.
- ``KIWOOM_USE_MOCK``: pywin32/PyQt5 미설치 환경 강제 mock fallback.
- ``KIWOOM_FORCE_MOCK``: 운영 Windows 에서도 mock 강제 (점검용).
- ``RATE_LIMIT_PER_SEC``: 키움 OpenAPI+ 초당 호출 제한 — 안전 마진 4건/sec.
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# 키움 OpenAPI+ 공식 가이드: 초당 5건, 1시간 1000건 (TR 호출 제한).
# 안전 마진 80% → 초당 4건.
_DEFAULT_RPS = 4


class GatewaySettings(BaseSettings):
    """게이트웨이 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 공통 인프라
    REDIS_URL: str = "redis://localhost:6379/0"
    GATEWAY_API_KEY: str = "replace-with-long-random-string"
    GATEWAY_ID: str = "kiwoom-primary"
    GATEWAY_HOST: str = "0.0.0.0"
    GATEWAY_PORT: int = 9101

    # 키움 모드 / 계좌
    KIWOOM_TRADE_ENV: Literal["SIM", "REAL"] = "SIM"
    # 키움 모의투자/실거래 계좌번호 (8자리 + 2자리 product cd 별도)
    KIWOOM_ACCOUNT_NO: str = ""
    KIWOOM_ACCOUNT_PWD_ENCRYPTED: str = ""  # 화면번호 / 계좌 비밀번호 (보호)

    # 연결 / 재연결
    KIWOOM_HEALTHCHECK_INTERVAL_SEC: int = 5
    KIWOOM_AUTO_RECONNECT_MAX: int = 3
    KIWOOM_LOGIN_TIMEOUT_SEC: int = 60

    # 시세 / 요청 제한
    SUBSCRIBE_MAX_CODES: int = 100  # 키움 화면번호 1개당 100개 제한
    RATE_LIMIT_PER_SEC: int = Field(default=_DEFAULT_RPS, ge=1, le=5)
    RATE_LIMIT_PER_HOUR: int = Field(default=800, ge=1, le=1000)  # 안전 마진

    # Mock / 개발용
    KIWOOM_USE_MOCK: bool = True
    KIWOOM_FORCE_MOCK: bool = False

    # 로깅
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = ""

    # Idempotency
    IDEMPOTENCY_TTL_SEC: int = 600

    # 헬스비트
    HEALTHBEAT_INTERVAL_SEC: int = 30

    # Mock tick worker
    MOCK_TICK_ENABLED: bool = True
    MOCK_TICK_INTERVAL_SEC: float = 1.0

    def is_sim_mode(self) -> bool:
        return self.KIWOOM_TRADE_ENV == "SIM"

    def is_real_mode(self) -> bool:
        return self.KIWOOM_TRADE_ENV == "REAL"


@lru_cache(maxsize=1)
def get_settings() -> GatewaySettings:
    return GatewaySettings()


def reload_settings() -> GatewaySettings:
    """테스트용: 캐시 재로딩."""
    get_settings.cache_clear()
    return get_settings()


settings = get_settings()


def is_windows() -> bool:
    return os.name == "nt"
