"""체결/잔고 알림 WebSocket: ``/ws/account``.

사용자별 채널. 종목 구독 개념 없음 - 본인의 체결/주문 상태 변경만 수신.
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
    get_account_manager,
)
from app.api.websocket.protocol import (
    WS_CLOSE_INTERNAL_ERROR,
    WS_CLOSE_POLICY_VIOLATION,
    AuthRequest,
    ErrorMessage,
    PingRequest,
    PongMessage,
)

log = structlog.get_logger(__name__)

router = APIRouter()


@router.websocket("/account")
async def ws_account(
    websocket: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    await websocket.accept()
    manager = get_account_manager()

    try:
        client = await _ensure_authenticated(websocket, token)
    except AuthFailure as e:
        try:
            await websocket.send_bytes(
                orjson.dumps(
                    ErrorMessage(code="E0001", message=e.message).model_dump()
                )
            )
        except Exception:
            pass
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
                continue
            await _handle_client_message(manager, conn, msg)
    except WebSocketDisconnect:
        log.debug("ws_account_disconnect", connection_id=conn.connection_id)
    except Exception:
        log.exception("ws_account_unexpected", connection_id=conn.connection_id)
        try:
            await websocket.close(code=WS_CLOSE_INTERNAL_ERROR)
        except Exception:
            pass
    finally:
        await manager.disconnect(conn)


async def _ensure_authenticated(
    websocket: WebSocket, token: str | None
) -> Any:
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
    if msg.get("type") == "ping":
        try:
            PingRequest.model_validate(msg)
        except ValidationError:
            pass
        await manager.send_to_connection(conn, PongMessage().model_dump())
