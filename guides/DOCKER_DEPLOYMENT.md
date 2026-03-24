# Docker Deployment Guide

Comprehensive guide for deploying Auto Code using Docker and Docker Compose.

## Overview

Auto Code provides production-ready Docker images and Docker Compose configurations for containerized deployment. This guide covers:

- **Docker Compose** - Full stack deployment with all services
- **Individual Services** - Deploy backend, web-backend, or web-frontend separately
- **Persistent Storage** - Volume management for data, worktrees, and databases
- **Health Checks** - Automated service monitoring
- **Environment Configuration** - Secure credential management

## Prerequisites

### Required
- **Docker** 20.10+ (Docker Engine or Docker Desktop)
- **Docker Compose** 2.0+ (usually included with Docker Desktop)
- **Git** (for cloning the repository)

### Recommended
- **2+ CPU cores** - For running multiple services
- **4+ GB RAM** - PostgreSQL, Redis, and application services
- **10+ GB disk space** - Images, volumes, and logs

### API Keys
- **Claude API** - OAuth token or API key (see [Authentication](#authentication))
- **Graphiti Memory** - OpenAI API key (or alternative provider)
- **Optional** - GitHub, Linear, GitLab tokens for integrations

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-org/Auto-Coding.git
cd Auto-Coding
```

### 2. Create Environment File
```bash
cp apps/backend/.env.example .env
# Edit .env with your API keys
```

**Minimum required environment variables:**
```bash
# Claude authentication
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here

# Graphiti memory (required)
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Web backend security
SECRET_KEY=your-secret-key-here-change-in-production
```

See [Environment Variables](#environment-variables) for full configuration.

### 3. Start All Services
```bash
docker-compose up -d
```

This starts:
- **PostgreSQL** - Database (port 5432)
- **Redis** - Cache (port 6379)
- **Backend** - CLI service
- **Web Backend** - API server (port 8000)
- **Web Frontend** - UI (port 3000)

### 4. Wait for Health Checks
```bash
# Wait 30 seconds for services to initialize
sleep 30

# Check status (all should show "healthy")
docker-compose ps
```

### 5. Verify Deployment
```bash
# Test web backend API
curl http://localhost:8000/health

# Test web frontend
curl http://localhost:3000/

# View logs
docker-compose logs -f
```

### 6. Access Application
- **Web UI:** http://localhost:3000
- **API Docs:** http://localhost:8000/docs (if DEBUG=true)
- **Health Check:** http://localhost:8000/health

## Configuration

### Environment Variables

Docker Compose uses environment variables from `.env` file in the project root.

#### Authentication (REQUIRED)

**Claude API:**
```bash
# Option 1: OAuth token (recommended)
CLAUDE_CODE_OAUTH_TOKEN=your-oauth-token-here

# Option 2: Direct API key (not recommended - silent billing)
# ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# Model selection (optional)
CLAUDE_MODEL=claude-sonnet-4-5-20250929
```

**Graphiti Memory (REQUIRED):**
```bash
GRAPHITI_ENABLED=true
GRAPHITI_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### Web Backend Configuration

```bash
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false  # Set to true for development
LOG_LEVEL=INFO

# CORS origins (comma-separated)
CORS_ORIGINS=http://localhost:3000,https://autoclaude.app

# Security (REQUIRED)
SECRET_KEY=your-secret-key-here-change-in-production
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database (connects to postgres service)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autoclaude

# Redis (connects to redis service)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
```

#### Optional Integrations

```bash
# GitHub integration
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxxxx
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret

# Linear integration
LINEAR_API_KEY=lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
LINEAR_TEAM_ID=your-team-id

# GitLab integration
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_INSTANCE_URL=https://gitlab.com
```

#### CI/CD Mode

```bash
# Enable non-interactive CI mode
AUTO_CLAUDE_CI=true
AUTO_CLAUDE_JSON_OUTPUT=true
```

See `apps/backend/.env.example` for full configuration options.

### Persistent Volumes

Docker Compose automatically creates and manages persistent volumes:

| Volume Name | Purpose | Default Size | Path in Container |
|-------------|---------|--------------|-------------------|
| `postgres_data` | Database storage | ~1GB+ | `/var/lib/postgresql/data` |
| `redis_data` | Cache persistence | ~100MB | `/data` |
| `backend_data` | Auto-Claude workspace | ~500MB | `/app/.auto-claude` |
| `backend_worktrees` | Git worktrees | ~2GB+ | `/app/.worktrees` |

**View volumes:**
```bash
docker volume ls | grep autoclaude
```

**Inspect volume:**
```bash
# Volume names are prefixed with the Compose project name (directory name, lowercased).
# For a project in a directory named "Auto-Claude", the prefix is "auto-claude".
docker volume inspect auto-claude_postgres_data
```

**Backup volumes:**
```bash
# Backup postgres data
docker run --rm -v auto-claude_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-backup.tar.gz -C /data .

# Backup backend data
docker run --rm -v auto-claude_backend_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/backend-backup.tar.gz -C /data .
```

**Restore volumes:**
```bash
# Restore postgres data
docker run --rm -v auto-claude_postgres_data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/postgres-backup.tar.gz"
```

### Network Configuration

All services run on the `autoclaude-network` bridge network and communicate via service names:

- **postgres:5432** - PostgreSQL database
- **redis:6379** - Redis cache
- **web-backend:8000** - Web backend API
- **web-frontend:3000** - Web frontend UI

**External access:**
- PostgreSQL: `localhost:5432` (exposed)
- Redis: `localhost:6379` (exposed)
- Web Backend: `localhost:8000` (exposed)
- Web Frontend: `localhost:3000` (exposed)

## Deployment Options

### Development Deployment

**Characteristics:**
- Auto-reload on code changes
- Debug mode enabled
- API documentation available
- Local code mounted as volumes
- Detailed error messages

**Start:**
```bash
# Create .env with DEBUG=true
echo "DEBUG=true" >> .env

# Start with development settings
docker-compose up -d

# View logs in real-time
docker-compose logs -f web-backend
```

**Hot reload:**
```bash
# Mount local code (already configured in docker-compose.yml)
# Changes to ./apps/backend are reflected in backend container
# Changes to ./apps/web-backend are reflected in web-backend container
# Frontend requires rebuild for changes
```

### Production Deployment

**Characteristics:**
- No auto-reload
- Debug mode disabled
- Secure defaults
- Optimized images
- Log rotation

**Preparation:**
```bash
# Create production .env
cp apps/backend/.env.example .env

# Set production values
# - SECURE SECRET_KEY
# - DEBUG=false
# - Production CORS_ORIGINS
# - Strong DATABASE_URL password
# - REDIS_PASSWORD if exposed

# Remove development volume mounts
# Edit docker-compose.yml and comment out:
# - ./apps/backend:/app:ro
# - ${AUTO_CLAUDE_BACKEND_DIR:-./apps/backend}:/app/backend:ro
```

**Start:**
```bash
# Pull latest images
docker-compose pull

# Build images
docker-compose build --no-cache

# Start services
docker-compose up -d

# Verify health
docker-compose ps
```

**Security hardening:**
```bash
# Change default database password
# Edit docker-compose.yml:
# POSTGRES_PASSWORD: secure-random-password

# Add Redis password
# Edit docker-compose.yml:
# redis:
#   command: redis-server --appendonly yes --requirepass your-redis-password

# Update environment:
# REDIS_PASSWORD=your-redis-password
```

### Single Service Deployment

Deploy individual services separately:

**Backend only:**
```bash
cd apps/backend
docker build -t auto-code-backend .
docker run -d \
  --name backend \
  -e CLAUDE_CODE_OAUTH_TOKEN=xxx \
  -e GRAPHITI_ENABLED=true \
  -e OPENAI_API_KEY=xxx \
  -v $(pwd)/.auto-claude:/app/.auto-claude \
  auto-code-backend
```

**Web backend only:**
```bash
cd apps/web-backend
docker build -t auto-code-web-backend .
docker run -d \
  --name web-backend \
  -p 8000:8000 \
  -e DATABASE_URL=postgresql://user:pass@db:5432/autoclaude \
  -e SECRET_KEY=xxx \
  auto-code-web-backend
```

**Web frontend only:**
```bash
cd apps/web-frontend
docker build -t auto-code-web-frontend .
docker run -d \
  --name web-frontend \
  -p 3000:3000 \
  -e VITE_API_URL=http://backend:8000 \
  auto-code-web-frontend
```

## Health Checks

All services include health checks for monitoring and automatic restart.

### Health Check Configuration

| Service | Endpoint/Command | Interval | Timeout | Retries |
|---------|------------------|----------|---------|---------|
| PostgreSQL | `pg_isready -U postgres` | 10s | 5s | 5 |
| Redis | `redis-cli ping` | 10s | 5s | 5 |
| Web Backend | `GET /health` | 30s | 10s | 3 |
| Web Frontend | `GET /` | 30s | 3s | 3 |

### Check Service Health

```bash
# View all service status
docker-compose ps

# Check specific service
docker inspect --format='{{json .State.Health}}' autoclaude-web-backend | jq

# Test health endpoint directly
curl http://localhost:8000/health
```

**Expected response:**
```json
{
  "status": "healthy",
  "service": "auto-claude-web-api",
  "version": "1.0.0",
  "debug_mode": false
}
```

### Automated Health Check Script

Use the provided test script:

```bash
# Make executable
chmod +x test-docker-compose.sh

# Run health checks
./test-docker-compose.sh
```

**Script performs:**
1. Configuration validation
2. Service startup
3. 30-second initialization wait
4. Individual health checks (postgres, redis, web-backend, web-frontend)
5. Status summary

## Troubleshooting

### Services Won't Start

**Problem:** Containers exit immediately after start

**Solution:**
```bash
# Check logs
docker-compose logs backend
docker-compose logs web-backend

# Common issues:
# - Missing API keys in .env
# - Invalid environment variables
# - Port conflicts

# Verify .env file exists
ls -la .env

# Check for required variables
grep CLAUDE_CODE_OAUTH_TOKEN .env
grep OPENAI_API_KEY .env
```

### Port Already in Use

**Problem:** `Bind for 0.0.0.0:8000 failed: port is already allocated`

**Solution:**
```bash
# Find process using port
netstat -ano | findstr :8000  # Windows
lsof -i :8000                  # Linux/Mac

# Kill process or change port in docker-compose.yml:
# ports:
#   - "8001:8000"  # Map container port 8000 to host port 8001
```

### Database Connection Fails

**Problem:** `could not connect to server: Connection refused`

**Solution:**
```bash
# Check postgres is healthy
docker-compose ps postgres

# Verify postgres logs
docker-compose logs postgres

# Check DATABASE_URL matches postgres service
echo $DATABASE_URL
# Should be: postgresql://postgres:postgres@postgres:5432/autoclaude

# Wait for postgres to initialize (can take 10-20 seconds)
docker-compose exec postgres pg_isready -U postgres
```

### Health Checks Failing

**Problem:** Services show as "unhealthy" in `docker-compose ps`

**Solution:**
```bash
# Check specific service health
docker inspect --format='{{json .State.Health}}' autoclaude-web-backend | jq

# View health check logs
docker inspect autoclaude-web-backend | jq '.[0].State.Health.Log'

# Common causes:
# - Service not fully started (wait longer)
# - Missing dependencies (check DATABASE_URL, REDIS_HOST)
# - Invalid configuration (check .env)

# Restart unhealthy service
docker-compose restart web-backend

# Wait for health check
sleep 30
docker-compose ps
```

### Volume Permission Issues

**Problem:** `Permission denied` when accessing volumes

**Solution:**
```bash
# Linux: Fix ownership
sudo chown -R $(id -u):$(id -g) .auto-claude/

# Or run container as root (not recommended)
docker-compose run --user root backend bash
```

### Out of Disk Space

**Problem:** Docker runs out of disk space

**Solution:**
```bash
# Check disk usage
docker system df

# Clean up unused resources
docker system prune -a --volumes

# Remove old images
docker image prune -a

# Remove unused volumes (WARNING: deletes data)
docker volume prune
```

### API Authentication Fails

**Problem:** `401 Unauthorized` or `Invalid API key`

**Solution:**
```bash
# Verify CLAUDE_CODE_OAUTH_TOKEN is set
docker-compose exec backend printenv CLAUDE_CODE_OAUTH_TOKEN

# Test token manually
curl -H "Authorization: Bearer $CLAUDE_CODE_OAUTH_TOKEN" \
  https://api.anthropic.com/v1/messages

# Regenerate token if needed
claude setup-token --print
```

### Logs Not Rotating

**Problem:** Docker logs consuming too much disk space

**Solution:**
```bash
# Check log sizes
docker-compose logs --tail=0 | wc -l

# Logs should auto-rotate (configured in docker-compose.yml):
# logging:
#   driver: json-file
#   options:
#     max-size: "10m"
#     max-file: "3"

# Manual cleanup if needed
docker-compose logs --tail=0
```

## Monitoring & Logs

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web-backend

# Last 100 lines
docker-compose logs --tail=100 web-backend

# Since specific time
docker-compose logs --since 2024-01-01T10:00:00 web-backend
```

### Log Files

Logs are stored in JSON format with rotation:

```bash
# Find log files
docker inspect autoclaude-web-backend | jq '.[0].LogPath'

# View raw log file
sudo cat /var/lib/docker/containers/<container-id>/<container-id>-json.log | jq
```

### Resource Monitoring

```bash
# Real-time resource usage
docker stats

# Specific service
docker stats autoclaude-web-backend

# Check container disk usage
docker system df -v
```

### Metrics

Web backend exposes metrics at `/health`:

```bash
curl http://localhost:8000/health
```

**Response:**
```json
{
  "status": "healthy",
  "service": "auto-claude-web-api",
  "version": "1.0.0",
  "debug_mode": false,
  "database": "connected",
  "redis": "connected"
}
```

## Security Best Practices

### 1. Secure Secrets

**Never commit `.env` to git:**
```bash
# Ensure .env is in .gitignore
echo ".env" >> .gitignore

# Check for leaked secrets
git log -p | grep -i "api_key\|secret\|password"
```

**Use Docker secrets (Swarm mode):**
```yaml
# docker-compose.yml
secrets:
  anthropic_key:
    external: true

services:
  backend:
    secrets:
      - anthropic_key
```

### 2. Network Security

**Restrict external access:**
```yaml
# Only expose necessary ports
services:
  postgres:
    # ports:
    #   - "5432:5432"  # REMOVE - don't expose to host
    networks:
      - autoclaude-network  # Internal only
```

**Use firewalls:**
```bash
# Linux: Allow only web ports
sudo ufw allow 8000/tcp  # API
sudo ufw allow 3000/tcp  # Web UI
sudo ufw deny 5432/tcp   # PostgreSQL (internal only)
```

### 3. User Permissions

All containers run as non-root users:

```dockerfile
# Example from apps/backend/Dockerfile
USER autocode  # Non-root user
```

**Verify:**
```bash
docker-compose exec backend whoami
# Should NOT be "root"
```

### 4. Image Security

**Use official base images:**
```dockerfile
FROM python:3.12-slim  # Official Python image
FROM postgres:16-alpine  # Official PostgreSQL
FROM redis:7-alpine  # Official Redis
```

**Scan for vulnerabilities:**
```bash
# Scan images
docker scan auto-code-backend
docker scan auto-code-web-backend
docker scan auto-code-web-frontend
```

### 5. Log Sanitization

Ensure sensitive data is not logged:

```python
# Example: Sanitize logs
import logging
logging.getLogger('httpx').setLevel(logging.WARNING)  # Hide API calls
```

### 6. TLS/SSL

**Use reverse proxy for TLS:**
```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
```

**Example nginx config:**
```nginx
server {
    listen 443 ssl;
    ssl_certificate /etc/ssl/cert.pem;
    ssl_certificate_key /etc/ssl/key.pem;

    location / {
        proxy_pass http://web-frontend:3000;
    }

    location /api {
        proxy_pass http://web-backend:8000;
    }
}
```

## Stopping Services

### Stop All Services
```bash
# Stop containers (preserves volumes)
docker-compose stop

# Stop and remove containers (preserves volumes)
docker-compose down

# Stop and remove containers AND volumes (deletes data)
docker-compose down -v
```

### Stop Specific Service
```bash
docker-compose stop web-backend
docker-compose stop postgres
```

### Restart Services
```bash
# Restart all
docker-compose restart

# Restart specific service
docker-compose restart web-backend
```

## Updating Services

### Update Docker Images

```bash
# Pull latest images
docker-compose pull

# Rebuild from source
docker-compose build --no-cache

# Restart with new images
docker-compose up -d

# Remove old images
docker image prune
```

### Rolling Updates

```bash
# Update one service at a time
docker-compose up -d --no-deps --build web-backend

# Verify health
docker-compose ps web-backend

# Update next service
docker-compose up -d --no-deps --build web-frontend
```

### Database Migrations

```bash
# Run migrations before updating services
docker-compose exec web-backend python -m alembic upgrade head

# Or during startup (if configured)
docker-compose up -d web-backend
```

## Advanced Configuration

### Custom Docker Compose File

```bash
# Create override file
cat > docker-compose.override.yml <<EOF
version: '3.8'
services:
  web-backend:
    environment:
      - DEBUG=true
    ports:
      - "8001:8000"  # Different port
EOF

# Docker Compose automatically merges docker-compose.yml + docker-compose.override.yml
docker-compose up -d
```

### Scaling Services

```bash
# Scale backend service (if stateless)
docker-compose up -d --scale backend=3

# Verify
docker-compose ps backend
```

### Custom Network

```yaml
# docker-compose.yml
networks:
  autoclaude-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.25.0.0/16
```

### Resource Limits

```yaml
# docker-compose.yml
services:
  web-backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
```

## Next Steps

- **Kubernetes Deployment:** See [KUBERNETES_DEPLOYMENT.md](./KUBERNETES_DEPLOYMENT.md) for cluster deployment
- **Update Strategy:** See [UPDATE_STRATEGY.md](./UPDATE_STRATEGY.md) for rolling updates and blue-green deployments
- **CI/CD Integration:** See [ci-cd-integration.md](./ci-cd-integration.md) for automated builds
- **Cloud Deployment:** See [CLOUD_DEPLOYMENT.md](./CLOUD_DEPLOYMENT.md) for AWS/GCP/Azure deployment

## Support

For issues or questions:

1. **Check logs:** `docker-compose logs -f`
2. **Review health checks:** `docker-compose ps`
3. **Consult troubleshooting:** See [Troubleshooting](#troubleshooting) section above
4. **File an issue:** https://github.com/your-org/Auto-Coding/issues
5. **Discord/Slack:** Join our community for real-time help
