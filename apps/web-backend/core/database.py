"""
Database configuration and connection manager for Auto Claude Web Backend

Provides SQLAlchemy engine, session management, and database dependency injection.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from typing import Generator

from .config import settings


# Create SQLAlchemy engine
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=10,        # Maximum number of connections in the pool
    max_overflow=20      # Maximum overflow connections
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# Base class for ORM models
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Database dependency for FastAPI

    Yields a database session and ensures proper cleanup.

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """
    Initialize database by creating all tables

    This should be called on application startup if not using migrations.
    """
    Base.metadata.create_all(bind=engine)


def close_db():
    """
    Clean up database connections

    This should be called on application shutdown.
    """
    engine.dispose()
