"""도메인 열거형 모음."""
from enum import Enum


class TradeMode(str, Enum):
    """매매 모드."""

    SIM = "SIM"
    LIVE = "LIVE"


class OrderSide(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"


class OrderStatus(str, Enum):
    """주문 상태. DDL의 ck_orders_status와 일치."""

    NEW = "NEW"
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    ACCEPTED = "ACCEPTED"  # LIVE 라우터가 게이트웨이 수락 후 사용 (서비스 레이어 매핑용)


class SignalAction(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class SignalStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXECUTED = "EXECUTED"
    IGNORED = "IGNORED"
    EXPIRED = "EXPIRED"


class Role(str, Enum):
    """RBAC 역할."""

    ADMIN = "ROLE_ADMIN"
    OPERATOR = "ROLE_OPERATOR"
    TRADER_PRO = "ROLE_TRADER_PRO"
    TRADER = "ROLE_TRADER"
    GUEST = "ROLE_GUEST"
