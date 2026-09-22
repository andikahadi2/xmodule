import pytest

from app.core.config import settings


@pytest.fixture(autouse=True)
def _disable_admin_auth_by_default(monkeypatch):
    """Tests that exercise app.main.app shouldn't have to know about auth —
    only tests/test_auth.py opts back in by setting these itself."""
    monkeypatch.setattr(settings, "admin_username", "")
    monkeypatch.setattr(settings, "admin_password", "")
