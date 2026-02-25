"""
Database configuration and connection manager for Auto Code Web Backend

Provides SQLAlchemy engine, session management, and database dependency injection.
"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings

# Create SQLAlchemy engine with optimized connection pool settings
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,  # Enable connection health checks
    pool_size=settings.DB_POOL_SIZE,  # Maximum number of connections in the pool
    max_overflow=settings.DB_MAX_OVERFLOW,  # Maximum overflow connections beyond pool_size
    pool_timeout=settings.DB_POOL_TIMEOUT,  # Seconds to wait before giving up on getting a connection
    pool_recycle=settings.DB_POOL_RECYCLE,  # Seconds after which a connection is automatically recycled
    echo=settings.DB_ECHO,  # Log SQL queries (useful for debugging, disable in production)
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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
