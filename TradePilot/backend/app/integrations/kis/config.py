"""KIS 어댑터 설정.

`backend/app/core/config.py` 의 ``settings`` 와 별개로 KIS 전용 옵션을
모듈 안에서 읽어 사용한다. 운영에서는 환경변수로 주입.

- ``KIS_API_URL_REAL`` / ``KIS_API_URL_SIM``: KIS API 도메인
- ``KIS_WS_URL_REAL`` / ``KIS_WS_URL_SIM``: WebSocket 시세 도메인
- ``KIS_APPKEY`` / ``KIS_APPSECRET``: 시스템 기본 자격증명 (사용자별 설정은 DB)
- ``KIS_ACCOUNT_NO`` (8자리) / ``KIS_ACCOUNT_PROD_CD`` (2자리): 거래 계좌
- ``KIS_TRADE_ENV``: SIM | REAL
- ``KIS_TIMEOUT_SEC``: HTTP 타임아웃
- ``KIS_RATE_LIMIT_PER_SEC``: 초당 호출 한도 (안전 마진)
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache


@dataclass(frozen=True)
class KisConfig:
    """KIS 어댑터 환경 설정 (불변)."""

    api_url_real: str
    api_url_sim: str
    ws_url_real: str
    ws_url_sim: str
    appkey: str
    appsecret: str
    account_no: str        # CANO (8자리)
    account_prod_cd: str   # ACNT_PRDT_CD (2자리, 보통 "01")
    trade_env: str         # SIM | REAL
    timeout_sec: float
    rate_limit_per_sec: int
    token_cache_ttl_sec: int  # 토큰 만료 사전 갱신 마진

    def base_url(self, trade_mode: str | None = None) -> str:
        """현재(또는 지정한) trade_mode 에 맞는 REST 도메인."""
        mode = (trade_mode or self.trade_env).upper()
        if mode in ("REAL", "LIVE"):
            return self.api_url_real
        return self.api_url_sim

    def ws_url(self, trade_mode: str | None = None) -> str:
        mode = (trade_mode or self.trade_env).upper()
        if mode in ("REAL", "LIVE"):
            return self.ws_url_real
        return self.ws_url_sim

    def is_sim(self, trade_mode: str | None = None) -> bool:
        return (trade_mode or self.trade_env).upper() in ("SIM",)


def _get_env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


@lru_cache(maxsize=1)
def get_kis_config() -> KisConfig:
    """KIS 설정 싱글톤. 테스트는 ``reset_kis_config()`` 사용."""
    return KisConfig(
        api_url_real=_get_env(
            "KIS_API_URL_REAL", "https://openapi.koreainvestment.com:9443"
        ),
        api_url_sim=_get_env(
            "KIS_API_URL_SIM", "https://openapivts.koreainvestment.com:29443"
        ),
        ws_url_real=_get_env(
            "KIS_WS_URL_REAL", "ws://ops.koreainvestment.com:21000"
        ),
        ws_url_sim=_get_env(
            "KIS_WS_URL_SIM", "ws://ops.koreainvestment.com:31000"
        ),
        appkey=_get_env("KIS_APPKEY", ""),
        appsecret=_get_env("KIS_APPSECRET", ""),
        account_no=_get_env("KIS_ACCOUNT_NO", ""),
        account_prod_cd=_get_env("KIS_ACCOUNT_PROD_CD", "01"),
        trade_env=_get_env("KIS_TRADE_ENV", "SIM").upper(),
        timeout_sec=float(_get_env("KIS_TIMEOUT_SEC", "5.0")),
        rate_limit_per_sec=int(_get_env("KIS_RATE_LIMIT_PER_SEC", "16")),
        token_cache_ttl_sec=int(_get_env("KIS_TOKEN_CACHE_TTL_SEC", "82800")),  # 23h
    )


def reset_kis_config() -> None:
    """테스트용: 환경변수 변경 후 캐시 무효화."""
    get_kis_config.cache_clear()
