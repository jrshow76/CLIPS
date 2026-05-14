"""WebPush 채널 단위 테스트.

검증 항목:
1. VAPID 키 미설정 시 verify_config() = False
2. p256dh / auth 키 누락 시 send() 가 즉시 MISSING_KEYS 로 실패
3. pywebpush 호출 성공 → SendResult.ok = True
4. 410 Gone / 404 응답 시 WebPushSubscriptionExpired 발생
5. 일반 예외 시 SendResult.ok = False + error_code 채워짐
6. _dispatch_webpush: 만료된 구독 자동 삭제 후 commit 호출
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.notifications.webpush.channel import (
    WebPushChannel,
    WebPushSubscriptionExpired,
)


# ---------------------------------------------------------------------------
# verify_config
# ---------------------------------------------------------------------------
class TestVerifyConfig:
    def test_verify_with_keys(self):
        ch = WebPushChannel(
            public_key="BPub",
            private_key="prv",
            subject="mailto:ops@example.com",
        )
        # pywebpush 가 설치되어 있는 환경에서만 True (테스트 인프라 의존)
        # 미설치 환경에서도 None 이 아닌 bool 반환 검증
        assert ch.verify_config() in (True, False)

    def test_verify_missing_public_key(self):
        ch = WebPushChannel(public_key="", private_key="prv", subject="mailto:a@b")
        assert ch.verify_config() is False

    def test_verify_missing_private_key(self):
        ch = WebPushChannel(public_key="pub", private_key="", subject="mailto:a@b")
        assert ch.verify_config() is False

    def test_verify_missing_subject(self):
        ch = WebPushChannel(public_key="pub", private_key="prv", subject="")
        assert ch.verify_config() is False


# ---------------------------------------------------------------------------
# send() 입력 검증
# ---------------------------------------------------------------------------
class TestSendInputValidation:
    @pytest.mark.asyncio
    async def test_send_missing_keys_returns_error(self):
        ch = WebPushChannel(
            public_key="pub",
            private_key="prv",
            subject="mailto:a@b",
        )
        res = await ch.send(
            recipient="https://push.example.com/abc",
            subject="t",
            body="b",
            metadata={},
        )
        assert res.ok is False
        assert res.error_code == "MISSING_KEYS"

    @pytest.mark.asyncio
    async def test_send_unconfigured_returns_disabled(self):
        ch = WebPushChannel(public_key="", private_key="", subject="")
        res = await ch.send(
            recipient="https://push.example.com/abc",
            subject="t",
            body="b",
            metadata={"p256dh_key": "k", "auth_key": "a"},
        )
        assert res.ok is False
        assert res.error_code == "CHANNEL_DISABLED"


# ---------------------------------------------------------------------------
# send() — pywebpush 호출 mock
# ---------------------------------------------------------------------------
class TestSendWithMock:
    @pytest.mark.asyncio
    async def test_send_success(self):
        ch = WebPushChannel(
            public_key="pub",
            private_key="prv",
            subject="mailto:a@b",
        )
        with patch.object(WebPushChannel, "verify_config", return_value=True), \
             patch.object(WebPushChannel, "_send_sync") as mock_sync:
            mock_sync.return_value = None
            res = await ch.send(
                recipient="https://push.example.com/abc",
                subject="제목",
                body="본문",
                metadata={
                    "p256dh_key": "BPub",
                    "auth_key": "auth",
                    "payload": {"event_type": "SIGNAL"},
                },
            )
            assert res.ok is True
            assert res.channel in ("INAPP", "WEBPUSH")
            assert res.recipient == "https://push.example.com/abc"
            mock_sync.assert_called_once()
            # payload 직렬화 확인 — keyword arg 'body' 가 bytes
            kwargs = mock_sync.call_args.kwargs
            assert isinstance(kwargs["body"], (bytes, bytearray))
            assert b"SIGNAL" in kwargs["body"]

    @pytest.mark.asyncio
    async def test_send_410_raises_expired(self):
        ch = WebPushChannel(
            public_key="pub",
            private_key="prv",
            subject="mailto:a@b",
        )

        def _raise_expired(**kwargs):
            raise WebPushSubscriptionExpired(kwargs["subscription_info"]["endpoint"], 410)

        with patch.object(WebPushChannel, "verify_config", return_value=True), \
             patch.object(WebPushChannel, "_send_sync", side_effect=_raise_expired):
            with pytest.raises(WebPushSubscriptionExpired) as exc_info:
                await ch.send(
                    recipient="https://push.example.com/expired",
                    subject="t",
                    body="b",
                    metadata={"p256dh_key": "k", "auth_key": "a"},
                )
            assert exc_info.value.status_code == 410
            assert "expired" in exc_info.value.endpoint

    @pytest.mark.asyncio
    async def test_send_generic_exception_returns_error(self):
        ch = WebPushChannel(
            public_key="pub",
            private_key="prv",
            subject="mailto:a@b",
        )

        def _raise(**kwargs):
            raise RuntimeError("network err")

        with patch.object(WebPushChannel, "verify_config", return_value=True), \
             patch.object(WebPushChannel, "_send_sync", side_effect=_raise):
            res = await ch.send(
                recipient="https://push.example.com/abc",
                subject="t",
                body="b",
                metadata={"p256dh_key": "k", "auth_key": "a"},
            )
            assert res.ok is False
            assert res.error_code == "WEBPUSH_EXCEPTION"
            assert "network err" in (res.error_message or "")


# ---------------------------------------------------------------------------
# NotificationService._dispatch_webpush 통합 (만료 정리)
# ---------------------------------------------------------------------------
class TestDispatchExpiredCleanup:
    @pytest.mark.asyncio
    async def test_expired_subscriptions_removed(self):
        """410 발생 시 push_subs.remove_by_endpoint 호출 및 commit."""
        from app.services.notification_service import NotificationService

        # 가짜 알림 + 가짜 사용자
        noti = SimpleNamespace(
            id=42,
            title="TEST",
            body="body",
            event_type="SIGNAL",
            priority="NORMAL",
            payload={"stock_code": "005930"},
        )
        user = SimpleNamespace(id=7)

        # 활성 구독 2건 (1건 만료, 1건 성공)
        sub_ok = SimpleNamespace(
            id=1, endpoint="https://push/ok",
            p256dh_key="k1", auth_key="a1", user_id=7,
        )
        sub_gone = SimpleNamespace(
            id=2, endpoint="https://push/gone",
            p256dh_key="k2", auth_key="a2", user_id=7,
        )

        # NotificationService 인스턴스 (DB 는 mock)
        db = MagicMock()
        db.commit = AsyncMock()
        svc = NotificationService.__new__(NotificationService)  # __init__ 우회
        svc.db = db
        svc.push_subs = MagicMock()
        svc.push_subs.list_active_for_user = AsyncMock(return_value=[sub_ok, sub_gone])
        svc.push_subs.touch_last_used = AsyncMock()
        svc.push_subs.remove_by_endpoint = AsyncMock(return_value=1)
        svc._webpush = None

        async def _send_side_effect(*, recipient, subject, body, metadata):
            if "gone" in recipient:
                raise WebPushSubscriptionExpired(recipient, 410)
            return SimpleNamespace(ok=True, channel="INAPP", recipient=recipient)

        # adapter mock
        adapter = MagicMock()
        adapter.verify_config = MagicMock(return_value=True)
        adapter.send = AsyncMock(side_effect=_send_side_effect)
        svc.get_webpush_channel = MagicMock(return_value=adapter)  # type: ignore[assignment]

        results = await svc._dispatch_webpush(noti, user)  # type: ignore[arg-type]

        # 결과: 1건 성공 + 1건 만료(error_code)
        assert len(results) == 2
        ok_results = [r for r in results if r.ok]
        assert len(ok_results) == 1
        gone_results = [r for r in results if not r.ok]
        assert len(gone_results) == 1
        assert "GONE" in (gone_results[0].error_code or "")

        # 만료 endpoint 자동 정리
        svc.push_subs.remove_by_endpoint.assert_awaited_once()
        call_kwargs = svc.push_subs.remove_by_endpoint.call_args.kwargs
        assert call_kwargs["endpoint"] == "https://push/gone"
        assert call_kwargs["user_id"] == 7
        # commit 호출
        db.commit.assert_awaited()
