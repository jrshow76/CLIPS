"""KIS 어댑터 단위 테스트 (D4 — 다증권사 어댑터).

검증:
- 토큰 발급/캐시 hit/만료 갱신
- KIS 응답 envelope 파싱 (rt_cd, msg_cd)
- 주문 페이로드 구조 (TR ID 분기 SIM/REAL × BUY/SELL)
- 에러 매핑 (msg_cd → Exxxx)
- LiveOrderRouter.submit_order / cancel_order 정상 흐름
"""
from __future__ import annotations

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# 테스트 환경: REAL/SIM 도메인 분리만 확인 가능하면 충분
os.environ.setdefault("KIS_APPKEY", "test-appkey-1234567890")
os.environ.setdefault("KIS_APPSECRET", "test-appsecret-abcdefghij")
os.environ.setdefault("KIS_ACCOUNT_NO", "12345678")
os.environ.setdefault("KIS_ACCOUNT_PROD_CD", "01")
os.environ.setdefault("KIS_TRADE_ENV", "SIM")
os.environ.setdefault("KIS_RATE_LIMIT_PER_SEC", "16")

from app.integrations.kis.auth import KisAuth, KisToken
from app.integrations.kis.client import KisClient, KisRateLimiter
from app.integrations.kis.config import get_kis_config, reset_kis_config
from app.integrations.kis.error_mapping import is_success, map_kis_error
from app.integrations.kis.live_order_router import KisLiveOrderRouter
from app.domains.ports.order_router_port import OrderRequest
from decimal import Decimal


@pytest.fixture(autouse=True)
def _reset_config():
    reset_kis_config()
    yield
    reset_kis_config()


# ---------------------------------------------------------------------------
# 1. 설정 — SIM/REAL 도메인 분기
# ---------------------------------------------------------------------------
class TestKisConfig:
    def test_sim_base_url(self):
        cfg = get_kis_config()
        # 기본 SIM
        assert "openapivts" in cfg.base_url("SIM")
        assert "openapi.koreainvestment" in cfg.base_url("REAL")

    def test_is_sim(self):
        cfg = get_kis_config()
        assert cfg.is_sim("SIM")
        assert not cfg.is_sim("REAL")


# ---------------------------------------------------------------------------
# 2. 에러 매핑
# ---------------------------------------------------------------------------
class TestErrorMapping:
    def test_known_codes(self):
        assert map_kis_error("EGW00121") == "E0001"  # 토큰 만료
        assert map_kis_error("APBK0918") == "E0024"  # 증거금 부족
        assert map_kis_error("APBK0920") == "E0026"  # 호가단위
        assert map_kis_error("APBK0921") == "E0027"  # 상하한가
        assert map_kis_error("APBK0922") == "E0028"  # 거래정지

    def test_unknown_defaults(self):
        assert map_kis_error("UNKNOWN") == "E0023"
        assert map_kis_error(None) == "E0023"
        assert map_kis_error("") == "E0023"

    def test_is_success(self):
        assert is_success("0") is True
        assert is_success(0) is True
        assert is_success("1") is False
        assert is_success(None) is False


# ---------------------------------------------------------------------------
# 3. RateLimiter
# ---------------------------------------------------------------------------
class TestKisRateLimiter:
    @pytest.mark.asyncio
    async def test_under_limit_no_wait(self):
        rl = KisRateLimiter(per_sec=5)
        for _ in range(5):
            assert await rl.acquire() == 0

    @pytest.mark.asyncio
    async def test_over_limit_blocks(self):
        rl = KisRateLimiter(per_sec=2)
        await rl.acquire()
        await rl.acquire()
        start = time.monotonic()
        await rl.acquire()  # 3번째는 대기
        elapsed = time.monotonic() - start
        assert elapsed >= 0.8


# ---------------------------------------------------------------------------
# 4. KisToken 만료 판단
# ---------------------------------------------------------------------------
class TestKisToken:
    def test_not_expired(self):
        t = KisToken(access_token="x", token_type="Bearer", expires_at=time.time() + 3600)
        assert not t.is_expired()
        assert t.bearer() == "Bearer x"

    def test_expired_with_margin(self):
        # 30초 후 만료 + 60초 마진 → 만료 처리
        t = KisToken(access_token="x", token_type="Bearer", expires_at=time.time() + 30)
        assert t.is_expired(margin_sec=60)


# ---------------------------------------------------------------------------
# 5. TR ID 결정 — SIM/REAL × BUY/SELL
# ---------------------------------------------------------------------------
class TestTrIdMapping:
    @pytest.mark.asyncio
    async def test_sim_buy_sell(self):
        client = KisClient()
        client.auth.trade_mode = "SIM"
        assert client._tr_id_order("BUY") == "VTTC0802U"
        assert client._tr_id_order("SELL") == "VTTC0801U"
        assert client._tr_id_cancel() == "VTTC0803U"

    @pytest.mark.asyncio
    async def test_real_buy_sell(self):
        client = KisClient()
        client.auth.trade_mode = "REAL"
        assert client._tr_id_order("BUY") == "TTTC0802U"
        assert client._tr_id_order("SELL") == "TTTC0801U"
        assert client._tr_id_cancel() == "TTTC0803U"


# ---------------------------------------------------------------------------
# 6. LiveOrderRouter — submit_order 정상 흐름 (mock client)
# ---------------------------------------------------------------------------
class TestKisLiveOrderRouter:
    @pytest.mark.asyncio
    async def test_submit_success(self):
        # mock client 가 KIS 표준 응답을 반환하도록 구성
        fake_client = MagicMock()
        fake_client.submit_order = AsyncMock(
            return_value={
                "rt_cd": "0",
                "msg_cd": "OPSP0000",
                "msg1": "정상처리",
                "output": {
                    "KRX_FWDG_ORD_ORGNO": "00950",
                    "ODNO": "0000123456",
                    "ORD_TMD": "094530",
                },
            }
        )
        router = KisLiveOrderRouter(client=fake_client)
        req = OrderRequest(
            order_id=42,
            user_id=1,
            stock_code="005930",
            side="BUY",
            order_type="LIMIT",
            qty=Decimal("10"),
            price=Decimal("70000"),
            trade_mode="LIVE",
            idempotency_key="abc",
        )
        result = await router.submit_order(req)
        assert result.accepted
        assert result.status == "ACCEPTED"
        assert result.broker_order_no == "0000123456"

    @pytest.mark.asyncio
    async def test_submit_rejected_on_app_exception(self):
        from app.core.exceptions import AppException

        fake_client = MagicMock()
        fake_client.submit_order = AsyncMock(
            side_effect=AppException("E0024", message="증거금 부족")
        )
        router = KisLiveOrderRouter(client=fake_client)
        req = OrderRequest(
            order_id=43,
            user_id=1,
            stock_code="000660",
            side="BUY",
            order_type="LIMIT",
            qty=Decimal("100"),
            price=Decimal("200000"),
            trade_mode="LIVE",
        )
        result = await router.submit_order(req)
        assert not result.accepted
        assert result.status == "REJECTED"
        assert "증거금" in (result.reject_reason or "")

    @pytest.mark.asyncio
    async def test_cancel_requires_broker_order_no(self):
        fake_client = MagicMock()
        router = KisLiveOrderRouter(client=fake_client)
        result = await router.cancel_order(
            order_id=1, broker_order_no=None, stock_code="005930"
        )
        assert not result.accepted
        assert result.status == "REJECTED"
        assert "broker_order_no" in (result.reject_reason or "")

    @pytest.mark.asyncio
    async def test_cancel_success(self):
        fake_client = MagicMock()
        fake_client.cancel_order = AsyncMock(
            return_value={"rt_cd": "0", "output": {"ODNO": "0000123456"}}
        )
        router = KisLiveOrderRouter(client=fake_client)
        result = await router.cancel_order(
            order_id=1,
            broker_order_no="0000123456",
            stock_code="005930",
            timeout_sec=2.0,
            idempotency_key="cancel-xyz",
        )
        assert result.accepted
        assert result.status == "CANCELED"
        # cancel_order 가 timeout_sec / idempotency_key 를 client 에 전달했는지 확인
        fake_client.cancel_order.assert_awaited_once()
        kwargs = fake_client.cancel_order.await_args.kwargs
        assert kwargs.get("timeout_sec") == 2.0
        assert kwargs.get("idempotency_key") == "cancel-xyz"


# ---------------------------------------------------------------------------
# 7. KisAuth 토큰 발급 — httpx mock
# ---------------------------------------------------------------------------
class TestKisAuth:
    @pytest.mark.asyncio
    async def test_token_endpoint_call(self):
        """KisAuth._call_token_endpoint 가 expires_at 을 정확히 계산하는지."""
        auth = KisAuth(appkey="k", appsecret="s", trade_mode="SIM")

        class FakeResp:
            status_code = 200

            def json(self):
                return {
                    "access_token": "TOKEN_AAA",
                    "token_type": "Bearer",
                    "expires_in": 86400,
                }

        class FakeClient:
            def __init__(self, *a, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a, **kw):
                return False

            async def post(self, *a, **kw):
                return FakeResp()

        with patch("app.integrations.kis.auth.httpx.AsyncClient", FakeClient):
            token = await auth._call_token_endpoint()
        assert token.access_token == "TOKEN_AAA"
        assert token.bearer() == "Bearer TOKEN_AAA"
        # 1시간 사전 마진 → expires_at 은 약 82800초 이후
        assert token.expires_at > time.time() + 82000
        assert token.expires_at < time.time() + 86400

    @pytest.mark.asyncio
    async def test_token_no_credentials_raises(self):
        """자격증명 미설정 시 E0001 raise.

        ``KisAuth.__init__`` 는 빈 문자열을 config 기본값으로 대체하므로,
        instance 의 ``appkey/appsecret`` 을 직접 비워서 검증한다.
        """
        from app.core.exceptions import AppException

        auth = KisAuth(trade_mode="SIM")
        # 인스턴스 단위로 비워야 config fallback 도 회피
        auth.appkey = ""
        auth.appsecret = ""
        with pytest.raises(AppException) as exc:
            await auth._call_token_endpoint()
        assert exc.value.code == "E0001"
