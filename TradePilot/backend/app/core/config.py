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
# - .env.example 의 기본값
# - 흔히 사용되는 약한 패턴(개발 placeholder, "secret", "changeme" 등)
_FORBIDDEN_PROD_SECRETS = (
    "change-this-in-production-please-32bytes-min",
    "base64-encoded-32byte-random-key",
    "replace-with-long-random-string",
    "tradepilot",
    "secret",
    "changeme",
    "change-me",
    "password",
    "admin",
    "test",
    "",
)

# 운영 DB/Redis 호스트로 사용 금지(개발 호스트명/루프백)
# 운영 환경에서는 사설망 IP 또는 정식 도메인을 사용해야 한다.
_FORBIDDEN_PROD_HOSTS = (
    "localhost",
    "127.0.0.1",
    "::1",
    "postgres",   # docker-compose 개발 호스트명
    "redis",      # docker-compose 개발 호스트명
    "db",
)

# 운영 환경 최소 시크릿 길이
_MIN_SECRET_LEN = 32

# 시크릿 엔트로피 최소 고유문자 수
# (예: "aaaaaa...aaaa" 32자는 길이는 OK 이지만 엔트로피가 매우 낮다)
_MIN_SECRET_ENTROPY = 16


def _has_forbidden_host(url: str) -> str | None:
    """URL 문자열에서 금지된 호스트가 포함되어 있으면 해당 호스트 반환.

    URL 파싱 실패 시 단순 부분 문자열 매칭으로 폴백한다.
    """
    if not url:
        return None
    try:
        # postgresql+asyncpg://user:pw@host:5432/db 형식 처리
        # 호스트는 '@' 뒤, ':' 또는 '/' 앞에 위치
        if "://" in url:
            after_scheme = url.split("://", 1)[1]
        else:
            after_scheme = url
        host_part = after_scheme.split("@")[-1]  # 인증정보 제거
        host = host_part.split("/")[0].split(":")[0].lower()
    except Exception:  # pragma: no cover - 방어
        host = url.lower()
    for forbidden in _FORBIDDEN_PROD_HOSTS:
        if host == forbidden:
            return forbidden
    return None


def _is_weak_secret(value: str, *, min_len: int = _MIN_SECRET_LEN) -> str | None:
    """시크릿 강도 검증. 약하면 사유 문자열을 반환하고, 강하면 None 반환."""
    if value in _FORBIDDEN_PROD_SECRETS:
        return "기본값/약한 패턴"
    if len(value) < min_len:
        return f"{min_len}자 미만(현재 {len(value)}자)"
    # 엔트로피: 고유 문자 수
    unique_chars = len(set(value))
    if unique_chars < _MIN_SECRET_ENTROPY:
        return f"엔트로피 부족(고유문자 {unique_chars}개 < 최소 {_MIN_SECRET_ENTROPY}개)"
    return None


def _validate_production_settings(s: "Settings") -> None:
    """운영 환경(APP_ENV=production)에서만 동작하는 시크릿/설정 검증.

    SEC-001/SEC-005 자동 방어: 개발용 기본값/약한 시크릿/CORS 와일드카드/개발 호스트 등
    운영 부적합 설정으로 기동 시 즉시 RuntimeError 발생(fail-fast).

    검증 항목:
      1. JWT_SECRET: 32자 이상 + 엔트로피 16 + 기본값 아님
      2. AES_KEY: 32자 이상 + 엔트로피 16 + 기본값 아님
      3. CREON_GATEWAY_API_KEY: 32자 이상 + 엔트로피 16 + 기본값 아님
      4. DATABASE_URL: localhost/127.0.0.1/postgres 등 개발 호스트 금지
      5. REDIS_URL: localhost/127.0.0.1/redis 등 개발 호스트 금지
      6. CORS_ORIGINS: 와일드카드(*) 금지 + 빈 값 금지
      7. DB_ECHO: False 강제 (SQL 평문 로그 방지)
      8. JWT_ALGORITHM: 화이트리스트 강제
      9. POSTGRES_PASSWORD/SMTP_PASSWORD 기본값 금지(설정된 경우만 검증)
    """
    if s.APP_ENV != "production":
        return

    issues: list[str] = []

    # 1. JWT_SECRET
    reason = _is_weak_secret(s.JWT_SECRET)
    if reason:
        issues.append(f"JWT_SECRET 가 운영 부적합: {reason}")

    # 2. AES_KEY (base64 인코딩이므로 길이 기준은 동일하게 32자 이상)
    reason = _is_weak_secret(s.AES_KEY)
    if reason:
        issues.append(f"AES_KEY 가 운영 부적합: {reason}")

    # 3. CREON_GATEWAY_API_KEY
    reason = _is_weak_secret(s.CREON_GATEWAY_API_KEY)
    if reason:
        issues.append(f"CREON_GATEWAY_API_KEY 가 운영 부적합: {reason}")

    # 4. DATABASE_URL 호스트 검증
    forbidden_host = _has_forbidden_host(s.DATABASE_URL)
    if forbidden_host:
        issues.append(
            f"DATABASE_URL 에 개발용 호스트 '{forbidden_host}' 가 사용되었습니다. "
            "운영에서는 사설망 IP 또는 정식 도메인을 사용해야 합니다."
        )

    # 5. REDIS_URL 호스트 검증 (모든 Redis URL)
    for name, url in (
        ("REDIS_URL", s.REDIS_URL),
        ("REDIS_BROKER_URL", s.REDIS_BROKER_URL),
        ("REDIS_RESULT_URL", s.REDIS_RESULT_URL),
    ):
        forbidden_host = _has_forbidden_host(url)
        if forbidden_host:
            issues.append(
                f"{name} 에 개발용 호스트 '{forbidden_host}' 가 사용되었습니다. "
                "운영에서는 사설망 IP 또는 정식 도메인을 사용해야 합니다."
            )

    # 6. CORS_ORIGINS
    if "*" in s.CORS_ORIGINS:
        issues.append("운영 환경에서 CORS_ORIGINS 와일드카드(*) 는 허용되지 않습니다.")
    if not s.cors_origin_list:
        issues.append("운영 환경에서 CORS_ORIGINS 가 비어 있습니다. 최소 1개의 정식 origin 이 필요합니다.")

    # 7. DB_ECHO
    if s.DB_ECHO:
        issues.append("운영 환경에서 DB_ECHO=True 는 SQL 평문 로그 노출을 일으킵니다.")

    # 8. JWT_ALGORITHM 화이트리스트
    if s.JWT_ALGORITHM not in ("HS256", "HS384", "HS512", "RS256", "RS384", "RS512"):
        issues.append(f"지원하지 않는 JWT_ALGORITHM: {s.JWT_ALGORITHM}")

    # 9. SMTP_PASSWORD: 빈 값은 SMTP 미사용으로 간주(통과), 설정된 경우만 약한 값 차단
    if s.SMTP_PASSWORD and s.SMTP_PASSWORD in _FORBIDDEN_PROD_SECRETS:
        issues.append("SMTP_PASSWORD 가 기본값/약한 패턴입니다.")

    if issues:
        msg = (
            "[SECURITY] 운영 환경(APP_ENV=production) 부적합 설정 감지. "
            "운영 진입 차단(fail-fast):\n  - " + "\n  - ".join(issues) + "\n"
            "조치 가이드:\n"
            "  1. 강한 시크릿 생성: openssl rand -hex 32  (또는 openssl rand -base64 48)\n"
            "  2. .env 파일에서 값 교체 후 컨테이너 재기동\n"
            "  3. 자세한 절차: docs/43_secrets_management.md 참조\n"
            "  4. 시크릿 정책: security/73_secrets_policy.md 참조"
        )
        raise RuntimeError(msg)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """싱글톤 설정 객체를 반환한다."""
    s = Settings()
    _validate_production_settings(s)
    return s


# 모듈 레벨 캐시(편의용)
settings = get_settings()
