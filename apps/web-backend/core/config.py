"""
Configuration management for Auto Claude Web Backend

Loads settings from environment variables and provides centralized configuration.
"""

import os
from pathlib import Path
from typing import List
from functools import lru_cache

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
        cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173")
        self.CORS_ORIGINS: List[str] = [origin.strip() for origin in cors_origins.split(",")]

        # Authentication
        self.SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
        self.ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

        # Auto Claude backend integration
        self.AUTO_CLAUDE_BACKEND_DIR: str = os.getenv(
            "AUTO_CLAUDE_BACKEND_DIR",
            os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "backend"))
        )

        # WebSocket configuration
        self.WS_HEARTBEAT_INTERVAL: int = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))

        # Validate critical settings
        self._validate()

    def _validate(self):
        """Validate critical configuration"""
        if not self.DEBUG and self.SECRET_KEY == "dev-secret-key-change-in-production":
            raise ValueError(
                "SECRET_KEY must be set to a secure value in production. "
                "Set DEBUG=false only when SECRET_KEY is properly configured."
            )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Global settings instance
settings = get_settings()
