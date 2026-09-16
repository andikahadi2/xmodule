import base64
import hmac

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings


class BasicAuthMiddleware(BaseHTTPMiddleware):
    """Gate the entire app behind a single shared username/password.

    Disabled automatically when ADMIN_USERNAME/ADMIN_PASSWORD are unset, so local
    dev without a configured password keeps working exactly as before.
    """

    async def dispatch(self, request: Request, call_next):
        if not settings.admin_username or not settings.admin_password:
            return await call_next(request)

        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Basic "):
            try:
                decoded = base64.b64decode(auth_header[len("Basic ") :]).decode("utf-8")
                username, _, password = decoded.partition(":")
            except (ValueError, UnicodeDecodeError):
                username, password = "", ""

            if hmac.compare_digest(username, settings.admin_username) and hmac.compare_digest(
                password, settings.admin_password
            ):
                return await call_next(request)

        return Response(
            status_code=401,
            headers={"WWW-Authenticate": 'Basic realm="Content Engine"'},
        )
