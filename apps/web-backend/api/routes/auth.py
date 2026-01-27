"""
Authentication API routes

Provides endpoints for token verification and authentication management.
"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from core.security import get_current_token, require_auth

logger = logging.getLogger(__name__)

# Create router for auth endpoints
router = APIRouter(prefix="/api/auth", tags=["authentication"])


class TokenResponse(BaseModel):
    """Response model for token verification"""

    valid: bool
    message: str
    claims: Dict = {}


@router.post("/verify", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def verify_token_endpoint(token_data: dict = Depends(require_auth)):
    """
    Verify the authentication token provided in the Authorization header.

    This endpoint validates the JWT token and returns its claims if valid.
    Returns 401 Unauthorized if the token is missing, invalid, or expired.

    Args:
        token_data: Token claims from authentication dependency

    Returns:
        TokenResponse with validation result and token claims

    Raises:
        HTTPException: 401 if token is invalid (handled by require_auth dependency)

    Example:
        ```bash
        # Valid token
        curl -X POST http://localhost:8000/api/auth/verify \
             -H "Authorization: Bearer <valid-token>"
        # Returns: {"valid": true, "message": "Token is valid", "claims": {...}}

        # Invalid/missing token
        curl -X POST http://localhost:8000/api/auth/verify
        # Returns: 401 Unauthorized
        ```
    """
    return TokenResponse(
        valid=True,
        message="Token is valid",
        claims=token_data,
    )


@router.get("/status")
async def auth_status():
    """
    Get authentication system status (no auth required).

    This endpoint provides information about the authentication system
    without requiring authentication.

    Returns:
        Dictionary with authentication system status
    """
    return {
        "status": "ok",
        "auth_enabled": True,
        "message": "Authentication system is operational",
    }
