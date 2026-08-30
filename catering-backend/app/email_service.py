"""app/email_service.py

Sends all service emails. Primary path: Brevo HTTPS API (works on Render free
tier, which blocks outbound SMTP). Fallback: Gmail SMTP via smtplib when
BREVO_API_KEY is unset (e.g. local dev or a paid Render instance).

Sending runs on a background thread; failures are logged, never raised, so a
mail outage can never break inquiry creation, quotations, bookings, or
verification.

Config fields: BREVO_API_KEY, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD,
SMTP_FROM_NAME
"""

from __future__ import annotations
import json
import smtplib
import ssl
import threading
import logging
import urllib.request
import urllib.error
from email.message import EmailMessage
from typing import Callable

logger = logging.getLogger("email_service")

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


class EmailService:
    def __init__(self, settings):
        self._brevo_key = getattr(settings, "BREVO_API_KEY", "")
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD
        self._from_name = settings.SMTP_FROM_NAME or "ARGO Catering"
        self._from_email = self._username or "no-reply@local"
        self._from = f"{self._from_name} <{self._from_email}>"

    def _brevo_configured(self) -> bool:
        return bool(self._brevo_key)

    def _smtp_configured(self) -> bool:
        return bool(self._host and self._username and self._password)

    def _send_via_brevo(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        payload = {
            "sender": {"name": self._from_name, "email": self._from_email},
            "to": [{"email": to}],
            "subject": subject,
            "htmlContent": html,
        }
        if text:
            payload["textContent"] = text
        req = urllib.request.Request(
            BREVO_API_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "api-key": self._brevo_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                logger.info("Brevo OK (subject=%r, to=%s)", subject, to)
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace") if e.fp else ""
            logger.error("Brevo %s: %s", e.code, body)
            raise RuntimeError(f"Brevo {e.code}: {body}") from e

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

    def _configured(self) -> bool:
        return self._brevo_configured() or self._smtp_configured()

    def _send_now(self, to: str, subject: str, html: str, text: str | None = None) -> None:
        if self._brevo_configured():
            self._send_via_brevo(to, subject, html, text)
        elif self._smtp_configured():
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
