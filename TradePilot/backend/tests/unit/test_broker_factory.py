"""다증권사 factory 단위 테스트 (D4).

검증:
- enum / BROKER_REGISTRY 일관성
- 환경변수/유저 선호 broker 우선순위
- factory 가 정확한 LiveOrderRouter / MarketData 인스턴스 반환
- FallbackOrderRouter: 게이트웨이 장애(E0012) → backup 으로 1회 재시도
- FallbackOrderRouter: 비즈니스 거부(E0024) → fallback 하지 않고 그대로 전파
- 취소(cancel_order) 는 fallback 금지
"""
from __future__ import annotations

import os
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.core.exceptions import AppException
from app.domains.brokers import (
    BROKER_REGISTRY,
    Broker,
    BrokerApiType,
    BrokerInfo,
    get_broker_info,
    list_broker_infos,
)


# ---------------------------------------------------------------------------
# 1. Broker enum / Registry
# ---------------------------------------------------------------------------
class TestBrokerRegistry:
    def test_enum_values(self):
        assert Broker.CREON.value == "CREON"
        assert Broker.KIS.value == "KIS"
        assert Broker.KIWOOM.value == "KIWOOM"

    def test_all_brokers_have_info(self):
        for b in Broker:
            info = get_broker_info(b)
            assert isinstance(info, BrokerInfo)
            assert info.broker is b

    def test_kis_is_rest_no_windows(self):
        kis = get_broker_info(Broker.KIS)
        assert kis.api_type is BrokerApiType.REST
        assert kis.requires_windows is False
        assert kis.recommended is True

    def test_kiwoom_is_com_windows(self):
        k = get_broker_info(Broker.KIWOOM)
        assert k.api_type is BrokerApiType.COM
        assert k.requires_windows is True

    def test_list_returns_all(self):
        infos = list_broker_infos()
        assert len(infos) == len(BROKER_REGISTRY)


# ---------------------------------------------------------------------------
# 2. Factory — broker 결정 우선순위
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_factory_cache():
    from app.integrations import factory

    factory.reset_factory_cache()
    # 환경변수 보존
    orig_default = os.environ.get("DEFAULT_BROKER")
    orig_fb_en = os.environ.get("BROKER_FALLBACK_ENABLED")
    orig_fb_bk = os.environ.get("BROKER_FALLBACK_BACKUP")
    yield
    factory.reset_factory_cache()
    # 복원
    for k, v in (
        ("DEFAULT_BROKER", orig_default),
        ("BROKER_FALLBACK_ENABLED", orig_fb_en),
        ("BROKER_FALLBACK_BACKUP", orig_fb_bk),
    ):
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v


class TestBrokerResolution:
    def test_sim_mode_ignores_broker(self):
        from app.integrations.factory import get_order_router
        from app.integrations.simulator.sim_order_router import SimOrderRouter

        router = get_order_router("SIM")
        assert isinstance(router, SimOrderRouter)

        # broker 명시도 무시 (SIM 은 sim router)
        router2 = get_order_router("SIM", broker=Broker.KIS)
        assert isinstance(router2, SimOrderRouter)

    def test_live_explicit_broker_kis(self):
        from app.integrations.factory import get_order_router
        from app.integrations.kis.live_order_router import KisLiveOrderRouter

        router = get_order_router("LIVE", broker=Broker.KIS)
        assert isinstance(router, KisLiveOrderRouter)

    def test_live_explicit_broker_kiwoom(self):
        from app.integrations.factory import get_order_router
        from app.integrations.kiwoom.live_order_router import KiwoomLiveOrderRouter

        router = get_order_router("LIVE", broker=Broker.KIWOOM)
        assert isinstance(router, KiwoomLiveOrderRouter)

    def test_live_explicit_broker_creon(self):
        from app.integrations.creon.live_order_router import LiveOrderRouter
        from app.integrations.factory import get_order_router

        router = get_order_router("LIVE", broker=Broker.CREON)
        assert isinstance(router, LiveOrderRouter)

    def test_live_user_preferred_broker(self):
        """user.preferred_broker 가 KIS 면 KIS 라우터 선택."""
        from app.integrations.factory import get_order_router
        from app.integrations.kis.live_order_router import KisLiveOrderRouter

        user = SimpleNamespace(id=1, preferred_broker="KIS")
        router = get_order_router("LIVE", user=user)
        assert isinstance(router, KisLiveOrderRouter)

    def test_live_default_env(self):
        """DEFAULT_BROKER 환경변수가 우선순위 (사용자 + 명시 미설정 시)."""
        from app.integrations import factory
        from app.integrations.factory import get_order_router
        from app.integrations.kis.live_order_router import KisLiveOrderRouter

        os.environ["DEFAULT_BROKER"] = "KIS"
        factory.reset_factory_cache()
        router = get_order_router("LIVE")
        assert isinstance(router, KisLiveOrderRouter)

    def test_user_invalid_pref_falls_back_default(self):
        """잘못된 user.preferred_broker 는 시스템 기본으로 fallback."""
        from app.integrations import factory
        from app.integrations.creon.live_order_router import LiveOrderRouter
        from app.integrations.factory import get_order_router

        os.environ["DEFAULT_BROKER"] = "CREON"
        factory.reset_factory_cache()
        user = SimpleNamespace(id=1, preferred_broker="UNKNOWN_BROKER")
        router = get_order_router("LIVE", user=user)
        assert isinstance(router, LiveOrderRouter)


# ---------------------------------------------------------------------------
# 3. FallbackOrderRouter
# ---------------------------------------------------------------------------
class TestFallbackRouter:
    @pytest.mark.asyncio
    async def test_fallback_on_gateway_error(self):
        """주 broker E0012 → backup 으로 재시도."""
        from app.domains.ports.order_router_port import OrderRequest, OrderResult
        from app.integrations.factory import FallbackOrderRouter

        primary = MagicMock()
        primary.submit_order = AsyncMock(
            side_effect=AppException("E0012", message="게이트웨이 미연결")
        )
        backup = MagicMock()
        backup.submit_order = AsyncMock(
            return_value=OrderResult(accepted=True, status="ACCEPTED", broker_order_no="BK-1")
        )
        router = FallbackOrderRouter(primary=primary, backup=backup)
        req = OrderRequest(
            order_id=1,
            user_id=1,
            stock_code="005930",
            side="BUY",
            order_type="LIMIT",
            qty=Decimal("10"),
            price=Decimal("70000"),
            trade_mode="LIVE",
        )
        result = await router.submit_order(req)
        assert result.accepted
        assert result.broker_order_no == "BK-1"
        primary.submit_order.assert_awaited_once()
        backup.submit_order.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_no_fallback_on_business_reject(self):
        """비즈니스 거부(E0024) 는 fallback 대상이 아님 — 그대로 전파."""
        from app.domains.ports.order_router_port import OrderRequest
        from app.integrations.factory import FallbackOrderRouter

        primary = MagicMock()
        primary.submit_order = AsyncMock(
            side_effect=AppException("E0024", message="증거금 부족")
        )
        backup = MagicMock()
        backup.submit_order = AsyncMock()
        router = FallbackOrderRouter(primary=primary, backup=backup)
        req = OrderRequest(
            order_id=1,
            user_id=1,
            stock_code="005930",
            side="BUY",
            order_type="LIMIT",
            qty=Decimal("1000"),
            price=Decimal("70000"),
            trade_mode="LIVE",
        )
        with pytest.raises(AppException) as exc:
            await router.submit_order(req)
        assert exc.value.code == "E0024"
        backup.submit_order.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_cancel_does_not_fallback(self):
        """취소는 broker_order_no 가 원래 broker 종속이므로 fallback 금지."""
        from app.integrations.factory import FallbackOrderRouter

        primary = MagicMock()
        primary.cancel_order = AsyncMock(
            side_effect=AppException("E0012", message="게이트웨이 미연결")
        )
        backup = MagicMock()
        backup.cancel_order = AsyncMock()
        router = FallbackOrderRouter(primary=primary, backup=backup)
        with pytest.raises(AppException) as exc:
            await router.cancel_order(
                order_id=1, broker_order_no="X", stock_code="005930"
            )
        assert exc.value.code == "E0012"
        backup.cancel_order.assert_not_awaited()

    def test_factory_wraps_when_env_enabled(self):
        """BROKER_FALLBACK_ENABLED + BACKUP 다르면 FallbackOrderRouter 반환."""
        from app.integrations import factory
        from app.integrations.factory import FallbackOrderRouter, get_order_router

        os.environ["DEFAULT_BROKER"] = "CREON"
        os.environ["BROKER_FALLBACK_ENABLED"] = "true"
        os.environ["BROKER_FALLBACK_BACKUP"] = "KIS"
        factory.reset_factory_cache()
        router = get_order_router("LIVE")
        assert isinstance(router, FallbackOrderRouter)

    def test_factory_no_wrap_when_backup_equals_primary(self):
        """주==백업 인 경우 FallbackOrderRouter 미적용."""
        from app.integrations import factory
        from app.integrations.factory import FallbackOrderRouter, get_order_router

        os.environ["DEFAULT_BROKER"] = "CREON"
        os.environ["BROKER_FALLBACK_ENABLED"] = "true"
        os.environ["BROKER_FALLBACK_BACKUP"] = "CREON"
        factory.reset_factory_cache()
        router = get_order_router("LIVE")
        assert not isinstance(router, FallbackOrderRouter)
