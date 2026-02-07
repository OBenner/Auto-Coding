"""
Pytest configuration for integration tests

Handles fixtures and test configuration for cloud integration tests.
"""

import pytest
import fakeredis
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from unittest.mock import patch

# Import application components
from core.database import Base, get_db

# Import all models so Base.metadata knows about all tables
from api.models.user import User  # noqa: F401
from api.models.repository import GitRepository  # noqa: F401


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
    from main import app

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    # Mock Redis connections in the app
    with patch('services.usage_tracker.redis.Redis') as mock_redis_class:
        # Make Redis() return our fake Redis
        mock_redis_class.return_value = test_redis

        app.dependency_overrides[get_db] = override_get_db

        client = TestClient(app)

        yield client

        # Cleanup
        app.dependency_overrides.clear()


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
