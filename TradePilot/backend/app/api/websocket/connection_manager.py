"""WebSocket 연결 관리자.

책임:
- 사용자/연결별 종목 구독 상태 관리 (메모리 dict + asyncio.Lock)
- 종목별 broadcast (구독자에게만 전송)
- 사용자별 send (체결/알림용)
- 종목별 throttle (기본 100ms) - 과도한 tick 푸시 방지
- 연결당 메시지 큐 cap (기본 1000건, oldest drop) - back-pressure 보호
- 연결당 종목 구독 한도 (기본 50개)

설계 메모:
- WebSocket.send_text는 동시 호출 안전하지 않으므로 연결마다 단일 sender task가 큐에서 꺼내 전송
- broadcast는 큐에 push만 하고 즉시 반환 (느린 클라이언트가 전체 영향 안 줌)
"""
from __future__ import annotations

import asyncio
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

import orjson
import structlog
from fastapi import WebSocket

from app.api.websocket.auth import AuthenticatedClient

log = structlog.get_logger(__name__)


# 기본 부하 한도
DEFAULT_MAX_SUBSCRIPTIONS_PER_CLIENT = 50
DEFAULT_MAX_QUEUE_SIZE = 1000
DEFAULT_THROTTLE_MS = 100


@dataclass
class ClientConnection:
    """단일 WebSocket 연결 상태."""

    connection_id: str
    websocket: WebSocket
    user_id: str
    role: str
    trade_mode: str
    subscribed_codes: set[str] = field(default_factory=set)
    send_queue: deque[bytes] = field(default_factory=deque)
    queue_event: asyncio.Event = field(default_factory=asyncio.Event)
    sender_task: asyncio.Task[None] | None = None
    closed: bool = False
    last_ping_at: float = field(default_factory=time.monotonic)
    drop_count: int = 0  # 큐 오버플로 시 dropped 메시지 수


class ConnectionManager:
    """다수 WebSocket 클라이언트 + 종목 구독 관리.

    - subscribe/unsubscribe는 비동기 lock으로 보호
    - tick broadcast는 종목별 throttle 적용 (마지막 발송 시점 추적)
    """

    def __init__(
        self,
        *,
        max_subscriptions_per_client: int = DEFAULT_MAX_SUBSCRIPTIONS_PER_CLIENT,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
        throttle_ms: int = DEFAULT_THROTTLE_MS,
    ) -> None:
        self.max_subscriptions_per_client = max_subscriptions_per_client
        self.max_queue_size = max_queue_size
        self.throttle_ms = throttle_ms

        # 모든 활성 연결 (connection_id → ClientConnection)
        self._connections: dict[str, ClientConnection] = {}
        # 사용자 → 연결 ID 셋 (한 사용자 다중 탭 지원)
        self._user_connections: dict[str, set[str]] = defaultdict(set)
        # 종목 → 연결 ID 셋 (broadcast 라우팅용)
        self._stock_subscribers: dict[str, set[str]] = defaultdict(set)
        # 종목별 마지막 broadcast 시각 (monotonic) - throttle
        self._last_emit_at: dict[str, float] = {}

        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # 연결 라이프사이클
    # ------------------------------------------------------------------
    async def connect(
        self, websocket: WebSocket, client: AuthenticatedClient
    ) -> ClientConnection:
        """이미 ``websocket.accept()``가 호출된 상태에서 등록.

        반환된 ``ClientConnection``의 sender_task가 자동 시작된다.
        """
        connection_id = uuid4().hex
        conn = ClientConnection(
            connection_id=connection_id,
            websocket=websocket,
            user_id=client.user_id,
            role=client.role,
            trade_mode=client.trade_mode,
        )
        async with self._lock:
            self._connections[connection_id] = conn
            self._user_connections[client.user_id].add(connection_id)

        # sender 코루틴 시작
        conn.sender_task = asyncio.create_task(
            self._sender_loop(conn), name=f"ws-sender-{connection_id[:8]}"
        )
        log.info(
            "ws_connected",
            connection_id=connection_id,
            user_id=client.user_id,
            total_connections=len(self._connections),
        )
        return conn

    async def disconnect(self, conn: ClientConnection) -> None:
        """연결 정리. 멱등."""
        if conn.closed:
            return
        conn.closed = True

        async with self._lock:
            self._connections.pop(conn.connection_id, None)
            self._user_connections.get(conn.user_id, set()).discard(conn.connection_id)
            if not self._user_connections.get(conn.user_id):
                self._user_connections.pop(conn.user_id, None)
            for code in list(conn.subscribed_codes):
                self._stock_subscribers.get(code, set()).discard(conn.connection_id)
                if not self._stock_subscribers.get(code):
                    self._stock_subscribers.pop(code, None)
            conn.subscribed_codes.clear()

        # sender 깨워서 종료
        conn.queue_event.set()
        if conn.sender_task and not conn.sender_task.done():
            conn.sender_task.cancel()
        log.info(
            "ws_disconnected",
            connection_id=conn.connection_id,
            user_id=conn.user_id,
            drop_count=conn.drop_count,
        )

    # ------------------------------------------------------------------
    # 구독 관리
    # ------------------------------------------------------------------
    async def subscribe_stocks(
        self, conn: ClientConnection, codes: list[str]
    ) -> tuple[list[str], list[str]]:
        """종목 구독. 반환: (newly_subscribed, rejected_due_to_limit)."""
        added: list[str] = []
        rejected: list[str] = []
        async with self._lock:
            current = len(conn.subscribed_codes)
            for code in codes:
                if code in conn.subscribed_codes:
                    continue
                if current >= self.max_subscriptions_per_client:
                    rejected.append(code)
                    continue
                conn.subscribed_codes.add(code)
                self._stock_subscribers[code].add(conn.connection_id)
                added.append(code)
                current += 1
        if added or rejected:
            log.debug(
                "ws_subscribe",
                connection_id=conn.connection_id,
                added=len(added),
                rejected=len(rejected),
                total=len(conn.subscribed_codes),
            )
        return added, rejected

    async def unsubscribe_stocks(
        self, conn: ClientConnection, codes: list[str]
    ) -> list[str]:
        removed: list[str] = []
        async with self._lock:
            for code in codes:
                if code not in conn.subscribed_codes:
                    continue
                conn.subscribed_codes.discard(code)
                self._stock_subscribers.get(code, set()).discard(conn.connection_id)
                if not self._stock_subscribers.get(code):
                    self._stock_subscribers.pop(code, None)
                removed.append(code)
        return removed

    # ------------------------------------------------------------------
    # 메시지 송신
    # ------------------------------------------------------------------
    async def send_to_connection(
        self, conn: ClientConnection, payload: dict[str, Any]
    ) -> bool:
        """단일 연결 큐에 push. 큐 초과 시 oldest drop. 성공 여부 반환."""
        if conn.closed:
            return False
        data = orjson.dumps(payload)
        if len(conn.send_queue) >= self.max_queue_size:
            try:
                conn.send_queue.popleft()
                conn.drop_count += 1
            except IndexError:
                pass
        conn.send_queue.append(data)
        conn.queue_event.set()
        return True

    async def send_to_user(self, user_id: str, payload: dict[str, Any]) -> int:
        """특정 사용자의 모든 연결에 전송. 전송된 연결 수 반환."""
        sent = 0
        async with self._lock:
            conn_ids = list(self._user_connections.get(user_id, set()))
        for cid in conn_ids:
            conn = self._connections.get(cid)
            if conn and await self.send_to_connection(conn, payload):
                sent += 1
        return sent

    async def broadcast_to_stock_subscribers(
        self,
        stock_code: str,
        payload: dict[str, Any],
        *,
        respect_throttle: bool = True,
    ) -> int:
        """종목 구독자 전원에게 전송 (throttle 적용)."""
        if respect_throttle and self._is_throttled(stock_code):
            return 0
        async with self._lock:
            conn_ids = list(self._stock_subscribers.get(stock_code, set()))
        if not conn_ids:
            return 0
        if respect_throttle:
            self._last_emit_at[stock_code] = time.monotonic()
        sent = 0
        for cid in conn_ids:
            conn = self._connections.get(cid)
            if conn and await self.send_to_connection(conn, payload):
                sent += 1
        return sent

    async def broadcast_all(self, payload: dict[str, Any]) -> int:
        """모든 활성 연결에 전송."""
        sent = 0
        async with self._lock:
            conn_ids = list(self._connections.keys())
        for cid in conn_ids:
            conn = self._connections.get(cid)
            if conn and await self.send_to_connection(conn, payload):
                sent += 1
        return sent

    def _is_throttled(self, stock_code: str) -> bool:
        last = self._last_emit_at.get(stock_code, 0.0)
        elapsed_ms = (time.monotonic() - last) * 1000.0
        return elapsed_ms < self.throttle_ms

    # ------------------------------------------------------------------
    # 통계 / 메트릭 (관측용)
    # ------------------------------------------------------------------
    def stats(self) -> dict[str, Any]:
        return {
            "connections": len(self._connections),
            "users": len(self._user_connections),
            "subscribed_stocks": len(self._stock_subscribers),
            "throttle_ms": self.throttle_ms,
            "max_subscriptions_per_client": self.max_subscriptions_per_client,
            "max_queue_size": self.max_queue_size,
        }

    # ------------------------------------------------------------------
    # 내부: 연결별 sender 루프
    # ------------------------------------------------------------------
    async def _sender_loop(self, conn: ClientConnection) -> None:
        """큐에서 메시지를 꺼내 직렬 송신."""
        try:
            while not conn.closed:
                if not conn.send_queue:
                    conn.queue_event.clear()
                    try:
                        await asyncio.wait_for(conn.queue_event.wait(), timeout=30.0)
                    except asyncio.TimeoutError:
                        # 유휴 - 다음 루프에서 closed 체크
                        continue
                if conn.closed:
                    return
                while conn.send_queue and not conn.closed:
                    data = conn.send_queue.popleft()
                    try:
                        await conn.websocket.send_bytes(data)
                    except Exception as e:
                        log.warning(
                            "ws_send_failed",
                            connection_id=conn.connection_id,
                            error=str(e),
                        )
                        # 송신 실패는 연결 종료로 본다
                        await self.disconnect(conn)
                        return
        except asyncio.CancelledError:
            return
        except Exception:
            log.exception("ws_sender_loop_error", connection_id=conn.connection_id)
            await self.disconnect(conn)


# ---------------------------------------------------------------------------
# 채널별 싱글톤 (FastAPI 앱 lifespan에서 생성/종료)
# ---------------------------------------------------------------------------
_market_manager: ConnectionManager | None = None
_account_manager: ConnectionManager | None = None
_notifications_manager: ConnectionManager | None = None


def get_market_manager() -> ConnectionManager:
    global _market_manager
    if _market_manager is None:
        _market_manager = ConnectionManager()
    return _market_manager


def get_account_manager() -> ConnectionManager:
    global _account_manager
    if _account_manager is None:
        _account_manager = ConnectionManager(max_subscriptions_per_client=0)
    return _account_manager


def get_notifications_manager() -> ConnectionManager:
    global _notifications_manager
    if _notifications_manager is None:
        _notifications_manager = ConnectionManager(max_subscriptions_per_client=0)
    return _notifications_manager


def reset_managers() -> None:
    """테스트 격리용."""
    global _market_manager, _account_manager, _notifications_manager
    _market_manager = None
    _account_manager = None
    _notifications_manager = None
