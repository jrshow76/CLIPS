"""KIS (한국투자증권 Open API) 어댑터 패키지.

`docs/50_multi_broker_guide.md` §3 참조.

- 외부 통신: REST(주문/조회) + WebSocket(실시간 시세)
- 환경: 모의투자 / 실거래 분리 (도메인 URL 다름)
- 인증: OAuth2 access_token (24시간) — Redis 캐시 + 자동 갱신
- Rate Limit: 초당 약 20건 (안전 마진 16건/sec)

본 패키지의 외부 사용 진입점:
- ``LiveOrderRouter`` (OrderRouterPort 구현)
- ``LiveMarketData`` (MarketDataPort 구현)
- ``KisClient`` (저수준 httpx 클라이언트)
- ``KisAuth`` (토큰 발급/갱신)
"""
from app.integrations.kis.auth import KisAuth, get_kis_auth
from app.integrations.kis.client import KisClient, get_kis_client
from app.integrations.kis.live_market_data import KisLiveMarketData
from app.integrations.kis.live_order_router import KisLiveOrderRouter

__all__ = [
    "KisAuth",
    "KisClient",
    "KisLiveMarketData",
    "KisLiveOrderRouter",
    "get_kis_auth",
    "get_kis_client",
]
