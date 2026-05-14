"""트레이드 모드/증권사별 라우터/시세 어댑터 팩토리.

본 파일은 OrderService 등 서비스 계층이 사용자(trade_mode + preferred_broker)에
따라 적절한 구현체를 받아가도록 한다.

확장 포인트:
- ``get_order_router(trade_mode, *, user=None, broker=None)``
  * SIM → SimOrderRouter
  * LIVE → 사용자 preferred_broker (또는 시스템 기본값) 기반 구현체
- ``get_market_data(trade_mode, *, broker=None)`` 동일 원칙

추가 정책:
- ``FallbackOrderRouter``: 주 broker 가 503/E0012 등 게이트웨이 장애 시
  설정된 backup broker 로 1회 재시도 (옵션, 기본 OFF).
"""
from __future__ import annotations

import os
from functools import lru_cache
from typing import TYPE_CHECKING

import structlog

from app.core.exceptions import AppException
from app.domains.brokers import DEFAULT_BROKER, Broker
from app.domains.enums import TradeMode
from app.domains.ports.market_data_port import MarketDataPort
from app.domains.ports.order_router_port import (
    OrderRequest,
    OrderResult,
    OrderRouterPort,
)
from app.integrations.creon.live_market_data import LiveMarketData as CreonLiveMarketData
from app.integrations.creon.live_order_router import LiveOrderRouter as CreonLiveOrderRouter
from app.integrations.kis.live_market_data import KisLiveMarketData
from app.integrations.kis.live_order_router import KisLiveOrderRouter
from app.integrations.kiwoom.live_market_data import KiwoomLiveMarketData
from app.integrations.kiwoom.live_order_router import KiwoomLiveOrderRouter
from app.integrations.simulator.sim_market_data import SimMarketData
from app.integrations.simulator.sim_order_router import SimOrderRouter

if TYPE_CHECKING:
    from app.models.user import User

log = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Sim/Live 싱글톤 (broker 별 분리 캐시)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def get_sim_market_data() -> SimMarketData:
    return SimMarketData()


@lru_cache(maxsize=1)
def get_sim_router() -> SimOrderRouter:
    return SimOrderRouter(market_data=get_sim_market_data())


@lru_cache(maxsize=1)
def _get_creon_router() -> CreonLiveOrderRouter:
    return CreonLiveOrderRouter()


@lru_cache(maxsize=1)
def _get_creon_market() -> CreonLiveMarketData:
    return CreonLiveMarketData()


@lru_cache(maxsize=1)
def _get_kis_router() -> KisLiveOrderRouter:
    return KisLiveOrderRouter()


@lru_cache(maxsize=1)
def _get_kis_market() -> KisLiveMarketData:
    return KisLiveMarketData()


@lru_cache(maxsize=1)
def _get_kiwoom_router() -> KiwoomLiveOrderRouter:
    return KiwoomLiveOrderRouter()


@lru_cache(maxsize=1)
def _get_kiwoom_market() -> KiwoomLiveMarketData:
    return KiwoomLiveMarketData()


# 호환 alias (기존 코드 영향 차단)
def get_live_market_data() -> MarketDataPort:
    """기존 호출자 호환: 시스템 기본 broker 의 LIVE 시세 어댑터 반환."""
    return _market_for_broker(_resolve_default_broker())


def get_live_router() -> OrderRouterPort:
    """기존 호출자 호환: 시스템 기본 broker 의 LIVE 라우터 반환."""
    return _router_for_broker(_resolve_default_broker())


# ---------------------------------------------------------------------------
# Broker 결정
# ---------------------------------------------------------------------------
def _resolve_default_broker() -> Broker:
    """환경변수 ``DEFAULT_BROKER`` → 미설정 시 ``DEFAULT_BROKER`` (CREON)."""
    raw = (os.environ.get("DEFAULT_BROKER") or "").upper()
    try:
        return Broker(raw) if raw else DEFAULT_BROKER
    except ValueError:
        log.warning("invalid_default_broker_env", value=raw, fallback=DEFAULT_BROKER.value)
        return DEFAULT_BROKER


def _resolve_broker(
    user: "User | None", broker: Broker | str | None
) -> Broker:
    """우선순위: (1) 명시 파라미터 (2) user.preferred_broker (3) 시스템 기본."""
    if broker is not None:
        return Broker(broker) if isinstance(broker, str) else broker
    if user is not None:
        # users 테이블 마이그레이션 이후 추가된 컬럼. getattr 로 안전 접근.
        pref = getattr(user, "preferred_broker", None)
        if pref:
            try:
                return Broker(pref)
            except ValueError:
                log.warning(
                    "invalid_user_preferred_broker",
                    user_id=user.id,
                    value=pref,
                )
    return _resolve_default_broker()


def _router_for_broker(broker: Broker) -> OrderRouterPort:
    if broker is Broker.KIS:
        return _get_kis_router()
    if broker is Broker.KIWOOM:
        return _get_kiwoom_router()
    return _get_creon_router()


def _market_for_broker(broker: Broker) -> MarketDataPort:
    if broker is Broker.KIS:
        return _get_kis_market()
    if broker is Broker.KIWOOM:
        return _get_kiwoom_market()
    return _get_creon_market()


# ---------------------------------------------------------------------------
# Fallback 라우터 (주 → 백업 broker)
# ---------------------------------------------------------------------------
# 어댑터 장애로 간주할 에러 코드 — 백업 broker 로 재시도.
# (비즈니스 거부는 fallback 대상이 아님 — 잔고부족 등은 그대로 실패해야 한다.)
_FALLBACK_TRIGGER_CODES: frozenset[str] = frozenset(
    {
        "E0012",  # 게이트웨이 미연결
        "E0004",  # 게이트웨이 내부 오류
        "E0072",  # 응답 타임아웃
    }
)


class FallbackOrderRouter(OrderRouterPort):
    """주 broker 장애 시 백업 broker 로 1회 재시도 하는 라우터.

    ``submit_order`` 만 fallback 한다. ``cancel_order`` 는 broker_order_no 가
    원래 broker 에 종속이므로 fallback 하지 않는다 (잘못된 broker 에 취소 보내면
    더 큰 사고).
    """

    def __init__(
        self, primary: OrderRouterPort, backup: OrderRouterPort
    ) -> None:
        self.primary = primary
        self.backup = backup

    async def submit_order(self, request: OrderRequest) -> OrderResult:
        try:
            return await self.primary.submit_order(request)
        except AppException as e:
            if e.code in _FALLBACK_TRIGGER_CODES:
                log.warning(
                    "broker_fallback_triggered",
                    primary_error=e.code,
                    order_id=request.order_id,
                )
                return await self.backup.submit_order(request)
            raise

    async def cancel_order(
        self,
        order_id: int,
        broker_order_no: str | None,
        stock_code: str,
        *,
        timeout_sec: float | None = None,
        idempotency_key: str | None = None,
    ) -> OrderResult:
        # 취소는 fallback 금지 — broker_order_no 가 원래 broker 에 귀속됨.
        return await self.primary.cancel_order(
            order_id,
            broker_order_no,
            stock_code,
            timeout_sec=timeout_sec,
            idempotency_key=idempotency_key,
        )

    async def get_order_status(
        self, order_id: int, broker_order_no: str | None
    ) -> OrderResult:
        return await self.primary.get_order_status(order_id, broker_order_no)


def _fallback_backup_broker() -> Broker | None:
    """환경변수 ``BROKER_FALLBACK_BACKUP`` (KIS/KIWOOM/CREON) — 없으면 비활성."""
    raw = (os.environ.get("BROKER_FALLBACK_BACKUP") or "").upper()
    if not raw:
        return None
    try:
        return Broker(raw)
    except ValueError:
        log.warning("invalid_broker_fallback_env", value=raw)
        return None


def _fallback_enabled() -> bool:
    return (
        os.environ.get("BROKER_FALLBACK_ENABLED", "false").lower() == "true"
        and _fallback_backup_broker() is not None
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def get_order_router(
    trade_mode: str,
    *,
    user: "User | None" = None,
    broker: Broker | str | None = None,
) -> OrderRouterPort:
    """매매 모드 + 사용자 선호 broker 기반 주문 라우터.

    호환성:
    - 기존 호출 ``get_order_router("SIM")`` 동작 유지.
    - 신규 호출 ``get_order_router("LIVE", user=user)`` → user.preferred_broker 사용.

    Fallback:
    - 환경변수 ``BROKER_FALLBACK_ENABLED=true`` + ``BROKER_FALLBACK_BACKUP=KIS`` 등
      설정 시 주 라우터를 ``FallbackOrderRouter`` 로 wrapping.
    """
    if trade_mode != TradeMode.LIVE.value:
        return get_sim_router()

    chosen = _resolve_broker(user, broker)
    primary = _router_for_broker(chosen)
    if not _fallback_enabled():
        return primary

    backup_broker = _fallback_backup_broker()
    if backup_broker is None or backup_broker is chosen:
        return primary
    backup = _router_for_broker(backup_broker)
    log.info(
        "fallback_router_active",
        primary=chosen.value,
        backup=backup_broker.value,
    )
    return FallbackOrderRouter(primary=primary, backup=backup)


def get_market_data(
    trade_mode: str = "SIM",
    *,
    user: "User | None" = None,
    broker: Broker | str | None = None,
) -> MarketDataPort:
    """모드별 시세 어댑터.

    SIM/LIVE 모두 DB 기반 SimMarketData가 기본. 실시간 시세가 필요할 때만
    broker별 LiveMarketData 사용.
    """
    if trade_mode != TradeMode.LIVE.value:
        return get_sim_market_data()
    chosen = _resolve_broker(user, broker)
    return _market_for_broker(chosen)


# ---------------------------------------------------------------------------
# 테스트 헬퍼
# ---------------------------------------------------------------------------
def reset_factory_cache() -> None:
    """모든 어댑터 싱글톤 캐시 무효화 (테스트용)."""
    get_sim_market_data.cache_clear()
    get_sim_router.cache_clear()
    _get_creon_router.cache_clear()
    _get_creon_market.cache_clear()
    _get_kis_router.cache_clear()
    _get_kis_market.cache_clear()
    _get_kiwoom_router.cache_clear()
    _get_kiwoom_market.cache_clear()
