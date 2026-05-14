"""Prometheus 메트릭 정의 및 FastAPI 미들웨어.

본 모듈은 TradePilot 의 핵심 메트릭을 한 곳에서 정의한다.
- HTTP 메트릭은 미들웨어로 자동 수집
- 비즈니스 메트릭(주문/시그널/Kill Switch/인증)은 각 서비스 코드에서 호출

설계 원칙:
- prometheus_client 가 설치되지 않은 환경(테스트, 경량 빌드)에서도
  import 가 실패하지 않도록 graceful fallback (no-op shim) 을 제공한다.
- 라벨 카디널리티 보호: `user_id` 는 직접 라벨로 노출하지 않고,
  집계 메트릭(예: `live_mode_users` Gauge, `pnl_users_below_threshold`) 만 노출.
- 엔드포인트 라벨은 라우트 패턴(`/api/v1/orders/{id}`) 으로 정규화하여
  path parameter 폭주를 방지한다.

참고: docs/45_observability_guide.md
"""
from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

# -----------------------------------------------------------------------------
# prometheus_client lazy import + graceful fallback
# -----------------------------------------------------------------------------
try:
    from prometheus_client import (  # type: ignore[import-untyped]
        CONTENT_TYPE_LATEST,
        REGISTRY,
        CollectorRegistry,
        Counter,
        Gauge,
        Histogram,
        generate_latest,
    )

    _PROM_AVAILABLE = True
except Exception:  # pragma: no cover - 의존성 부재 시
    _PROM_AVAILABLE = False
    CONTENT_TYPE_LATEST = "text/plain; version=0.0.4; charset=utf-8"  # type: ignore[assignment]
    REGISTRY = None  # type: ignore[assignment]

    class _NoopMetric:
        """모든 메서드를 흡수하는 no-op 메트릭."""

        def __init__(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def labels(self, *_args: Any, **_kwargs: Any) -> "_NoopMetric":
            return self

        def inc(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def dec(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def set(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def observe(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def time(self) -> "_NoopTimer":
            return _NoopTimer()

    class _NoopTimer:
        def __enter__(self) -> "_NoopTimer":
            return self

        def __exit__(self, *_args: Any) -> None:
            return None

    # 동일 시그니처의 no-op 생성자
    Counter = Gauge = Histogram = _NoopMetric  # type: ignore[misc,assignment]
    CollectorRegistry = type("CollectorRegistry", (), {})  # type: ignore[misc,assignment]

    def generate_latest(*_args: Any, **_kwargs: Any) -> bytes:  # type: ignore[misc]
        return b"# prometheus_client unavailable\n"


# -----------------------------------------------------------------------------
# 메트릭 정의
# -----------------------------------------------------------------------------

# 공통 버킷 (HTTP / 게이트웨이 latency 모두 사용)
_LATENCY_BUCKETS: tuple[float, ...] = (
    0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0, 10.0,
)

# --- HTTP 메트릭 -------------------------------------------------------------
http_requests_total = Counter(
    "http_requests_total",
    "HTTP 요청 누적 수",
    labelnames=("method", "endpoint", "status"),
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP 요청 응답시간 분포(초)",
    labelnames=("method", "endpoint"),
    buckets=_LATENCY_BUCKETS,
)

# --- 매매 메트릭 ------------------------------------------------------------
# 주의: user_id 는 라벨로 노출하지 않는다 (카디널리티 보호).
orders_submitted_total = Counter(
    "orders_submitted_total",
    "주문 제출 누적 수",
    labelnames=("mode", "side", "result"),    # mode: SIM/LIVE, side: BUY/SELL, result: success/failure
)

signals_generated_total = Counter(
    "signals_generated_total",
    "시그널 생성 누적 수",
    labelnames=("strategy_id",),
)

kill_switch_triggered_total = Counter(
    "kill_switch_triggered_total",
    "Kill Switch 발동 누적 수",
    labelnames=("source", "result"),    # source: user/system/security, result: success/partial/failure
)

live_mode_users = Gauge(
    "live_mode_users",
    "현재 LIVE 모드로 설정된 사용자 수",
)

sim_mode_users = Gauge(
    "sim_mode_users",
    "현재 SIM 모드로 설정된 사용자 수",
)

# PnL 분위 집계 (개인정보 보호: user_id 라벨 미사용)
daily_pnl_p50 = Gauge("daily_pnl_p50", "당일 PnL p50 (전체 사용자 집계)")
daily_pnl_p95 = Gauge("daily_pnl_p95", "당일 PnL p95")
daily_pnl_p05 = Gauge("daily_pnl_p05", "당일 PnL p5 (꼬리손실)")

pnl_users_below_threshold = Gauge(
    "pnl_users_below_threshold",
    "당일 PnL 이 임계 이하인 사용자 수",
    labelnames=("threshold",),    # "3pct" / "5pct" / "10pct"
)

# --- 보안 메트릭 ------------------------------------------------------------
auth_failures_total = Counter(
    "auth_failures_total",
    "인증 실패 누적 수",
    labelnames=("reason",),    # invalid_credentials / invalid_token / expired_token / locked / mfa_failed
)

refresh_replay_detected_total = Counter(
    "refresh_replay_detected_total",
    "Refresh token replay (재사용) 감지 누적 수",
)

# --- 실시간/WebSocket -------------------------------------------------------
websocket_connections = Gauge(
    "websocket_connections",
    "활성 WebSocket 연결 수",
    labelnames=("channel",),    # market / account / notifications
)

# --- Creon Gateway ----------------------------------------------------------
creon_gateway_requests_total = Counter(
    "creon_gateway_requests_total",
    "Creon Gateway 호출 누적 수",
    labelnames=("result",),    # success / failure / timeout / throttled
)

creon_gateway_requests_duration_seconds = Histogram(
    "creon_gateway_requests_duration_seconds",
    "Creon Gateway 호출 응답시간 분포(초)",
    labelnames=("operation",),    # quote / order / cancel / account
    buckets=_LATENCY_BUCKETS,
)

# --- 시장 상태 (룰 평가에 사용) ---------------------------------------------
tradepilot_market_open = Gauge(
    "tradepilot_market_open",
    "장 개장 여부 (1=open, 0=closed)",
)


# -----------------------------------------------------------------------------
# 엔드포인트 라벨 정규화
# -----------------------------------------------------------------------------
def normalize_endpoint(path: str) -> str:
    """path parameter 가 포함된 경로를 라우트 패턴으로 정규화한다.

    FastAPI 의 `request.scope["route"].path` 를 우선 사용하지만,
    매칭 실패 시(404 등) 본 함수가 fallback 으로 동작한다.

    카디널리티 폭주를 막기 위해 숫자/uuid/긴 토큰을 placeholder 로 치환한다.
    """
    if not path:
        return "unknown"

    parts = path.split("/")
    normalized: list[str] = []
    for p in parts:
        if not p:
            normalized.append(p)
            continue
        # 숫자 ID
        if p.isdigit():
            normalized.append("{id}")
            continue
        # UUID
        if len(p) == 36 and p.count("-") == 4:
            normalized.append("{uuid}")
            continue
        # 긴 토큰/해시
        if len(p) >= 32 and all(c.isalnum() or c in "-_" for c in p):
            normalized.append("{token}")
            continue
        normalized.append(p)
    return "/".join(normalized) or "/"


# -----------------------------------------------------------------------------
# FastAPI 미들웨어
# -----------------------------------------------------------------------------
class PrometheusMiddleware:
    """ASGI 미들웨어: 모든 HTTP 요청의 카운트/지연시간을 수집.

    설계:
    - 라우트 매칭이 끝난 후 `request.scope["route"]` 의 path 를 라벨로 사용.
    - `/metrics` 자체는 측정 대상에서 제외 (self-noise 방지).
    - 헬스체크(`/healthz`, `/readyz`) 는 측정 대상에서 제외.
    """

    EXCLUDED_PATHS: frozenset[str] = frozenset(
        {"/metrics", "/healthz", "/readyz"}
    )

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable[[], Awaitable[Any]],
        send: Callable[[Any], Awaitable[None]],
    ) -> None:
        if scope.get("type") != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.EXCLUDED_PATHS:
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "GET")
        status_code_holder = {"code": 500}

        async def _send(message: Any) -> None:
            if message.get("type") == "http.response.start":
                status_code_holder["code"] = int(message.get("status", 500))
            await send(message)

        start = time.perf_counter()
        try:
            await self.app(scope, receive, _send)
        finally:
            elapsed = time.perf_counter() - start
            # 라우트 매칭 결과를 우선 사용 (path parameter 정규화)
            route = scope.get("route")
            endpoint = getattr(route, "path", None) or normalize_endpoint(path)
            status = str(status_code_holder["code"])

            try:
                http_requests_total.labels(
                    method=method, endpoint=endpoint, status=status
                ).inc()
                http_request_duration_seconds.labels(
                    method=method, endpoint=endpoint
                ).observe(elapsed)
            except Exception:
                # 메트릭 수집 실패는 요청 처리에 영향을 주지 않는다.
                pass


# -----------------------------------------------------------------------------
# /metrics 엔드포인트 헬퍼
# -----------------------------------------------------------------------------
def render_metrics() -> tuple[bytes, str]:
    """현재 레지스트리의 메트릭을 텍스트 포맷으로 직렬화.

    Returns:
        (body, content_type)
    """
    if not _PROM_AVAILABLE:
        return (b"# prometheus_client unavailable\n", CONTENT_TYPE_LATEST)
    return (generate_latest(REGISTRY), CONTENT_TYPE_LATEST)


__all__ = [
    "PrometheusMiddleware",
    "auth_failures_total",
    "creon_gateway_requests_duration_seconds",
    "creon_gateway_requests_total",
    "daily_pnl_p05",
    "daily_pnl_p50",
    "daily_pnl_p95",
    "http_request_duration_seconds",
    "http_requests_total",
    "kill_switch_triggered_total",
    "live_mode_users",
    "normalize_endpoint",
    "orders_submitted_total",
    "pnl_users_below_threshold",
    "refresh_replay_detected_total",
    "render_metrics",
    "signals_generated_total",
    "sim_mode_users",
    "tradepilot_market_open",
    "websocket_connections",
]
