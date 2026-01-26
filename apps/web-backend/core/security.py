"""
Security and authentication utilities for Auto Claude Web Backend

Provides JWT token validation, authentication middleware, and FastAPI dependencies
for securing API endpoints.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from core.config import settings

logger = logging.getLogger(__name__)

# HTTP Bearer token scheme for FastAPI
security = HTTPBearer()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Dictionary of claims to encode in the token
        expires_delta: Optional custom expiration time

    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


def verify_token(token: str) -> dict:
    """
    Verify and decode JWT token.

    Args:
        token: JWT token string to verify

    Returns:
        Dictionary of decoded token claims

    Raises:
        HTTPException: If token is invalid or expired
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError as e:
        logger.warning("JWT validation failed: %s", str(e))
        raise credentials_exception


async def get_current_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    FastAPI dependency to get and validate the current authentication token.

    This dependency extracts the Bearer token from the Authorization header,
    validates it, and returns the decoded claims.

    Args:
        credentials: HTTP Bearer credentials from Authorization header

    Returns:
        Dictionary of decoded token claims

    Raises:
        HTTPException: If token is missing, invalid, or expired

    Example:
        @app.get("/protected")
        async def protected_route(token: dict = Depends(get_current_token)):
            return {"user": token.get("sub")}
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return verify_token(credentials.credentials)


async def require_auth(token: dict = Depends(get_current_token)) -> dict:
    """
    FastAPI dependency to require authentication on routes.

    This is an alias for get_current_token with a more semantic name.
    Use this dependency on routes that require authentication.

    Args:
        token: Token claims from get_current_token dependency

    Returns:
        Dictionary of decoded token claims

    Example:
        @app.post("/api/protected")
        async def protected_route(auth: dict = Depends(require_auth)):
            return {"authenticated": True}
    """
    return token
