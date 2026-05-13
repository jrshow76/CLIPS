"""실시간 시세 WebSocket 핸들러: ``/ws/market``.

흐름:
1. 클라이언트 ``ws://.../ws/market?token=<jwt>`` 또는 ``?token=`` 없이 연결
2. 토큰 검증 (query 또는 첫 메시지)
3. ``subscribe`` 메시지로 종목 코드 등록 → 구독 ack
4. 매니저가 Redis pub 메시지를 throttle 후 전달
5. ``unsubscribe`` / 끊김 시 정리
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
    get_market_manager,
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


@router.websocket("/market")
async def ws_market(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    """실시간 시세 채널.

    - 인증: query string ``?token=`` 우선, 없으면 첫 메시지로 ``auth`` 수신
    - 종목 구독은 ``subscribe`` 메시지로 동적 변경 가능
    """
    await websocket.accept()
    manager = get_market_manager()

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
        log.debug("ws_market_disconnect", connection_id=conn.connection_id)
    except Exception:
        log.exception("ws_market_unexpected", connection_id=conn.connection_id)
        try:
            await websocket.close(code=WS_CLOSE_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        await manager.disconnect(conn)


async def _ensure_authenticated(
    websocket: WebSocket, token: str | None
) -> Any:
    """query token이 있으면 즉시 검증, 없으면 첫 메시지에서 ``auth`` 대기."""
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
        added, rejected = await manager.subscribe_stocks(conn, req.stock_codes)
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
                        f"구독 한도 초과: 최대 "
                        f"{manager.max_subscriptions_per_client}개"
                    ),
                    details={"rejected": rejected},
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
        # 이미 인증된 상태에서 추가 auth → 무시 (오류는 아님)
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
