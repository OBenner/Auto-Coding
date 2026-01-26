"""
Auto Claude Web Backend - FastAPI Server

This is the main entry point for the Auto Claude web backend API server.
It exposes Auto Claude functionality via REST API and WebSocket connections.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from core.config import settings
from api.routes import auth, specs, tasks
from api import websocket

# Create FastAPI application
app = FastAPI(
    title="Auto Claude Web API",
    description="REST API and WebSocket server for Auto Claude web interface",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(auth.router)
app.include_router(specs.router)
app.include_router(tasks.router)

# Include WebSocket router
app.include_router(websocket.router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "service": "auto-claude-web-api",
        "version": "1.0.0"
    }


@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "service": "auto-claude-web-api",
        "version": "1.0.0",
        "debug_mode": settings.DEBUG
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
