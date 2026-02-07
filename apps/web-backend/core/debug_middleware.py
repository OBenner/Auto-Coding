"""
Debug middleware to log all requests
"""

import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class DebugMiddleware(BaseHTTPMiddleware):
    """Debug middleware to log all incoming requests"""

    async def dispatch(self, request, call_next):
        """Log request details"""
        logger.info(f"[DEBUG] Incoming request:")
        logger.info(f"  Type: {request.scope.get('type')}")
        logger.info(f"  Method: {request.scope.get('method')}")
        logger.info(f"  Path: {request.url.path}")
        logger.info(f"  Headers: {dict(request.headers)}")

        response = await call_next(request)

        logger.info(f"[DEBUG] Response status: {response.status_code}")

        return response
