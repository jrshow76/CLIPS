"""알림 서비스.

DB 영속화 + 실시간 WebSocket 푸시(Redis Pub/Sub) + 외부 채널 발송 책임.

`notify_user`는 WebSocket 인앱 푸시 + DB 저장만 처리하며,
`dispatch`는 사용자의 채널 설정에 따라 외부 채널(이메일/카카오/SMS)로 발송한다.

채널 우선순위:
1. INAPP (항상): DB 저장 + Redis publish → WebSocket
2. EMAIL: 사용자 설정 활성화 + 이메일 등록 시
3. KAKAO 알림톡: 사용자 옵트인 + 전화번호 등록 시
4. SMS: 알림톡 실패 시 fallback 또는 단독 사용

야간 조용 모드(quiet hours): 사용자 설정 시간대에는 CRITICAL 이외 무음.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo

import orjson
import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import AppException
from app.core.redis_client import get_redis
from app.integrations.notifications.base import ChannelType, SendResult
from app.integrations.notifications.email.smtp_channel import render_template
from app.integrations.notifications.factory import get_channel
from app.integrations.notifications.kakao.templates_registry import render_kakao_content
from app.integrations.notifications.webpush import (
    WebPushChannel,
    WebPushSubscriptionExpired,
)
from app.models.notification import (
    Notification,
    NotificationChannel,
    PushSubscription,
)
from app.models.user import User
from app.repositories.notification_repository import (
    NotificationChannelRepository,
    NotificationRepository,
    PushSubscriptionRepository,
)

log = structlog.get_logger(__name__)


Severity = Literal["INFO", "WARN", "CRITICAL", "SUCCESS"]


# 채널 우선순위 (이벤트 종류별 기본 매핑)
_DEFAULT_EVENT_CHANNELS: dict[str, tuple[ChannelType, ...]] = {
    # 매매 시그널은 빠른 인지 필요 — 인앱 + 이메일
    "SIGNAL": ("INAPP", "EMAIL"),
    # 체결은 정보성 — 인앱 + 이메일
    "ORDER_FILLED": ("INAPP", "EMAIL"),
    # Kill Switch / 보안 / 시스템은 모든 채널
    "KILL_SWITCH": ("INAPP", "EMAIL", "KAKAO", "SMS"),
    "SECURITY": ("INAPP", "EMAIL", "KAKAO"),
    # 일일 리포트는 이메일 + 알림톡 요약
    "DAILY_REPORT": ("EMAIL", "KAKAO"),
    "SYSTEM": ("INAPP",),
    "TEST": ("INAPP",),
}


class NotificationService:
    """알림 도메인 유스케이스."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.notis = NotificationRepository(db)
        self.channels = NotificationChannelRepository(db)
        self.push_subs = PushSubscriptionRepository(db)
        # WEBPUSH 어댑터 (싱글톤 캐시 외부 — VAPID 키 환경 변경에 즉시 반응)
        self._webpush: WebPushChannel | None = None

    # ------------------------------------------------------------------
    # 조회/읽음 처리 (기존 동작)
    # ------------------------------------------------------------------
    async def list_for_user(
        self, user_id: int, *, read: bool | None, offset: int, limit: int
    ) -> tuple[list[Notification], int]:
        return await self.notis.list_for_user(
            user_id, read=read, offset=offset, limit=limit
        )

    async def mark_read(self, user_id: int, noti_id: int) -> None:
        updated = await self.notis.mark_read(user_id, noti_id)
        if not updated:
            raise AppException("E0062", message="알림을 찾을 수 없습니다.")
        await self.db.commit()

    async def mark_read_all(self, user_id: int) -> int:
        updated = await self.notis.mark_read_all(user_id)
        await self.db.commit()
        return updated

    async def get_channels(self, user_id: int) -> NotificationChannel:
        ch = await self.channels.get_or_create(user_id)
        await self.db.commit()
        return ch

    async def update_channels(
        self,
        user_id: int,
        *,
        inapp_enabled: bool | None = None,
        email_enabled: bool | None = None,
        telegram_enabled: bool | None = None,
        telegram_chat_id: str | None = None,
    ) -> NotificationChannel:
        ch = await self.channels.get_or_create(user_id)
        if inapp_enabled is not None:
            ch.inapp_enabled = inapp_enabled
        if email_enabled is not None:
            ch.email_enabled = email_enabled
        if telegram_enabled is not None:
            ch.telegram_enabled = telegram_enabled
        if telegram_chat_id is not None:
            ch.telegram_chat_id = telegram_chat_id
        await self.db.commit()
        await self.db.refresh(ch)
        return ch

    # ------------------------------------------------------------------
    # 실시간 푸시 (DB 저장 + Redis publish) - 기존 동작
    # ------------------------------------------------------------------
    async def notify_user(
        self,
        *,
        user_id: int,
        user_public_id: str,
        title: str,
        body: str | None = None,
        event_type: str = "SYSTEM",
        severity: Severity = "INFO",
        payload: dict[str, Any] | None = None,
        persist: bool = True,
    ) -> Notification | None:
        """사용자 1명에게 알림 전송.

        - ``persist=True``: ``notifications`` 테이블에 INAPP 행 저장
        - ``user_public_id``: WebSocket 토큰 sub 클레임과 일치해야 라우팅됨
        - Redis publish 실패는 로그만 남기고 무시 (DB 영속이 SoT)
        """
        noti: Notification | None = None
        if persist:
            noti = Notification(
                user_id=user_id,
                event_type=event_type,
                priority="HIGH" if severity == "CRITICAL" else "NORMAL",
                channel="INAPP",
                title=title,
                body=body or "",
                payload=payload or {},
                sent_at=datetime.now(tz=timezone.utc),
            )
            self.db.add(noti)
            await self.db.commit()
            await self.db.refresh(noti)

        ws_payload = {
            "user_id": user_public_id,
            "notification_id": noti.id if noti else None,
            "title": title,
            "body": body,
            "event_type": event_type,
            "severity": severity,
            "payload": payload or {},
            "ts": datetime.now(tz=timezone.utc).isoformat(),
        }
        try:
            await get_redis().publish(
                f"tp:notifications.{user_public_id}",
                orjson.dumps(ws_payload),
            )
        except Exception as e:
            log.warning(
                "notify_publish_failed",
                user_public_id=user_public_id,
                error=str(e),
            )
        return noti

    # ------------------------------------------------------------------
    # 외부 채널 dispatch
    # ------------------------------------------------------------------
    async def dispatch(self, notification_id: int) -> list[SendResult]:
        """DB의 알림 1건을 사용자의 채널 설정에 따라 외부 채널로 발송.

        - ``notifications`` 테이블에서 ID 조회 → 사용자 채널 설정 결합
        - 채널별로 ``factory.get_channel`` 어댑터 호출
        - 결과를 로그 + 알림 행의 ``payload['delivery']`` 에 누적
        - 카카오 실패 시 SMS fallback 자동 시도
        """
        # 알림 조회 (파티션 키 created_at 포함 PK 이지만 BIGSERIAL id 로 유일 검색은
        # 단일 파티션에서 행 발견 시 충분)
        stmt = select(Notification).where(Notification.id == notification_id)
        noti = (await self.db.execute(stmt)).scalar_one_or_none()
        if noti is None:
            log.warning("dispatch_notification_not_found", id=notification_id)
            return []

        # 사용자 + 채널 설정 조회
        user = await self.db.get(User, noti.user_id)
        if user is None:
            log.warning("dispatch_user_not_found", user_id=noti.user_id)
            return []
        ch_pref = await self.channels.get_or_create(noti.user_id)

        # 조용 시간 체크
        if self._is_quiet_hours(ch_pref) and noti.priority != "HIGH":
            log.info("dispatch_skipped_quiet_hours", notification_id=noti.id)
            return []

        channels = self._resolve_channels(noti.event_type, ch_pref, noti.payload or {})
        results: list[SendResult] = []
        for ch_type in channels:
            if ch_type == "INAPP":
                # 인앱은 notify_user 흐름에서 처리되었으므로 skip
                continue
            res = await self._send_via_channel(
                channel_type=ch_type,
                user=user,
                ch_pref=ch_pref,
                notification=noti,
            )
            results.append(res)
            # 카카오 실패 → SMS fallback
            if (
                ch_type == "KAKAO"
                and not res.ok
                and "SMS" not in channels
                and (ch_pref.telegram_chat_id or _user_phone(user))
            ):
                fb = await self._send_via_channel(
                    channel_type="SMS",
                    user=user,
                    ch_pref=ch_pref,
                    notification=noti,
                )
                results.append(fb)
                log.info(
                    "kakao_fallback_to_sms",
                    notification_id=noti.id,
                    kakao_error=res.error_code,
                    sms_ok=fb.ok,
                )

        # WEBPUSH 채널 — INAPP 사용자 활성 구독에 모두 발송 (사용자가 인앱 활성화한 경우만)
        if ch_pref.inapp_enabled and getattr(self, "push_subs", None) is not None:
            try:
                webpush_results = await self._dispatch_webpush(noti, user)
                results.extend(webpush_results)
            except Exception as e:  # noqa: BLE001
                log.warning("webpush_dispatch_block_failed", error=str(e)[:200])

        # delivery 정보를 페이로드에 누적 (감사용)
        delivery = list((noti.payload or {}).get("delivery") or [])
        for r in results:
            delivery.append(
                {
                    "channel": r.channel,
                    "ok": r.ok,
                    "error_code": r.error_code,
                    "elapsed_ms": r.elapsed_ms,
                    "ts": r.sent_at.isoformat(),
                }
            )
        # 새 dict 로 갱신해야 SQLAlchemy 가 변경 감지
        new_payload = dict(noti.payload or {})
        new_payload["delivery"] = delivery
        noti.payload = new_payload
        # sent_at 갱신 (외부 채널 발송 성공이 1개 이상이면)
        if any(r.ok for r in results):
            noti.sent_at = datetime.now(tz=timezone.utc)
        await self.db.commit()
        return results

    # ------------------------------------------------------------------
    # 이벤트별 발송 API
    # ------------------------------------------------------------------
    async def send_signal_alert(
        self,
        *,
        user: User,
        stock_code: str,
        stock_name: str,
        action: str,
        rule_code: str,
        confidence: str,
        trigger_price: str,
        strategy_name: str,
    ) -> Notification | None:
        title = f"[{action}] {stock_name}({stock_code}) 매매 시그널"
        body = f"{strategy_name} 전략 — {rule_code} (신뢰도 {confidence}), 기준가 {trigger_price}원"
        html_body = render_template(
            "signal_alert.html",
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "action": action,
                "rule_code": rule_code,
                "confidence": confidence,
                "trigger_price": trigger_price,
                "strategy_name": strategy_name,
                "generated_at": _now_iso(),
            },
        )
        kakao_vars = {
            "stock_name": stock_name,
            "stock_code": stock_code,
            "action_ko": "매수" if action == "BUY" else "매도",
            "strategy_name": strategy_name,
            "confidence": confidence,
            "trigger_price": trigger_price,
        }
        return await self._persist_and_dispatch(
            user=user,
            event_type="SIGNAL",
            severity="INFO",
            title=title,
            body=body,
            payload={
                "html_body": html_body,
                "kakao_template_code": "SIGNAL_ALERT",
                "kakao_variables": kakao_vars,
                "stock_code": stock_code,
                "action": action,
            },
        )

    async def send_execution_alert(
        self,
        *,
        user: User,
        stock_code: str,
        stock_name: str,
        side: str,
        trade_mode: str,
        filled_qty: str,
        filled_price: str,
        amount: str,
        fee: str,
        order_public_id: str,
    ) -> Notification | None:
        side_ko = "매수" if side == "BUY" else "매도"
        title = f"[체결] {stock_name}({stock_code}) {side_ko} {filled_qty}주"
        body = f"{stock_name} {side_ko} {filled_qty}주 / 단가 {filled_price}원 체결"
        html_body = render_template(
            "execution_alert.html",
            {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "side_ko": side_ko,
                "trade_mode": trade_mode,
                "filled_qty": filled_qty,
                "filled_price": filled_price,
                "amount": amount,
                "fee": fee,
                "filled_at": _now_iso(),
                "order_public_id": order_public_id,
            },
        )
        kakao_vars = {
            "stock_name": stock_name,
            "stock_code": stock_code,
            "side_ko": side_ko,
            "filled_qty": filled_qty,
            "filled_price": filled_price,
            "filled_at": _now_iso(),
        }
        return await self._persist_and_dispatch(
            user=user,
            event_type="ORDER_FILLED",
            severity="INFO",
            title=title,
            body=body,
            payload={
                "html_body": html_body,
                "kakao_template_code": "EXECUTION_ALERT",
                "kakao_variables": kakao_vars,
                "order_public_id": order_public_id,
            },
        )

    async def send_kill_switch_alert(
        self,
        *,
        user: User,
        trade_mode: str,
        reason: str | None,
        trigger_source: str,
        result: dict[str, Any],
    ) -> Notification | None:
        title = "[중요] Kill Switch 발동"
        body = (
            f"비상정지 발동: {reason or '사유 미기재'} | "
            f"취소 {result.get('canceled_orders', []) and len(result['canceled_orders']) or 0}건 / "
            f"실패 {len(result.get('failed') or [])}건"
        )
        html_body = render_template(
            "kill_switch.html",
            {
                "reason": reason or "(미기재)",
                "trigger_source": trigger_source,
                "trade_mode": trade_mode,
                "canceled_count": len(result.get("canceled_orders") or []),
                "failed_count": len(result.get("failed") or []),
                "duration_ms": result.get("duration_ms", 0),
                "sla_violated": bool(result.get("sla_violated")),
                "mode_switched": bool(result.get("mode_switched")),
            },
        )
        kakao_vars = {
            "reason": (reason or "(미기재)")[:30],
            "canceled_count": str(len(result.get("canceled_orders") or [])),
            "failed_count": str(len(result.get("failed") or [])),
        }
        return await self._persist_and_dispatch(
            user=user,
            event_type="KILL_SWITCH",
            severity="CRITICAL",
            title=title,
            body=body,
            payload={
                "html_body": html_body,
                "kakao_template_code": "KILL_SWITCH",
                "kakao_variables": kakao_vars,
                "result": result,
            },
        )

    async def send_security_alert(
        self,
        *,
        user: User,
        event_type_code: str,
        ip: str | None = None,
        user_agent: str | None = None,
        detail: str | None = None,
    ) -> Notification | None:
        event_ko = _SECURITY_EVENT_LABELS.get(event_type_code, event_type_code)
        title = f"[보안] {event_ko}"
        body = f"보안 이벤트 감지: {event_ko}"
        html_body = render_template(
            "security_alert.html",
            {
                "event_type_ko": event_ko,
                "occurred_at": _now_iso(),
                "ip": ip,
                "user_agent": user_agent,
                "detail": detail,
            },
        )
        kakao_vars = {"event_type_ko": event_ko, "occurred_at": _now_iso()}
        return await self._persist_and_dispatch(
            user=user,
            event_type="SECURITY",
            severity="CRITICAL",
            title=title,
            body=body,
            payload={
                "html_body": html_body,
                "kakao_template_code": "SECURITY_ALERT",
                "kakao_variables": kakao_vars,
                "ip": ip,
                "user_agent": user_agent,
                "event_code": event_type_code,
            },
        )

    async def send_daily_report(
        self,
        *,
        user: User,
        report_date: str,
        report_data: dict[str, Any],
        csv_attachment: bytes | None = None,
    ) -> Notification | None:
        realized_pnl = str(report_data.get("realized_pnl", "0"))
        win_rate_val = report_data.get("win_rate", 0.0)
        try:
            win_rate = round(float(win_rate_val) * 100, 1) if float(win_rate_val) <= 1 else round(float(win_rate_val), 1)
        except (TypeError, ValueError):
            win_rate = 0.0
        title = f"{report_date} 일일 매매 리포트"
        body = f"실현 손익 {realized_pnl}원, 승률 {win_rate}%"
        html_body = render_template(
            "daily_report.html",
            {
                "nickname": user.nickname,
                "report_date": report_date,
                "realized_pnl": realized_pnl,
                "realized_pnl_signed": _safe_float(realized_pnl),
                "unrealized_pnl": str(report_data.get("unrealized_pnl", "0")),
                "buy_count": report_data.get("buy_count", 0),
                "sell_count": report_data.get("sell_count", 0),
                "win_rate": win_rate,
                "total_amount": str(report_data.get("total_amount", "0")),
                "top_pnl_stocks": report_data.get("top_pnl_stocks", []),
            },
        )
        attachments: list[tuple[str, bytes, str]] = []
        if csv_attachment:
            attachments.append((f"tradepilot_daily_{report_date}.csv", csv_attachment, "text/csv"))
        kakao_vars = {
            "report_date": report_date,
            "realized_pnl": realized_pnl,
            "win_rate": str(win_rate),
        }
        return await self._persist_and_dispatch(
            user=user,
            event_type="DAILY_REPORT",
            severity="INFO",
            title=title,
            body=body,
            payload={
                "html_body": html_body,
                "kakao_template_code": "DAILY_REPORT",
                "kakao_variables": kakao_vars,
                "email_attachments": attachments,
                "report_date": report_date,
            },
        )

    # ------------------------------------------------------------------
    # 테스트 발송 (각 채널 검증)
    # ------------------------------------------------------------------
    async def send_test(self, user_id: int, *, channel: str) -> dict[str, Any]:
        """테스트 알림 발송.

        - INAPP: DB 행 생성 + Redis publish
        - EMAIL/KAKAO/SMS: 실제 어댑터 호출(설정 미비 시 mock 상태로 응답)
        """
        ch = await self.channels.get_or_create(user_id)
        enabled_map: dict[str, bool] = {
            "INAPP": ch.inapp_enabled,
            "EMAIL": ch.email_enabled,
            "TELEGRAM": ch.telegram_enabled,
            "KAKAO": ch.telegram_enabled,  # 카카오/텔레그램 토글 공용 (스키마 호환)
            "SMS": ch.email_enabled or ch.telegram_enabled,
        }
        ch_key = channel.upper()
        if not enabled_map.get(ch_key, False):
            raise AppException(
                "E0082",
                message=f"{ch_key} 채널이 활성화되어 있지 않습니다.",
            )

        if ch_key == "INAPP":
            noti = Notification(
                user_id=user_id,
                event_type="TEST",
                priority="LOW",
                channel="INAPP",
                title="테스트 알림",
                body="알림 시스템 테스트입니다.",
                payload={"test": True},
                sent_at=datetime.now(tz=timezone.utc),
            )
            self.db.add(noti)
            await self.db.commit()
            log.info("test_notification_sent_inapp", user_id=user_id)
            return {"sent": True, "channel": ch_key}

        # 외부 채널: 어댑터 가용 여부 + 사용자 컨택트 확인
        user = await self.db.get(User, user_id)
        adapter = get_channel(ch_key)
        if adapter is None or not adapter.verify_config():
            log.info("test_notification_mock", user_id=user_id, channel=ch_key)
            return {"sent": True, "channel": ch_key, "mock": True}

        if ch_key == "EMAIL":
            if not user or not user.email:
                raise AppException("E0082", message="이메일 주소가 없습니다.")
            html = render_template(
                "welcome.html",
                {"nickname": user.nickname or "사용자", "verify_url": "https://app.tradepilot.example.com"},
            )
            res = await adapter.send(
                recipient=user.email,
                subject="[TradePilot] 알림 테스트",
                body=html,
                metadata={"html": True},
            )
        else:
            phone = _user_phone(user)
            if not phone:
                raise AppException("E0082", message="휴대폰 번호가 등록되어 있지 않습니다.")
            if ch_key == "KAKAO":
                res = await adapter.send(
                    recipient=phone,
                    subject="TradePilot",
                    body="알림 테스트입니다.",
                    metadata={
                        "template_code": "SECURITY_ALERT",
                        "variables": {"event_type_ko": "알림 테스트", "occurred_at": _now_iso()},
                    },
                )
            else:  # SMS
                res = await adapter.send(
                    recipient=phone,
                    subject="TradePilot",
                    body="[TradePilot] 알림 채널 테스트입니다.",
                    metadata={"country_code": "82"},
                )
        return {"sent": res.ok, "channel": ch_key, "provider_message_id": res.provider_message_id, "error": res.error_code}

    # ------------------------------------------------------------------
    # Web Push 구독 관리
    # ------------------------------------------------------------------
    def get_webpush_channel(self) -> WebPushChannel:
        # 테스트가 __init__ 을 우회해 인스턴스를 만들 수 있어 안전 가드
        current = getattr(self, "_webpush", None)
        if current is None:
            current = WebPushChannel()
            self._webpush = current
        return current

    def webpush_public_key(self) -> str | None:
        """클라이언트에 노출할 VAPID 공개키. 미설정 시 None."""
        key = (settings.VAPID_PUBLIC_KEY or "").strip()
        return key or None

    async def register_push_subscription(
        self,
        *,
        user_id: int,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_agent: str | None,
        expires_at: datetime | None,
    ) -> PushSubscription:
        sub = await self.push_subs.upsert(
            user_id=user_id,
            endpoint=endpoint,
            p256dh_key=p256dh_key,
            auth_key=auth_key,
            user_agent=user_agent,
            expires_at=expires_at,
        )
        await self.db.commit()
        return sub

    async def unregister_push_subscription(
        self,
        *,
        user_id: int,
        endpoint: str | None = None,
    ) -> int:
        if endpoint:
            removed = await self.push_subs.remove_by_endpoint(
                user_id=user_id, endpoint=endpoint
            )
        else:
            removed = await self.push_subs.remove_all_for_user(user_id)
        await self.db.commit()
        return removed

    async def send_test_webpush(self, user_id: int) -> dict[str, Any]:
        """사용자 활성 구독 모두에 테스트 발송."""
        subs = await self.push_subs.list_active_for_user(user_id)
        if not subs:
            raise AppException("E0082", message="활성 푸시 구독이 없습니다.")
        adapter = self.get_webpush_channel()
        if not adapter.verify_config():
            return {"sent": 0, "failed": len(subs), "mock": True}

        payload = {
            "title": "TradePilot 테스트 알림",
            "body": "Web Push 알림이 정상 수신되었습니다.",
            "severity": "INFO",
            "event_type": "TEST",
            "url": "/notifications",
        }
        sent = 0
        failed = 0
        expired_endpoints: list[str] = []
        for sub in subs:
            try:
                res = await adapter.send(
                    recipient=sub.endpoint,
                    subject=payload["title"],
                    body=payload["body"],
                    metadata={
                        "p256dh_key": sub.p256dh_key,
                        "auth_key": sub.auth_key,
                        "payload": payload,
                    },
                )
                if res.ok:
                    sent += 1
                    await self.push_subs.touch_last_used(sub.id)
                else:
                    failed += 1
            except WebPushSubscriptionExpired:
                failed += 1
                expired_endpoints.append(sub.endpoint)
            except Exception as e:  # noqa: BLE001
                log.warning("webpush_test_failed", error=str(e), sub_id=sub.id)
                failed += 1
        # 만료된 구독 즉시 정리
        for ep in expired_endpoints:
            await self.push_subs.remove_by_endpoint(user_id=user_id, endpoint=ep)
        await self.db.commit()
        return {"sent": sent, "failed": failed, "expired": len(expired_endpoints)}

    async def _dispatch_webpush(
        self,
        noti: Notification,
        user: User,
    ) -> list[SendResult]:
        """단일 알림 행을 사용자의 모든 활성 push 구독으로 발송.

        만료된 endpoint(404/410)는 자동 삭제한다.
        """
        adapter = self.get_webpush_channel()
        if not adapter.verify_config():
            return []
        subs = await self.push_subs.list_active_for_user(user.id)
        if not subs:
            return []

        payload: dict[str, Any] = {
            "title": noti.title,
            "body": noti.body or "",
            "severity": "CRITICAL" if noti.priority == "HIGH" else "INFO",
            "event_type": noti.event_type,
            "notification_id": noti.id,
            "payload": noti.payload or {},
        }
        # 이벤트별 URL 라우팅 힌트 (Service Worker 측에도 동일 fallback 룰이 있음)
        stock_code = (noti.payload or {}).get("stock_code")
        order_pub = (noti.payload or {}).get("order_public_id")
        if noti.event_type == "SIGNAL" and stock_code:
            payload["url"] = f"/chart/{stock_code}"
        elif noti.event_type == "ORDER_FILLED" and order_pub:
            payload["url"] = "/auto-trading/orders"
        elif noti.event_type == "KILL_SWITCH":
            payload["url"] = "/auto-trading"
        else:
            payload["url"] = settings.WEBPUSH_DEFAULT_URL

        results: list[SendResult] = []
        expired_endpoints: list[str] = []
        for sub in subs:
            try:
                res = await adapter.send(
                    recipient=sub.endpoint,
                    subject=noti.title,
                    body=noti.body or "",
                    metadata={
                        "p256dh_key": sub.p256dh_key,
                        "auth_key": sub.auth_key,
                        "payload": payload,
                        "urgency": "high" if noti.priority == "HIGH" else "normal",
                        "topic": noti.event_type[:32] if noti.event_type else None,
                    },
                )
                results.append(res)
                if res.ok:
                    await self.push_subs.touch_last_used(sub.id)
            except WebPushSubscriptionExpired as exc:
                expired_endpoints.append(exc.endpoint)
                results.append(
                    SendResult(
                        ok=False,
                        channel="INAPP",
                        recipient=exc.endpoint,
                        error_code=f"WEBPUSH_GONE_{exc.status_code}",
                        error_message="구독 만료(자동 정리)",
                    )
                )
            except Exception as e:  # noqa: BLE001
                log.warning(
                    "webpush_send_failed",
                    notification_id=noti.id,
                    sub_id=sub.id,
                    error=str(e)[:200],
                )
                results.append(
                    SendResult(
                        ok=False,
                        channel="INAPP",
                        recipient=sub.endpoint,
                        error_code="WEBPUSH_EXCEPTION",
                        error_message=str(e)[:200],
                    )
                )
        for ep in expired_endpoints:
            try:
                await self.push_subs.remove_by_endpoint(user_id=user.id, endpoint=ep)
            except Exception as e:  # noqa: BLE001
                log.warning("webpush_cleanup_failed", endpoint=ep, error=str(e))
        if expired_endpoints:
            await self.db.commit()
        return results

    # ------------------------------------------------------------------
    # 내부 헬퍼
    # ------------------------------------------------------------------
    async def _persist_and_dispatch(
        self,
        *,
        user: User,
        event_type: str,
        severity: Severity,
        title: str,
        body: str,
        payload: dict[str, Any],
    ) -> Notification | None:
        """DB 행 저장 + Redis publish(인앱) + dispatch(외부 채널)."""
        noti = await self.notify_user(
            user_id=user.id,
            user_public_id=str(user.public_id),
            title=title,
            body=body,
            event_type=event_type,
            severity=severity,
            payload=payload,
        )
        if noti is None:
            return None
        try:
            await self.dispatch(noti.id)
        except Exception as e:  # noqa: BLE001
            log.warning("dispatch_failed", notification_id=noti.id, error=str(e)[:200])
        return noti

    def _resolve_channels(
        self,
        event_type: str,
        ch_pref: NotificationChannel,
        payload: dict[str, Any],
    ) -> list[ChannelType]:
        """이벤트 종류 + 사용자 설정으로 활성 채널 리스트 결정."""
        defaults = list(_DEFAULT_EVENT_CHANNELS.get(event_type, ("INAPP",)))
        # 페이로드 override
        if payload.get("channels"):
            defaults = list(payload["channels"])
        active: list[ChannelType] = []
        for ch in defaults:
            if ch == "INAPP" and ch_pref.inapp_enabled:
                active.append("INAPP")
            elif ch == "EMAIL" and ch_pref.email_enabled:
                active.append("EMAIL")
            elif ch == "KAKAO" and ch_pref.telegram_enabled:
                # 스키마 호환: telegram_enabled 가 카카오 동의를 겸한다 (마이그레이션 전)
                active.append("KAKAO")
            elif ch == "SMS" and ch_pref.email_enabled:
                # 보안/Kill Switch CRITICAL은 SMS 강제
                if event_type in ("KILL_SWITCH", "SECURITY"):
                    active.append("SMS")
        return active

    def _is_quiet_hours(self, ch_pref: NotificationChannel) -> bool:
        """야간 조용 모드 판정.

        v1: 페이로드/설정 미지원 — 기본은 항상 False.
        후속: ``notification_channels`` 에 quiet_start/end 컬럼 추가 시 활성화.
        """
        # 후속 확장 자리. 현재는 quiet hours 미지원으로 항상 False.
        # 구현 시 사용자 timezone (Asia/Seoul) 기준 22:00~08:00 무음 등 가능.
        try:
            tz = ZoneInfo(settings.APP_TIMEZONE)
            now_local = datetime.now(tz=tz).time()
            # 환경변수로 일괄 적용 (개인화 컬럼 추가 전 임시 정책)
            quiet_start = time(22, 0)
            quiet_end = time(8, 0)
            in_quiet = now_local >= quiet_start or now_local < quiet_end
            # 기본은 미적용 (개인 옵트인 정책 추가 전까지)
            return False and in_quiet  # noqa: SIM103
        except Exception:
            return False

    async def _send_via_channel(
        self,
        *,
        channel_type: ChannelType,
        user: User,
        ch_pref: NotificationChannel,
        notification: Notification,
    ) -> SendResult:
        """단일 채널에 알림을 발송."""
        adapter = get_channel(channel_type)
        if adapter is None or not adapter.verify_config():
            return SendResult(
                ok=False,
                channel=channel_type,
                recipient="",
                error_code="CHANNEL_DISABLED",
                error_message=f"{channel_type} 어댑터 미설정",
            )

        payload = notification.payload or {}
        if channel_type == "EMAIL":
            if not user.email:
                return SendResult(
                    ok=False,
                    channel=channel_type,
                    recipient="",
                    error_code="NO_RECIPIENT",
                    error_message="이메일 주소가 없습니다.",
                )
            html_body = str(payload.get("html_body") or notification.body or "")
            attachments = payload.get("email_attachments") or []
            return await adapter.send(
                recipient=user.email,
                subject=notification.title,
                body=html_body,
                metadata={"html": True, "attachments": attachments},
            )
        if channel_type == "KAKAO":
            phone = _user_phone(user)
            if not phone:
                return SendResult(
                    ok=False,
                    channel=channel_type,
                    recipient="",
                    error_code="NO_RECIPIENT",
                    error_message="휴대폰 번호가 없습니다.",
                )
            tpl_code = str(payload.get("kakao_template_code") or "")
            variables = payload.get("kakao_variables") or {}
            kakao_body = render_kakao_content(tpl_code, variables) or notification.body or ""
            return await adapter.send(
                recipient=phone,
                subject=notification.title,
                body=kakao_body,
                metadata={"template_code": tpl_code, "variables": variables},
            )
        if channel_type == "SMS":
            phone = _user_phone(user)
            if not phone:
                return SendResult(
                    ok=False,
                    channel=channel_type,
                    recipient="",
                    error_code="NO_RECIPIENT",
                    error_message="휴대폰 번호가 없습니다.",
                )
            sms_body = (notification.title or "") + "\n" + (notification.body or "")
            return await adapter.send(
                recipient=phone,
                subject=notification.title,
                body=sms_body,
                metadata={"country_code": "82"},
            )
        return SendResult(
            ok=False,
            channel=channel_type,
            recipient="",
            error_code="UNSUPPORTED",
            error_message=f"미지원 채널: {channel_type}",
        )


# ---------------------------------------------------------------------------
# 보조
# ---------------------------------------------------------------------------
_SECURITY_EVENT_LABELS: dict[str, str] = {
    "refresh_replay_detected": "리프레시 토큰 재사용 탐지",
    "refresh_token_unknown": "알 수 없는 리프레시 토큰 사용",
    "login_failed_burst": "로그인 실패 다발",
    "account_locked": "계정 잠금",
    "password_changed": "비밀번호 변경",
    "kill_switch": "비상정지 발동",
}


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).astimezone(ZoneInfo(settings.APP_TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")


def _user_phone(user: User | None) -> str | None:
    """User.phone 을 SMS/카카오 수신번호로 정규화 (숫자만)."""
    if not user or not getattr(user, "phone", None):
        return None
    digits = "".join(c for c in str(user.phone) if c.isdigit())
    return digits or None


def _safe_float(s: str) -> float:
    try:
        return float(str(s).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0
