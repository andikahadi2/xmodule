import hashlib
import hmac
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse, Response

from app.core.config import settings

SESSION_COOKIE = "session"
SESSION_MAX_AGE_SECONDS = 7 * 24 * 60 * 60
PUBLIC_PATHS = {"/login"}


def _secret() -> str:
    return settings.admin_password


def _sign(expiry: str) -> str:
    return hmac.new(_secret().encode(), expiry.encode(), hashlib.sha256).hexdigest()


def make_session_cookie() -> str:
    expiry = str(int(time.time()) + SESSION_MAX_AGE_SECONDS)
    return f"{expiry}:{_sign(expiry)}"


def verify_session_cookie(value: str | None) -> bool:
    if not value or ":" not in value:
        return False
    expiry, _, signature = value.partition(":")
    if not hmac.compare_digest(signature, _sign(expiry)):
        return False
    try:
        return int(expiry) > time.time()
    except ValueError:
        return False


def verify_credentials(username: str, password: str) -> bool:
    return hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
        password, settings.admin_password
    )


class SessionAuthMiddleware(BaseHTTPMiddleware):
    """Gate the entire app behind a login form + signed session cookie.

    Disabled automatically when ADMIN_USERNAME/ADMIN_PASSWORD are unset, so local
    dev without a configured password keeps working exactly as before.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.admin_username or not settings.admin_password:
            return await call_next(request)

        if request.url.path in PUBLIC_PATHS or request.url.path.startswith("/login"):
            return await call_next(request)

        if verify_session_cookie(request.cookies.get(SESSION_COOKIE)):
            return await call_next(request)

        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Session expired, please log in again"}, status_code=401)

        next_url = request.url.path + (f"?{request.url.query}" if request.url.query else "")
        return RedirectResponse(url=f"/login?next={next_url}", status_code=303)
