from app.core.errors import upstream_error


def test_upstream_error_does_not_leak_exception_text():
    secret_detail = "Bearer sk-live-abc123 rejected: internal-host.local timed out"
    exc = Exception(secret_detail)

    http_exc = upstream_error(exc, context="Script generation")

    assert http_exc.status_code == 502
    assert secret_detail not in http_exc.detail
    assert "Script generation" in http_exc.detail
