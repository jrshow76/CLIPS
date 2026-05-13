"""애플리케이션 설정.

Pydantic Settings 기반으로 환경변수(.env 포함)를 일괄 로딩한다.
모든 설정은 단일 `settings` 객체로 참조한다.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """TradePilot 백엔드 환경설정."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # 애플리케이션
    APP_ENV: Literal["development", "staging", "production", "test"] = "development"
    APP_NAME: str = "tradepilot"
    APP_TIMEZONE: str = "Asia/Seoul"
    LOG_LEVEL: str = "INFO"
    SERVICE_ROLE: Literal["api", "worker", "scheduler"] = "api"

    # 서버
    BACKEND_HOST: str = "0.0.0.0"
    BACKEND_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000"

    # DB
    DATABASE_URL: str = (
        "postgresql+asyncpg://tradepilot:tradepilot@localhost:5432/tradepilot"
    )
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_ECHO: bool = False

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_BROKER_URL: str = "redis://localhost:6379/1"
    REDIS_RESULT_URL: str = "redis://localhost:6379/2"

    # JWT
    JWT_SECRET: str = "change-this-in-production-please-32bytes-min"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TTL_SEC: int = 1800
    JWT_REFRESH_TTL_SEC: int = 604800

    # 암호화
    AES_KEY: str = "base64-encoded-32byte-random-key"

    # 크레온 게이트웨이
    CREON_GATEWAY_URL: str = "http://localhost:9100"
    CREON_GATEWAY_API_KEY: str = "replace-with-long-random-string"
    CREON_GATEWAY_TIMEOUT_SEC: float = 5.0

    # SMTP (선택)
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "TradePilot <noreply@example.com>"
    SMTP_USE_TLS: bool = True

    # 텔레그램 (선택)
    TELEGRAM_BOT_TOKEN: str = ""

    # 시세 백업
    FALLBACK_QUOTE_ENABLED: bool = True
    FALLBACK_QUOTE_SOURCE: str = "naver"

    # ML
    ML_MODEL_DIR: str = "/var/lib/tradepilot/models"
    ML_RETRAIN_HOUR_KST: int = 18

    # RateLimit
    RATE_LIMIT_AUTH_PER_MIN: int = 10
    RATE_LIMIT_QUOTE_PER_SEC: int = 10
    RATE_LIMIT_ORDER_PER_SEC: int = 3
    RATE_LIMIT_ORDER_PER_DAY: int = 1000
    RATE_LIMIT_DEFAULT_PER_MIN: int = 600

    # OTP
    OTP_LENGTH: int = 6
    OTP_TTL_SEC: int = 300  # 5분 (정책 §1.1 OTP 5분)
    OTP_MAX_ATTEMPTS: int = 5

    # 멱등성
    IDEMPOTENCY_TTL_SEC: int = 86400  # 24시간

    # 관측
    SENTRY_DSN: str = ""
    PROMETHEUS_ENABLED: bool = False

    @computed_field  # type: ignore[misc]
    @property
    def cors_origin_list(self) -> list[str]:
        """CORS_ORIGINS 환경변수를 콤마로 분리한 리스트."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @computed_field  # type: ignore[misc]
    @property
    def is_dev(self) -> bool:
        return self.APP_ENV == "development"

    @computed_field  # type: ignore[misc]
    @property
    def is_test(self) -> bool:
        return self.APP_ENV == "test"

    @computed_field  # type: ignore[misc]
    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"


# 보안: 운영 환경에서 사용 금지 기본값/약한 시크릿 패턴
_FORBIDDEN_PROD_SECRETS = (
    "change-this-in-production-please-32bytes-min",
    "base64-encoded-32byte-random-key",
    "replace-with-long-random-string",
    "tradepilot",
    "secret",
    "changeme",
    "",
)


def _validate_production_settings(s: "Settings") -> None:
    """운영 환경(APP_ENV=production)에서만 동작하는 시크릿/설정 검증.

    SEC-001/SEC-005 자동 방어: 개발용 기본값으로 운영 기동 시 즉시 RuntimeError로 차단.
    """
    if s.APP_ENV != "production":
        return

    issues: list[str] = []
    if s.JWT_SECRET in _FORBIDDEN_PROD_SECRETS or len(s.JWT_SECRET) < 32:
        issues.append("JWT_SECRET 가 기본값이거나 32자 미만입니다.")
    if s.AES_KEY in _FORBIDDEN_PROD_SECRETS or len(s.AES_KEY) < 32:
        issues.append("AES_KEY 가 기본값이거나 32자 미만입니다.")
    if s.CREON_GATEWAY_API_KEY in _FORBIDDEN_PROD_SECRETS or len(s.CREON_GATEWAY_API_KEY) < 32:
        issues.append("CREON_GATEWAY_API_KEY 가 기본값이거나 32자 미만입니다.")
    if "*" in s.CORS_ORIGINS:
        issues.append("운영 환경에서 CORS_ORIGINS 와일드카드(*) 는 허용되지 않습니다.")
    if s.DB_ECHO:
        issues.append("운영 환경에서 DB_ECHO=True 는 SQL 평문 로그 노출을 일으킵니다.")
    if s.JWT_ALGORITHM not in ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512"):
        issues.append(f"지원하지 않는 JWT_ALGORITHM: {s.JWT_ALGORITHM}")

    if issues:
        msg = "[SECURITY] 운영 환경 부적합 설정 감지:\n  - " + "\n  - ".join(issues)
        raise RuntimeError(msg)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤 설정 객체를 반환한다."""
    s = Settings()
    _validate_production_settings(s)
    return s


# 모듈 레벨 캐시(편의용)
settings = get_settings()
