"""이메일(SMTP) 채널 패키지."""
from app.integrations.notifications.email.smtp_channel import (
    SmtpEmailChannel,
    render_template,
)

__all__ = ["SmtpEmailChannel", "render_template"]
