"""Web Push 채널 어댑터.

- `pywebpush` 가 설치되어 있으면 실제 VAPID 인증으로 푸시를 전송한다.
- 설치되지 않은 환경 / 키 미설정 환경에서는 `verify_config()` 가 False 를 반환하며,
  서비스 계층이 채널을 비활성으로 처리한다.
- 404 / 410 (Gone) 응답 시 `WebPushSubscriptionExpired` 예외를 발생시켜
  서비스 계층에서 해당 구독을 DB 에서 제거하도록 한다.

`send()` 의 `recipient` 는 사용 컨벤션상 endpoint URL 이며,
`metadata` 에는 다음 키가 포함되어야 한다.

  - ``p256dh_key`` (str): base64url 인코딩된 P-256 공개키
  - ``auth_key`` (str): base64url 인코딩된 인증 시크릿
  - ``payload`` (dict, 선택): showNotification 에 직접 넘길 JSON 페이로드
       기본 키: title, body, severity, event_type, payload, url

암호화/서명은 pywebpush 가 RFC 8030/8291/8292 절차를 따른다.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import orjson
import structlog

from app.core.config import settings
from app.integrations.notifications.base import (
    ChannelType,
    NotificationChannel,
    SendResult,
)

log = structlog.get_logger(__name__)


class WebPushSubscriptionExpired(Exception):
    """구독이 만료/취소되었음을 알린다 (404/410)."""

    def __init__(self, endpoint: str, status_code: int) -> None:
        super().__init__(f"Web Push subscription expired: {endpoint} ({status_code})")
        self.endpoint = endpoint
        self.status_code = status_code


# pywebpush 는 운영 환경 의존성. 미설치 환경에서는 verify_config 가 False 가 되도록 폴백.
try:  # pragma: no cover - 설치 상태 가드
    from pywebpush import WebPushException, webpush  # type: ignore

    _PYWEBPUSH_AVAILABLE = True
except Exception:  # noqa: BLE001
    _PYWEBPUSH_AVAILABLE = False

    class WebPushException(Exception):  # type: ignore
        response = None


class WebPushChannel(NotificationChannel):
    """Web Push (VAPID) 어댑터."""

    channel_type: ChannelType = "INAPP"  # 사용처 라우팅 시 별도 'WEBPUSH' 키로 디스패치

    # 별도 키워드로 사용 (NotificationChannel 기본 라우팅과 분리)
    WEBPUSH_KEY: str = "WEBPUSH"

    DEFAULT_TTL_SECONDS: int = 24 * 60 * 60  # 24h

    def __init__(
        self,
        *,
        public_key: str | None = None,
        private_key: str | None = None,
        subject: str | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        self.public_key = (public_key if public_key is not None else getattr(settings, "VAPID_PUBLIC_KEY", "")) or ""
        self.private_key = (
            private_key if private_key is not None else getattr(settings, "VAPID_PRIVATE_KEY", "")
        ) or ""
        self.subject = (
            subject if subject is not None else getattr(settings, "VAPID_SUBJECT", "")
        ) or "mailto:admin@tradepilot.example.com"
        self.ttl_seconds = int(ttl_seconds or getattr(settings, "WEBPUSH_TTL_SECONDS", self.DEFAULT_TTL_SECONDS))

    # ------------------------------------------------------------------
    # verify_config
    # ------------------------------------------------------------------
    def verify_config(self) -> bool:
        if not _PYWEBPUSH_AVAILABLE:
            return False
        if not self.public_key or not self.private_key:
            return False
        if not self.subject:
            return False
        return True

    # ------------------------------------------------------------------
    # send (단일 endpoint)
    # ------------------------------------------------------------------
    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """단일 endpoint 에 발송.

        - ``recipient``: subscription endpoint URL
        - ``metadata.p256dh_key``, ``metadata.auth_key`` 필수
        - ``metadata.payload``: dict 페이로드 (없으면 subject/body 로 기본 구성)
        """
        meta = metadata or {}
        p256dh = meta.get("p256dh_key")
        auth = meta.get("auth_key")
        if not p256dh or not auth:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="MISSING_KEYS",
                error_message="p256dh_key/auth_key 가 필요합니다.",
            )
        if not self.verify_config():
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="CHANNEL_DISABLED",
                error_message="WebPush 어댑터 미설정 (VAPID 키 또는 pywebpush 누락)",
            )

        payload: dict[str, Any] = dict(meta.get("payload") or {})
        payload.setdefault("title", subject or payload.get("title") or "TradePilot")
        payload.setdefault("body", body or payload.get("body") or "")
        # severity / event_type / url 등은 호출 측이 추가

        subscription_info = {
            "endpoint": recipient,
            "keys": {"p256dh": p256dh, "auth": auth},
        }
        body_bytes = orjson.dumps(payload)

        started = time.time()
        try:
            await asyncio.to_thread(
                self._send_sync,
                subscription_info=subscription_info,
                body=body_bytes,
                ttl=self.ttl_seconds,
                urgency=meta.get("urgency", "high"),
                topic=meta.get("topic"),
            )
            elapsed_ms = int((time.time() - started) * 1000)
            return SendResult(
                ok=True,
                channel=self.channel_type,
                recipient=recipient,
                elapsed_ms=elapsed_ms,
            )
        except WebPushSubscriptionExpired as exc:
            # 서비스 계층에서 catch → DB 정리
            raise exc
        except WebPushException as exc:  # pragma: no cover - 외부 의존성
            elapsed_ms = int((time.time() - started) * 1000)
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                raise WebPushSubscriptionExpired(recipient, status) from exc
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code=f"WEBPUSH_HTTP_{status}" if status else "WEBPUSH_FAIL",
                error_message=str(exc)[:200],
                elapsed_ms=elapsed_ms,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed_ms = int((time.time() - started) * 1000)
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="WEBPUSH_EXCEPTION",
                error_message=str(exc)[:200],
                elapsed_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    # 내부: pywebpush 동기 호출 (asyncio.to_thread 래핑)
    # ------------------------------------------------------------------
    def _send_sync(
        self,
        *,
        subscription_info: dict[str, Any],
        body: bytes,
        ttl: int,
        urgency: str,
        topic: str | None,
    ) -> None:
        """pywebpush 동기 호출. 410/404 는 WebPushSubscriptionExpired 로 변환."""
        if not _PYWEBPUSH_AVAILABLE:  # pragma: no cover
            raise RuntimeError("pywebpush 미설치")

        headers: dict[str, Any] = {"Urgency": urgency}
        if topic:
            headers["Topic"] = topic

        try:
            webpush(  # type: ignore
                subscription_info=subscription_info,
                data=body,
                vapid_private_key=self.private_key,
                vapid_claims={"sub": self.subject},
                ttl=ttl,
                headers=headers,
            )
        except WebPushException as exc:  # type: ignore
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in (404, 410):
                raise WebPushSubscriptionExpired(subscription_info["endpoint"], status) from exc
            raise
