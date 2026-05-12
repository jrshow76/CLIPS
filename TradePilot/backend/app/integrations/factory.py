"""트레이드 모드별 라우터/시세 어댑터 팩토리.

OrderService 등 서비스 계층에서 사용자 trade_mode에 따라 적절한 구현체를 받아간다.
"""
from __future__ import annotations

from functools import lru_cache

from app.domains.enums import TradeMode
from app.domains.ports.market_data_port import MarketDataPort
from app.domains.ports.order_router_port import OrderRouterPort
from app.integrations.creon.live_market_data import LiveMarketData
from app.integrations.creon.live_order_router import LiveOrderRouter
from app.integrations.simulator.sim_market_data import SimMarketData
from app.integrations.simulator.sim_order_router import SimOrderRouter


@lru_cache(maxsize=1)
def get_sim_market_data() -> SimMarketData:
    return SimMarketData()


@lru_cache(maxsize=1)
def get_live_market_data() -> LiveMarketData:
    return LiveMarketData()


@lru_cache(maxsize=1)
def get_sim_router() -> SimOrderRouter:
    return SimOrderRouter(market_data=get_sim_market_data())


@lru_cache(maxsize=1)
def get_live_router() -> LiveOrderRouter:
    return LiveOrderRouter()


def get_order_router(trade_mode: str) -> OrderRouterPort:
    """모드별 주문 라우터."""
    if trade_mode == TradeMode.LIVE.value:
        return get_live_router()
    return get_sim_router()


def get_market_data(trade_mode: str = "SIM") -> MarketDataPort:
    """모드별 시세 어댑터.

    조회성 API는 SIM/LIVE 모두 DB 기반 SimMarketData 가 기본이며,
    실시간 시세가 필요한 경우에만 LiveMarketData를 사용한다.
    """
    if trade_mode == TradeMode.LIVE.value:
        return get_live_market_data()
    return get_sim_market_data()
