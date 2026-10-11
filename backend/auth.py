import logging
import threading
from typing import Any

from fastapi import Depends, Header, HTTPException

from .config import settings

logger = logging.getLogger(__name__)
_firebase_app: Any = None
_firebase_app_lock = threading.Lock()


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app
    with _firebase_app_lock:
        if _firebase_app is None:
            import firebase_admin
            from firebase_admin import credentials

            try:
                _firebase_app = firebase_admin.get_app()
            except ValueError:
                _firebase_app = firebase_admin.initialize_app(
                    credentials.ApplicationDefault(),
                    {"projectId": settings.GOOGLE_CLOUD_PROJECT},
                )
    return _firebase_app


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, str]:
    if settings.ENVIRONMENT.casefold() == "development":
        return {"email": "local-development", "uid": "local-development"}

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sign in is required.")

    allowed_emails = {
        email.strip().casefold()
        for email in settings.ALLOWED_USER_EMAILS.split(",")
        if email.strip()
    }
    if not allowed_emails:
        raise HTTPException(status_code=503, detail="No application users are configured.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="Sign in is required.")

    import firebase_admin
    from firebase_admin import auth

    try:
        claims = auth.verify_id_token(token, app=_get_firebase_app())
    except (
        auth.ExpiredIdTokenError,
        auth.InvalidIdTokenError,
        auth.RevokedIdTokenError,
        auth.UserDisabledError,
    ) as error:
        raise HTTPException(status_code=401, detail="Your sign-in token is invalid or expired.") from error
    except firebase_admin.exceptions.FirebaseError as error:
        logger.exception("Firebase ID token verification failed.")
        raise HTTPException(status_code=503, detail="The sign-in service is temporarily unavailable.") from error

    email = claims.get("email")
    if not isinstance(email, str) or not claims.get("email_verified", False):
        raise HTTPException(status_code=403, detail="A verified Google account is required.")
    if email.casefold() not in allowed_emails:
        raise HTTPException(status_code=403, detail="This Google account is not authorized for this application.")

    return {"email": email, "uid": str(claims["uid"])}


def get_restaurant_id(user: dict[str, str] = Depends(get_current_user)) -> str:
    if not settings.DEFAULT_RESTAURANT_ID.strip():
        raise HTTPException(status_code=503, detail="No restaurant workspace is configured.")
    return settings.DEFAULT_RESTAURANT_ID
