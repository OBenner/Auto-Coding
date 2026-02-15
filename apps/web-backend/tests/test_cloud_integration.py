"""
Integration tests for cloud-hosted Auto Code

Tests the integration of:
- Database models and ORM
- User authentication and registration
- OAuth configuration
- Usage tracking service
- Git service integration
- API endpoints with database

Unlike E2E tests which test the full deployed stack, integration tests
focus on testing how components work together in isolation with mock
dependencies where appropriate.

NOTE: Some tests require bcrypt backend to be properly configured.
If bcrypt tests fail, ensure bcrypt is installed: pip install bcrypt
"""

from datetime import UTC, datetime

import pytest
from api.models.repository import GitRepository

# Import application components
from api.models.user import User
from services.usage_tracker import UsageTracker


# Helper function to check if bcrypt is working
def check_bcrypt_available():
    """Check if bcrypt backend is available and working."""
    try:
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        # Try a simple hash to see if it works
        pwd_context.hash("test")
        return True
    except Exception:
        return False


bcrypt_available = check_bcrypt_available()


# ============================================================================
# Database Model Integration Tests
# ============================================================================


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_model_creation(test_db):
    """Test creating a user in the database."""
    user = User(email="test@example.com", hashed_password="hashed_password_here")
    user.set_password("testpass123")

    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.is_verified is False
    assert user.verify_password("testpass123")
    assert not user.verify_password("wrongpassword")


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_password_hashing(test_db):
    """Test password hashing and verification."""
    user = User(email="hash@test.com")

    # Set password
    user.set_password("mysecretpassword")

    # Verify password is hashed (not plain text)
    assert user.hashed_password != "mysecretpassword"

    # Verify password verification works
    assert user.verify_password("mysecretpassword")
    assert not user.verify_password("wrongpassword")


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_repository_relationship(test_db):
    """Test the relationship between User and GitRepository models."""
    # Create user
    user = User(email="repo@test.com")
    user.set_password("testpass123")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    # Create repository linked to user
    repo = GitRepository(
        user_id=user.id,
        provider="github",
        repository_url="https://github.com/test/repo",
        repository_name="repo",
        repository_owner="test",
        access_token="fake_token_123",
    )
    test_db.add(repo)
    test_db.commit()
    test_db.refresh(repo)

    # Test relationship
    assert len(user.repositories) == 1
    assert user.repositories[0].repository_name == "repo"
    assert user.repositories[0].provider == "github"


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_cascade_delete_repositories(test_db):
    """Test that deleting a user cascades to repositories."""
    # Create user with repository
    user = User(email="cascade@test.com")
    user.set_password("testpass123")
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)

    repo = GitRepository(
        user_id=user.id,
        provider="gitlab",
        repository_url="https://gitlab.com/test/project",
        repository_name="project",
        repository_owner="test",
        access_token="fake_token_456",
    )
    test_db.add(repo)
    test_db.commit()

    user_id = user.id

    # Delete user
    test_db.delete(user)
    test_db.commit()

    # Verify repositories are also deleted
    repos = test_db.query(GitRepository).filter_by(user_id=user_id).all()
    assert len(repos) == 0


# ============================================================================
# Usage Tracking Service Integration Tests
# ============================================================================


def test_usage_tracker_initialization(test_redis):
    """Test UsageTracker initialization with Redis."""
    tracker = UsageTracker(redis_client=test_redis)
    assert tracker.redis is not None
    assert tracker.health_check()


def test_usage_tracker_record_request(test_redis):
    """Test recording API requests."""
    tracker = UsageTracker(redis_client=test_redis)

    # Record a request
    tracker.record_request(
        user_id=1, endpoint="/api/users/register", method="POST", status_code=201
    )

    # Verify usage was recorded
    usage = tracker.get_user_usage(user_id=1, period="daily", days_back=1)
    assert len(usage) > 0

    # Verify the request is in today's stats
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    assert any(stat["period"] == today for stat in usage)


def test_usage_tracker_rate_limiting(test_redis):
    """Test rate limiting functionality."""
    tracker = UsageTracker(redis_client=test_redis)

    user_id = 1
    limit = 5

    # Make requests up to the limit
    for i in range(limit):
        # Record request to increment count
        tracker.record_request(user_id, "/api/test", "GET", 200)

        # Check rate limit
        allowed, current_count = tracker.check_rate_limit(
            user_id=user_id, limit=limit, period="hourly"
        )

        # First 4 requests should be allowed, 5th should hit limit
        if i < limit - 1:
            assert allowed is True
        else:
            assert allowed is False
        assert current_count == i + 1

    # Next check should still be denied
    allowed, current_count = tracker.check_rate_limit(
        user_id=user_id, limit=limit, period="hourly"
    )
    assert allowed is False
    assert current_count == limit


def test_usage_tracker_endpoint_stats(test_redis):
    """Test tracking endpoint-specific statistics."""
    tracker = UsageTracker(redis_client=test_redis)

    user_id = 1

    # Record multiple requests to different endpoints
    tracker.record_request(user_id, "/api/users/register", "POST", 201)
    tracker.record_request(user_id, "/api/users/login", "POST", 200)
    tracker.record_request(user_id, "/api/users/register", "POST", 201)

    # Get endpoint stats for register endpoint
    register_stats = tracker.get_endpoint_stats(
        user_id=user_id, endpoint="/api/users/register", period="daily"
    )

    # Verify stats were recorded
    assert register_stats["endpoint"] == "/api/users/register"
    assert register_stats["total_requests"] == 2
    assert "POST" in register_stats["methods"]
    assert register_stats["methods"]["POST"] == 2

    # Get endpoint stats for login endpoint
    login_stats = tracker.get_endpoint_stats(
        user_id=user_id, endpoint="/api/users/login", period="daily"
    )

    assert login_stats["endpoint"] == "/api/users/login"
    assert login_stats["total_requests"] == 1


def test_usage_tracker_multiple_periods(test_redis):
    """Test usage tracking across different time periods."""
    tracker = UsageTracker(redis_client=test_redis)

    user_id = 1

    # Record requests
    for i in range(10):
        tracker.record_request(user_id, "/api/test", "GET", 200)

    # Get hourly usage
    hourly = tracker.get_user_usage(user_id, period="hourly", days_back=1)
    assert len(hourly) > 0

    # Get daily usage
    daily = tracker.get_user_usage(user_id, period="daily", days_back=1)
    assert len(daily) > 0

    # Get monthly usage
    monthly = tracker.get_user_usage(user_id, period="monthly", days_back=30)
    assert len(monthly) > 0


# ============================================================================
# API Endpoint Integration Tests
# ============================================================================


def test_health_endpoint(test_client):
    """Test the health check endpoint."""
    response = test_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_registration_endpoint(test_client):
    """Test user registration via API."""
    response = test_client.post(
        "/api/users/register",
        json={"email": "newuser@example.com", "password": "securepass123"},
    )

    assert response.status_code == 201
    data = response.json()

    # Verify response structure
    assert "access_token" in data
    assert "user" in data
    assert data["user"]["email"] == "newuser@example.com"
    assert data["user"]["is_active"] is True


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_registration_duplicate_email(test_client, test_db):
    """Test that duplicate email registration fails."""
    # Create first user
    user = User(email="duplicate@test.com")
    user.set_password("pass123")
    test_db.add(user)
    test_db.commit()

    # Try to register with same email
    response = test_client.post(
        "/api/users/register",
        json={"email": "duplicate@test.com", "password": "anotherpass123"},
    )

    assert response.status_code == 400
    assert "already" in response.json()["detail"].lower()


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_login_endpoint(test_client, test_db):
    """Test user login via API."""
    # Create user first
    user = User(email="login@test.com")
    user.set_password("mypassword")
    test_db.add(user)
    test_db.commit()

    # Login
    response = test_client.post(
        "/api/users/login", json={"email": "login@test.com", "password": "mypassword"}
    )

    assert response.status_code == 200
    data = response.json()

    assert "access_token" in data
    assert data["user"]["email"] == "login@test.com"


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_login_wrong_password(test_client, test_db):
    """Test login with incorrect password."""
    # Create user
    user = User(email="wrongpass@test.com")
    user.set_password("correctpass")
    test_db.add(user)
    test_db.commit()

    # Try login with wrong password
    response = test_client.post(
        "/api/users/login",
        json={"email": "wrongpass@test.com", "password": "wrongpass"},
    )

    assert response.status_code == 401


@pytest.mark.skipif(not bcrypt_available, reason="bcrypt backend not available")
def test_user_login_nonexistent_user(test_client):
    """Test login with non-existent user."""
    response = test_client.post(
        "/api/users/login",
        json={"email": "nonexistent@test.com", "password": "anypass"},
    )

    assert response.status_code == 401


def test_oauth_status_endpoint(test_client):
    """Test OAuth provider status endpoint."""
    response = test_client.get("/api/git/status")
    assert response.status_code == 200
    data = response.json()

    # Should be a dictionary with provider statuses
    assert isinstance(data, dict)


def test_oauth_github_authorize_redirect(test_client):
    """Test GitHub OAuth authorize endpoint redirects or returns 503 if not configured."""
    response = test_client.get("/api/git/github/authorize", follow_redirects=False)

    # Should redirect to GitHub OAuth (302) or return 503 if not configured
    assert response.status_code in (302, 503)
    if response.status_code == 302:
        assert "location" in response.headers


def test_usage_dashboard_endpoint(test_client):
    """Test usage dashboard endpoint."""
    response = test_client.get("/api/usage/dashboard")

    # Should return 200 even if Redis unavailable (fail-open design)
    assert response.status_code == 200
    data = response.json()

    # Verify response is a dictionary (structure may vary based on Redis availability)
    assert isinstance(data, dict)


def test_usage_stats_endpoint(test_client):
    """Test usage statistics endpoint."""
    response = test_client.get("/api/usage/stats?period=daily&days_back=7")

    # Should return 200 even if Redis unavailable
    assert response.status_code == 200
    data = response.json()

    # Verify response is a dictionary
    assert isinstance(data, dict)


def test_usage_health_endpoint(test_client):
    """Test usage service health endpoint."""
    response = test_client.get("/api/usage/health")

    assert response.status_code == 200
    data = response.json()

    # Should have status field
    assert "status" in data
    # Should have redis connection info (field name may vary)
    assert "redis" in data or "redis_healthy" in data


# ============================================================================
# Integration Test Summary
# ============================================================================


def test_integration_summary():
    """
    Integration test coverage summary.

    This test always passes and serves as documentation of what is tested.
    """
    coverage = {
        "database_models": [
            "User creation and password hashing",
            "User-Repository relationship",
            "Cascade delete functionality",
        ],
        "services": [
            "UsageTracker initialization",
            "Request recording",
            "Rate limiting",
            "Endpoint statistics",
            "Multiple time periods",
        ],
        "api_endpoints": [
            "Health check",
            "User registration (success and duplicate)",
            "User login (success, wrong password, non-existent)",
            "OAuth status and authorize",
            "Usage dashboard and statistics",
        ],
    }

    print("\n" + "=" * 70)
    print("INTEGRATION TEST COVERAGE SUMMARY")
    print("=" * 70)

    for category, tests in coverage.items():
        print(f"\n{category.upper().replace('_', ' ')}:")
        for test in tests:
            print(f"  ✓ {test}")

    print("\n" + "=" * 70)

    assert True  # Always pass - this is just documentation
