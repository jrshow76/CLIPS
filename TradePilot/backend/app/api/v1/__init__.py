"""v1 API 라우터 통합.

BackendDev가 새 도메인 라우터를 추가할 때 본 파일의 `register_v1_routers()`에 등록한다.
"""
from fastapi import APIRouter

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.backtest import router as backtest_router
from app.api.v1.indicators import router as indicators_router
from app.api.v1.market import admin_calendar_router as market_admin_calendar_router
from app.api.v1.market import router as market_router
from app.api.v1.ml_predictions import ml_router as ml_v2_router
from app.api.v1.ml_predictions import router as ml_predictions_router
from app.api.v1.notifications import router as notifications_router
from app.api.v1.orders import router as orders_router
from app.api.v1.portfolios import router as portfolios_router
from app.api.v1.recommendations import router as recommendations_router
from app.api.v1.reports import router as reports_router
from app.api.v1.sectors import router as sectors_router
from app.api.v1.settings import router as settings_router
from app.api.v1.signals import router as signals_router
from app.api.v1.stocks import router as stocks_router
from app.api.v1.strategies import router as strategies_router
from app.api.v1.users import router as users_router

# 메타 라우터 (헬스/시스템)
meta_router = APIRouter()


def register_v1_routers(parent: APIRouter) -> None:
    """v1 라우터를 부모(FastAPI 앱 또는 prefix 라우터)에 등록."""
    # 인증 / 사용자
    parent.include_router(auth_router)
    parent.include_router(users_router)
    # 시장 데이터
    parent.include_router(stocks_router)
    parent.include_router(indicators_router)
    parent.include_router(sectors_router)
    parent.include_router(market_router)
    # 분석/시그널/추천
    parent.include_router(recommendations_router)
    parent.include_router(signals_router)
    parent.include_router(ml_predictions_router)
    parent.include_router(ml_v2_router)
    # 매매
    parent.include_router(orders_router)
    parent.include_router(strategies_router)
    parent.include_router(portfolios_router)
    parent.include_router(backtest_router)
    # 알림/설정/리포트/관리자
    parent.include_router(notifications_router)
    parent.include_router(settings_router)
    parent.include_router(reports_router)
    parent.include_router(admin_router)
    # 관리자 - 시장 캘린더 (별도 prefix /admin/market/calendar)
    parent.include_router(market_admin_calendar_router)
