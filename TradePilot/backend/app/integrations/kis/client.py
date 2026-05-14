"""KIS REST 클라이언트 (저수준).

책임:
- 공통 헤더 (Authorization, appkey, appsecret, tr_id, custtype) 자동 주입
- 호출 단위 idempotency_key 헤더 지원
- 응답 envelope 파싱 (rt_cd / msg_cd / msg1 / output)
- Rate Limit (sliding window): 초당 안전 마진 16건
- 에러 매핑 (KIS msg_cd → AppException Exxxx)
- 토큰 만료 1회 자동 재시도 (EGW00121 등)

스레드/태스크 안전: httpx.AsyncClient 1개 재사용 + asyncio.Lock(rate limit).
"""
from __future__ import annotations

import asyncio
import time
from collections import deque
from typing import Any

import httpx
import structlog

from app.core.exceptions import AppException
from app.integrations.kis.auth import KisAuth, get_kis_auth
from app.integrations.kis.config import KisConfig, get_kis_config
from app.integrations.kis.error_mapping import is_success, map_kis_error

log = structlog.get_logger(__name__)


# KIS REST API에서 광범위하게 사용하는 사용자 구분 (개인=P, 법인=B).
# 본 어댑터는 개인 계정을 기본으로 한다.
_CUSTTYPE_PERSONAL = "P"


class KisRateLimiter:
    """단순 sliding window (초 단위) — KIS 초당 한도 보호용."""

    def __init__(self, per_sec: int) -> None:
        self.per_sec = max(1, per_sec)
        self._ts: deque[float] = deque(maxlen=self.per_sec * 2)
        self._lock = asyncio.Lock()

    async def acquire(self) -> float:
        wait_total = 0.0
        while True:
            async with self._lock:
                now = time.monotonic()
                while self._ts and (now - self._ts[0]) > 1.0:
                    self._ts.popleft()
                if len(self._ts) < self.per_sec:
                    self._ts.append(now)
                    return wait_total
                sleep_for = 1.0 - (now - self._ts[0]) + 0.005
            sleep_for = max(sleep_for, 0.01)
            wait_total += sleep_for
            await asyncio.sleep(sleep_for)


class KisClient:
    """KIS REST 비동기 클라이언트."""

    def __init__(
        self,
        config: KisConfig | None = None,
        auth: KisAuth | None = None,
    ) -> None:
        self.config = config or get_kis_config()
        self.auth = auth or get_kis_auth()
        self.rate_limiter = KisRateLimiter(self.config.rate_limit_per_sec)
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.config.base_url(self.auth.trade_mode),
                timeout=httpx.Timeout(self.config.timeout_sec, connect=2.0),
                headers={"Content-Type": "application/json; charset=utf-8"},
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # ------------------------------------------------------------------
    # 저수준 호출
    # ------------------------------------------------------------------
    async def request(
        self,
        method: str,
        path: str,
        *,
        tr_id: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
        retry_on_token_expire: bool = True,
        hashkey: str | None = None,
    ) -> dict[str, Any]:
        """KIS API 호출.

        - ``tr_id``: TR ID (예: 매수 ``TTTC0802U``, 매도 ``TTTC0801U``, 모의 ``VTTC...``)
        - ``hashkey``: 일부 주문 TR에서 사전 해시 발급 후 헤더에 첨부 (선택).
        - ``idempotency_key``: 클라이언트 측 멱등성. 본체에서 Redis 별도 처리하므로
          여기서는 ``custtype`` 다음에 ``custom_idem`` 헤더로 전달만 한다.
        """
        await self.rate_limiter.acquire()
        token = await self.auth.get_token()

        headers = {
            "authorization": token.bearer(),
            "appkey": self.auth.appkey,
            "appsecret": self.auth.appsecret,
            "tr_id": tr_id,
            "custtype": _CUSTTYPE_PERSONAL,
        }
        if hashkey:
            headers["hashkey"] = hashkey
        if idempotency_key:
            headers["custom_idem"] = idempotency_key

        client = await self._get_client()
        kwargs: dict[str, Any] = {"params": params, "json": json, "headers": headers}
        if timeout_sec is not None:
            kwargs["timeout"] = httpx.Timeout(
                timeout_sec, connect=min(2.0, timeout_sec)
            )
        try:
            resp = await client.request(method, path, **kwargs)
        except httpx.TimeoutException as e:
            log.warning("kis_timeout", path=path, tr=tr_id)
            raise AppException("E0072", message="KIS 응답 타임아웃") from e
        except httpx.RequestError as e:
            log.warning("kis_unreachable", path=path, error=str(e))
            raise AppException("E0012", message="KIS API 연결 실패") from e

        if resp.status_code >= 500:
            raise AppException(
                "E0004",
                message="KIS 서버 내부 오류",
                details={"status": resp.status_code, "body": resp.text[:300]},
            )
        try:
            data: dict[str, Any] = resp.json()
        except Exception as e:
            raise AppException("E0004", message="KIS 응답 파싱 실패") from e

        msg_cd = str(data.get("msg_cd", ""))
        if not is_success(data.get("rt_cd")):
            # 토큰 만료 → 1회 자동 재시도
            if retry_on_token_expire and msg_cd in ("EGW00121", "EGW00123"):
                log.info("kis_token_expired_retry", tr=tr_id, path=path)
                await self.auth.invalidate()
                return await self.request(
                    method,
                    path,
                    tr_id=tr_id,
                    params=params,
                    json=json,
                    timeout_sec=timeout_sec,
                    idempotency_key=idempotency_key,
                    retry_on_token_expire=False,
                    hashkey=hashkey,
                )
            e_code = map_kis_error(msg_cd)
            raise AppException(
                e_code,
                message=str(data.get("msg1", "KIS 비즈니스 오류")),
                details={"msg_cd": msg_cd, "tr_id": tr_id},
            )
        return data

    # ------------------------------------------------------------------
    # 고수준 도메인 API (선임 개발 — 핵심만 추상화)
    # ------------------------------------------------------------------
    def _tr_id_order(self, side: str) -> str:
        """주문 TR ID 결정 (SIM/REAL × BUY/SELL).

        매핑 (KIS 표준 명세):
        - REAL 매수: TTTC0802U
        - REAL 매도: TTTC0801U
        - SIM  매수: VTTC0802U
        - SIM  매도: VTTC0801U
        """
        sim = self.config.is_sim(self.auth.trade_mode)
        if side == "BUY":
            return "VTTC0802U" if sim else "TTTC0802U"
        return "VTTC0801U" if sim else "TTTC0801U"

    def _tr_id_cancel(self) -> str:
        sim = self.config.is_sim(self.auth.trade_mode)
        # 정정/취소 공통 TR (취소는 RVSE_CNCL_DVSN_CD=02)
        return "VTTC0803U" if sim else "TTTC0803U"

    def _tr_id_quote(self) -> str:
        # 현재가 — SIM/REAL 동일
        return "FHKST01010100"

    def _tr_id_orderbook(self) -> str:
        return "FHKST01010200"

    async def submit_order(
        self,
        *,
        code: str,
        side: str,
        qty: int,
        order_type: str,
        price: float | None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """주문 발주. KIS 응답 ``output`` 그대로 반환."""
        payload = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_prod_cd,
            "PDNO": code,
            # ORD_DVSN: 00=지정가, 01=시장가
            "ORD_DVSN": "01" if order_type == "MARKET" else "00",
            "ORD_QTY": str(int(qty)),
            "ORD_UNPR": str(int(price or 0)),
        }
        return await self.request(
            "POST",
            "/uapi/domestic-stock/v1/trading/order-cash",
            tr_id=self._tr_id_order(side),
            json=payload,
            idempotency_key=idempotency_key,
        )

    async def cancel_order(
        self,
        *,
        broker_order_no: str,
        code: str,
        qty: int = 0,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """주문 취소. 정정/취소 공통 TR 사용 (RVSE_CNCL_DVSN_CD=02)."""
        payload = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_prod_cd,
            "KRX_FWDG_ORD_ORGNO": "",
            "ORGN_ODNO": broker_order_no,
            "ORD_DVSN": "00",  # 지정가 기본 (실거래에서는 원주문 DVSN 추적 필요)
            "RVSE_CNCL_DVSN_CD": "02",  # 02=취소
            "ORD_QTY": str(int(qty or 0)),
            "ORD_UNPR": "0",
            "QTY_ALL_ORD_YN": "Y" if qty == 0 else "N",
        }
        return await self.request(
            "POST",
            "/uapi/domestic-stock/v1/trading/order-rvsecncl",
            tr_id=self._tr_id_cancel(),
            json=payload,
            timeout_sec=timeout_sec,
            idempotency_key=idempotency_key,
        )

    async def get_quote(self, code: str) -> dict[str, Any]:
        """현재가 조회."""
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        return await self.request(
            "GET",
            "/uapi/domestic-stock/v1/quotations/inquire-price",
            tr_id=self._tr_id_quote(),
            params=params,
        )

    async def get_orderbook(self, code: str) -> dict[str, Any]:
        """호가/예상체결."""
        params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": code}
        return await self.request(
            "GET",
            "/uapi/domestic-stock/v1/quotations/inquire-asking-price-exp-ccn",
            tr_id=self._tr_id_orderbook(),
            params=params,
        )

    async def get_balance(self) -> dict[str, Any]:
        """주식 잔고."""
        sim = self.config.is_sim(self.auth.trade_mode)
        tr_id = "VTTC8434R" if sim else "TTTC8434R"
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_prod_cd,
            "AFHR_FLPR_YN": "N",
            "OFL_YN": "",
            "INQR_DVSN": "02",
            "UNPR_DVSN": "01",
            "FUND_STTL_ICLD_YN": "N",
            "FNCG_AMT_AUTO_RDPT_YN": "N",
            "PRCS_DVSN": "00",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        return await self.request(
            "GET",
            "/uapi/domestic-stock/v1/trading/inquire-balance",
            tr_id=tr_id,
            params=params,
        )

    async def get_order_history(
        self, *, from_date: str, to_date: str
    ) -> dict[str, Any]:
        """일별 주문체결 조회 (YYYYMMDD 문자열)."""
        sim = self.config.is_sim(self.auth.trade_mode)
        tr_id = "VTTC8001R" if sim else "TTTC8001R"
        params = {
            "CANO": self.config.account_no,
            "ACNT_PRDT_CD": self.config.account_prod_cd,
            "INQR_STRT_DT": from_date,
            "INQR_END_DT": to_date,
            "SLL_BUY_DVSN_CD": "00",
            "INQR_DVSN": "01",
            "PDNO": "",
            "CCLD_DVSN": "00",
            "ORD_GNO_BRNO": "",
            "ODNO": "",
            "INQR_DVSN_3": "00",
            "INQR_DVSN_1": "",
            "CTX_AREA_FK100": "",
            "CTX_AREA_NK100": "",
        }
        return await self.request(
            "GET",
            "/uapi/domestic-stock/v1/trading/inquire-daily-ccld",
            tr_id=tr_id,
            params=params,
        )


# 모듈 싱글톤
_client_singleton: KisClient | None = None


def get_kis_client() -> KisClient:
    global _client_singleton
    if _client_singleton is None:
        _client_singleton = KisClient()
    return _client_singleton


async def close_kis_client() -> None:
    global _client_singleton
    if _client_singleton is not None:
        await _client_singleton.close()
        _client_singleton = None


def reset_kis_client() -> None:
    """테스트용."""
    global _client_singleton
    _client_singleton = None
