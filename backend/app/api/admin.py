"""
Admin utilities — data management and diagnostics.
"""
from fastapi import APIRouter
from app.db.client import get_db

router = APIRouter(prefix="/admin", tags=["admin"])


@router.delete("/clear-demo-data")
async def clear_demo_data():
    """Wipe all briefings, notifications, and outcomes so the demo starts clean."""
    db = get_db()
    b = await db.briefings.delete_many({})
    n = await db.notifications.delete_many({})
    o = await db.outcomes.delete_many({})
    return {
        "status": "cleared",
        "briefings_deleted": b.deleted_count,
        "notifications_deleted": n.deleted_count,
        "outcomes_deleted": o.deleted_count,
    }


@router.post("/test-email")
async def test_email(body: dict):
    """
    Send a test email to verify the email provider is configured correctly.
    POST { "to": "you@example.com" }
    """
    to = body.get("to", "").strip()
    if not to or "@" not in to:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Provide a valid 'to' email address")
    from app.services.notification_service import send_test_email
    return await send_test_email(to)


@router.get("/email-config")
async def email_config():
    """Check which email provider is configured (without exposing credentials)."""
    from app.config import settings
    resend = bool(getattr(settings, "resend_api_key", ""))
    smtp = bool(getattr(settings, "smtp_host", ""))
    return {
        "resend_configured": resend,
        "smtp_configured": smtp,
        "any_provider": resend or smtp,
        "instructions": (
            "Set RESEND_API_KEY in backend/.env to enable email. "
            "Free account at https://resend.com — takes 2 minutes."
        ) if not (resend or smtp) else "Email provider is active.",
    }
