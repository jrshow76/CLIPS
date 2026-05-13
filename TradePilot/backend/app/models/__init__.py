"""SQLAlchemy ORM 모델 패키지.

DDL은 `database/init/*.sql` 로 관리하며, 본 모델 클래스는 1:1 매핑 용도이다.
모든 모델은 `Base = DeclarativeBase` 상속.
"""
from app.models.base import Base, TimestampMixin
from app.models.user import (
    AuditLogin,
    OtpCode,
    Session,
    User,
    UserFavorite,
    UserProfile,
    UserSettings,
)
from app.models.market import (
    CorporateAction,
    MarketCalendar,
    MarketIndex,
    MarketIndexDaily,
    PriceDaily,
    PriceMinute,
    Sector,
    Stock,
    StockSector,
)
from app.models.analysis import (
    IndicatorDaily,
    MLPrediction,
    Recommendation,
    SectorMetricsDaily,
    Signal,
)
from app.models.trade import (
    DailyPnl,
    Fill,
    KillSwitchLog,
    Order,
    Portfolio,
    Position,
    Strategy,
    StrategyRule,
    TradeLimit,
)
from app.models.backtest import BacktestResult, BacktestRun, BacktestTrade
from app.models.notification import AlertRule, Notification, NotificationChannel

__all__ = [
    "Base",
    "TimestampMixin",
    # user
    "User",
    "UserProfile",
    "UserSettings",
    "OtpCode",
    "Session",
    "UserFavorite",
    "AuditLogin",
    # market
    "Stock",
    "Sector",
    "StockSector",
    "PriceDaily",
    "PriceMinute",
    "CorporateAction",
    "MarketIndex",
    "MarketIndexDaily",
    "MarketCalendar",
    # analysis
    "IndicatorDaily",
    "SectorMetricsDaily",
    "Recommendation",
    "Signal",
    "MLPrediction",
    # trade
    "Strategy",
    "StrategyRule",
    "Order",
    "Fill",
    "Position",
    "Portfolio",
    "DailyPnl",
    "TradeLimit",
    "KillSwitchLog",
    # backtest
    "BacktestRun",
    "BacktestResult",
    "BacktestTrade",
    # notification
    "Notification",
    "NotificationChannel",
    "AlertRule",
]
