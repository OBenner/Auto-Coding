"""
Database configuration and connection manager for Auto Code Web Backend

Provides SQLAlchemy engine, session management, and database dependency injection.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from .config import settings


def enable_sqlite_foreign_keys(target_engine: "Engine") -> None:
    """Turn on FK enforcement for every connection of a SQLite engine.

    SQLite ignores foreign keys (including ON DELETE CASCADE) unless
    ``PRAGMA foreign_keys=ON`` is issued per connection — without this,
    workspace deletions would leave orphaned child rows on sqlite-backed
    deployments. No-op for other dialects.
    """
    if target_engine.dialect.name != "sqlite":
        return

    @event.listens_for(target_engine, "connect")
    def _set_sqlite_fk_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

# Create SQLAlchemy engine with optimized connection pool settings
# SQLite doesn't support pool_size/max_overflow/pool_timeout/pool_recycle
_engine_kwargs: dict = {"pool_pre_ping": True}
if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite requires check_same_thread=False for use across multiple threads
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    _engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
    _engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
    _engine_kwargs["pool_timeout"] = settings.DB_POOL_TIMEOUT
    _engine_kwargs["pool_recycle"] = settings.DB_POOL_RECYCLE
    _engine_kwargs["echo"] = settings.DB_ECHO

engine = create_engine(settings.DATABASE_URL, **_engine_kwargs)
enable_sqlite_foreign_keys(engine)

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
