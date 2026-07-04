"""
Web Backend - FastAPI Application
Main entry point for the FastAPI web service
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Application configuration
HOST = os.getenv("HOST", "")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
_cors_env = os.getenv("CORS_ORIGINS", "")
CORS_ORIGINS = [o.strip() for o in _cors_env.split(",") if o.strip()]
SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_urlsafe(32)
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
WS_HEARTBEAT_INTERVAL = int(os.getenv("WS_HEARTBEAT_INTERVAL", "30"))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler for startup and shutdown events
    """
    # Startup
    logger.info("Starting Web Backend API")
    logger.info(f"Server will run on {HOST}:{PORT}")
    logger.info(f"Debug mode: {DEBUG}")
    logger.info(f"CORS origins: {CORS_ORIGINS}")

    # Validate required configuration
    if not SECRET_KEY:
        logger.warning(
            "⚠️  SECRET_KEY not configured! Using auto-generated key - DO NOT use in production!"
        )

    yield

    # Shutdown
    logger.info("Shutting down Web Backend API")


# Create FastAPI application
app = FastAPI(
    title="Web Backend API",
    description="FastAPI backend service for Auto Code web interface",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS - use explicit origins list, fall back to localhost for dev
cors_origins = (
    CORS_ORIGINS if CORS_ORIGINS else ["http://localhost:3000", "http://localhost:5173"]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "X-Requested-With"],
)

# Configure session middleware for OAuth state management
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Configure usage tracking middleware
from core.middleware import UsageTrackingMiddleware

app.add_middleware(
    UsageTrackingMiddleware,
    rate_limit_enabled=False,  # Disable rate limiting by default (can be enabled in production)
    rate_limit_requests=1000,
    rate_limit_period="hourly",
)

# Import and register API routes
from api.routes import (
    agents,
    auth,
    executions,
    files,
    git,
    specs,
    tasks,
    terminals,
    usage,
    users,
    workspaces,
)
from api.websocket import router as websocket_router

app.include_router(agents.router)
app.include_router(auth.router)
app.include_router(executions.router)
app.include_router(files.router)
app.include_router(git.router)
app.include_router(specs.router)
app.include_router(tasks.router)
app.include_router(terminals.router)
app.include_router(usage.router)
app.include_router(users.router)
app.include_router(workspaces.router)
app.include_router(websocket_router)

# Only expose test routes in debug/development mode
if DEBUG:
    try:
        from api import test_routes

        app.include_router(test_routes.router)
        logger.info("Test routes enabled (DEBUG mode)")
    except ImportError:
        logger.debug("Test routes module not available")


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Web Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {"status": "healthy", "service": "web-backend"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app", host=HOST, port=PORT, reload=DEBUG, log_level=LOG_LEVEL.lower()
    )
