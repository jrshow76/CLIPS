"""SMTP 이메일 채널.

- 라이브러리 우선순위: ``aiosmtplib`` → 미설치 시 ``smtplib`` + ``run_in_executor``.
  CI/개발 환경에서 ``aiosmtplib`` 가 없어도 동작하도록 두 경로를 모두 지원한다.
- 본문은 jinja2 기반 HTML 템플릿을 사용한다. 자동 escape 활성화로 XSS 방어.
- 첨부파일은 ``metadata["attachments"]`` 에 ``[(filename, content_bytes, mime)]``
  형태로 전달한다. 일일 리포트 PDF/CSV 등을 첨부할 때 사용.
- SPF/DKIM/DMARC: 발신자 도메인 측 인프라 설정으로 다루며, 본 모듈은 ``From``
  헤더만 ``SMTP_FROM`` 으로 지정. 운영 시 도메인 DNS에 SPF(``v=spf1 ...``),
  DKIM, DMARC 레코드를 등록하여 스팸 분류를 회피한다.
"""
from __future__ import annotations

import asyncio
import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import structlog

from app.core.config import settings
from app.integrations.notifications.base import (
    ChannelType,
    NotificationChannel,
    SendResult,
)

log = structlog.get_logger(__name__)


# jinja2 환경: 모듈 로드 시점에 한 번만 초기화
try:  # pragma: no cover - jinja2 미설치 환경 폴백
    from jinja2 import Environment, FileSystemLoader, select_autoescape

    _TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"
    _JINJA_ENV: "Environment | None" = Environment(
        loader=FileSystemLoader(str(_TEMPLATE_DIR)),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
except Exception:  # pragma: no cover
    _JINJA_ENV = None


def render_template(template_name: str, context: dict[str, Any]) -> str:
    """주어진 이름의 jinja2 템플릿을 렌더링하여 HTML 문자열을 반환.

    - 템플릿 이름 예: ``signal_alert.html``, ``daily_report.html``.
    - jinja2 미설치 또는 템플릿 누락 시 간단한 fallback 텍스트를 반환한다.
    """
    if _JINJA_ENV is None:
        # 폴백: 키-값을 단순 직렬화
        items = "\n".join(f"<li>{k}: {v}</li>" for k, v in context.items())
        return f"<html><body><h1>{template_name}</h1><ul>{items}</ul></body></html>"
    try:
        tpl = _JINJA_ENV.get_template(template_name)
        return tpl.render(**context)
    except Exception as e:  # noqa: BLE001
        log.warning("email_template_render_failed", name=template_name, error=str(e))
        items = "\n".join(f"<li>{k}: {v}</li>" for k, v in context.items())
        return f"<html><body><h1>{template_name}</h1><ul>{items}</ul></body></html>"


class SmtpEmailChannel(NotificationChannel):
    """SMTP 이메일 어댑터.

    ``SMTP_USE_TLS=True`` 면 STARTTLS, 포트 465 인 경우 SMTPS(SSL) 직결.
    """

    channel_type: ChannelType = "EMAIL"

    def __init__(
        self,
        *,
        host: str | None = None,
        port: int | None = None,
        user: str | None = None,
        password: str | None = None,
        from_email: str | None = None,
        use_tls: bool | None = None,
        timeout_sec: float = 10.0,
    ) -> None:
        self.host = host if host is not None else settings.SMTP_HOST
        self.port = port if port is not None else settings.SMTP_PORT
        self.user = user if user is not None else settings.SMTP_USER
        self.password = password if password is not None else settings.SMTP_PASSWORD
        self.from_email = from_email if from_email is not None else settings.SMTP_FROM
        self.use_tls = use_tls if use_tls is not None else settings.SMTP_USE_TLS
        self.timeout_sec = timeout_sec

    def verify_config(self) -> bool:
        return bool(self.host and self.from_email)

    async def send(
        self,
        *,
        recipient: str,
        subject: str | None,
        body: str,
        metadata: dict[str, Any] | None = None,
    ) -> SendResult:
        """단일 이메일 발송.

        - ``metadata['html']=True`` (기본 True) 이면 HTML 본문으로 처리.
        - ``metadata['attachments']`` 리스트: ``[(filename, bytes, mime_type)]``.
        """
        meta = metadata or {}
        is_html = bool(meta.get("html", True))
        attachments: list[tuple[str, bytes, str]] = list(meta.get("attachments", []))

        message = self._build_message(
            recipient=recipient,
            subject=subject or "TradePilot 알림",
            body=body,
            is_html=is_html,
            attachments=attachments,
        )

        started = time.monotonic()
        try:
            await self._send_message(message)
            elapsed = int((time.monotonic() - started) * 1000)
            log.info(
                "email_sent",
                recipient=_mask_email(recipient),
                subject=subject,
                elapsed_ms=elapsed,
            )
            return SendResult(
                ok=True,
                channel=self.channel_type,
                recipient=recipient,
                elapsed_ms=elapsed,
            )
        except Exception as e:  # noqa: BLE001
            elapsed = int((time.monotonic() - started) * 1000)
            log.warning(
                "email_send_failed",
                recipient=_mask_email(recipient),
                error=str(e)[:200],
                elapsed_ms=elapsed,
            )
            return SendResult(
                ok=False,
                channel=self.channel_type,
                recipient=recipient,
                error_code="SMTP_ERROR",
                error_message=str(e)[:200],
                elapsed_ms=elapsed,
            )

    # ------------------------------------------------------------------
    # 내부
    # ------------------------------------------------------------------
    def _build_message(
        self,
        *,
        recipient: str,
        subject: str,
        body: str,
        is_html: bool,
        attachments: list[tuple[str, bytes, str]],
    ) -> EmailMessage:
        msg = EmailMessage()
        msg["From"] = self.from_email
        msg["To"] = recipient
        msg["Subject"] = subject
        if is_html:
            # 텍스트 fallback + HTML 본문
            msg.set_content("HTML 메일을 지원하는 클라이언트에서 확인해주세요.")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)

        for filename, content, mime in attachments:
            maintype, _, subtype = mime.partition("/")
            if not maintype or not subtype:
                maintype, subtype = "application", "octet-stream"
            msg.add_attachment(
                content,
                maintype=maintype,
                subtype=subtype,
                filename=filename,
            )
        return msg

    async def _send_message(self, message: EmailMessage) -> None:
        """aiosmtplib 우선, 없으면 smtplib + 스레드 풀."""
        # 1) aiosmtplib 시도
        try:
            import aiosmtplib  # type: ignore[import-not-found]

            kwargs: dict[str, Any] = {
                "hostname": self.host,
                "port": self.port,
                "timeout": self.timeout_sec,
                "username": self.user or None,
                "password": self.password or None,
            }
            if self.port == 465:
                kwargs["use_tls"] = True
            elif self.use_tls:
                kwargs["start_tls"] = True
            await aiosmtplib.send(message, **kwargs)
            return
        except ImportError:
            pass

        # 2) smtplib(동기) + executor 폴백
        def _send_sync() -> None:
            context = ssl.create_default_context()
            if self.port == 465:
                with smtplib.SMTP_SSL(
                    self.host, self.port, timeout=self.timeout_sec, context=context
                ) as server:
                    if self.user:
                        server.login(self.user, self.password)
                    server.send_message(message)
            else:
                with smtplib.SMTP(self.host, self.port, timeout=self.timeout_sec) as server:
                    if self.use_tls:
                        server.starttls(context=context)
                    if self.user:
                        server.login(self.user, self.password)
                    server.send_message(message)

        await asyncio.get_running_loop().run_in_executor(None, _send_sync)


def _mask_email(email: str) -> str:
    """이메일 주소를 로그용으로 마스킹: ``foo@bar.com`` → ``f**@bar.com``."""
    if "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if not local:
        return f"***@{domain}"
    return f"{local[0]}{'*' * max(1, len(local) - 1)}@{domain}"
