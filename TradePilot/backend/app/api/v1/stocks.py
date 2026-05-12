"""종목/시세 API 라우터.

`docs/13_api_requirements.md` §3 명세 구현.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core.pagination import PageParams, page_params
from app.core.response import page_response, success_response
from app.schemas.stock import (
    CandleItem,
    FavoriteIn,
    FavoriteItem,
    OrderbookOut,
    QuoteOut,
    StockOut,
    StockSearchItem,
)
from app.services.stock_service import StockService

router = APIRouter(prefix="/stocks", tags=["stocks"])


@router.get("/search", summary="종목 검색")
async def search_stocks(
    db: AsyncSession = Depends(get_db),
    page: PageParams = Depends(page_params),
    q: str | None = Query(None, description="이름/코드 검색어"),
    market: str | None = Query(None, description="KOSPI|KOSDAQ"),
):
    svc = StockService(db)
    rows, total = await svc.search(q=q, market=market, offset=page.offset, limit=page.limit)
    items: list[StockSearchItem] = []
    for s in rows:
        sector = await svc.stocks.get_primary_sector(s.id)
        items.append(
            StockSearchItem(
                code=s.code,
                name=s.name,
                market=s.market,
                sector=sector.name if sector else None,
            )
        )
    has_next = page.page * page.size < total
    return page_response(items, page=page.page, size=page.size, total=total, has_next=has_next)


@router.get("/favorites", summary="즐겨찾기 목록")
async def list_favorites(user: CurrentUser, db: AsyncSession = Depends(get_db)):
    svc = StockService(db)
    rows = await svc.list_favorites(user.id)
    items = [FavoriteItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.post("/favorites", summary="즐겨찾기 추가", status_code=201)
async def add_favorite(
    payload: FavoriteIn,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StockService(db)
    await svc.add_favorite(user.id, payload.code)
    return success_response({"added": True, "code": payload.code}, http_status=201)


@router.delete("/favorites/{code}", summary="즐겨찾기 삭제")
async def delete_favorite(
    code: str,
    user: CurrentUser,
    db: AsyncSession = Depends(get_db),
):
    svc = StockService(db)
    await svc.remove_favorite(user.id, code)
    return success_response({"removed": True, "code": code})


@router.get("/{code}", summary="종목 메타 조회")
async def get_stock(code: str, db: AsyncSession = Depends(get_db)):
    svc = StockService(db)
    s = await svc.get_by_code(code)
    return success_response(
        StockOut(
            code=s.code,
            name=s.name,
            market=s.market,
            status=s.status,
            listing_shares=s.listing_shares,
            market_cap=s.market_cap,
            listed_at=s.listed_at,
        )
    )


@router.get("/{code}/quote", summary="실시간 시세")
async def get_quote(code: str, db: AsyncSession = Depends(get_db)):
    svc = StockService(db)
    q = await svc.get_quote(code)
    return success_response(QuoteOut(**q))


@router.get("/{code}/candles", summary="OHLCV 봉 조회")
async def get_candles(
    code: str,
    db: AsyncSession = Depends(get_db),
    interval: str = Query("D", description="D|W|M|1m|5m|15m|30m|60m"),
    from_: str | None = Query(None, alias="from"),
    to: str | None = Query(None),
):
    svc = StockService(db)
    rows = await svc.get_candles(code, interval=interval, from_=from_, to=to)
    items = [CandleItem(**r) for r in rows]
    return success_response([i.model_dump() for i in items])


@router.get("/{code}/orderbook", summary="호가 10단계")
async def get_orderbook(code: str, db: AsyncSession = Depends(get_db)):
    svc = StockService(db)
    ob = await svc.get_orderbook(code)
    return success_response(OrderbookOut(**ob))
