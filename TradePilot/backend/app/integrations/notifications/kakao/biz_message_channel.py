"""카카오 알림톡(NHN Cloud Notification Service) 채널 어댑터.

전제:
- NHN Cloud 알림톡 (https://docs.nhncloud.com/ko/Notification/KakaoTalk/ko/api-guide/) 사용.
- 카카오비즈 채널이 발급한 ``senderKey`` 및 콘솔에서 사전 승인된 ``templateCode``
  가 필요하다(``templates_registry.py`` 참조).
- 실패(승인 미완료, 일시 장애 등) 시 호출자가 SMS fallback 으로 전환할 수 있도록
  ``SendResult`` 에 ``error_code='KAKAO_FAIL'`` 을 명시한다.

인증:
- NHN Cloud SecretKey 를 ``KAKAO_BIZ_SECRET`` 헤더(``X-Secret-Key``) 로 전송한다.
- 별도 토큰 교환이 필요한 게이트웨이 사용 시 ``_get_access_token`` 을 확장한다.
"""
from __future__ import annotations

import time
from typing import Any

import httpx
import structlog

from app.core.config import settings
from app.integrations.notifications.base import (
    ChannelType,
    NotificationChannel,
    SendResult,
)
from app.integrations.notifications.kakao.templates_registry import get_kakao_template

log = structlog.get_logger(__name__)


# 기본값 — 운영 시 환경변수로 override
_DEFAULT_API_URL = "https://api-alimtalk.cloud.toast.com/alimtalk/v2.3"
_HTTP_TIMEOUT = httpx.Timeout(5.0, connect=3.0)


class KakaoBizMessageChannel(NotificationChannel):
    """카카오 알림톡 어댑터.

    ``metadata`` 필수 키:
      - ``template_code`` (str): ``KAKAO_TEMPLATES`` 의 코드
      - ``variables`` (dict[str, str]): 템플릿 변수
    선택 키:
      - ``button`` (dict): {name, type(WL/AL/BK 등), url_mobile, url_pc}
    """

    channel_type: ChannelType = "KAKAO"

    def __init__(
        self,
        *,
        api_url: str | None = None,
        app_key: str | None = None,
        secret: str | None = None,
        sender_key: str | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self.api_url = (api_url or getattr(settings, "KAKAO_BIZ_API_URL", "") or _DEFAULT_API_URL).rstrip("/")
        self.app_key = app_key if app_key is not None else getattr(settings, "KAKAO_BIZ_APP_KEY", "")
        self.secret = secret if secret is not None else getattr(settings, "KAKAO_BIZ_SECRET", "")
        self.sender_key = sender_key if sender_key is not None else getattr(settings, "KAKAO_BIZ_SENDER_KEY", "")
        self.timeout = timeout or _HTTP_TIMEOUT
        # 향후 OAuth 토큰 캐시용 (NHN Cloud는 secret-key 직사용이지만 다른 게이트웨이 대응)
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    def verify_config(self) -> bool:
        return bool(self.app_key and self.secret and self.sender_key)

    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        meta = metadata or {}
        template_code = str(meta.get("template_code") or "")
        variables: dict[str, str] = {k: str(v) for k, v in (meta.get("variables") or {}).items()}
        if not template_code or not get_kakao_template(template_code):
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="TEMPLATE_REQUIRED",
                error_message="알림톡 template_code 가 필요합니다.",
            )
        if not self.verify_config():
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="CHANNEL_DISABLED",
                error_message="카카오 알림톡 설정이 없습니다.",
            )

        tpl = get_kakao_template(template_code)
        # 변수 누락 체크 (사전 차단)
        missing = [v for v in tpl.variables if v not in variables]
        if missing:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="VARIABLE_MISSING",
                error_message=f"필수 변수 누락: {missing}",
            )

        payload = self._build_payload(
            recipient=recipient,
            template=tpl,
            variables=variables,
            override_body=body,
            button=meta.get("button"),
        )
        url = f"{self.api_url}/appkeys/{self.app_key}/messages"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Secret-Key": self.secret,
        }

        # 인증 토큰을 사용하는 다른 게이트웨이 대응: 토큰이 있으면 Bearer 헤더 추가
        token = await self._get_access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="KAKAO_TIMEOUT",
                error_message="카카오 알림톡 게이트웨이 응답 지연",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as e:  # noqa: BLE001
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="KAKAO_FAIL",
                error_message=str(e)[:200],
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )

        elapsed = int((time.monotonic() - started) * 1000)
        if resp.status_code >= 400:
            log.warning(
                "kakao_send_http_error",
                status=resp.status_code,
                recipient=_mask_phone(recipient),
                template=template_code,
            )
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code=f"HTTP_{resp.status_code}",
                error_message=resp.text[:200],
                elapsed_ms=elapsed,
            )

        try:
            data = resp.json()
        except Exception:
            data = {}

        # NHN Cloud 응답 규약: header.isSuccessful=True, message.messageId
        header = (data or {}).get("header") or {}
        ok = bool(header.get("isSuccessful", True))
        message = (data or {}).get("message") or {}
        msg_id = message.get("messageId") if isinstance(message, dict) else None

        if not ok:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code=str(header.get("resultCode") or "KAKAO_FAIL"),
                error_message=str(header.get("resultMessage") or "알림톡 전송 실패")[:200],
                elapsed_ms=elapsed,
                raw=data,
            )

        log.info(
            "kakao_sent",
            recipient=_mask_phone(recipient),
            template=template_code,
            message_id=msg_id,
            elapsed_ms=elapsed,
        )
        return SendResult(
            ok=True,
            channel=self.channel_type,
            recipient=recipient,
            provider_message_id=str(msg_id) if msg_id else None,
            elapsed_ms=elapsed,
            raw=data,
        )

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------
    def _build_payload(
        self,
        *,
        recipient: str,
        template,
        variables: dict[str, str],
        override_body: str | None,
        button: dict[str, Any] | None,
    ) -> dict[str, Any]:
        # NHN Cloud Alimtalk Spec: senderKey, templateCode, recipientList[].recipientNo,
        # recipientList[].templateParameter, recipientList[].content(선택)
        recipient_obj: dict[str, Any] = {
            "recipientNo": recipient,
            "templateParameter": variables,
        }
        if override_body:
            recipient_obj["content"] = override_body
        if button:
            recipient_obj["buttons"] = [button]
        return {
            "senderKey": self.sender_key,
            "templateCode": template.template_id,
            "recipientList": [recipient_obj],
        }

    async def _get_access_token(self) -> str | None:
        """OAuth 토큰 캐싱 + 자동 갱신.

        NHN Cloud 알림톡은 secret-key 헤더 방식이므로 None 반환이 기본이다.
        다른 게이트웨이로 교체 시 만료시간 기반으로 토큰을 발급/캐싱한다.
        """
        # 토큰 모드를 사용하지 않는 환경에서는 None
        if not getattr(settings, "KAKAO_BIZ_USE_OAUTH", False):
            return None
        now = time.monotonic()
        if self._token and now < self._token_expires_at - 30:
            return self._token
        # 게이트웨이별 토큰 발급 엔드포인트가 다르므로 본 모듈에서는 더미 구현
        log.debug("kakao_token_refresh_stub")
        self._token = None
        self._token_expires_at = now + 1800
        return self._token


def _mask_phone(phone: str) -> str:
    """전화번호를 로그용으로 마스킹: ``01012345678`` → ``010****5678``."""
    if not phone or len(phone) < 8:
        return "***"
    return phone[:3] + "*" * (len(phone) - 7) + phone[-4:]
