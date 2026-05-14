"""알림 채널 추상 클래스.

채널별 어댑터는 본 추상 클래스를 구현하고 ``factory.get_channel`` 을 통해 주입된다.

- 모든 채널은 비동기(``async def send``) 인터페이스를 가진다.
- ``send_bulk`` 의 기본 구현은 순차 호출 + 부분 실패 허용이며, 채널별로 배치 API
  가 있는 경우 override 한다(예: SMS 다건 전송).
- ``verify_config`` 는 기동/헬스체크 시 환경변수 누락 등 명백한 미설정을 빠르게
  감지하기 위한 동기 검증이다. 외부 API 호출은 하지 않는다.
"""
from __future__ import annotations

import abc
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal

ChannelType = Literal["EMAIL", "KAKAO", "SMS", "INAPP"]


@dataclass(slots=True)
class SendResult:
    """채널 발송 결과.

    - ``ok``: 채널 측이 접수(또는 즉시 전송) 성공으로 응답한 경우 True.
    - ``provider_message_id``: 외부 서비스가 발급한 추적 ID(있는 경우).
    - ``error_code`` / ``error_message``: 실패 사유. ``ok=False`` 일 때 채움.
    - ``elapsed_ms``: 호출-응답까지 걸린 시간(ms). 관측용.
    - ``raw``: 원본 응답 페이로드(디버깅용). 시크릿은 상위에서 마스킹해 저장한다.
    """

    ok: bool
    channel: ChannelType
    recipient: str
    provider_message_id: str | None = None
    error_code: str | None = None
    error_message: str | None = None
    elapsed_ms: int = 0
    sent_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    raw: dict[str, Any] = field(default_factory=dict)


class NotificationChannel(abc.ABC):
    """알림 채널 추상 클래스."""

    #: 채널 식별자 (subclass에서 지정)
    channel_type: ChannelType = "INAPP"

    @abc.abstractmethod
    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """단일 수신자에게 메시지를 발송한다.

        - ``recipient``: 채널별 수신 식별자(이메일/카카오ID/전화번호 등).
        - ``subject``: 이메일 등에서 사용하는 제목. 알림톡/SMS 는 무시될 수 있다.
        - ``body``: 본문(이메일은 HTML 또는 텍스트, SMS/알림톡은 텍스트).
        - ``metadata``: 채널별 추가 필드. 예: 알림톡 ``template_id``,
          이메일 ``attachments``, SMS ``country_code`` 등.
        """

    async def send_bulk(
        self,
        *,
        recipients: list[str],
        subject: str | None,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> list[SendResult]:
        """다수 수신자에게 동일 메시지 발송. 기본 구현은 순차 호출.

        채널별 배치 API가 있는 경우 override 권장(SMS bulk 등).
        """
        results: list[SendResult] = []
        for r in recipients:
            try:
                results.append(
                    await self.send(
                        recipient=r,
                        subject=subject,
                        body=body,
                        metadata=metadata,
                    )
                )
            except Exception as e:  # noqa: BLE001
                results.append(
                    SendResult(
                        ok=False,
                        channel=self.channel_type,
                        recipient=r,
                        error_code="CHANNEL_EXCEPTION",
                        error_message=str(e)[:200],
                    )
                )
        return results

    @abc.abstractmethod
    def verify_config(self) -> bool:
        """기본 환경변수가 셋업되어 있는지 동기 검증.

        외부 API 호출 없이 즉시 반환. False 면 ``factory.get_channel`` 이
        해당 채널을 비활성으로 처리한다.
        """
