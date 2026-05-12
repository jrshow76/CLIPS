"""게이트웨이 환경설정."""
from __future__ import annotations

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class GatewaySettings(BaseSettings):
    """게이트웨이 설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    REDIS_URL: str = "redis://localhost:6379/0"
    GATEWAY_API_KEY: str = "replace-with-long-random-string"

    GATEWAY_ID: str = "primary"
    GATEWAY_HOST: str = "0.0.0.0"
    GATEWAY_PORT: int = 9100

    CREON_ACCOUNT_NO: str = ""
    CREON_ACCOUNT_KIND: str = "01"
    CREON_PASSWORD_ENCRYPTED: str = ""
    CREON_AUTO_RECONNECT_MAX: int = 3
    CREON_HEALTHCHECK_INTERVAL_SEC: int = 5

    SUBSCRIBE_MAX_CODES: int = 400
    RATE_LIMIT_PER_SEC: int = 10

    LOG_LEVEL: str = "INFO"
    LOG_PATH: str = ""

    # 모킹 강제 (개발/CI)
    CREON_FORCE_MOCK: bool = False


@lru_cache(maxsize=1)
def get_settings() -> GatewaySettings:
    return GatewaySettings()


settings = get_settings()


def is_windows() -> bool:
    return os.name == "nt"
