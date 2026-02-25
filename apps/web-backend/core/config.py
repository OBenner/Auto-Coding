"""
Configuration management for Auto Code Web Backend

Loads settings from environment variables and provides centralized configuration.
"""

import os
from functools import lru_cache
from pathlib import Path

# Try to load .env file if dotenv is available
try:
    from dotenv import load_dotenv

    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except ImportError:
    # dotenv not installed, will use environment variables directly
    pass


class Settings:
    """Application settings loaded from environment variables"""

    def __init__(self):
        # Server configuration
        self.HOST: str = os.getenv("HOST", "127.0.0.1")
        self.PORT: int = int(os.getenv("PORT", "8000"))
        self.DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"

        # CORS configuration
        cors_origins = os.getenv("CORS_ORIGINS", "")
        self.CORS_ORIGINS: list[str] = [
            origin.strip() for origin in cors_origins.split(",")
        ]

        # Authentication
        self.SECRET_KEY: str = os.getenv(
            "SECRET_KEY", "dev-secret-key-change-in-production"
        )
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(
            os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")
        )

        # Auto Code backend integration
        self.AUTO_CLAUDE_BACKEND_DIR: str = os.getenv(
            "AUTO_CLAUDE_BACKEND_DIR",
            os.path.abspath(
                os.path.join(os.path.dirname(__file__), "..", "..", "backend")
            ),
        )
        self.PYTHON_BACKEND_URL: str = os.getenv(
            "PYTHON_BACKEND_URL", "http://127.0.0.1:8000"
        )

        # WebSocket configuration
        self.WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

        # Database configuration
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "")

        # Database connection pool settings
        self.DB_POOL_SIZE: int = int(os.getenv("DB_POOL_SIZE", "10"))
        self.DB_MAX_OVERFLOW: int = int(os.getenv("DB_MAX_OVERFLOW", "20"))
        self.DB_POOL_TIMEOUT: int = int(os.getenv("DB_POOL_TIMEOUT", "30"))
        self.DB_POOL_RECYCLE: int = int(os.getenv("DB_POOL_RECYCLE", "3600"))
        self.DB_ECHO: bool = os.getenv("DB_ECHO", "false").lower() == "true"

        # OAuth configuration - GitHub
        self.GITHUB_CLIENT_ID: str = os.getenv("GITHUB_CLIENT_ID", "")
        self.GITHUB_CLIENT_SECRET: str = os.getenv("GITHUB_CLIENT_SECRET", "")

        # OAuth configuration - GitLab
        self.GITLAB_CLIENT_ID: str = os.getenv("GITLAB_CLIENT_ID", "")
        self.GITLAB_CLIENT_SECRET: str = os.getenv("GITLAB_CLIENT_SECRET", "")

        # OAuth redirect URI
        self.OAUTH_REDIRECT_URI: str = os.getenv(
            "OAUTH_REDIRECT_URI", "http://localhost:8000/api/git/callback"
        )

        # Redis configuration for usage tracking
        self.REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
        self.REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
        self.REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))
        self.REDIS_PASSWORD: str = os.getenv("REDIS_PASSWORD", "")

        # Validate critical settings
        self._validate()

    def _validate(self):
        """Validate critical configuration"""
        if not self.DEBUG and self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a secure value in production. "
                "Set DEBUG=false only when SECRET_KEY is properly configured."
            )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
