"""
Guardian notification service.

Creates in-app notifications + sends real HTML emails via:
  1. Resend API  (RESEND_API_KEY — recommended, one env var)
  2. SMTP        (SMTP_HOST + credentials — fallback)

Falls back silently if neither is configured.
"""
from __future__ import annotations

import logging
from datetime import datetime
from email.utils import parseaddr

from app.db.repositories.notifications import create_notification

logger = logging.getLogger(__name__)


# ── Formatting helpers ────────────────────────────────────────────────────────

def _fmt_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%b %d, %Y")
    except Exception:
        return iso[:10]


def _risk_color(tier: str) -> tuple[str, str, str]:
    """Returns (label, hex_color, bg_hex) for the risk tier."""
    if tier in ("critical", "CRITICAL"):
        return "CRITICAL RISK", "#ef4444", "#1a0000"
    if tier in ("high", "HIGH"):
        return "HIGH RISK", "#f97316", "#1a0900"
    if tier in ("elevated", "ELEVATED"):
        return "ELEVATED", "#f59e0b", "#1a1000"
    return "COMPLIANT", "#22c55e", "#001a06"


# ── HTML email template ───────────────────────────────────────────────────────

def _html_guardian_activated(
    address: str,
    developer_name: str,
    pct: int,
    risk_tier: str,
    tree_count: int,
    ecosystem_usd_yr: float,
    day90: str,
    m12: str,
    m36: str,
    y5: str,
) -> str:
    tier_label, tier_color, tier_bg = _risk_color(risk_tier)
    timeline_rows = "\n".join([
        _tl_row("Day 1",    "Today",   "Day 1 intervention filed to public record",   True,  tier_color),
        _tl_row("Day 90",   day90,     "Permit status check — confirm removal or approval", False, "#555"),
        _tl_row("Month 12", m12,       "Planting promise audit — NYC Parks ForMS cross-check", False, "#555"),
        _tl_row("Month 36", m36,       "Survival verification — inspect replacement trees",   False, "#555"),
        _tl_row("Year 5",   y5,        "Case closure — final compliance on permanent ledger",  False, "#555"),
    ])

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#111;border:1px solid #222;border-radius:6px;overflow:hidden">

<!-- Logo bar -->
<tr><td style="padding:24px 32px;border-bottom:1px solid #1e1e1e">
  <span style="font-size:18px;font-weight:800;letter-spacing:0.1em;color:#fff;font-family:'Courier New',monospace">ROOT</span>
  <span style="font-size:10px;color:#555;margin-left:10px;letter-spacing:0.12em;text-transform:uppercase">Urban Tree Intelligence</span>
</td></tr>

<!-- Badge + title -->
<tr><td style="padding:28px 32px 0">
  <div style="display:inline-block;background:#16a34a;color:#fff;font-size:9px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;padding:4px 10px;border-radius:2px;margin-bottom:14px">
    ● Guardian Activated
  </div>
  <h1 style="color:#fff;font-size:20px;font-weight:700;margin:0;line-height:1.4">{address}</h1>
  <p style="color:#777;font-size:12px;margin:6px 0 0;font-family:'Courier New',monospace">Day 1 intervention filed · 5-year guardian watch begins</p>
</td></tr>

<!-- Developer risk card -->
<tr><td style="padding:20px 32px">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:{tier_bg};border-left:3px solid {tier_color};padding:16px;border-radius:0 4px 4px 0">
  <tr><td>
    <span style="font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.12em;color:{tier_color}">{tier_label}</span>
    <p style="color:#fff;font-size:15px;font-weight:700;margin:8px 0 4px">{developer_name}</p>
    <p style="color:#999;font-size:12px;margin:0">{pct}% replacement survival &nbsp;·&nbsp; 85% city target &nbsp;·&nbsp; {tree_count} trees at risk &nbsp;·&nbsp; ${ecosystem_usd_yr:,.0f}/yr ecosystem value</p>
  </td></tr>
  </table>
</td></tr>

<!-- Guardian timeline -->
<tr><td style="padding:0 32px 28px">
  <p style="color:#555;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.14em;margin:0 0 18px">Guardian Schedule</p>
  <table width="100%" cellpadding="0" cellspacing="0">
  {timeline_rows}
  </table>
</td></tr>

<!-- Footer -->
<tr><td style="padding:20px 32px;border-top:1px solid #1a1a1a;background:#0d0d0d">
  <p style="color:#555;font-size:11px;margin:0;line-height:1.7">
    ROOT monitors this tree automatically at each checkpoint. The developer's compliance
    record updates regardless of permit outcome — permanently attached to future applications.
  </p>
  <p style="color:#333;font-size:10px;margin:14px 0 0;font-family:'Courier New',monospace">
    — ROOT Guardian System &nbsp;·&nbsp; Urban Tree Intelligence
  </p>
</td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def _html_guardian_check(
    address: str,
    step_label: str,
    audit_report: str,
    next_label: str | None,
    next_date: str | None,
) -> str:
    next_block = ""
    if next_label and next_date:
        next_block = f"""
<tr><td style="padding:0 32px 24px">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#161616;border:1px solid #222;padding:16px;border-radius:4px">
  <tr><td>
    <span style="color:#555;font-size:9px;font-weight:800;text-transform:uppercase;letter-spacing:0.12em">Next Check</span>
    <p style="color:#fff;font-size:13px;font-weight:600;margin:8px 0 0">{next_label} &mdash; {next_date}</p>
  </td></tr>
  </table>
</td></tr>"""

    # Convert audit report newlines to HTML
    report_html = audit_report.replace("\n\n", "<br><br>").replace("\n", " ")

    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#0a0a0a;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0a0a0a;padding:40px 20px">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#111;border:1px solid #222;border-radius:6px;overflow:hidden">

<!-- Logo bar -->
<tr><td style="padding:24px 32px;border-bottom:1px solid #1e1e1e">
  <span style="font-size:18px;font-weight:800;letter-spacing:0.1em;color:#fff;font-family:'Courier New',monospace">ROOT</span>
  <span style="font-size:10px;color:#555;margin-left:10px;letter-spacing:0.12em;text-transform:uppercase">Guardian Audit</span>
</td></tr>

<!-- Badge + title -->
<tr><td style="padding:28px 32px 0">
  <div style="display:inline-block;background:#f59e0b;color:#000;font-size:9px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;padding:4px 10px;border-radius:2px;margin-bottom:14px">
    ⚡ {step_label}
  </div>
  <h1 style="color:#fff;font-size:20px;font-weight:700;margin:0;line-height:1.4">{address}</h1>
</td></tr>

<!-- Audit report -->
<tr><td style="padding:20px 32px">
  <p style="color:#ccc;font-size:13px;line-height:1.8;margin:0">{report_html}</p>
</td></tr>

{next_block}

<!-- Footer -->
<tr><td style="padding:20px 32px;border-top:1px solid #1a1a1a;background:#0d0d0d">
  <p style="color:#333;font-size:10px;margin:0;font-family:'Courier New',monospace">
    — ROOT Guardian System &nbsp;·&nbsp; Urban Tree Intelligence
  </p>
</td></tr>

</table>
</td></tr>
</table>
</body></html>"""


def _tl_row(when: str, date: str, desc: str, active: bool, color: str) -> str:
    dot_style = f"background:{color};border-radius:50%;width:10px;height:10px;display:inline-block;margin-right:12px;flex-shrink:0;margin-top:3px"
    text_color = "#fff" if active else "#888"
    return f"""<tr>
  <td style="padding:0 0 16px;vertical-align:top">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:top;padding-top:3px"><div style="{dot_style}"></div></td>
      <td>
        <span style="color:{color};font-size:10px;font-weight:800;text-transform:uppercase;letter-spacing:0.1em;font-family:'Courier New',monospace">{when}</span>
        &nbsp;
        <span style="color:#444;font-size:10px;font-family:'Courier New',monospace">{date}</span>
        <p style="color:{text_color};font-size:12px;margin:3px 0 0;line-height:1.5">{desc}</p>
      </td>
    </tr></table>
  </td>
</tr>"""


# ── Public API ────────────────────────────────────────────────────────────────

async def notify_guardian_activated(
    briefing_id: str,
    permit_id: str,
    address: str,
    developer_name: str,
    compliance_rate: float,
    risk_tier: str,
    tree_count: int,
    ecosystem_usd_yr: float,
    guardian_schedule: dict[str, str],
    recipient_email: str | None = None,
    send_email: bool = True,
) -> str:
    subject, body_text, body_html = build_guardian_activated_message(
        address=address,
        developer_name=developer_name,
        compliance_rate=compliance_rate,
        risk_tier=risk_tier,
        tree_count=tree_count,
        ecosystem_usd_yr=ecosystem_usd_yr,
        guardian_schedule=guardian_schedule,
    )

    notification_id = await create_notification({
        "type": "guardian_activated",
        "briefing_id": briefing_id,
        "permit_id": permit_id,
        "address": address,
        "subject": subject,
        "body": body_text,
        "tags": [risk_tier, "activated"],
        "guardian_schedule": guardian_schedule,
        "recipient_email": recipient_email or "",
    })

    if send_email and recipient_email:
        await _send_email(subject, body_text, body_html, recipient_email)
    return notification_id


def build_guardian_activated_message(
    address: str,
    developer_name: str,
    compliance_rate: float,
    risk_tier: str,
    tree_count: int,
    ecosystem_usd_yr: float,
    guardian_schedule: dict[str, str],
) -> tuple[str, str, str]:
    pct = round(compliance_rate * 100)
    day90 = _fmt_date(guardian_schedule.get("day90", ""))
    m12 = _fmt_date(guardian_schedule.get("month12", ""))
    m36 = _fmt_date(guardian_schedule.get("month36", ""))
    y5 = _fmt_date(guardian_schedule.get("year5", ""))

    subject = f"[ROOT] Guardian activated — {address}"
    body_text = (
        f"ROOT Guardian activated for {address}.\n\n"
        f"Developer: {developer_name} | {pct}% survival | {risk_tier.upper()} risk\n"
        f"Day 90: {day90} · Month 12: {m12} · Month 36: {m36} · Year 5: {y5}\n\n"
        "ROOT will email you at each checkpoint.\n— ROOT Guardian System"
    )
    body_html = _html_guardian_activated(
        address, developer_name, pct, risk_tier, tree_count, ecosystem_usd_yr,
        day90, m12, m36, y5,
    )
    return subject, body_text, body_html


async def notify_guardian_check(
    briefing_id: str,
    permit_id: str,
    address: str,
    step: str,
    audit_report: str,
    next_check: str | None = None,
    next_check_date: str | None = None,
) -> str:
    step_labels = {
        "day90": "Day 90 Check",
        "month12": "Month 12 Audit",
        "month36": "Month 36 Survival Check",
        "year5": "Year 5 Case Closure",
    }
    label = step_labels.get(step, step.replace("_", " ").title())
    next_label = step_labels.get(next_check, "") if next_check else None
    next_date = _fmt_date(next_check_date) if next_check_date else None

    subject = f"[ROOT] {label} — {address}"
    body_text = f"ROOT {label} for {address}\n\n{audit_report}\n\n— ROOT Guardian System"
    body_html = _html_guardian_check(address, label, audit_report, next_label, next_date)

    from app.db.repositories.briefings import get_briefing_by_id
    from app.config import settings
    from app.db.client import get_db
    from bson import ObjectId

    briefing_doc = await get_briefing_by_id(briefing_id)
    stored_email = briefing_doc.get("submitted_by_email", "") if briefing_doc else ""
    recipients: list[str] = []
    if briefing_doc:
        for email in [stored_email, *(briefing_doc.get("guardian_emails") or []), settings.notification_email]:
            email = str(email or "").strip()
            if email and email.lower() not in {recipient.lower() for recipient in recipients}:
                recipients.append(email)

    notification_id = await create_notification({
        "type": f"guardian_{step}",
        "briefing_id": briefing_id,
        "permit_id": permit_id,
        "address": address,
        "subject": subject,
        "body": body_text,
        "tags": [step, "audit"],
        "step": step,
        "recipient_email": stored_email,
        "recipient_emails": recipients,
    })

    sent_recipients: list[str] = []
    failed_recipients: list[str] = []
    for recipient in recipients:
        try:
            if await _send_email(subject, body_text, body_html, recipient):
                sent_recipients.append(recipient)
            else:
                failed_recipients.append(recipient)
        except Exception as exc:
            failed_recipients.append(recipient)
            logger.error("Guardian check email failed for %s: %s", recipient, exc, exc_info=True)

    if recipients:
        try:
            db = get_db()
            await db.notifications.update_one(
                {"_id": ObjectId(notification_id)},
                {"$set": {
                    "email_sent": bool(sent_recipients),
                    "email_recipients": sent_recipients,
                    "email_failed_recipients": failed_recipients,
                    "email_error": "delivery_failed" if failed_recipients else "",
                }},
            )
        except Exception as exc:
            logger.warning("Could not persist check email delivery status: %s", exc)
    return notification_id


# ── Email dispatch ────────────────────────────────────────────────────────────

async def _send_email(subject: str, text: str, html: str, to: str) -> bool:
    """Send via Gmail SMTP. Runs the blocking SMTP call in a thread pool."""
    import os, asyncio
    smtp_host = os.environ.get("SMTP_HOST", "")
    smtp_user = os.environ.get("SMTP_USER", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    logger.info("EMAIL ATTEMPT to=%s host=%s user=%s pass_set=%s", to, smtp_host or "(not set)", smtp_user or "(not set)", bool(smtp_pass))
    if not smtp_host:
        logger.error("EMAIL FAILED — SMTP_HOST not in environment. Check backend/.env or Render env vars.")
        return False
    try:
        await asyncio.to_thread(_send_via_smtp, to, subject, text, html)
        logger.info("EMAIL SENT OK to=%s subject=%s", to, subject)
        return True
    except Exception as exc:
        logger.error("EMAIL FAILED to=%s error=%s: %s", to, type(exc).__name__, exc, exc_info=True)
        return False


async def send_test_email(to: str) -> dict:
    """Send a test email and return status. Used by /admin/test-email."""
    import os
    if not os.environ.get("SMTP_HOST"):
        return {"ok": False, "provider": "none",
                "error": "SMTP_HOST not set. Add SMTP_HOST/SMTP_USER/SMTP_PASSWORD to backend/.env."}
    subject = "[ROOT] Email test — guardian system active"
    text = "ROOT Guardian email test — SMTP is working."
    html = """<!DOCTYPE html><html><body style="background:#0a0a0a;font-family:-apple-system,sans-serif;padding:40px 20px">
<div style="max-width:480px;margin:0 auto;background:#111;border:1px solid #222;border-radius:6px;padding:32px">
  <div style="font-size:18px;font-weight:800;letter-spacing:0.1em;color:#fff;font-family:'Courier New',monospace;margin-bottom:20px">ROOT</div>
  <div style="display:inline-block;background:#16a34a;color:#fff;font-size:9px;font-weight:800;letter-spacing:0.14em;text-transform:uppercase;padding:4px 10px;border-radius:2px;margin-bottom:16px">● System active</div>
  <p style="color:#ccc;font-size:13px;line-height:1.7;margin:0">Email delivery confirmed via Gmail SMTP.</p>
  <p style="color:#444;font-size:10px;margin:20px 0 0;font-family:'Courier New',monospace">— ROOT Guardian System</p>
</div></body></html>"""
    import asyncio
    try:
        await asyncio.to_thread(_send_via_smtp, to, subject, text, html)
        return {"ok": True, "provider": "smtp", "to": to,
                "smtp_host": os.environ.get("SMTP_HOST"), "smtp_user": os.environ.get("SMTP_USER")}
    except Exception as exc:
        import traceback
        return {"ok": False, "provider": "smtp", "error": str(exc),
                "traceback": traceback.format_exc(),
                "smtp_host": os.environ.get("SMTP_HOST"), "smtp_user": os.environ.get("SMTP_USER")}


async def _send_via_resend(api_key: str, to: str, subject: str, html: str, text: str) -> None:
    import httpx
    from app.config import settings
    from_addr = "ROOT Guardian <onboarding@resend.dev>"

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={"from": from_addr, "to": [to], "subject": subject, "html": html, "text": text},
        )

        if resp.status_code == 403:
            # Resend sandbox: can only deliver to the account owner.
            # Fall back to the configured notification_email so the demo still works.
            fallback = settings.notification_email
            if not fallback:
                logger.warning(
                    "Resend sandbox rejected %s (domain not verified). "
                    "Set NOTIFICATION_EMAIL in backend/.env to receive guardian emails.", to
                )
                return
            fallback_subject = f"{subject} [→ {to}]"
            resp2 = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"from": from_addr, "to": [fallback], "subject": fallback_subject, "html": html, "text": text},
            )
            resp2.raise_for_status()
            logger.info("Email delivered via sandbox fallback to %s (intended: %s)", fallback, to)
            return

        resp.raise_for_status()


def _send_via_smtp(to: str, subject: str, text: str, html: str) -> None:
    import os, smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText

    host     = os.environ["SMTP_HOST"]
    port     = int(os.environ.get("SMTP_PORT", "587"))
    user     = os.environ.get("SMTP_USER", "")
    password = os.environ.get("SMTP_PASSWORD", "")
    from_hdr = os.environ.get("SMTP_FROM", f"ROOT Guardian <{user}>")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = from_hdr
    msg["To"]      = to
    msg.attach(MIMEText(text, "plain"))
    msg.attach(MIMEText(html, "html"))

    sender = parseaddr(from_hdr)[1] or user
    with smtplib.SMTP(host, port, timeout=15) as srv:
        srv.ehlo()
        srv.starttls()
        srv.ehlo()
        srv.login(user, password)
        srv.sendmail(sender, to, msg.as_string())
