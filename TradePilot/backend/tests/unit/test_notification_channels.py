"""알림 채널 단위 테스트.

검증:
1. 각 채널 어댑터 send() 가 mock 환경에서 SendResult 를 정상 반환
2. 이메일 jinja2 템플릿 렌더링이 한글/변수 치환을 정상 처리
3. 카카오 알림톡: 필수 변수 누락 시 즉시 실패 응답
4. SMS: 본문 90바이트 초과 시 truncate
5. 채널 우선순위 결정 로직 (NotificationService._resolve_channels)
"""
from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.integrations.notifications.base import SendResult
from app.integrations.notifications.email.smtp_channel import (
    SmtpEmailChannel,
    _mask_email,
    render_template,
)
from app.integrations.notifications.kakao.biz_message_channel import (
    KakaoBizMessageChannel,
    _mask_phone,
)
from app.integrations.notifications.kakao.templates_registry import (
    KAKAO_TEMPLATES,
    get_kakao_template,
    render_kakao_content,
)
from app.integrations.notifications.sms.channel import SmsChannel, _truncate_for_sms


# ---------------------------------------------------------------------------
# 이메일 채널
# ---------------------------------------------------------------------------
class TestEmailChannel:
    def test_verify_config_with_host(self):
        ch = SmtpEmailChannel(host="smtp.test.com", from_email="t@test.com")
        assert ch.verify_config() is True

    def test_verify_config_without_host(self):
        ch = SmtpEmailChannel(host="", from_email="")
        assert ch.verify_config() is False

    def test_mask_email_normal(self):
        assert _mask_email("alice@example.com").startswith("a")
        assert "@example.com" in _mask_email("alice@example.com")

    def test_mask_email_short(self):
        # 단문자 로컬도 한 자리 마스킹 처리
        masked = _mask_email("a@b.com")
        assert masked.endswith("@b.com")
        assert masked.startswith("a")

    def test_mask_email_invalid(self):
        assert _mask_email("invalid") == "***"

    def test_render_template_fallback(self):
        """jinja2 가 있더라도 누락 템플릿은 fallback HTML 반환."""
        out = render_template("__missing__.html", {"k": "v"})
        assert "k" in out and "v" in out

    def test_render_signal_alert_template(self):
        out = render_template(
            "signal_alert.html",
            {
                "stock_code": "005930",
                "stock_name": "삼성전자",
                "action": "BUY",
                "rule_code": "GOLDEN_CROSS",
                "confidence": "HIGH",
                "trigger_price": "70000",
                "strategy_name": "테스트 전략",
                "generated_at": "2026-05-14 09:00:00",
            },
        )
        assert "삼성전자" in out
        assert "005930" in out
        assert "BUY" in out

    @pytest.mark.asyncio
    async def test_send_returns_ok_when_aiosmtplib_mocked(self):
        ch = SmtpEmailChannel(host="smtp.test", from_email="t@test")
        with patch.object(ch, "_send_message", new=AsyncMock(return_value=None)):
            res = await ch.send(
                recipient="user@example.com",
                subject="제목",
                body="<p>본문</p>",
            )
        assert isinstance(res, SendResult)
        assert res.ok is True
        assert res.channel == "EMAIL"

    @pytest.mark.asyncio
    async def test_send_returns_error_on_exception(self):
        ch = SmtpEmailChannel(host="smtp.test", from_email="t@test")
        with patch.object(ch, "_send_message", new=AsyncMock(side_effect=RuntimeError("boom"))):
            res = await ch.send(recipient="u@e.com", subject="s", body="b")
        assert res.ok is False
        assert res.error_code == "SMTP_ERROR"
        assert "boom" in (res.error_message or "")


# ---------------------------------------------------------------------------
# 카카오 알림톡
# ---------------------------------------------------------------------------
class TestKakaoChannel:
    def test_template_registry_has_all_events(self):
        for code in ["SIGNAL_ALERT", "EXECUTION_ALERT", "KILL_SWITCH", "SECURITY_ALERT", "DAILY_REPORT"]:
            assert code in KAKAO_TEMPLATES
            tpl = get_kakao_template(code)
            assert tpl is not None
            assert tpl.template_id

    def test_render_kakao_content_substitutes_variables(self):
        out = render_kakao_content("KILL_SWITCH", {"reason": "테스트", "canceled_count": "3", "failed_count": "0"})
        assert "테스트" in out
        assert "3" in out

    def test_mask_phone_normal(self):
        out = _mask_phone("01012345678")
        assert out.startswith("010")
        assert out.endswith("5678")
        assert "*" in out

    def test_mask_phone_short(self):
        assert _mask_phone("123") == "***"

    @pytest.mark.asyncio
    async def test_verify_config_returns_false_without_keys(self):
        ch = KakaoBizMessageChannel(app_key="", secret="", sender_key="")
        assert ch.verify_config() is False

    @pytest.mark.asyncio
    async def test_send_fails_when_template_missing(self):
        ch = KakaoBizMessageChannel(app_key="k", secret="s", sender_key="sk")
        res = await ch.send(recipient="01012345678", subject=None, body="x", metadata={})
        assert res.ok is False
        assert res.error_code == "TEMPLATE_REQUIRED"

    @pytest.mark.asyncio
    async def test_send_fails_when_variable_missing(self):
        ch = KakaoBizMessageChannel(app_key="k", secret="s", sender_key="sk")
        res = await ch.send(
            recipient="01012345678",
            subject=None,
            body="x",
            metadata={"template_code": "KILL_SWITCH", "variables": {"reason": "x"}},
        )
        assert res.ok is False
        assert res.error_code == "VARIABLE_MISSING"

    @pytest.mark.asyncio
    async def test_send_disabled_when_no_config(self):
        ch = KakaoBizMessageChannel(app_key="", secret="", sender_key="")
        res = await ch.send(
            recipient="01012345678",
            subject=None,
            body="x",
            metadata={
                "template_code": "SECURITY_ALERT",
                "variables": {"event_type_ko": "테스트", "occurred_at": "2026-05-14"},
            },
        )
        assert res.ok is False
        assert res.error_code == "CHANNEL_DISABLED"

    @pytest.mark.asyncio
    async def test_send_ok_with_mocked_httpx(self):
        ch = KakaoBizMessageChannel(app_key="k", secret="s", sender_key="sk")

        class _Resp:
            status_code = 200

            def json(self):
                return {"header": {"isSuccessful": True}, "message": {"messageId": "m-1"}}

            text = "{}"

        class _Client:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, headers=None, json=None):
                return _Resp()

        with patch("app.integrations.notifications.kakao.biz_message_channel.httpx.AsyncClient", _Client):
            res = await ch.send(
                recipient="01012345678",
                subject=None,
                body="x",
                metadata={
                    "template_code": "SECURITY_ALERT",
                    "variables": {"event_type_ko": "테스트", "occurred_at": "2026-05-14"},
                },
            )
        assert res.ok is True
        assert res.provider_message_id == "m-1"


# ---------------------------------------------------------------------------
# SMS 채널
# ---------------------------------------------------------------------------
class TestSmsChannel:
    def test_truncate_for_sms_short_pass(self):
        assert _truncate_for_sms("hello", 90) == "hello"

    def test_truncate_for_sms_long_korean(self):
        body = "가" * 100  # 한글 100자 ≈ 300 bytes
        out = _truncate_for_sms(body, 90)
        assert len(out.encode("utf-8")) <= 90
        assert out.endswith("...")

    def test_verify_config_nhn(self):
        ch = SmsChannel(provider="nhn_cloud", app_key="k", secret="s", from_number="0212345678")
        assert ch.verify_config() is True

    def test_verify_config_aws(self):
        ch = SmsChannel(provider="aws_sns", aws_access_key="ak", aws_secret_key="sk", aws_region="us-east-1")
        assert ch.verify_config() is True

    def test_verify_config_missing(self):
        ch = SmsChannel(provider="nhn_cloud", app_key="", secret="", from_number="")
        assert ch.verify_config() is False

    @pytest.mark.asyncio
    async def test_send_disabled(self):
        ch = SmsChannel(provider="nhn_cloud", app_key="", secret="", from_number="")
        res = await ch.send(recipient="01012345678", subject=None, body="x")
        assert res.ok is False
        assert res.error_code == "CHANNEL_DISABLED"

    @pytest.mark.asyncio
    async def test_send_nhn_ok_with_mock(self):
        ch = SmsChannel(provider="nhn_cloud", app_key="k", secret="s", from_number="0212345678")

        class _Resp:
            status_code = 200

            def json(self):
                return {
                    "header": {"isSuccessful": True},
                    "body": {"data": {"requestId": "req-1"}},
                }

            text = "{}"

        class _Client:
            def __init__(self, **kw):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, *a):
                return False

            async def post(self, url, headers=None, json=None):
                return _Resp()

        with patch("app.integrations.notifications.sms.channel.httpx.AsyncClient", _Client):
            res = await ch.send(recipient="01012345678", subject="t", body="짧은 메시지")
        assert res.ok is True
        assert res.provider_message_id == "req-1"


# ---------------------------------------------------------------------------
# 채널 우선순위 결정 로직
# ---------------------------------------------------------------------------
class TestChannelResolution:
    def test_resolve_channels_signal_default(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService.__new__(NotificationService)
        # mock channel pref
        pref = SimpleNamespace(
            inapp_enabled=True, email_enabled=True, telegram_enabled=False, telegram_chat_id=None
        )
        result = svc._resolve_channels("SIGNAL", pref, {})
        assert "INAPP" in result
        assert "EMAIL" in result
        assert "KAKAO" not in result

    def test_resolve_channels_kill_switch_all_enabled(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService.__new__(NotificationService)
        pref = SimpleNamespace(
            inapp_enabled=True, email_enabled=True, telegram_enabled=True, telegram_chat_id="x"
        )
        result = svc._resolve_channels("KILL_SWITCH", pref, {})
        assert set(["INAPP", "EMAIL", "KAKAO", "SMS"]).issubset(set(result))

    def test_resolve_channels_user_disabled(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService.__new__(NotificationService)
        pref = SimpleNamespace(
            inapp_enabled=False, email_enabled=False, telegram_enabled=False, telegram_chat_id=None
        )
        result = svc._resolve_channels("SIGNAL", pref, {})
        assert result == []

    def test_resolve_channels_payload_override(self):
        from app.services.notification_service import NotificationService

        svc = NotificationService.__new__(NotificationService)
        pref = SimpleNamespace(
            inapp_enabled=True, email_enabled=True, telegram_enabled=True, telegram_chat_id="x"
        )
        result = svc._resolve_channels(
            "SIGNAL", pref, {"channels": ["KAKAO"]}
        )
        assert result == ["KAKAO"]


# ---------------------------------------------------------------------------
# Fallback 검증 (카카오 실패 → SMS)
# ---------------------------------------------------------------------------
class TestFallback:
    @pytest.mark.asyncio
    async def test_dispatch_invokes_sms_fallback_on_kakao_fail(self):
        """KAKAO 발송이 실패하면 SMS 채널로 대체 발송된다."""
        from app.integrations.notifications import factory as ch_factory
        from app.models.notification import Notification
        from app.services.notification_service import NotificationService

        # Mock 채널: KAKAO 는 실패, SMS 는 성공
        kakao_mock = MagicMock()
        kakao_mock.verify_config = MagicMock(return_value=True)
        kakao_mock.send = AsyncMock(
            return_value=SendResult(
                ok=False,
                channel="KAKAO",
                recipient="01012345678",
                error_code="KAKAO_TIMEOUT",
            )
        )
        sms_mock = MagicMock()
        sms_mock.verify_config = MagicMock(return_value=True)
        sms_mock.send = AsyncMock(
            return_value=SendResult(
                ok=True,
                channel="SMS",
                recipient="01012345678",
                provider_message_id="sms-1",
            )
        )

        ch_factory.register_channel("KAKAO", kakao_mock)
        ch_factory.register_channel("SMS", sms_mock)
        try:
            # 가짜 DB/repo/svc
            svc = NotificationService.__new__(NotificationService)
            svc.db = MagicMock()
            noti = Notification(
                id=42,
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
            svc.db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=MagicMock(return_value=noti)))
            svc.db.get = AsyncMock(
                return_value=SimpleNamespace(
                    id=1, public_id="pub", email="t@test.com", phone="01012345678", nickname="t"
                )
            )
            svc.db.commit = AsyncMock(return_value=None)

            ch_pref = SimpleNamespace(
                inapp_enabled=True,
                email_enabled=False,
                telegram_enabled=True,  # KAKAO
                telegram_chat_id="01012345678",
            )
            svc.channels = MagicMock()
            svc.channels.get_or_create = AsyncMock(return_value=ch_pref)

            results = await svc.dispatch(42)
            # KAKAO 1 + SMS 1
            assert len(results) >= 2
            channels = [r.channel for r in results]
            assert "KAKAO" in channels
            assert "SMS" in channels
            sms_mock.send.assert_awaited()  # SMS fallback 호출
        finally:
            ch_factory.reset_channels()
