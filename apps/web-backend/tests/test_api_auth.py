"""
Integration tests for Auth API endpoints

Tests all /api/auth endpoints including token verification, authentication
validation, error handling, and response formats.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_verify_token_without_auth(async_client: AsyncClient):
    """Test that verify_token requires authentication"""
    response = await async_client.post("/api/auth/verify")
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_verify_token_with_invalid_token(async_client: AsyncClient):
    """Test that verify_token rejects invalid tokens"""
    headers = {"Authorization": "Bearer invalid-token-12345"}
    response = await async_client.post("/api/auth/verify", headers=headers)
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_verify_token_with_expired_token(
    async_client: AsyncClient, expired_token: str
):
    """Test that verify_token rejects expired tokens"""
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await async_client.post("/api/auth/verify", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_verify_token_success(async_client: AsyncClient, auth_headers: dict):
    """Test successful token verification with valid authentication"""
    response = await async_client.post("/api/auth/verify", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["valid"] is True
    assert data["message"] == "Token is valid"
    assert "claims" in data
    assert isinstance(data["claims"], dict)

    # Verify token claims structure
    claims = data["claims"]
    assert "sub" in claims
    assert claims["sub"] == "test-user"
    assert "email" in claims
    assert claims["email"] == "test@example.com"
    assert "name" in claims
    assert claims["name"] == "Test User"
    assert "exp" in claims  # Expiration timestamp


@pytest.mark.asyncio
async def test_verify_token_missing_bearer_prefix(
    async_client: AsyncClient, auth_token: str
):
    """Test that verify_token rejects tokens without Bearer prefix"""
    headers = {"Authorization": auth_token}  # Missing "Bearer " prefix
    response = await async_client.post("/api/auth/verify", headers=headers)
    # Security layer returns 401 for all authentication failures
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_verify_token_empty_authorization_header(async_client: AsyncClient):
    """Test that verify_token rejects empty Authorization header"""
    headers = {"Authorization": ""}
    response = await async_client.post("/api/auth/verify", headers=headers)
    # Security layer returns 401 for all authentication failures
    assert response.status_code == 401


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "malformed_token",
    [
        pytest.param("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9", id="one-part-jwt"),
        pytest.param(
            "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0In0",
            id="two-part-jwt",
        ),
        pytest.param("Bearer not.a.jwt.at.all", id="invalid-base64"),
    ],
)
async def test_verify_token_malformed_jwt(
    async_client: AsyncClient, malformed_token: str
):
    """Test that verify_token rejects malformed JWT tokens"""
    headers = {"Authorization": malformed_token}
    response = await async_client.post("/api/auth/verify", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_auth_status_no_auth_required(async_client: AsyncClient):
    """Test that auth_status endpoint works without authentication"""
    response = await async_client.get("/api/auth/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["auth_enabled"] is True
    assert data["message"] == "Authentication system is operational"


@pytest.mark.asyncio
async def test_auth_status_with_auth(async_client: AsyncClient, auth_headers: dict):
    """Test that auth_status works with authentication too"""
    response = await async_client.get("/api/auth/status", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["auth_enabled"] is True


@pytest.mark.asyncio
async def test_verify_token_response_model(
    async_client: AsyncClient, auth_headers: dict
):
    """Test that verify_token returns correct response model structure"""
    response = await async_client.post("/api/auth/verify", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()

    # Verify required TokenResponse model fields are present with correct types
    for key in ("valid", "message", "claims"):
        assert key in data
    assert isinstance(data["valid"], bool)
    assert isinstance(data["message"], str)
    assert isinstance(data["claims"], dict)


@pytest.mark.asyncio
async def test_verify_token_with_multiple_requests(
    async_client: AsyncClient, auth_headers: dict
):
    """Test that the same token can be verified multiple times"""
    # Make multiple requests with the same token
    for _ in range(3):
        response = await async_client.post("/api/auth/verify", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True


@pytest.mark.asyncio
async def test_verify_token_case_insensitive_bearer(
    async_client: AsyncClient, auth_token: str
):
    """Test that Bearer scheme is case-insensitive per RFC 7235 (lowercase 'bearer')"""
    # FastAPI's HTTPBearer accepts 'bearer' and 'Bearer' interchangeably
    headers = {"Authorization": f"bearer {auth_token}"}  # lowercase 'bearer'
    response = await async_client.post("/api/auth/verify", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is True


@pytest.mark.asyncio
async def test_auth_status_response_structure(async_client: AsyncClient):
    """Test that auth_status returns the expected response structure"""
    response = await async_client.get("/api/auth/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["auth_enabled"] is True
    assert isinstance(data["message"], str)


@pytest.mark.asyncio
async def test_verify_token_with_tampered_token(
    async_client: AsyncClient, auth_token: str
):
    """Test that verify_token rejects tokens with tampered payload"""
    # Tamper with the token by changing one character
    tampered_token = auth_token[:-5] + "XXXXX"
    headers = {"Authorization": f"Bearer {tampered_token}"}
    response = await async_client.post("/api/auth/verify", headers=headers)
    assert response.status_code == 401
