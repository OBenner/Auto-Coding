"""
Pytest configuration and fixtures for Auto Claude Web Backend tests

This module provides reusable fixtures for testing FastAPI endpoints,
authentication, and async operations.
"""

import os
import pytest
from datetime import timedelta
from typing import AsyncGenerator, Dict
from httpx import AsyncClient, ASGITransport

# Set test environment variables before importing the app
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"
os.environ["DEBUG"] = "true"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"

from main import app
from core.security import create_access_token


@pytest.fixture
def test_app():
    """
    Fixture providing the FastAPI application instance for testing.

    Returns:
        FastAPI: The configured FastAPI application
    """
    return app


@pytest.fixture
async def async_client(test_app) -> AsyncGenerator[AsyncClient, None]:
    """
    Fixture providing an async HTTP client for testing FastAPI endpoints.

    Uses httpx.AsyncClient with ASGITransport for async FastAPI testing.
    This is the correct approach for async FastAPI tests (NOT TestClient).

    Args:
        test_app: FastAPI application fixture

    Yields:
        AsyncClient: Configured async HTTP client

    Example:
        async def test_endpoint(async_client):
            response = await async_client.get("/api/tasks")
            assert response.status_code == 200
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.fixture
def auth_token() -> str:
    """
    Fixture providing a valid JWT authentication token for testing.

    Returns:
        str: Valid JWT token string

    Example:
        async def test_protected_endpoint(async_client, auth_token):
            headers = {"Authorization": f"Bearer {auth_token}"}
            response = await async_client.get("/api/tasks", headers=headers)
            assert response.status_code == 200
    """
    token_data = {
        "sub": "test-user",
        "email": "test@example.com",
        "name": "Test User"
    }
    return create_access_token(token_data)


@pytest.fixture
def expired_token() -> str:
    """
    Fixture providing an expired JWT token for testing authentication failures.

    Returns:
        str: Expired JWT token string

    Example:
        async def test_expired_token(async_client, expired_token):
            headers = {"Authorization": f"Bearer {expired_token}"}
            response = await async_client.get("/api/tasks", headers=headers)
            assert response.status_code == 401
    """
    token_data = {
        "sub": "test-user",
        "email": "test@example.com",
        "name": "Test User"
    }
    # Create token that expires immediately
    return create_access_token(token_data, expires_delta=timedelta(seconds=-1))


@pytest.fixture
def auth_headers(auth_token) -> Dict[str, str]:
    """
    Fixture providing authentication headers with valid token.

    Args:
        auth_token: Valid JWT token fixture

    Returns:
        Dict[str, str]: Headers dictionary with Authorization header

    Example:
        async def test_with_auth(async_client, auth_headers):
            response = await async_client.get("/api/tasks", headers=auth_headers)
            assert response.status_code == 200
    """
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture(scope="session")
def anyio_backend():
    """
    Configure anyio backend for pytest-asyncio.

    Returns:
        str: Backend name ('asyncio')
    """
    return "asyncio"
