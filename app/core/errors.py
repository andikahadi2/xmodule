import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def upstream_error(exc: Exception, *, context: str) -> HTTPException:
    """Build a 502 for an external-provider failure without leaking upstream
    response bodies/internal details to the client. Full exception text is
    logged server-side for debugging."""
    logger.error("%s failed: %s", context, exc)
    return HTTPException(status_code=502, detail=f"{context} failed; please try again later")
