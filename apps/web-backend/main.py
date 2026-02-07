"""
Web Backend - FastAPI Application
Main entry point for the FastAPI web service
"""

import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Application configuration
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
SECRET_KEY = os.getenv("SECRET_KEY")
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
    if not SECRET_KEY or SECRET_KEY == "your-secret-key-here-change-in-production":
        logger.warning("⚠️  SECRET_KEY not configured! Using default - DO NOT use in production!")

    yield

    # Shutdown
    logger.info("Shutting down Web Backend API")


# Create FastAPI application
app = FastAPI(
    title="Web Backend API",
    description="FastAPI backend service for Auto Code web interface",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan
)

# Configure CORS
# WebSocket connections need special CORS handling
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for WebSocket
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)


# Import and register API routes
from api.routes import users, auth, git, usage
from api import websocket

app.include_router(users.router)
app.include_router(auth.router)
app.include_router(git.router)
app.include_router(usage.router)
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Root endpoint - API information"""
    return {
        "name": "Web Backend API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "web-backend",
        "debug": DEBUG
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=DEBUG,
        log_level=LOG_LEVEL.lower()
    )
