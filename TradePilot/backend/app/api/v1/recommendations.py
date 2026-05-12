"""추천주 API 라우터.

`docs/13_api_requirements.md` §6 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AppException
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.models.analysis import MLPrediction
from app.models.trade import Strategy
from app.repositories.recommendation_repository import RecommendationRepository
from app.repositories.sector_repository import SectorRepository
from app.repositories.stock_repository import StockExtRepository
from app.schemas.recommendation import (
    RecommendationDetail,
    RecommendationItem,
    StrategyMetaItem,
    TopRecommendation,
)

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("", summary="추천주 목록")
async def list_recommendations(
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    strategy_id: str | None = Query(None, description="전략 public_id"),
    sector: str | None = Query(None, description="섹터 코드"),
    market_cap_min: int | None = Query(None, ge=0),
    market_cap_max: int | None = Query(None, ge=0),
    sort: str = Query("score,desc"),
):
    repo = RecommendationRepository(db)

    # strategy_id 변환
    strategy_pk: int | None = None
    if strategy_id:
        from sqlalchemy import select as _s

        s_row = (
            await db.execute(_s(Strategy).where(Strategy.public_id == strategy_id))
        ).scalar_one_or_none()
        if not s_row:
            raise AppException("E0062", message="전략을 찾을 수 없습니다.")
        strategy_pk = s_row.id

    # sector 변환
    sector_pk: int | None = None
    if sector:
        sec = await SectorRepository(db).find_by_code(sector)
        if not sec:
            raise AppException("E0062", message="섹터를 찾을 수 없습니다.")
        sector_pk = sec.id

    rows, total = await repo.list_by_filters(
        strategy_id=strategy_pk,
        sector_id=sector_pk,
        market_cap_min=market_cap_min,
        market_cap_max=market_cap_max,
        sort=sort,
        offset=page.offset,
        limit=page.limit,
    )

    stock_repo = StockExtRepository(db)
    items: list[RecommendationItem] = []
    for reco, stock in rows:
        latest = await stock_repo.latest_daily(stock.id)
        items.append(
            RecommendationItem(
                id=str(reco.id),
                code=stock.code,
                name=stock.name,
                score=reco.score,
                reason_code=reco.reason_code,
                reason=reco.reason_text,
                current_price=latest.close if latest else None,
                change_pct=latest.change_pct if latest else None,
                trade_date=reco.trade_date,
            )
        )
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.get("/top", summary="추천 TOP-N")
async def top(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(5, ge=1, le=20),
):
    repo = RecommendationRepository(db)
    rows = await repo.top_n(limit=limit)
    items = [
        TopRecommendation(
            code=stock.code,
            name=stock.name,
            score=reco.score,
            reason_code=reco.reason_code,
        )
        for reco, stock in rows
    ]
    return success_response([i.model_dump() for i in items])


@router.get("/strategies", summary="추천 산출에 사용된 전략 메타")
async def strategies_meta(db: AsyncSession = Depends(get_db)):
    """현재 사용 중인 추천 전략들의 메타 (간이: 활성 전략 N개)."""
    stmt = select(Strategy).where(Strategy.active.is_(True), Strategy.deleted_at.is_(None)).limit(20)
    rows = (await db.execute(stmt)).scalars().all()
    items = [
        StrategyMetaItem(id=str(s.public_id), name=s.name, description=s.description)
        for s in rows
    ]
    return success_response([i.model_dump() for i in items])


@router.get("/{code}/detail", summary="추천 상세 + 지표 + ML 예측")
async def detail(code: str, db: AsyncSession = Depends(get_db)):
    repo = RecommendationRepository(db)
    found = await repo.find_by_code(code)
    if not found:
        raise AppException("E0062", message="해당 종목 추천 데이터가 없습니다.")
    reco, stock = found

    # 일봉 + 지표 캐시
    stock_repo = StockExtRepository(db)
    last = await stock_repo.latest_daily(stock.id)
    indicators_dict = {}
    from app.models.analysis import IndicatorDaily

    if last:
        ind = await db.get(IndicatorDaily, (stock.id, last.trade_date))
        if ind:
            indicators_dict = {
                "ma5": ind.ma5,
                "ma20": ind.ma20,
                "ma60": ind.ma60,
                "rsi14": ind.rsi14,
                "macd": ind.macd,
                "bb_mid": ind.bb_mid,
            }

    # ML 예측
    from sqlalchemy import desc as _desc

    ml_row = (
        await db.execute(
            select(MLPrediction)
            .where(MLPrediction.stock_id == stock.id)
            .order_by(_desc(MLPrediction.base_date))
            .limit(1)
        )
    ).scalar_one_or_none()
    ml_dict = None
    if ml_row:
        ml_dict = {
            "horizon": ml_row.horizon,
            "pred_mean": ml_row.pred_mean,
            "pred_lower": ml_row.pred_lower,
            "pred_upper": ml_row.pred_upper,
            "model_version": ml_row.model_version,
        }

    return success_response(
        RecommendationDetail(
            code=stock.code,
            name=stock.name,
            score=reco.score,
            reason_code=reco.reason_code,
            reason=reco.reason_text,
            features=reco.features or {},
            indicators=indicators_dict,
            ml_prediction=ml_dict,
        )
    )
