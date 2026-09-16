import io

import pytest

from app.clipper.api.routes import UploadTooLargeError, save_upload


class _FakeUploadFile:
    def __init__(self, data: bytes):
        self.file = io.BytesIO(data)


def test_save_upload_within_limit_succeeds(monkeypatch, tmp_path):
    from app.clipper.api import routes as routes_module

    monkeypatch.setattr(routes_module.settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(routes_module, "MAX_UPLOAD_BYTES", 1024)

    upload = _FakeUploadFile(b"x" * 100)
    dest = save_upload(upload, ".mp4")

    assert dest.exists()
    assert dest.read_bytes() == b"x" * 100


def test_save_upload_over_limit_raises_and_cleans_up(monkeypatch, tmp_path):
    from app.clipper.api import routes as routes_module

    monkeypatch.setattr(routes_module.settings, "storage_path", str(tmp_path))
    monkeypatch.setattr(routes_module, "MAX_UPLOAD_BYTES", 1024 * 1024)

    oversized = b"x" * (2 * 1024 * 1024)
    upload = _FakeUploadFile(oversized)

    with pytest.raises(UploadTooLargeError):
        save_upload(upload, ".mp4")

    leftover = list((tmp_path / "uploads").glob("*.mp4"))
    assert leftover == []
