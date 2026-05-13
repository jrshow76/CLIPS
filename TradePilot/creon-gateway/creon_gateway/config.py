"""게이트웨이 환경설정.

CREON 모의투자(SIM) / 실거래(REAL) 토글 및 요청 제한, mock fallback 등을 제어한다.
모든 값은 환경변수 또는 `.env` 파일로 주입되며, 비밀 값은 절대 커밋되지 않는다.

핵심 토글:
- CREON_TRADE_ENV: SIM(모의투자) / REAL(실거래). 기본은 SIM (안전 우선)
- CREON_USE_MOCK: pythoncom 미설치 환경의 강제 mock fallback
- RATE_LIMIT_PER_SEC / RATE_LIMIT_PER_4SEC: CREON 공식 제한(15/60)에 안전 마진 80% 적용
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# CREON 공식 한도: 1초당 15건, 4초당 60건 (대신증권 공시).
# 안전 마진 80% 적용 → 1초 12건 / 4초 48건.
_DEFAULT_RPS = 12  # 15 * 0.8
_DEFAULT_RP4S = 48  # 60 * 0.8


class GatewaySettings(BaseSettings):
    """게이트웨이 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ---------------------------------------------------------------
    # 공통 인프라
    # ---------------------------------------------------------------
    REDIS_URL: str = "redis://localhost:6379/0"
    GATEWAY_API_KEY: str = "replace-with-long-random-string"

    GATEWAY_ID: str = "primary"
    GATEWAY_HOST: str = "0.0.0.0"
    GATEWAY_PORT: int = 9100

    # ---------------------------------------------------------------
    # CREON 모드 / 계좌
    # ---------------------------------------------------------------
    # 모의투자(SIM) vs 실거래(REAL) 토글
    # 기본값은 SIM (안전 원칙: 명시적으로 REAL을 설정하지 않으면 절대 실거래 발주하지 않는다)
    CREON_TRADE_ENV: Literal["SIM", "REAL"] = "SIM"

    # 모의투자 계좌 접두사 (대신증권 모의투자 계좌의 식별 패턴)
    # 운영 환경에서는 실제 계좌 접두사로 교체
    CREON_ACCOUNT_PREFIX_SIM: str = "55"  # 가정값: 모의투자 계좌 시작 두 자리
    CREON_ACCOUNT_PREFIX_REAL: str = "01"  # 가정값: 실계좌 시작 두 자리

    CREON_ACCOUNT_NO: str = ""
    CREON_ACCOUNT_KIND: str = "01"
    CREON_PASSWORD_ENCRYPTED: str = ""

    # 연결 / 재연결
    CREON_AUTO_RECONNECT_MAX: int = 3
    CREON_HEALTHCHECK_INTERVAL_SEC: int = 5
    CREON_CONNECT_RETRY_SEC: int = 2

    # ---------------------------------------------------------------
    # 시세 / 요청 제한
    # ---------------------------------------------------------------
    SUBSCRIBE_MAX_CODES: int = 400

    # 1초당 요청 한도 (CREON 공식 15건 → 안전 마진 80%)
    RATE_LIMIT_PER_SEC: int = Field(default=_DEFAULT_RPS, ge=1, le=15)
    # 4초당 요청 한도 (CREON 공식 60건 → 안전 마진 80%)
    RATE_LIMIT_PER_4SEC: int = Field(default=_DEFAULT_RP4S, ge=1, le=60)

    # ---------------------------------------------------------------
    # Mock / 개발용
    # ---------------------------------------------------------------
    # pythoncom/win32com 미설치 시 자동 mock fallback.
    # CI/Linux 환경에서 True. Windows 운영에서 False.
    CREON_USE_MOCK: bool = True
    # 명시적 강제 mock (운영 Windows에서도 mock으로 동작하게 함 — 점검용)
    CREON_FORCE_MOCK: bool = False

    # ---------------------------------------------------------------
    # 로깅
    # ---------------------------------------------------------------
    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = ""

    # ---------------------------------------------------------------
    # Idempotency
    # ---------------------------------------------------------------
    IDEMPOTENCY_TTL_SEC: int = 600  # 10분

    # ---------------------------------------------------------------
    # 헬스비트
    # ---------------------------------------------------------------
    HEALTHBEAT_INTERVAL_SEC: int = 30

    # ---------------------------------------------------------------
    # Mock tick worker (개발/E2E용)
    # ---------------------------------------------------------------
    # mock 어댑터 사용 시 자동으로 가짜 tick 발행 (1초 주기)
    MOCK_TICK_ENABLED: bool = True
    MOCK_TICK_INTERVAL_SEC: float = 1.0

    def is_sim_mode(self) -> bool:
        """모의투자 모드 여부."""
        return self.CREON_TRADE_ENV == "SIM"

    def is_real_mode(self) -> bool:
        """실거래 모드 여부."""
        return self.CREON_TRADE_ENV == "REAL"

    def expected_account_prefix(self) -> str:
        """현재 모드에 기대되는 계좌 접두사."""
        return (
            self.CREON_ACCOUNT_PREFIX_SIM
            if self.is_sim_mode()
            else self.CREON_ACCOUNT_PREFIX_REAL
        )


@lru_cache(maxsize=1)
def get_settings() -> GatewaySettings:
    return GatewaySettings()


def reload_settings() -> GatewaySettings:
    """테스트용: 캐시된 settings를 재로딩."""
    get_settings.cache_clear()
    return get_settings()


settings = get_settings()


def is_windows() -> bool:
    return os.name == "nt"
