"""주문 도메인 Pydantic 스키마.

`docs/13_api_requirements.md` §9, `docs/15_trading_policy.md` 매매 정책 준수.
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


OrderSide = Literal["BUY", "SELL"]
OrderType = Literal["MARKET", "LIMIT"]
TradeMode = Literal["SIM", "LIVE"]
OrderStatus = Literal[
    "NEW", "ACCEPTED", "PENDING", "PARTIAL", "FILLED", "CANCELED", "REJECTED", "EXPIRED"
]


class OrderCreateIn(BaseModel):
    """주문 생성 요청."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=6, max_length=6, description="6자리 종목코드")
    side: OrderSide
    qty: int = Field(ge=1, le=10_000)
    order_type: OrderType
    price: Decimal | None = None  # MARKET 시 None
    strategy_id: str | None = None  # public_id (UUID)

    @field_validator("code")
    @classmethod
    def _validate_code(cls, v: str) -> str:
        if not v.isdigit() or len(v) != 6:
            raise ValueError("종목코드는 6자리 숫자여야 합니다.")
        return v

    @field_validator("price")
    @classmethod
    def _validate_price(cls, v: Decimal | None, info) -> Decimal | None:
        if v is not None and v <= 0:
            raise ValueError("price는 0보다 커야 합니다.")
        return v


class OrderOut(BaseModel):
    """주문 응답."""

    id: str  # public_id (UUID)
    code: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Decimal | None = None
    status: OrderStatus
    mode: TradeMode
    broker_order_no: str | None = None
    reject_reason: str | None = None
    created_at: datetime
    filled_at: datetime | None = None


class OrderListItem(BaseModel):
    """주문 목록 아이템."""

    id: str
    code: str
    side: OrderSide
    order_type: OrderType
    qty: Decimal
    price: Decimal | None = None
    status: OrderStatus
    mode: TradeMode
    created_at: datetime
    filled_at: datetime | None = None


class CancelOrderResponse(BaseModel):
    id: str
    status: OrderStatus
    canceled: bool


class LiquidateAllRequest(BaseModel):
    reason: str | None = None


class LiquidateAllResponse(BaseModel):
    processed: list[str] = Field(default_factory=list)
    failed: list[dict] = Field(default_factory=list)
