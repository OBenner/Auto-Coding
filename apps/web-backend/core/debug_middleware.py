"""
Debug middleware to log requests (development only).

WARNING: Only register this middleware when DEBUG=true.
"""

import logging
import os

from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger(__name__)

# Headers that must never be logged
_SENSITIVE_HEADERS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "proxy-authorization",
        "x-api-key",
    }
)


class DebugMiddleware(BaseHTTPMiddleware):
    """Debug middleware to log incoming requests (development only)."""

    async def dispatch(self, request, call_next):
        """Log request details with sensitive headers redacted."""
        if not os.getenv("DEBUG", "false").lower() == "true":
            return await call_next(request)

        safe_headers = {
            k: ("[REDACTED]" if k.lower() in _SENSITIVE_HEADERS else v)
            for k, v in request.headers.items()
        }

        logger.debug(
            "Incoming %s %s headers=%s",
            request.scope.get("method"),
            request.url.path,
            safe_headers,
        )

        try:
            response = await call_next(request)
        except Exception:
            logger.debug("Request to %s raised an exception", request.url.path)
            raise

        logger.debug(
            "Response %s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
        )

        return response
