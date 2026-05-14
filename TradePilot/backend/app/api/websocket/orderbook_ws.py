"""실시간 호가창 (Level 2) WebSocket 핸들러: ``/ws/orderbook``.

`market_ws`와 동일한 메시지 패턴을 사용하되 매니저는 별도(``orderbook_manager``)로
부하를 격리한다.

부하 한도:
- 종목당 throttle 200ms (시세 100ms 대비 2배 - 호가가 더 빈번하게 변경됨)
- 사용자(연결)당 최대 30종목 구독
- 종목당 동시 구독자 50명 한도 (서비스 정책)
- 연결당 큐 cap 1000 (oldest drop)

메시지:
- 클라이언트→서버: ``auth``, ``subscribe``, ``unsubscribe``, ``ping``
- 서버→클라이언트: ``orderbook``, ``subscribed``, ``unsubscribed``, ``pong``, ``error``

자세한 흐름: ``docs/47_orderbook_guide.md``.
"""
from __future__ import annotations

from typing import Any

import orjson
import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.websocket.auth import AuthFailure, authenticate_token
from app.api.websocket.connection_manager import (
    ConnectionManager,
    get_orderbook_manager,
)
from app.api.websocket.protocol import (
    WS_CLOSE_INTERNAL_ERROR,
    WS_CLOSE_POLICY_VIOLATION,
    AuthRequest,
    ErrorMessage,
    PingRequest,
    PongMessage,
    SubscribedAck,
    SubscribeRequest,
    UnsubscribedAck,
    UnsubscribeRequest,
)

log = structlog.get_logger(__name__)

router = APIRouter()


# 종목당 동시 구독자 한도 (시세 채널과 별개, 호가 채널 정책)
MAX_SUBSCRIBERS_PER_STOCK = 50


@router.websocket("/orderbook")
async def ws_orderbook(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """실시간 호가창 채널.

    - 인증: query string ``?token=`` 우선, 없으면 첫 메시지로 ``auth`` 수신
    - 종목 구독은 ``subscribe`` 메시지로 동적 변경 (사용자당 30종목)
    """
    await websocket.accept()
    manager = get_orderbook_manager()

    # 1) 인증
    try:
        client = await _ensure_authenticated(websocket, token)
    except AuthFailure as e:
        await _send_error(websocket, "E0001", e.message)
        await websocket.close(code=WS_CLOSE_POLICY_VIOLATION)
        return
    except WebSocketDisconnect:
        return

    conn = await manager.connect(websocket, client)

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = orjson.loads(raw)
            except orjson.JSONDecodeError:
                await _send_error(websocket, "E0003", "JSON 파싱 실패")
                continue
            await _handle_client_message(manager, conn, msg)
    except WebSocketDisconnect:
        log.debug("ws_orderbook_disconnect", connection_id=conn.connection_id)
    except Exception:
        log.exception("ws_orderbook_unexpected", connection_id=conn.connection_id)
        try:
            await websocket.close(code=WS_CLOSE_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        await manager.disconnect(conn)


async def _ensure_authenticated(
    websocket: WebSocket, token: str | None
) -> Any:
    """query token 우선, 없으면 첫 메시지 ``auth`` 대기."""
    if token:
        return authenticate_token(token)

    raw = await websocket.receive_text()
    try:
        msg = orjson.loads(raw)
    except orjson.JSONDecodeError as e:
        raise AuthFailure("첫 메시지가 JSON이 아닙니다.") from e

    if msg.get("type") != "auth":
        raise AuthFailure("첫 메시지는 type=auth 여야 합니다.")
    try:
        auth_req = AuthRequest.model_validate(msg)
    except ValidationError as e:
        raise AuthFailure(f"auth 메시지 형식 오류: {e}") from e
    return authenticate_token(auth_req.token)


async def _handle_client_message(
    manager: ConnectionManager, conn: Any, msg: dict[str, Any]
) -> None:
    """클라이언트 메시지 분기."""
    msg_type = msg.get("type")
    if msg_type == "subscribe":
        try:
            req = SubscribeRequest.model_validate(msg)
        except ValidationError as e:
            await manager.send_to_connection(
                conn, ErrorMessage(code="E0003", message=str(e)).model_dump()
            )
            return

        # 종목당 동시 구독자 한도 사전 점검
        already_full: list[str] = []
        accepting: list[str] = []
        for code in req.stock_codes:
            if code in conn.subscribed_codes:
                continue  # 이미 본인이 구독 중인 종목은 제외 (재구독 noop)
            if manager.stock_subscriber_count(code) >= MAX_SUBSCRIBERS_PER_STOCK:
                already_full.append(code)
            else:
                accepting.append(code)

        added, rejected = await manager.subscribe_stocks(conn, accepting)
        await manager.send_to_connection(
            conn,
            SubscribedAck(
                stock_codes=added, total=len(conn.subscribed_codes)
            ).model_dump(),
        )
        if rejected:
            await manager.send_to_connection(
                conn,
                ErrorMessage(
                    code="E0021",
                    message=(
                        f"구독 한도 초과: 사용자당 최대 "
                        f"{manager.max_subscriptions_per_client}종목"
                    ),
                    details={"rejected": rejected},
                ).model_dump(),
            )
        if already_full:
            await manager.send_to_connection(
                conn,
                ErrorMessage(
                    code="E0022",
                    message=(
                        f"종목당 동시 구독자 한도 도달: 최대 "
                        f"{MAX_SUBSCRIBERS_PER_STOCK}명"
                    ),
                    details={"full": already_full},
                ).model_dump(),
            )
    elif msg_type == "unsubscribe":
        try:
            req = UnsubscribeRequest.model_validate(msg)
        except ValidationError as e:
            await manager.send_to_connection(
                conn, ErrorMessage(code="E0003", message=str(e)).model_dump()
            )
            return
        removed = await manager.unsubscribe_stocks(conn, req.stock_codes)
        await manager.send_to_connection(
            conn,
            UnsubscribedAck(
                stock_codes=removed, total=len(conn.subscribed_codes)
            ).model_dump(),
        )
    elif msg_type == "ping":
        try:
            PingRequest.model_validate(msg)
        except ValidationError:
            pass
        await manager.send_to_connection(conn, PongMessage().model_dump())
    elif msg_type == "auth":
        # 이미 인증된 상태 - noop
        pass
    else:
        await manager.send_to_connection(
            conn,
            ErrorMessage(
                code="E0003", message=f"알 수 없는 메시지 타입: {msg_type!r}"
            ).model_dump(),
        )


async def _send_error(websocket: WebSocket, code: str, message: str) -> None:
    try:
        await websocket.send_bytes(
            orjson.dumps(ErrorMessage(code=code, message=message).model_dump())
        )
    except Exception:
        pass
