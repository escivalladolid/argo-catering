"""app/email_service.py

Sends emails via Resend HTTP API (works on Render free tier where SMTP is blocked).
Falls back to SMTP if RESEND_API_KEY is not set.

Config fields: RESEND_API_KEY, EMAIL_FROM, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD
"""

from __future__ import annotations
import smtplib
import ssl
import threading
import logging
import urllib.request
import urllib.error
import json
from email.message import EmailMessage
from typing import Callable

logger = logging.getLogger("email_service")

RESEND_API_URL = "https://api.resend.com/emails"


class EmailService:
    def __init__(self, settings):
        self._resend_key = getattr(settings, "RESEND_API_KEY", "")
        self._from = getattr(settings, "EMAIL_FROM", "") or f"ARGO Catering <{settings.SMTP_USER}>"
        # SMTP fallback
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD

    def _send_via_resend(self, to: str, subject: str, html: str) -> None:
        payload = json.dumps({
            "from": self._from,
            "to": [to],
            "subject": subject,
            "html": html,
        }).encode("utf-8")

        req = urllib.request.Request(
            RESEND_API_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._resend_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            if resp.status not in (200, 201):
                raise RuntimeError(f"Resend returned {resp.status}")

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
        if self._resend_key:
            self._send_via_resend(to, subject, html)
        elif self._host and self._username and self._password:
            self._send_via_smtp(to, subject, html, text)
        else:
            logger.warning("No email provider configured; email to %s skipped", to)

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
