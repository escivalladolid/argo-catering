"""app/email_service.py

Replaces:
  - the two free functions in app/email.py (send_verification_code, send_inquiry_confirmation)
  - the duplicated SMTP boilerplate in each
  - the bare Thread(..., daemon=True).start() calls scattered in flow.py / public_portal.py

Centralizes SMTP connection + background-send behavior in one place.

Config field names match app/config.py:23-27 exactly:
  SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME
"""

from __future__ import annotations
import smtplib
import ssl
import threading
import logging
from email.message import EmailMessage
from typing import Callable

logger = logging.getLogger("email_service")


class EmailService:
    def __init__(self, settings):
        """`settings` is your existing pydantic-settings object from app.config."""
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._from_address = f"{(settings.SMTP_FROM_NAME or 'ARGO Catering')} <{settings.SMTP_USER}>"
        self._use_tls = True

    # -- low level ----------------------------------------------------------
    def _send_now(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._from_address
        msg["To"] = to
        msg.set_content(text or "This email requires an HTML-capable mail client to view.")
        msg.add_alternative(html, subtype="html")

        context = ssl.create_default_context()
        with smtplib.SMTP(self._host, self._port, timeout=15) as server:
            server.starttls(context=context)
            server.login(self._username, self._password)
            server.send_message(msg)

    def _send_background(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        def _run():
            try:
                self._send_now(to, subject, html, text)
            except Exception:
                logger.exception("Failed to send email to %s (subject=%r)", to, subject)

        threading.Thread(target=_run, daemon=True).start()

    # -- public API -----------------------------------------------------------
    def send(self, to: str, subject: str, html: str, text: str | None = None, background: bool = True) -> None:
        """Send one email.

        background=True (default) fires a daemon thread and returns immediately.
        Pass background=False for the admin step-up OTP path (flow.py:545),
        which currently blocks the request on purpose.
        """
        if not self._host or not self._username or not self._password:
            import sys
            msg = f"SMTP not configured; email to {to} skipped (subject={subject!r})"
            logger.warning(msg)
            print(f"[email_service] WARNING: {msg}", file=sys.stderr)
            return
        if background:
            self._send_background(to, subject, html, text)
        else:
            self._send_now(to, subject, html, text)

    def send_template(self, to: str, template_fn: Callable[..., dict], background: bool = True, **context) -> None:
        """Render a template function and send the result.

        template_fn is any function from app/email_templates.py that returns
        {"subject": str, "html": str}.

        Example:
            email_service.send_template(to, otp_verification, code=code, reference=ref)
            email_service.send_template(admin_email, otp_verification, code=code, background=False)
        """
        rendered = template_fn(**context)
        self.send(to=to, subject=rendered["subject"], html=rendered["html"], background=background)


# Module-level singleton — created in app/main.py after settings load.
# Import as: from app.email_service import email_service
email_service: EmailService = None  # type: ignore[assignment]
