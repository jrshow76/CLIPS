"""키움 게이트웨이 HTTP 클라이언트.

CREON 게이트웨이 클라이언트(`app.integrations.creon.client.CreonGatewayClient`)와
완전 동형의 구조를 가진다. 본체에서는 broker 별 클라이언트만 교체하면 된다.

- 헤더: ``X-Gateway-Api-Key``, ``X-Request-Id``, ``X-Idempotency-Key``
- 응답 envelope 동일: ``{success, data, raw}`` 또는 ``{success: false, error}``
- 키움 K0xxx 코드 → 본체 E0xxx 매핑
"""
from __future__ import annotations

import os
from typing import Any

import httpx
import structlog

from app.core.exceptions import AppException

log = structlog.get_logger(__name__)


# 키움 게이트웨이 K코드 → 본체 E코드 매핑
GATEWAY_ERROR_MAP: dict[str, str] = {
    "K0001": "E0012",  # 미접속
    "K0002": "E0012",  # 서버 접속 실패
    "K0010": "E0008",  # 호출 한도 초과 (rate limit)
    "K0011": "E0026",  # 주문가격 오류 → 호가단위 류
    "K0012": "E0024",  # 주문수량 오류
    "K0013": "E0023",  # 주문 입력 오류
    "K0014": "E0011",  # 계좌 비밀번호 오류
}


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default)


class KiwoomGatewayClient:
    """키움 게이트웨이 HTTP 클라이언트.

    환경변수:
    - ``KIWOOM_GATEWAY_URL`` (default: ``http://localhost:9101``)
    - ``KIWOOM_GATEWAY_API_KEY``
    - ``KIWOOM_GATEWAY_TIMEOUT_SEC`` (default: 5.0)
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_sec: float | None = None,
    ) -> None:
        self.base_url = (
            base_url or _env("KIWOOM_GATEWAY_URL", "http://localhost:9101")
        ).rstrip("/")
        self.api_key = api_key or _env("KIWOOM_GATEWAY_API_KEY", "")
        self.timeout = timeout_sec or float(_env("KIWOOM_GATEWAY_TIMEOUT_SEC", "5.0"))
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

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        client = await self._get_client()
        import structlog as _slog
        trace_id = _slog.contextvars.get_contextvars().get("trace_id", "")
        headers: dict[str, str] = {}
        if trace_id:
            headers["X-Request-Id"] = str(trace_id)
        if idempotency_key:
            headers["X-Idempotency-Key"] = idempotency_key

        try:
            kwargs: dict[str, Any] = {"json": json, "headers": headers or None}
            if timeout_sec is not None:
                kwargs["timeout"] = httpx.Timeout(timeout_sec, connect=min(2.0, timeout_sec))
            resp = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            log.warning("kiwoom_gateway_timeout", path=path, error=str(e))
            raise AppException("E0072", message="키움 게이트웨이 응답 타임아웃") from e
        except httpx.RequestError as e:
            log.warning("kiwoom_gateway_unreachable", path=path, error=str(e))
            raise AppException("E0012", message="키움 게이트웨이 연결 실패") from e

        if resp.status_code >= 500:
            raise AppException(
                "E0004",
                message="키움 게이트웨이 내부 오류",
                details={"status": resp.status_code, "body": resp.text[:300]},
            )

        try:
            data = resp.json()
        except Exception as e:
            raise AppException("E0004", message="게이트웨이 응답 파싱 실패") from e

        if not data.get("success", True):
            err = data.get("error", {}) or {}
            k_code = err.get("code", "K0001")
            e_code = GATEWAY_ERROR_MAP.get(k_code, "E0023")
            raise AppException(
                e_code,
                message=err.get("message", "키움 게이트웨이 오류"),
                details={
                    "raw_code": err.get("raw_code"),
                    "raw_msg": err.get("raw_msg"),
                    "gateway_code": k_code,
                },
            )
        return data

    # ------------------------------------------------------------------
    # 고수준 API
    # ------------------------------------------------------------------
    async def health(self) -> dict[str, Any]:
        return await self._request("GET", "/healthz")

    async def ready(self) -> dict[str, Any]:
        return await self._request("GET", "/readyz")

    async def system_status(self) -> dict[str, Any]:
        return await self._request("GET", "/system/status")

    async def reconnect(self) -> dict[str, Any]:
        return await self._request("POST", "/system/reconnect")

    async def submit_order(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/orders", json=payload)

    async def cancel_order(
        self,
        order_id: str,
        payload: dict[str, Any],
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        return await self._request(
            "POST",
            f"/orders/{order_id}/cancel",
            json=payload,
            timeout_sec=timeout_sec,
            idempotency_key=idempotency_key,
        )

    async def get_balance(self) -> dict[str, Any]:
        return await self._request("GET", "/account/balance")

    async def get_positions(self) -> dict[str, Any]:
        return await self._request("GET", "/account/positions")

    async def get_quote(self, code: str) -> dict[str, Any]:
        return await self._request("GET", f"/market/quote/{code}")

    async def subscribe_quote(self, codes: list[str]) -> dict[str, Any]:
        return await self._request("POST", "/subscribe/quote", json={"codes": codes})

    async def unsubscribe_quote(self, codes: list[str]) -> dict[str, Any]:
        return await self._request("POST", "/unsubscribe/quote", json={"codes": codes})


# 모듈 싱글톤
_client_singleton: KiwoomGatewayClient | None = None


def get_kiwoom_client() -> KiwoomGatewayClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = KiwoomGatewayClient()
    return _client_singleton


async def close_kiwoom_client() -> None:
    global _client_singleton
    if _client_singleton is not None:
        await _client_singleton.close()
        _client_singleton = None


def reset_kiwoom_client() -> None:
    """테스트용."""
    global _client_singleton
    _client_singleton = None
