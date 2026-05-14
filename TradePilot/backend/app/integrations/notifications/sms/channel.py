"""SMS 채널 어댑터.

환경변수 ``SMS_PROVIDER`` 로 게이트웨이를 선택한다.
- ``nhn_cloud`` (기본): NHN Cloud SMS API
- ``aws_sns``: AWS SNS Publish API (boto3 사용; 미설치 시 비활성)

본 어댑터는 카카오 알림톡 실패 시 fallback 으로 호출되는 경우가 많다.
국제 번호는 운영 정책상 차단(국내 한정)이 일반적이다.
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

log = structlog.get_logger(__name__)


_NHN_DEFAULT_URL = "https://api-sms.cloud.toast.com/sms/v3.0"
_HTTP_TIMEOUT = httpx.Timeout(5.0, connect=3.0)

# SMS(EMS 미사용 단문) 최대 길이: 한국 SMS 규격상 90 byte (EUC-KR 기준 45자) 가 안전선
_SMS_BODY_MAX = 90


class SmsChannel(NotificationChannel):
    """SMS 어댑터.

    ``metadata``:
      - ``country_code`` (str): 국가코드 (기본 "82"). 운영 정책상 KR 한정 권장.
    """

    channel_type: ChannelType = "SMS"

    def __init__(
        self,
        *,
        provider: str | None = None,
        from_number: str | None = None,
        api_url: str | None = None,
        app_key: str | None = None,
        secret: str | None = None,
        aws_access_key: str | None = None,
        aws_secret_key: str | None = None,
        aws_region: str | None = None,
        timeout: httpx.Timeout | None = None,
    ) -> None:
        self.provider = (provider or getattr(settings, "SMS_PROVIDER", "nhn_cloud")).lower()
        self.from_number = from_number if from_number is not None else getattr(settings, "SMS_FROM_NUMBER", "")
        self.api_url = (api_url or getattr(settings, "SMS_NHN_API_URL", "") or _NHN_DEFAULT_URL).rstrip("/")
        self.app_key = app_key if app_key is not None else getattr(settings, "SMS_NHN_APP_KEY", "")
        self.secret = secret if secret is not None else getattr(settings, "SMS_NHN_SECRET", "")
        self.aws_access_key = aws_access_key if aws_access_key is not None else getattr(settings, "SMS_AWS_ACCESS_KEY", "")
        self.aws_secret_key = aws_secret_key if aws_secret_key is not None else getattr(settings, "SMS_AWS_SECRET_KEY", "")
        self.aws_region = aws_region if aws_region is not None else getattr(settings, "SMS_AWS_REGION", "ap-northeast-2")
        self.timeout = timeout or _HTTP_TIMEOUT

    def verify_config(self) -> bool:
        if self.provider == "aws_sns":
            return bool(self.aws_access_key and self.aws_secret_key and self.aws_region)
        return bool(self.app_key and self.secret and self.from_number)

    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        if not self.verify_config():
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="CHANNEL_DISABLED",
                error_message=f"SMS 설정 없음 (provider={self.provider})",
            )

        # 본문 길이 가드 (단문 SMS 규약)
        if len(body.encode("utf-8")) > _SMS_BODY_MAX:
            body = _truncate_for_sms(body, _SMS_BODY_MAX)

        if self.provider == "aws_sns":
            return await self._send_aws(recipient=recipient, body=body, metadata=metadata)
        return await self._send_nhn(recipient=recipient, body=body, subject=subject, metadata=metadata)

    # ------------------------------------------------------------------
    # NHN Cloud SMS
    # ------------------------------------------------------------------
    async def _send_nhn(
        self,
        *,
        recipient: str,
        body: str,
        subject: str | None,
        metadata: dict[str, Any] | None,
    ) -> SendResult:
        url = f"{self.api_url}/appKeys/{self.app_key}/sender/sms"
        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "X-Secret-Key": self.secret,
        }
        payload: dict[str, Any] = {
            "body": body,
            "sendNo": self.from_number,
            "recipientList": [{"recipientNo": recipient}],
        }
        if subject:
            payload["title"] = subject[:30]

        started = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="SMS_TIMEOUT",
                error_message="SMS 게이트웨이 응답 지연",
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        except Exception as e:  # noqa: BLE001
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="SMS_FAIL",
                error_message=str(e)[:200],
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )

        elapsed = int((time.monotonic() - started) * 1000)
        if resp.status_code >= 400:
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
        header = (data or {}).get("header") or {}
        ok = bool(header.get("isSuccessful", True))
        if not ok:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code=str(header.get("resultCode") or "SMS_FAIL"),
                error_message=str(header.get("resultMessage") or "SMS 전송 실패")[:200],
                elapsed_ms=elapsed,
                raw=data,
            )
        body_section = (data or {}).get("body") or {}
        request_id = None
        if isinstance(body_section, dict):
            request_id = body_section.get("data", {}).get("requestId") if isinstance(body_section.get("data"), dict) else None

        log.info(
            "sms_sent_nhn",
            recipient=_mask_phone(recipient),
            request_id=request_id,
            elapsed_ms=elapsed,
        )
        return SendResult(
            ok=True,
            channel=self.channel_type,
            recipient=recipient,
            provider_message_id=str(request_id) if request_id else None,
            elapsed_ms=elapsed,
            raw=data,
        )

    # ------------------------------------------------------------------
    # AWS SNS
    # ------------------------------------------------------------------
    async def _send_aws(
        self,
        *,
        recipient: str,
        body: str,
        metadata: dict[str, Any] | None,
    ) -> SendResult:
        try:  # boto3 는 선택 의존성. 미설치 환경에서는 비활성으로 처리.
            import boto3  # type: ignore[import-not-found]
        except ImportError:
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="BOTO3_MISSING",
                error_message="aws_sns 사용을 위해 boto3 가 필요합니다.",
            )

        import asyncio as _asyncio

        country = str((metadata or {}).get("country_code") or "82")
        e164 = recipient if recipient.startswith("+") else f"+{country}{recipient.lstrip('0')}"

        def _publish_sync() -> dict[str, Any]:
            client = boto3.client(
                "sns",
                aws_access_key_id=self.aws_access_key,
                aws_secret_access_key=self.aws_secret_key,
                region_name=self.aws_region,
            )
            return client.publish(
                PhoneNumber=e164,
                Message=body,
                MessageAttributes={
                    "AWS.SNS.SMS.SenderID": {"DataType": "String", "StringValue": "TradePilot"},
                    "AWS.SNS.SMS.SMSType": {"DataType": "String", "StringValue": "Transactional"},
                },
            )

        started = time.monotonic()
        try:
            data = await _asyncio.get_running_loop().run_in_executor(None, _publish_sync)
        except Exception as e:  # noqa: BLE001
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="SNS_FAIL",
                error_message=str(e)[:200],
                elapsed_ms=int((time.monotonic() - started) * 1000),
            )
        elapsed = int((time.monotonic() - started) * 1000)
        mid = data.get("MessageId") if isinstance(data, dict) else None
        log.info("sms_sent_aws", recipient=_mask_phone(recipient), message_id=mid, elapsed_ms=elapsed)
        return SendResult(
            ok=True,
            channel=self.channel_type,
            recipient=recipient,
            provider_message_id=mid,
            elapsed_ms=elapsed,
            raw={"sns": True},
        )


def _truncate_for_sms(body: str, max_bytes: int) -> str:
    """UTF-8 바이트 기준으로 안전하게 잘라낸 문자열 반환."""
    encoded = body.encode("utf-8")
    if len(encoded) <= max_bytes:
        return body
    truncated = encoded[: max_bytes - 3]
    while True:
        try:
            return truncated.decode("utf-8") + "..."
        except UnicodeDecodeError:
            truncated = truncated[:-1]


def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 8:
        return "***"
    return phone[:3] + "*" * (len(phone) - 7) + phone[-4:]
