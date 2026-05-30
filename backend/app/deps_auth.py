from fastapi import Header, HTTPException
from app.config import settings


def resolve_user_email(
    *,
    x_root_user_email: str | None = None,
    x_goog_authenticated_user_email: str | None = None,
    x_firebase_user_email: str | None = None,
    authorization: str | None = None,
    auth_mode: str | None = None,
) -> str | None:
    mode = (auth_mode or settings.auth_mode).lower()
    if mode == "iap" and x_goog_authenticated_user_email:
        return x_goog_authenticated_user_email.replace("accounts.google.com:", "").lower()
    if mode == "firebase" and x_firebase_user_email:
        return x_firebase_user_email.lower()
    if mode == "oauth" and authorization and authorization.lower().startswith("bearer "):
        # Production OAuth should validate JWTs upstream or replace this with a verifier.
        return None
    if mode == "dev_header" and x_root_user_email:
        return x_root_user_email.lower()
    return x_root_user_email.lower() if x_root_user_email else None


async def current_user_email(
    x_root_user_email: str | None = Header(default=None),
    x_goog_authenticated_user_email: str | None = Header(default=None),
    x_firebase_user_email: str | None = Header(default=None),
    authorization: str | None = Header(default=None),
) -> str:
    email = resolve_user_email(
        x_root_user_email=x_root_user_email,
        x_goog_authenticated_user_email=x_goog_authenticated_user_email,
        x_firebase_user_email=x_firebase_user_email,
        authorization=authorization,
    )
    if not email:
        raise HTTPException(status_code=401, detail="Authenticated user email required")
    return email.strip().lower()
