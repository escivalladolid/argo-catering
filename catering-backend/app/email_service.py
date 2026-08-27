"""app/email_service.py

Sends emails via Resend HTTP API (works on Render free tier where SMTP is blocked).
Auto-adds recipients to the Resend audience so 403 errors never happen.
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
RESEND_CONTACTS_URL = "https://api.resend.com/audiences"


class EmailService:
    def __init__(self, settings):
        self._resend_key = getattr(settings, "RESEND_API_KEY", "")
        self._from = getattr(settings, "EMAIL_FROM", "") or f"ARGO Catering <{settings.SMTP_USER}>"
        self._audience_id: str | None = None
        # SMTP fallback
        self._host = settings.SMTP_HOST
        self._port = settings.SMTP_PORT
        self._username = settings.SMTP_USER
        self._password = settings.SMTP_PASSWORD

    def _resend_headers(self):
        return {
            "Authorization": f"Bearer {self._resend_key}",
            "Content-Type": "application/json",
            "User-Agent": "ARGO-Catering/1.0",
        }

    def _ensure_audience(self) -> str | None:
        if self._audience_id:
            return self._audience_id
        self._audience_id = "9f344cee-c4ef-4744-82e8-309fe5659177"
        return self._audience_id

    def _ensure_contact(self, email: str) -> None:
        audience_id = self._ensure_audience()
        if not audience_id:
            return
        try:
            payload = json.dumps({"email": email, "unsubscribed": False}).encode("utf-8")
            url = f"{RESEND_CONTACTS_URL}/{audience_id}/contacts"
            req = urllib.request.Request(
                url,
                data=payload,
                headers=self._resend_headers(),
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                logger.info("Resend contact added: %s", email)
        except urllib.error.HTTPError as e:
            if e.code == 409:
                logger.info("Resend contact already exists: %s", email)
            else:
                body = e.read().decode() if e.fp else ""
                logger.warning("Resend add contact %s failed: %s %s", email, e.code, body)
        except Exception:
            logger.warning("Could not add Resend contact %s", email, exc_info=True)

    def _send_via_resend(self, to: str, subject: str, html: str) -> None:
        self._ensure_contact(to)
        payload = json.dumps({
            "from": self._from,
            "to": [to],
            "subject": subject,
            "html": html,
        }).encode("utf-8")

        req = urllib.request.Request(
            RESEND_API_URL,
            data=payload,
            headers=self._resend_headers(),
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                logger.info("Resend OK: %s", resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            logger.error("Resend %s: %s", e.code, body)
            raise RuntimeError(f"Resend {e.code}: {body}") from e

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
