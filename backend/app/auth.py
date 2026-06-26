from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request, Response, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .models import AuthUser, LoginRequest


COOKIE_NAME = os.environ.get("DASHBOARD_COOKIE_NAME", "scp_session")
COOKIE_SECURE = os.environ.get("DASHBOARD_COOKIE_SECURE", "false").lower() in {"1", "true", "yes"}
SESSION_TTL_SECONDS = int(os.environ.get("DASHBOARD_SESSION_TTL_SECONDS", "28800"))
ADMIN_USERNAME = os.environ.get("DASHBOARD_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("DASHBOARD_ADMIN_PASSWORD", "change-me")
SECRET_KEY = os.environ.get("DASHBOARD_SECRET_KEY", "change-me-to-at-least-32-random-characters")

serializer = URLSafeTimedSerializer(SECRET_KEY, salt="server-control-panel-session")


def authenticate(credentials: LoginRequest) -> bool:
    username_ok = hmac.compare_digest(credentials.username, ADMIN_USERNAME)
    password_ok = hmac.compare_digest(credentials.password, ADMIN_PASSWORD)
    return username_ok and password_ok


def create_session(response: Response, username: str) -> AuthUser:
    token = serializer.dumps({"username": username})
    response.set_cookie(
        COOKIE_NAME,
        token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        secure=COOKIE_SECURE,
        samesite="lax",
        path="/",
    )
    return AuthUser(username=username)


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=COOKIE_SECURE, samesite="lax")


def require_user(request: Request) -> AuthUser:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")

    try:
        payload = serializer.loads(token, max_age=SESSION_TTL_SECONDS)
    except SignatureExpired as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc

    username = str(payload.get("username", ""))
    if not hmac.compare_digest(username, ADMIN_USERNAME):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session user")
    return AuthUser(username=username)

