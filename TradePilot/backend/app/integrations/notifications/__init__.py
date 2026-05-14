"""알림 채널 통합 패키지.

다중 채널(이메일/카카오 알림톡/SMS/인앱)을 추상화한 어댑터를 제공한다.

- ``base.NotificationChannel``: 모든 채널이 구현해야 하는 추상 클래스
- ``email.smtp_channel``: SMTP 기반 이메일 어댑터
- ``kakao.biz_message_channel``: 카카오 알림톡(NHN Cloud Notification Service) 어댑터
- ``sms.channel``: SMS(AWS SNS / NHN Cloud SMS) 어댑터
- ``factory.get_channel``: 채널 종류로 적절한 어댑터 인스턴스를 반환
"""
from app.integrations.notifications.base import (
    ChannelType,
    NotificationChannel,
    SendResult,
)

__all__ = ["ChannelType", "NotificationChannel", "SendResult"]
