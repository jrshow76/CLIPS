"""알림 발송 통합 흐름 테스트.

NotificationService 의 send_* 메서드 호출 → DB notification 행 생성 →
dispatch → 채널 어댑터(mock) 호출 → 결과 페이로드 누적까지 검증한다.

DB/Redis 가용성에 따라 일부 케이스는 skip 될 수 있다.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.integrations.notifications import factory as ch_factory
from app.integrations.notifications.base import SendResult

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def _reset_channels():
    ch_factory.reset_channels()
    yield
    ch_factory.reset_channels()


def _mock_channel(channel_type: str, ok: bool = True, error: str | None = None):
    m = MagicMock()
    m.verify_config = MagicMock(return_value=True)
    m.send = AsyncMock(
        return_value=SendResult(
            ok=ok,
            channel=channel_type,  # type: ignore[arg-type]
            recipient="x",
            provider_message_id=f"prov-{channel_type}" if ok else None,
            error_code=error,
        )
    )
    m.channel_type = channel_type
    return m


def _signup_and_login(app_client) -> tuple[str, str]:
    email = f"flow-{uuid.uuid4().hex[:8]}@test.local"
    pw = "Abcd1234!"
    app_client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": pw, "nickname": "t"},
    )
    r = app_client.post("/api/v1/auth/login", json={"email": email, "password": pw})
    if r.status_code != 200:
        pytest.skip("로그인 실패 - DB 미가용 환경")
    data = r.json().get("data") or {}
    return data.get("access_token", ""), email


def test_notification_settings_get_returns_default(app_client) -> None:
    """GET /settings/notifications 가 기본 채널 매핑을 포함하여 응답."""
    token, _ = _signup_and_login(app_client)
    r = app_client.get(
        "/api/v1/settings/notifications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["inapp_enabled"] is True
    assert "event_channel_map" in data
    assert "SIGNAL" in data["event_channel_map"]
    assert "KILL_SWITCH" in data["event_channel_map"]


def test_notification_settings_update_kakao_enabled(app_client) -> None:
    token, _ = _signup_and_login(app_client)
    r = app_client.put(
        "/api/v1/settings/notifications",
        headers={"Authorization": f"Bearer {token}"},
        json={"kakao_enabled": True, "sms_enabled": True},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["kakao_enabled"] is True


def test_kakao_optin_registers_phone(app_client) -> None:
    token, _ = _signup_and_login(app_client)
    r = app_client.post(
        "/api/v1/settings/notifications/kakao/optin",
        headers={"Authorization": f"Bearer {token}"},
        json={"phone": "010-1234-5678", "consent": True},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["consent"] is True
    assert "*" in data["phone"]  # 마스킹


def test_test_notification_inapp(app_client) -> None:
    token, _ = _signup_and_login(app_client)
    r = app_client.post(
        "/api/v1/settings/notifications/test",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": "INAPP"},
    )
    assert r.status_code == 200, r.text
    assert r.json()["data"]["sent"] is True


def test_test_notification_email_mock_when_smtp_missing(app_client) -> None:
    """SMTP 설정이 없으면 mock 응답."""
    token, _ = _signup_and_login(app_client)
    # 이메일 채널 활성화 (default true)
    r = app_client.post(
        "/api/v1/settings/notifications/test",
        headers={"Authorization": f"Bearer {token}"},
        json={"channel": "EMAIL"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    # SMTP_HOST 미설정 환경에서는 mock=True
    assert data["sent"] is True


@pytest.mark.asyncio
async def test_send_signal_alert_persists_notification_row():
    """send_signal_alert 가 DB notification 행을 생성하고 dispatch 를 호출한다.

    DB 가용 환경에서만 의미있는 검증이지만, mock fallback 으로 최소 호출 흐름만 확인.
    """
    from app.services.notification_service import NotificationService

    # Mock 채널 등록 (EMAIL 만)
    email_mock = _mock_channel("EMAIL", ok=True)
    ch_factory.register_channel("EMAIL", email_mock)

    svc = NotificationService.__new__(NotificationService)
    svc.db = MagicMock()
    svc.db.add = MagicMock()
    svc.db.commit = AsyncMock(return_value=None)
    svc.db.refresh = AsyncMock(return_value=None)
    svc.db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=None))
    )

    # notify_user 가 호출하는 Notification 행 인스턴스를 추적
    persisted = []

    def _add(obj):
        persisted.append(obj)
        # SQLAlchemy 가 했을 자동 PK 부여 흉내
        if hasattr(obj, "id") and obj.id is None:
            obj.id = 1

    svc.db.add = _add
    svc.channels = MagicMock()
    ch_pref = SimpleNamespace(
        inapp_enabled=True,
        email_enabled=True,
        telegram_enabled=False,
        telegram_chat_id=None,
    )
    svc.channels.get_or_create = AsyncMock(return_value=ch_pref)
    svc.notis = MagicMock()

    user = SimpleNamespace(
        id=1, public_id="pub-id", email="t@test.com", phone=None, nickname="t"
    )

    # Redis publish 는 모킹
    from app.core import redis_client as rc

    class _R:
        async def publish(self, *a, **kw):
            return 1

    rc._redis = _R()  # type: ignore[attr-defined]
    try:
        # dispatch 가 DB.execute -> Notification 조회 흉내내야 함
        # 첫 호출: notify_user 자체 — DB 행 ID 부여됨
        # 두 번째 호출: dispatch 의 select(Notification).where(id==X)
        first_noti = None

        def _add_capture(obj):
            nonlocal first_noti
            persisted.append(obj)
            if hasattr(obj, "id") and obj.id is None:
                obj.id = 100
            first_noti = obj

        svc.db.add = _add_capture
        svc.db.execute = AsyncMock(
            side_effect=lambda *a, **kw: MagicMock(
                scalar_one_or_none=MagicMock(return_value=first_noti)
            )
        )
        svc.db.get = AsyncMock(return_value=user)

        noti = await svc.send_signal_alert(
            user=user,
            stock_code="005930",
            stock_name="삼성전자",
            action="BUY",
            rule_code="GOLDEN_CROSS",
            confidence="HIGH",
            trigger_price="70000",
            strategy_name="t",
        )
        # 알림 행이 저장되었고 EMAIL 채널 send 가 호출됨
        assert noti is not None
        assert any(getattr(p, "event_type", "") == "SIGNAL" for p in persisted)
        email_mock.send.assert_awaited()
    finally:
        rc._redis = None  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_dispatch_uses_kakao_when_user_optin():
    """사용자가 카카오 옵트인 했을 때 KAKAO 채널이 dispatch 된다."""
    from app.models.notification import Notification
    from app.services.notification_service import NotificationService

    kakao_mock = _mock_channel("KAKAO", ok=True)
    ch_factory.register_channel("KAKAO", kakao_mock)

    svc = NotificationService.__new__(NotificationService)
    svc.db = MagicMock()
    svc.db.commit = AsyncMock(return_value=None)

    user = SimpleNamespace(
        id=1, public_id="pub", email="t@test.com", phone="01012345678", nickname="t"
    )
    svc.db.get = AsyncMock(return_value=user)
    noti = Notification(
        id=10,
        user_id=1,
        event_type="SECURITY",
        priority="HIGH",
        channel="INAPP",
        title="t",
        body="b",
        payload={
            "kakao_template_code": "SECURITY_ALERT",
            "kakao_variables": {"event_type_ko": "x", "occurred_at": "2026-05-14"},
        },
        read=False,
        created_at=datetime.now(tz=timezone.utc),
    )
    svc.db.execute = AsyncMock(
        return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=noti))
    )
    pref = SimpleNamespace(
        inapp_enabled=True, email_enabled=False, telegram_enabled=True, telegram_chat_id="01012345678"
    )
    svc.channels = MagicMock()
    svc.channels.get_or_create = AsyncMock(return_value=pref)

    results = await svc.dispatch(10)
    channels = [r.channel for r in results]
    assert "KAKAO" in channels
    kakao_mock.send.assert_awaited()
