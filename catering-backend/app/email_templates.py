"""app/email_templates.py

Pure functions, no Jinja/templates-directory needed. Each returns
{"subject": str, "html": str} and is called as:

    email_service.send_template(to, inquiry_received, name=..., reference=..., status_url=...)

Ported from the ARGO email preview HTML — table-based, inline styles, so it
survives Gmail/Outlook/Apple Mail clipping.
"""

from __future__ import annotations
from typing import Iterable

BRAND_NAME = "ARGO"
BRAND_SUB = "Catering"
SUPPORT_EMAIL = "catering@argo-platform.com"
SUPPORT_HOURS = "8:00 AM–6:00 PM"
SUPPORT_PHONE = "09XX XXX XXXX"

_WRAP_OPEN = """
<style>
  @media only screen and (max-width:480px){{
    .em-pad{{padding-left:20px !important;padding-right:20px !important;}}
    .em-pad-hdr{{padding:18px 20px !important;}}
    .em-code{{font-size:24px !important;letter-spacing:.22em !important;}}
    .em-ref{{font-size:18px !important;}}
    .em-title{{font-size:15px !important;}}
    .em-btn a{{display:block !important;text-align:center !important;}}
  }}
</style>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f1f5f9;padding:24px 12px;font-family:Arial,Helvetica,sans-serif;">
<tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border-radius:12px;overflow:hidden;">
<tr><td class="em-pad-hdr" style="background:#0f172a;padding:22px 32px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="vertical-align:middle;">
      <table role="presentation" cellpadding="0" cellspacing="0"><tr>
        <td style="width:34px;height:34px;background:#2563eb;border-radius:8px;text-align:center;vertical-align:middle;color:#ffffff;font-weight:bold;font-size:14px;font-family:Arial,sans-serif;">AR</td>
        <td style="padding-left:10px;color:#ffffff;font-size:15px;font-weight:bold;font-family:Arial,sans-serif;">{brand} <span style="color:#94a3b8;font-weight:normal;">| {brand_sub}</span></td>
      </tr></table>
    </td>
  </tr></table>
</td></tr>""".format(brand=BRAND_NAME, brand_sub=BRAND_SUB)

_WRAP_CLOSE = """
<tr><td class="em-pad" style="background:#f8fafc;padding:22px 32px;border-top:1px solid #e2e8f0;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr>
    <td style="font-size:11.5px;color:#94a3b8;font-family:Arial,sans-serif;line-height:1.6;">
      {brand} {brand_sub} Module · {hours} · {phone} · {email}<br>
      Always include your inquiry reference when contacting us.<br><br>
      This is an automated message from {brand} — please do not reply directly to this email.
    </td>
  </tr></table>
</td></tr>
</table>
</td></tr>
</table>""".format(brand=BRAND_NAME, brand_sub=BRAND_SUB, hours=SUPPORT_HOURS, phone=SUPPORT_PHONE, email=SUPPORT_EMAIL)


def _btn(label: str, href: str) -> str:
    return f"""<table role="presentation" cellpadding="0" cellspacing="0"><tr>
    <td style="background:#2563eb;border-radius:8px;">
      <a href="{href}" style="display:inline-block;padding:12px 26px;font-family:Arial,sans-serif;font-size:13.5px;font-weight:bold;color:#ffffff;text-decoration:none;">{label}</a>
    </td>
  </tr></table>"""


def _info_row(label: str, value: str) -> str:
    return f"""<tr>
    <td style="padding:6px 0;font-family:Arial,sans-serif;font-size:12.5px;color:#64748b;">{label}</td>
    <td style="padding:6px 0;font-family:Arial,sans-serif;font-size:12.5px;color:#0f172a;font-weight:bold;text-align:right;">{value}</td>
  </tr>"""


def _document(body: str) -> str:
    return _WRAP_OPEN + body + _WRAP_CLOSE


# ---------------------------------------------------------------------------
# 1. Inquiry received
# ---------------------------------------------------------------------------
def inquiry_received(name: str, reference: str, status_url: str) -> dict:
    body = f"""
<tr><td class="em-pad" style="padding:36px 32px 8px;">
  <p style="font-family:Arial,sans-serif;font-size:15px;color:#0f172a;margin:0 0 14px;">Hi {name},</p>
  <p style="font-family:Arial,sans-serif;font-size:13.5px;color:#334155;line-height:1.7;margin:0 0 20px;">
    Thanks for reaching out! We've received your catering inquiry <b>{reference}</b> and our team is
    already reviewing the details. We'll follow up shortly with your quotation.
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" class="em-btn" style="margin-bottom:14px;"><tr><td>
    {_btn('Track Your Inquiry', status_url)}
  </td></tr></table>
  <p style="font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;line-height:1.6;margin:0 0 24px;">
    Bookmark this link — it's the only way to check your quotation, payment, and booking status. No password required.
  </p>
</td></tr>"""
    return {"subject": f"We've received your catering inquiry — {reference}", "html": _document(body)}


# ---------------------------------------------------------------------------
# 2. OTP verification (admin step-up + customer billing)
# ---------------------------------------------------------------------------
def otp_verification(code: str, reference: str | None = None, expires_minutes: int = 10) -> dict:
    ref_line = f" for inquiry <b>{reference}</b>" if reference else ""
    body = f"""
<tr><td class="em-pad" style="padding:36px 32px 8px;text-align:center;">
  <table role="presentation" width="56" cellpadding="0" cellspacing="0" style="margin:0 auto 18px;"><tr>
    <td style="width:56px;height:56px;background:#dbeafe;border-radius:50%;text-align:center;vertical-align:middle;font-family:Arial,sans-serif;font-size:24px;">&#128274;</td>
  </tr></table>
  <p style="font-family:Arial,sans-serif;font-size:15px;color:#0f172a;font-weight:bold;margin:0 0 8px;">Verify it's you</p>
  <p style="font-family:Arial,sans-serif;font-size:13px;color:#64748b;line-height:1.6;margin:0 0 22px;max-width:380px;display:inline-block;">
    Use this code to view billing and payment details{ref_line}.
  </p>
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 20px;"><tr>
    <td style="background:#f1f5f9;border:1px solid #e2e8f0;border-radius:10px;padding:16px 30px;">
      <span class="em-code" style="font-family:Arial,sans-serif;font-size:30px;font-weight:bold;letter-spacing:.35em;color:#0f172a;">{code}</span>
    </td>
  </tr></table>
  <p style="font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;margin:0 0 24px;">This code expires in {expires_minutes} minutes.</p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fef3c7;border-radius:8px;margin-bottom:8px;"><tr>
    <td style="padding:12px 18px;font-family:Arial,sans-serif;font-size:11.5px;color:#92400e;text-align:left;">
      If you didn't request this code, you can safely ignore this email — no changes were made to your account or inquiry.
    </td>
  </tr></table>
</td></tr>"""
    return {"subject": f"Your verification code: {code}", "html": _document(body)}


# ---------------------------------------------------------------------------
# 3. Quotation ready
# ---------------------------------------------------------------------------
def quotation_ready(
    name: str,
    reference: str,
    line_items: Iterable[tuple[str, str]],
    total: str,
    valid_until: str,
    accept_url: str,
) -> dict:
    rows = "".join(_info_row(label, value) for label, value in line_items)
    body = f"""
<tr><td class="em-pad" style="padding:36px 32px 8px;">
  <p style="font-family:Arial,sans-serif;font-size:15px;color:#0f172a;margin:0 0 14px;">Hi {name},</p>
  <p style="font-family:Arial,sans-serif;font-size:13.5px;color:#334155;line-height:1.7;margin:0 0 20px;">
    Your official quotation for <b>{reference}</b> is ready for review. Take a look at the breakdown below
    and let us know if you'd like to accept it or request any changes.
  </p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;margin-bottom:22px;">
    <tr><td style="padding:18px 22px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        {rows}
      </table>
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-top:1px solid #e2e8f0;margin-top:10px;padding-top:10px;">
        <tr>
          <td style="padding-top:10px;font-family:Arial,sans-serif;font-size:14px;font-weight:bold;color:#0f172a;">Total Quotation</td>
          <td style="padding-top:10px;font-family:Arial,sans-serif;font-size:16px;font-weight:bold;color:#0f172a;text-align:right;">{total}</td>
        </tr>
      </table>
    </td></tr>
  </table>
  <table role="presentation" cellpadding="0" cellspacing="0" class="em-btn" style="margin-bottom:14px;"><tr><td>
    {_btn('View & Accept Quotation', accept_url)}
  </td></tr></table>
  <p style="font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;line-height:1.6;margin:0 0 24px;">
    This quotation is valid until {valid_until}. Submitting an inquiry does not automatically confirm a booking —
    your booking is confirmed only once this quotation is accepted and the required deposit is received.
  </p>
</td></tr>"""
    return {"subject": f"Your catering quotation is ready — {reference}", "html": _document(body)}


# ---------------------------------------------------------------------------
# 4. Booking confirmed
# ---------------------------------------------------------------------------
def booking_confirmed(
    name: str,
    reference: str,
    event_date: str,
    venue: str,
    coordinator: str,
    coordinator_contact: str,
    details_url: str,
) -> dict:
    body = f"""
<tr><td class="em-pad" style="padding:36px 32px 8px;text-align:center;">
  <table role="presentation" width="56" cellpadding="0" cellspacing="0" style="margin:0 auto 16px;"><tr>
    <td style="width:56px;height:56px;background:#dbeafe;border-radius:50%;text-align:center;vertical-align:middle;">
      <span style="font-family:Arial,sans-serif;font-size:26px;font-weight:bold;color:#2563eb;line-height:56px;">&#10003;</span>
    </td>
  </tr></table>
  <p style="font-family:Arial,sans-serif;font-size:17px;color:#0f172a;font-weight:bold;margin:0 0 8px;">You're all set, {name}!</p>
  <p style="font-family:Arial,sans-serif;font-size:13px;color:#64748b;line-height:1.7;margin:0 0 24px;max-width:420px;display:inline-block;">
    Your booking for <b>{reference}</b> is fully confirmed. Feel free to visit the venue ahead of time, and reach out
    to your coordinator for any final details.
  </p>
</td></tr>
<tr><td class="em-pad" style="padding:0 32px 8px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;margin-bottom:22px;">
    <tr><td style="padding:18px 22px;">
      <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
        {_info_row('Event Date', event_date)}
        {_info_row('Venue', venue)}
        {_info_row('Event Coordinator', coordinator)}
        {_info_row('Coordinator Contact', coordinator_contact)}
      </table>
    </td></tr>
  </table>
  <table role="presentation" cellpadding="0" cellspacing="0" class="em-btn" style="margin-bottom:22px;"><tr><td>
    {_btn('View Full Booking Details', details_url)}
  </td></tr></table>
</td></tr>"""
    return {"subject": f"You're all set! Booking confirmed — {reference}", "html": _document(body)}


# ---------------------------------------------------------------------------
# 5. Cancellation
# ---------------------------------------------------------------------------
def cancellation(name: str, reference: str, status_url: str, support_email: str = SUPPORT_EMAIL) -> dict:
    body = f"""
<tr><td class="em-pad" style="padding:36px 32px 8px;">
  <p style="font-family:Arial,sans-serif;font-size:15px;color:#0f172a;margin:0 0 14px;">Hi {name},</p>
  <p style="font-family:Arial,sans-serif;font-size:13.5px;color:#334155;line-height:1.7;margin:0 0 20px;">
    We've received your cancellation request for inquiry <b>{reference}</b>. Since a payment has already been
    recorded on this booking, our staff will personally review your request before it's finalized.
  </p>
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fef3c7;border-radius:8px;margin-bottom:22px;"><tr>
    <td style="padding:14px 18px;font-family:Arial,sans-serif;font-size:12px;color:#92400e;">
      Cancellation Request Submitted — our staff will contact you regarding this request and any applicable refund,
      per our Cancellation &amp; Refund Policy.
    </td>
  </tr></table>
  <table role="presentation" cellpadding="0" cellspacing="0" class="em-btn" style="margin-bottom:14px;"><tr><td>
    {_btn('View Inquiry Status', status_url)}
  </td></tr></table>
  <p style="font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;line-height:1.6;margin:0 0 24px;">
    Questions in the meantime? Reach us at {support_email} and mention your reference above.
  </p>
</td></tr>"""
    return {"subject": f"Cancellation request received — {reference}", "html": _document(body)}


# ---------------------------------------------------------------------------
# 6. Resend status link (customer lost the original email)
# ---------------------------------------------------------------------------
def resend_link(items: list[dict]) -> dict:
    """Re-send private tracking links for inquiries tied to one email address.

    ``items`` is a list of {"reference": str, "event_date": str, "status_url": str}
    — at most a handful, already capped by the caller.
    """
    blocks = ""
    for it in items:
        blocks += f"""
<tr><td class="em-pad" style="padding:0 32px 22px;">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;">
    <tr><td style="padding:14px 18px;font-family:Arial,sans-serif;font-size:12.5px;color:#334155;">
      Inquiry <b class="em-ref">{it['reference']}</b>{' &middot; Event ' + it['event_date'] if it.get('event_date') else ''}
    </td></tr>
    <tr><td style="padding:0 18px 14px;">{_btn('Open Status Page', it['status_url'])}</td></tr>
  </table>
</td></tr>"""
    body = f"""
<tr><td class="em-pad" style="padding:36px 32px 20px;">
  <p style="font-family:Arial,sans-serif;font-size:13.5px;color:#334155;line-height:1.7;margin:0 0 20px;">
    You asked us to re-send the private tracking link{'s' if len(items) != 1 else ''} for your catering
    inquir{'ies' if len(items) != 1 else 'y'}. Here {'they are' if len(items) != 1 else 'it is'} — use the
    button{'s' if len(items) != 1 else ''} below to check your status at any time. No password required.
  </p>
</td></tr>""" + blocks + """
<tr><td class="em-pad" style="padding:0 32px 24px;">
  <p style="font-family:Arial,sans-serif;font-size:12px;color:#94a3b8;line-height:1.6;margin:0;">
    Didn't request this? You can safely ignore this email — your links only work for whoever has access to this inbox.
  </p>
</td></tr>"""
    return {"subject": "Your catering inquiry link — ARGO Catering", "html": _document(body)}
