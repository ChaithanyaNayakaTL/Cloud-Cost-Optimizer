"""
firebase_auth.py
----------------
Firebase JWT verification middleware implemented as a FastAPI dependency.

Design decisions:
- Firebase Admin SDK is initialized once at module load (singleton).
- `verify_token()` is a FastAPI dependency injected into all protected routes.
- On failure, raises structured HTTPException(401) — never leaks internal errors.
- The decoded token UID is returned to the route handler; no session is created.
"""
from __future__ import annotations

import json
import logging

import firebase_admin
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials

from app.config import get_settings

logger = logging.getLogger(__name__)

# ─── Firebase Admin Singleton ─────────────────────────────────────────────────

_firebase_app: firebase_admin.App | None = None


def _get_firebase_app() -> firebase_admin.App:
    """Lazily initialise the Firebase Admin SDK exactly once per process."""
    global _firebase_app
    if _firebase_app is None:
        settings = get_settings()
        cred_dict = settings.firebase_service_account_dict
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase Admin SDK initialised.")
    return _firebase_app


# ─── Bearer Token Extractor ───────────────────────────────────────────────────

_bearer_scheme = HTTPBearer(auto_error=False)


# ─── Public Dependency ────────────────────────────────────────────────────────

async def verify_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
) -> str:
    """
    FastAPI dependency that validates a Firebase JWT.

    Returns the authenticated user's UID on success.
    Raises HTTP 401 on missing, invalid, or expired tokens.
    """
    _get_firebase_app()  # ensure SDK is initialised

    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error": {
                    "code": "MISSING_TOKEN",
                    "message": "Authorization header with Bearer token is required.",
                },
            },
        )

    token = credentials.credentials
    try:
        decoded = firebase_auth.verify_id_token(token)
        uid: str = decoded["uid"]
        logger.debug("Token verified for uid=%s", uid)
        return uid
    except firebase_auth.ExpiredIdTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error": {
                    "code": "TOKEN_EXPIRED",
                    "message": "The provided token has expired. Please re-authenticate.",
                },
            },
        )
    except (firebase_auth.InvalidIdTokenError, Exception) as exc:
        logger.warning("Token verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "status": "error",
                "error": {
                    "code": "INVALID_TOKEN",
                    "message": "Token is invalid or could not be verified.",
                },
            },
        )
