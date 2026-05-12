"""도메인 포트(인터페이스) 패키지.

외부 시스템(증권사, 시세, 알림 등)에 대한 추상 인터페이스를 정의한다.
구현체는 `app.integrations.*` 에 위치.
"""
from app.domains.ports.order_router_port import (
    OrderRequest,
    OrderResult,
    OrderRouterPort,
)
from app.domains.ports.market_data_port import (
    MarketDataPort,
    OrderbookSnapshot,
    QuoteSnapshot,
)
from app.domains.ports.account_port import (
    AccountBalance,
    AccountPort,
    ExecutionEvent,
    PositionSnapshot,
)

__all__ = [
    "OrderRouterPort",
    "OrderRequest",
    "OrderResult",
    "MarketDataPort",
    "QuoteSnapshot",
    "OrderbookSnapshot",
    "AccountPort",
    "AccountBalance",
    "PositionSnapshot",
    "ExecutionEvent",
]
