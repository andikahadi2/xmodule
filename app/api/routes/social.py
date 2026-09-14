import secrets
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.providers.social.base import SocialMediaProviderError
from app.schemas.social_account import SocialAccountOut
from app.services import social_service

router = APIRouter(prefix="/api/social", tags=["social"])
templates = Jinja2Templates(directory="app/templates")

SUPPORTED_PLATFORMS = {"tiktok"}

# ponytail: in-memory state store is fine for a single-process dev server;
# move to a persisted/shared store if this ever runs behind multiple workers.
_pending_states: dict[str, str] = {}


def _redirect_uri(platform: str) -> str:
    return f"{settings.app_base_url}/api/social/{platform}/callback"


def _affiliate_redirect(**params: str) -> RedirectResponse:
    return RedirectResponse(f"/affiliate?{urlencode(params)}")


@router.get("/accounts", response_model=list[SocialAccountOut])
def list_accounts(db: Session = Depends(get_db)):
    return social_service.list_accounts(db)


@router.get("/accounts/render", response_class=HTMLResponse)
def render_accounts(request: Request, db: Session = Depends(get_db)):
    accounts = social_service.list_accounts(db)
    return templates.TemplateResponse(request, "_social_accounts.html", {"accounts": accounts})


@router.delete("/accounts/{account_id}", response_class=HTMLResponse)
def disconnect_account(account_id: int, db: Session = Depends(get_db)):
    account = social_service.get_account(db, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Account not found")
    social_service.disconnect_account(db, account)
    return HTMLResponse("")


@router.get("/{platform}/connect")
def connect(platform: str):
    if platform not in SUPPORTED_PLATFORMS:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    state = secrets.token_urlsafe(24)
    _pending_states[state] = platform

    try:
        url = social_service.get_authorize_url(platform, state, _redirect_uri(platform))
    except SocialMediaProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return RedirectResponse(url)


@router.get("/{platform}/callback")
def callback(
    platform: str,
    code: str | None = Query(default=None),
    state: str | None = Query(default=None),
    error: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    if error:
        return _affiliate_redirect(connect_error=error)

    if not code or not state or _pending_states.pop(state, None) != platform:
        return _affiliate_redirect(connect_error="invalid_state")

    try:
        social_service.connect_account(db, platform, code, _redirect_uri(platform))
    except SocialMediaProviderError as exc:
        return _affiliate_redirect(connect_error=str(exc))

    return _affiliate_redirect(connected="1")
