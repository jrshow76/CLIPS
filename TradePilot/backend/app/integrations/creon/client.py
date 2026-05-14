"""크레온 게이트웨이 HTTP 클라이언트.

`docs/23_creon_gateway.md` §5 명세를 구현한다.
- 헤더: X-Gateway-Api-Key, X-Request-Id
- 응답 포맷: {success, data, raw} 또는 {success: false, error}
- 에러 매핑: G0xxx → Exxxx (본 클라이언트에서 변환)
"""
from __future__ import annotations

from typing import Any

import httpx
import structlog

from app.core.config import settings
from app.core.exceptions import AppException

log = structlog.get_logger(__name__)


# 게이트웨이 G코드 → 본체 E코드 매핑 (docs/23_creon_gateway.md §5.4)
GATEWAY_ERROR_MAP: dict[str, str] = {
    "G0001": "E0012",  # COM 초기화 실패
    "G0002": "E0012",  # 연결 단절
    "G0010": "E0023",  # 주문 응답 코드 != 0
    "G0011": "E0024",  # 증거금 부족
    "G0012": "E0026",  # 호가단위 오류
    "G0013": "E0027",  # 상하한가 도달
    "G0014": "E0028",  # 거래 정지
    "G0020": "E0072",  # 응답 타임아웃
    "G0030": "E0061",  # 시세 미수신
}


class CreonGatewayClient:
    """크레온 게이트웨이 HTTP 클라이언트 (싱글톤 사용 권장)."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.CREON_GATEWAY_URL).rstrip("/")
        self.api_key = api_key or settings.CREON_GATEWAY_API_KEY
        self.timeout = timeout_sec or settings.CREON_GATEWAY_TIMEOUT_SEC
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout, connect=2.0),
                headers={
                    "X-Gateway-Api-Key": self.api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # 저수준 호출
    # ------------------------------------------------------------------
    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """게이트웨이 호출 + 에러 매핑.

        SEC-003(GATE-1) 보강:
        - ``timeout_sec`` 호출별 오버라이드: Kill Switch 같은 SLA가 엄격한 경로는 2초 등 짧게 설정.
        - ``idempotency_key`` 호출별 헤더 주입 (X-Idempotency-Key): cancel_order 중복 호출 방지.
        """
        client = await self._get_client()
        import structlog
        trace_id = structlog.contextvars.get_contextvars().get("trace_id", "")
        extra_headers: dict[str, str] = {}
        if trace_id:
            extra_headers["X-Request-Id"] = str(trace_id)
        if idempotency_key:
            extra_headers["X-Idempotency-Key"] = idempotency_key
        try:
            kwargs: dict[str, Any] = {
                "json": json,
                "headers": extra_headers or None,
            }
            if timeout_sec is not None:
                kwargs["timeout"] = httpx.Timeout(timeout_sec, connect=min(2.0, timeout_sec))
            resp = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            log.warning("creon_gateway_timeout", path=path, error=str(e))
            raise AppException("E0072", message="크레온 게이트웨이 응답 타임아웃") from e
        except httpx.RequestError as e:
            log.warning("creon_gateway_unreachable", path=path, error=str(e))
            raise AppException("E0012", message="크레온 게이트웨이에 연결할 수 없습니다.") from e

        # HTTP 레벨 실패
        if resp.status_code >= 500:
            raise AppException(
                "E0004",
                message="크레온 게이트웨이 내부 오류",
                details={"status": resp.status_code, "body": resp.text[:300]},
            )

        try:
            data = resp.json()
        except Exception as e:
            raise AppException("E0004", message="게이트웨이 응답 파싱 실패") from e

        # 비즈니스 레벨 실패 (success=false)
        if not data.get("success", True):
            err = data.get("error", {}) or {}
            g_code = err.get("code", "G0001")
            e_code = GATEWAY_ERROR_MAP.get(g_code, "E0023")
            raise AppException(
                e_code,
                message=err.get("message", "크레온 게이트웨이 오류"),
                details={
                    "raw_code": err.get("raw_code"),
                    "raw_msg": err.get("raw_msg"),
                    "gateway_code": g_code,
                },
            )
        return data

    # ------------------------------------------------------------------
    # 고수준 API
    # ------------------------------------------------------------------
    async def health(self) -> dict[str, Any]:
        """게이트웨이 liveness."""
        return await self._request("GET", "/healthz")

    async def ready(self) -> dict[str, Any]:
        """COM 세션 readiness."""
        return await self._request("GET", "/readyz")

    async def system_status(self) -> dict[str, Any]:
        return await self._request("GET", "/system/status")

    async def reconnect(self) -> dict[str, Any]:
        return await self._request("POST", "/system/reconnect")

    async def submit_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        """주문 발주 → broker_order_no 반환."""
        return await self._request("POST", "/orders", json=payload)

    async def cancel_order(
        self,
        order_id: str,
        payload: dict[str, Any],
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """주문 취소 호출.

        SEC-003(GATE-1): Kill Switch 경로는 ``timeout_sec=2.0`` + ``idempotency_key`` 권장.
        """
        return await self._request(
            "POST",
            f"/orders/{order_id}/cancel",
            json=payload,
            timeout_sec=timeout_sec,
            idempotency_key=idempotency_key,
        )

    async def liquidate_all(self, reason: str | None = None) -> dict[str, Any]:
        return await self._request("POST", "/orders/liquidate-all", json={"reason": reason})

    async def get_balance(self) -> dict[str, Any]:
        return await self._request("GET", "/account/balance")

    async def get_positions(self) -> dict[str, Any]:
        return await self._request("GET", "/account/positions")

    async def get_quote(self, code: str) -> dict[str, Any]:
        return await self._request("GET", f"/market/quote/{code}")

    async def get_orderbook(self, code: str) -> dict[str, Any]:
        return await self._request("GET", f"/market/orderbook/{code}")

    async def subscribe_quote(self, codes: list[str]) -> dict[str, Any]:
        return await self._request("POST", "/subscribe/quote", json={"codes": codes})

    async def unsubscribe_quote(self, codes: list[str]) -> dict[str, Any]:
        return await self._request("POST", "/unsubscribe/quote", json={"codes": codes})


# 모듈 싱글톤
_client_singleton: CreonGatewayClient | None = None


def get_creon_client() -> CreonGatewayClient:
    """싱글톤 클라이언트."""
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = CreonGatewayClient()
    return _client_singleton


async def close_creon_client() -> None:
    global _client_singleton
    if _client_singleton is not None:
        await _client_singleton.close()
        _client_singleton = None
