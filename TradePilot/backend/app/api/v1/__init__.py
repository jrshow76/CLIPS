"""v1 API 라우터 통합.

BackendDev가 새 도메인 라우터를 추가할 때 본 파일의 `register_v1_routers()`에 등록한다.
"""
from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.orders import router as orders_router

# 메타 라우터 (헬스/시스템)
meta_router = APIRouter()


def register_v1_routers(parent: APIRouter) -> None:
    """v1 라우터를 부모(FastAPI 앱 또는 prefix 라우터)에 등록."""
    parent.include_router(auth_router)
    parent.include_router(orders_router)
    # BackendDev가 추가할 도메인 라우터:
    # parent.include_router(stocks_router)
    # parent.include_router(indicators_router)
    # parent.include_router(sectors_router)
    # parent.include_router(recommendations_router)
    # parent.include_router(signals_router)
    # parent.include_router(strategies_router)
    # parent.include_router(portfolios_router)
    # parent.include_router(backtest_router)
    # parent.include_router(ml_predictions_router)
    # parent.include_router(market_router)
    # parent.include_router(notifications_router)
    # parent.include_router(settings_router)
    # parent.include_router(reports_router)
    # parent.include_router(admin_router)
