"""채널 어댑터 팩토리.

서비스 계층에서 ``ChannelType`` (또는 문자열) 으로 어댑터 인스턴스를 받아 사용한다.
어댑터는 프로세스 수명동안 재사용되며, ``reset_channels()`` 로 캐시를 비울 수 있다.

테스트 환경에서는 ``register_channel(type, instance)`` 로 mock 인스턴스를 주입한다.
"""
from __future__ import annotations

from threading import Lock
from typing import Literal

from app.integrations.notifications.base import ChannelType, NotificationChannel
from app.integrations.notifications.email.smtp_channel import SmtpEmailChannel
from app.integrations.notifications.kakao.biz_message_channel import (
    KakaoBizMessageChannel,
)
from app.integrations.notifications.sms.channel import SmsChannel

_LOCK = Lock()
_CHANNELS: dict[str, NotificationChannel] = {}


def _build_channel(channel_type: str) -> NotificationChannel | None:
    """채널 종류로 새 인스턴스를 생성. 미지원 채널은 None."""
    if channel_type == "EMAIL":
        return SmtpEmailChannel()
    if channel_type == "KAKAO":
        return KakaoBizMessageChannel()
    if channel_type == "SMS":
        return SmsChannel()
    return None


def get_channel(channel_type: ChannelType | str) -> NotificationChannel | None:
    """채널 어댑터 인스턴스 조회 (프로세스 캐시).

    환경변수 미설정으로 ``verify_config`` 가 False 인 경우에도 인스턴스는 반환된다.
    호출자가 ``verify_config()`` 로 사전 체크하거나, ``send`` 결과의
    ``error_code='CHANNEL_DISABLED'`` 로 우회 판단한다.
    """
    key = str(channel_type).upper()
    with _LOCK:
        if key in _CHANNELS:
            return _CHANNELS[key]
        ch = _build_channel(key)
        if ch is not None:
            _CHANNELS[key] = ch
        return ch


def register_channel(
    channel_type: ChannelType | Literal["EMAIL", "KAKAO", "SMS"],
    instance: NotificationChannel,
) -> None:
    """테스트용: 채널 어댑터 인스턴스를 강제 주입."""
    with _LOCK:
        _CHANNELS[str(channel_type).upper()] = instance


def reset_channels() -> None:
    """테스트용: 캐시 초기화."""
    with _LOCK:
        _CHANNELS.clear()
