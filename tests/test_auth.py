import base64

import pytest
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.core import auth as auth_module
from app.core.auth import BasicAuthMiddleware


def _basic_header(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


async def _ok(request):
    return PlainTextResponse("ok")


def _build_app() -> Starlette:
    app = Starlette(routes=[Route("/", _ok)])
    app.add_middleware(BasicAuthMiddleware)
    return app


def test_no_auth_configured_allows_through(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "")
    monkeypatch.setattr(auth_module.settings, "admin_password", "")
    client = TestClient(_build_app())

    resp = client.get("/")

    assert resp.status_code == 200


def test_missing_credentials_rejected(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app())

    resp = client.get("/")

    assert resp.status_code == 401
    assert resp.headers["WWW-Authenticate"].startswith("Basic")


def test_wrong_credentials_rejected(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app())

    resp = client.get("/", headers=_basic_header("admin", "wrong"))

    assert resp.status_code == 401


def test_correct_credentials_allowed(monkeypatch):
    monkeypatch.setattr(auth_module.settings, "admin_username", "admin")
    monkeypatch.setattr(auth_module.settings, "admin_password", "secret")
    client = TestClient(_build_app())

    resp = client.get("/", headers=_basic_header("admin", "secret"))

    assert resp.status_code == 200
    assert resp.text == "ok"
