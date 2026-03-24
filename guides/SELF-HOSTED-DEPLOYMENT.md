# Self-Hosted Docker Deployment

## Overview

Deploy Auto Code's web interface (frontend + backend + PostgreSQL + Redis) using Docker Compose. This provides a self-hosted alternative to the Electron desktop app.

## Prerequisites

- Docker 20.10+
- Docker Compose v2 (included with Docker Desktop)

## Quick Start

```bash
# Create .env file with required secrets
cat > .env << 'EOF'
POSTGRES_PASSWORD=your-secure-password-here
SECRET_KEY=your-secret-key-here
REDIS_PASSWORD=your-redis-password-here
EOF

# Start all services
docker compose up -d

# Verify health
docker compose ps
```

The web frontend is available at `http://localhost:3000`.

## Architecture

```text
┌─────────────┐     ┌──────────────┐     ┌────────────┐
│ Web Frontend │────▶│  Web Backend  │────▶│ PostgreSQL │
│ (nginx:80)   │     │ (uvicorn:8000)│     │  (:5432)   │
└─────────────┘     └──────┬───────┘     └────────────┘
                           │
                    ┌──────▼───────┐
                    │    Redis     │
                    │   (:6379)    │
                    └──────────────┘
```

| Service | Image | Purpose |
|---------|-------|---------|
| `postgres` | postgres:16-alpine | User data, repositories |
| `redis` | redis:7-alpine | Usage tracking, caching |
| `web-backend` | Built from `apps/web-backend/` | REST API + WebSocket server |
| `web-frontend` | Built from `apps/web-frontend/` | Vite/React SPA served via nginx |

## Configuration

### Required Environment Variables

| Variable | Description |
|----------|-------------|
| `POSTGRES_PASSWORD` | PostgreSQL password (required, no default) |
| `SECRET_KEY` | JWT signing key for auth (required, no default) |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_PASSWORD` | `redis` | Redis authentication password |
| `POSTGRES_USER` | `postgres` | PostgreSQL username |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | JWT token expiry |
| `GITHUB_CLIENT_ID` | — | GitHub OAuth app client ID |
| `GITHUB_CLIENT_SECRET` | — | GitHub OAuth app secret |
| `VITE_API_URL` | `http://localhost:8000` | Backend URL for frontend |
| `VITE_WS_URL` | `ws://localhost:8000` | WebSocket URL for frontend |

## Security Notes

- PostgreSQL and Redis are **not exposed** to the host — only accessible within the Docker network
- All secrets must be provided via environment variables (no insecure defaults)
- The web-backend healthcheck uses Python stdlib (`urllib`) — no extra dependencies
- The frontend runs as a non-root nginx user
- The backend uses `condition: service_healthy` (Docker Compose v2) to wait for dependencies

## Services

### Frontend (nginx)

- Serves the built Vite/React SPA
- Proxies `/api/` requests to the backend
- Proxies `/ws` WebSocket connections to the backend
- Gzip compression enabled
- Security headers (X-Frame-Options, X-Content-Type-Options, CSP)
- Static asset caching (1 year for immutable assets)

### Backend (uvicorn)

- FastAPI application
- Connects to PostgreSQL for persistent storage
- Connects to Redis for caching and usage tracking
- OAuth integration for GitHub/GitLab

## Commands

```bash
# Start services
docker compose up -d

# View logs
docker compose logs -f web-backend

# Rebuild after code changes
docker compose up -d --build

# Stop services
docker compose down

# Stop and remove volumes (destructive)
docker compose down -v
```
