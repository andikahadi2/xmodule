from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from app.core.auth import SESSION_COOKIE, SESSION_MAX_AGE_SECONDS, make_session_cookie, verify_credentials
from app.core.config import settings

router = APIRouter(tags=["auth"])
templates = Jinja2Templates(directory="app/templates")


def _safe_next(next_url: str | None) -> str:
    if next_url and next_url.startswith("/") and not next_url.startswith("//"):
        return next_url
    return "/"


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, next: str | None = None, error: str | None = None):
    if not settings.admin_username or not settings.admin_password:
        return RedirectResponse(url=_safe_next(next), status_code=303)
    return templates.TemplateResponse(
        request, "login.html", {"next": _safe_next(next), "error": error}
    )


@router.post("/login", response_class=HTMLResponse)
def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form("/"),
):
    if not verify_credentials(username, password):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"next": _safe_next(next), "error": "Username atau password salah."},
            status_code=401,
        )

    response = RedirectResponse(url=_safe_next(next), status_code=303)
    response.set_cookie(
        SESSION_COOKIE,
        make_session_cookie(),
        max_age=SESSION_MAX_AGE_SECONDS,
        httponly=True,
        samesite="lax",
    )
    return response


@router.post("/logout")
def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response
