"""
Pytest configuration for integration tests

Handles fixtures and test configuration for cloud integration tests.
"""

import os
import secrets
from datetime import timedelta
from unittest.mock import patch

# Must set DATABASE_URL before importing any models that trigger core.database
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

import fakeredis
import pytest
from api.models.agent_execution import AgentExecution  # noqa: F401
from api.models.repository import GitRepository  # noqa: F401

# Import all models so Base.metadata knows about all tables
# These imports register models with SQLAlchemy Base.metadata
from api.models.user import User  # noqa: F401
from api.models.workspace import Workspace, WorkspaceUser  # noqa: F401

# Import application components
from core.database import Base, get_db
from core.security import create_access_token
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

__all__ = ["User", "GitRepository", "Workspace", "WorkspaceUser", "AgentExecution"]


@pytest.fixture(scope="session", autouse=True)
def _set_test_env():
    """Set test environment variables via monkeypatch-style context."""
    _originals: dict[str, str | None] = {}
    _vars = {
        "SECRET_KEY": secrets.token_hex(32),
        "DEBUG": "true",
        "ACCESS_TOKEN_EXPIRE_MINUTES": "60",
    }
    for key, val in _vars.items():
        _originals[key] = os.environ.get(key)
        os.environ.setdefault(key, val)
    yield
    for key, orig in _originals.items():
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig


# Test database configuration (in-memory SQLite)
TEST_DATABASE_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def test_db():
    """
    Create a fresh test database for each test.

    Uses in-memory SQLite for fast, isolated tests.
    StaticPool ensures all connections share the same in-memory database.
    """
    # Create test engine with StaticPool for shared in-memory DB
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create all tables
    Base.metadata.create_all(bind=engine)

    # Create session factory
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    # Create session
    session = TestingSessionLocal()

    yield session

    # Cleanup
    session.close()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_redis():
    """
    Create a fake Redis instance for testing.

    Uses fakeredis for in-memory Redis simulation.
    """
    fake_redis = fakeredis.FakeStrictRedis(decode_responses=True)
    return fake_redis


@pytest.fixture(scope="function")
def test_client(test_db, test_redis):
    """
    Create a FastAPI test client with test database and mocked dependencies.

    Overrides the database and Redis dependencies to use test instances.
    """
    # Import app here to avoid issues
    from core.security import require_auth
    from main import app

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    def override_require_auth():
        return {"sub": "test-user", "email": "test@example.com"}

    # Mock Redis connections in the app
    with patch("services.usage_tracker.redis.Redis") as mock_redis_class:
        # Make Redis() return our fake Redis
        mock_redis_class.return_value = test_redis

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[require_auth] = override_require_auth

        client = TestClient(app)

        yield client

        # Cleanup
        app.dependency_overrides.clear()


@pytest.fixture
def test_app():
    """
    Fixture providing the FastAPI application instance for testing.

    Returns:
        FastAPI: The configured FastAPI application
    """
    from main import app

    return app


@pytest.fixture
async def async_client(test_app):
    """
    Fixture providing an async HTTP client for testing FastAPI endpoints.

    Uses httpx.AsyncClient with ASGITransport for async FastAPI testing.
    """
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="https://test") as client:
        yield client


@pytest.fixture
def auth_token() -> str:
    """
    Fixture providing a valid JWT authentication token for testing.

    Returns:
        str: Valid JWT token string
    """
    token_data = {"sub": "test-user", "email": "test@example.com", "name": "Test User"}
    return create_access_token(token_data)


@pytest.fixture
def expired_token() -> str:
    """
    Fixture providing an expired JWT token for testing authentication failures.

    Returns:
        str: Expired JWT token string
    """
    token_data = {"sub": "test-user", "email": "test@example.com", "name": "Test User"}
    # Create token that expired 60 seconds ago (enough margin for slow CI)
    return create_access_token(token_data, expires_delta=timedelta(seconds=-60))


@pytest.fixture
def auth_headers(auth_token) -> dict[str, str]:
    """
    Fixture providing authentication headers with valid token.

    Args:
        auth_token: Valid JWT token fixture

    Returns:
        dict[str, str]: Headers dictionary with Authorization header
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


def pytest_configure(config):
    """
    Configure pytest with custom markers.
    """
    config.addinivalue_line(
        "markers", "bcrypt_required: tests that require bcrypt backend"
    )
    config.addinivalue_line(
        "markers", "redis_required: tests that require Redis connection"
    )
