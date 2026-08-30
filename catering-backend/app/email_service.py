"""app/email_service.py

Sends all service emails over Gmail SMTP (SMTP_HOST / SMTP_PORT / SMTP_USER /
SMTP_PASSWORD with a Gmail address + App Password). Sending runs on a
background thread; failures are logged, never raised, so a mail outage can
never break inquiry creation, quotations, bookings, or verification.

Config fields: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_NAME
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
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._from_name = settings.SMTP_FROM_NAME or "ARGO Catering"
        if self._username:
            self._from = f"{self._from_name} <{self._username}>"
        else:
            self._from = f"{self._from_name} <no-reply@local>"

    def _configured(self) -> bool:
        return bool(self._host and self._username and self._password)

    def _send_via_smtp(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self._from
        msg["To"] = to
        msg.set_content(text or "This email requires an HTML-capable mail client to view.")
        msg.add_alternative(html, subtype="html")

        context = ssl.create_default_context()
        if self._port == 465:
            with smtplib.SMTP_SSL(self._host, self._port, timeout=15, context=context) as server:
                server.login(self._username, self._password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(self._host, self._port, timeout=15) as server:
                server.starttls(context=context)
                server.login(self._username, self._password)
                server.send_message(msg)

    def _send_now(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        if not self._configured():
            logger.warning("No SMTP credentials configured; email to %s skipped", to)
            return
        self._send_via_smtp(to, subject, html, text)

    def _send_background(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        def _run():
            try:
                self._send_now(to, subject, html, text)
            except Exception:
                logger.exception("Failed to send email to %s (subject=%r)", to, subject)

        threading.Thread(target=_run, daemon=True).start()

    def send(self, to: str, subject: str, html: str, text: str | None = None, background: bool = True) -> None:
        if background:
            self._send_background(to, subject, html, text)
        else:
            self._send_now(to, subject, html, text)

    def send_template(self, to: str, template_fn: Callable[..., dict], background: bool = True, **context) -> None:
        rendered = template_fn(**context)
        self.send(to=to, subject=rendered["subject"], html=rendered["html"], background=background)


# Module-level singleton — created in app/main.py after settings load.
email_service: EmailService = None  # type: ignore[assignment]
