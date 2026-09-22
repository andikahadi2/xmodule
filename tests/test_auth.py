from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core import auth as auth_module
from app.core.auth import SESSION_COOKIE, SessionAuthMiddleware, make_session_cookie


async def _ok(request):
    return PlainTextResponse("ok")


def _build_app() -> Starlette:
    app = Starlette(routes=[Route("/", _ok), Route("/login", _ok), Route("/api/thing", _ok)])
    app.add_middleware(SessionAuthMiddleware)
    return app


def test_no_auth_configured_allows_through(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "")
    monkeypatch.setattr(auth_module.settings, "admin_password", "")
    client = TestClient(_build_app())

    resp = client.get("/")

    assert resp.status_code == 200


def test_missing_session_redirects_to_login(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app(), follow_redirects=False)

    resp = client.get("/")

    assert resp.status_code == 303
    assert resp.headers["location"].startswith("/login")


def test_invalid_session_cookie_rejected(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app(), follow_redirects=False, cookies={SESSION_COOKIE: "garbage"})

    resp = client.get("/")

    assert resp.status_code == 303


def test_valid_session_cookie_allowed(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    cookie = make_session_cookie()
    client = TestClient(_build_app(), cookies={SESSION_COOKIE: cookie})

    resp = client.get("/")

    assert resp.status_code == 200
    assert resp.text == "ok"


def test_session_cookie_signed_with_different_secret_rejected(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    cookie = make_session_cookie()
    monkeypatch.setattr(auth_module.settings, "admin_password", "different-secret")
    client = TestClient(_build_app(), follow_redirects=False, cookies={SESSION_COOKIE: cookie})

    resp = client.get("/")

    assert resp.status_code == 303


def test_login_path_always_reachable(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app())

    resp = client.get("/login")

    assert resp.status_code == 200


def test_api_path_without_session_returns_401_json_not_redirect(monkeypatch):
    """A fetch() call must be able to detect an expired session: if this
    returned a 303 redirect instead, fetch() would silently follow it and
    treat the resulting 200 (the login page's HTML) as success."""
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app(), follow_redirects=False)

    resp = client.get("/api/thing")

    assert resp.status_code == 401
    assert resp.json() == {"detail": "Session expired, please log in again"}


def test_api_path_with_valid_session_allowed(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    cookie = make_session_cookie()
    client = TestClient(_build_app(), cookies={SESSION_COOKIE: cookie})

    resp = client.get("/api/thing")

    assert resp.status_code == 200
