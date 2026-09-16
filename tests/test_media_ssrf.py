import pytest

from app.services.media_service import UnsafeUrlError, _assert_safe_host


def test_rejects_non_http_scheme():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("file:///etc/passwd")


def test_rejects_ftp_scheme():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("ftp://example.com/x.jpg")


def test_rejects_loopback():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("http://127.0.0.1/secret.jpg")


def test_rejects_localhost_hostname():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("http://localhost/secret.jpg")


def test_rejects_link_local_metadata_address():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("http://169.254.169.254/latest/meta-data/")


def test_rejects_private_range():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("http://10.0.0.5/internal.jpg")


def test_rejects_url_with_no_hostname():
    with pytest.raises(UnsafeUrlError):
        _assert_safe_host("http:///no-host.jpg")


def test_allows_public_host(monkeypatch):
    import socket

    def fake_getaddrinfo(host, port):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0))]

    monkeypatch.setattr(socket, "getaddrinfo", fake_getaddrinfo)

    _assert_safe_host("https://example.com/image.jpg")
