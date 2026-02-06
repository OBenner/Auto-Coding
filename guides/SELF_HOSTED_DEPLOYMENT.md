# Self-Hosted Deployment Guide - Auto Code

This guide covers deploying Auto Code on your own infrastructure for complete data privacy and control. Self-hosting ensures your code never leaves your environment, making it ideal for enterprises, privacy-conscious teams, and air-gapped networks.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Deployment Methods](#deployment-methods)
  - [Docker Compose Deployment](#docker-compose-deployment)
  - [Kubernetes/Helm Deployment](#kubernetesthelm-deployment)
- [Configuration](#configuration)
- [Air-Gapped Environments](#air-gapped-environments)
- [Telemetry and Privacy](#telemetry-and-privacy)
- [Verification](#verification)
- [Next Steps](#next-steps)

---

## Overview

Auto Code's self-hosted option gives you full control over your AI-powered development environment. All code, AI interactions, and metadata remain within your infrastructure.

**Key Benefits:**
- **Complete Data Privacy**: Code never leaves your infrastructure
- **Air-Gap Support**: Deploy in isolated networks without internet access
- **Custom Integration**: Connect to internal GitLab instances, private repositories
- **Compliance**: Meet strict regulatory requirements (HIPAA, SOC2, etc.)
- **No Vendor Lock-in**: Full control over updates and configuration

**Deployment Options:**
- **Docker Compose**: Single-server deployment, quick to set up
- **Kubernetes/Helm**: Scalable, production-ready, high-availability

**Target Audience:**
- Enterprise DevOps teams
- Organizations with data sovereignty requirements
- Government and defense contractors
- Privacy-conscious development teams

---

## Architecture

### Self-Hosted Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Your Infrastructure                        │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │              │  │              │  │              │      │
│  │  Backend     │◄─┤  PostgreSQL  │  │    Redis     │      │
│  │  (FastAPI)   │  │   Database   │  │   (Cache)    │      │
│  │              │  │              │  │              │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                     │
│         │                                                     │
│         ├─────► Internal Git (GitLab, GitHub Enterprise)     │
│         ├─────► Private Repositories                         │
│         └─────► User Workspace Directories                   │
│                                                               │
│  ┌──────────────┐                                            │
│  │  Optional:   │                                            │
│  │  Frontend    │                                            │
│  │  (Electron)  │                                            │
│  └──────────────┘                                            │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │
         ▼ (Optional, controlled by you)
   ┌────────────────┐
   │   External     │
   │  AI Provider   │
   │  (Claude SDK)  │
   └────────────────┘
```

### Component Responsibilities

| Component | Purpose | Data Storage | External Access |
|-----------|---------|--------------|-----------------|
| **Backend** | API server, agent orchestration, Git operations | Local filesystem only | AI Provider (configurable) |
| **PostgreSQL** | User data, repository links, specs, metadata | Persistent volumes | None |
| **Redis** | Session caching, rate limiting, message queuing | In-memory/AOF | None |
| **Frontend (Optional)** | Desktop UI for users | Local filesystem | Backend API |

### Data Flow

**User Workspace → Backend → AI Provider (Optional)**
1. User creates spec in local workspace
2. Backend reads/writes to local Git repository
3. Backend sends code context to AI provider (if enabled)
4. AI provider returns suggestions
5. Backend writes changes to local workspace
6. **No code leaves your infrastructure** (only metadata sent to AI)

**Air-Gapped Mode:**
- All AI interactions disabled
- Manual spec creation and code generation
- Full offline operation

---

## Prerequisites

### Hardware Requirements

**Minimum (Single Team, < 10 Users):**
- CPU: 2 cores
- RAM: 4GB
- Storage: 20GB SSD
- Network: 100 Mbps

**Recommended (Multiple Teams, 10-50 Users):**
- CPU: 4+ cores
- RAM: 8GB+
- Storage: 50GB+ SSD
- Network: 1 Gbps
- High availability (load balancer + database replication)

**Enterprise (50+ Users):**
- CPU: 8+ cores
- RAM: 16GB+
- Storage: 100GB+ SSD with backup
- Network: 10 Gbps
- Kubernetes cluster with 3+ nodes
- Managed PostgreSQL and Redis

### Software Requirements

**For Docker Compose Deployment:**
```bash
# Docker Engine 20.10+
docker --version

# Docker Compose 2.0+
docker-compose --version

# Git (for workspace operations)
git --version

# OpenSSL (for generating secrets)
openssl version
```

**For Kubernetes/Helm Deployment:**
```bash
# Kubernetes cluster 1.27+
kubectl version --client

# Helm 3.0+
helm version

# kubectl access to cluster
kubectl cluster-info

# Git
git --version

# OpenSSL
openssl version
```

**Optional (for local development):**
```bash
# Python 3.12+ (for backend development)
python --version

# Node.js 20+ (for frontend development)
node --version
```

### Network Requirements

**Internet Connected:**
- Outbound access to **AI Provider** (Anthropic Claude API):
  - `api.anthropic.com:443`
- Outbound access to **Docker Registry** (for pulling images):
  - `docker.io`, `ghcr.io`, or your private registry
- Outbound access to **Git Provider** (if using cloud Git):
  - `github.com`, `gitlab.com`, or your internal Git server

**Air-Gapped (Offline):**
- No internet access required
- All images pre-loaded to private registry
- All dependencies available locally
- AI features disabled (manual spec creation)

### Domain and SSL (Optional but Recommended)

For production deployments with browser access:
- Domain name (e.g., `autoclaude.yourcompany.com`)
- SSL/TLS certificate (Let's Encrypt or internal CA)
- Load balancer or ingress controller

---

## Deployment Methods

### Docker Compose Deployment

**Best for:** Quick start, single-server, testing, small teams

#### Prerequisites

Before starting, ensure you have:
- **Docker Engine 20.10+** and **Docker Compose 2.0+** installed
- **Git** for cloning the repository
- **OpenSSL** for generating secure secrets
- **Ports 8000, 5432, and 6379** available
- At least **4GB RAM** and **20GB disk space** (see [Resource Requirements](../infrastructure/RESOURCE_REQUIREMENTS.md))

```bash
# Verify prerequisites
docker --version        # Docker 20.10+
docker-compose --version  # Docker Compose 2.0+
git --version           # Git 2.0+
openssl version         # OpenSSL 1.1+
```

#### Quick Start

Get Auto Code running in under 5 minutes:

```bash
# 1. Clone repository
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude

# 2. Navigate to deployment directory
cd infrastructure

# 3. Copy environment template
cp .env.example .env

# 4. Generate secure secrets
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -base64 32)

# 5. Update .env with secrets
sed -i.bak "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" .env
sed -i.bak "s/postgres:postgres@postgres/postgres:$POSTGRES_PASSWORD@postgres/" .env

# 6. Start services
docker-compose up -d

# 7. Wait for services to be healthy (up to 60 seconds)
echo "Waiting for services to start..."
sleep 30

# 8. Check service status
docker-compose ps

# 9. Verify deployment
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","redis":"connected"}
```

**If everything looks good**, skip to [Verification](#verification). If you encountered issues, see the [Troubleshooting](#docker-compose-troubleshooting) section below.

#### Detailed Configuration

For production deployments or custom configurations, follow this detailed setup.

**Step 1: Create `.env` file**

```bash
cd infrastructure
cp .env.example .env
```

**Step 2: Generate secure secrets**

```bash
# Generate SECRET_KEY for JWT signing (64 hex characters)
export SECRET_KEY=$(openssl rand -hex 32)

# Generate POSTGRES_PASSWORD (secure random password)
export POSTGRES_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-32)

# (Optional) Generate REDIS_PASSWORD
export REDIS_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-16)

# Display generated passwords (save these securely!)
echo "SECRET_KEY=$SECRET_KEY"
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD"
echo "REDIS_PASSWORD=$REDIS_PASSWORD"
```

**Step 3: Edit `.env` with your settings**

Open `.env` in your editor and configure the following:

```env
# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
# Server host (0.0.0.0 listens on all interfaces)
HOST=0.0.0.0

# Server port (default: 8000)
PORT=8000

# Debug mode - set to "false" in production!
DEBUG=false

# Logging level: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO

# =============================================================================
# SECURITY (REQUIRED)
# =============================================================================
# CRITICAL: Generate with: openssl rand -hex 32
# This is used for JWT token signing - keep it secret!
SECRET_KEY=your-64-char-hex-secret-key-here

# JWT access token expiration time in minutes
ACCESS_TOKEN_EXPIRE_MINUTES=60

# =============================================================================
# DATABASE CONFIGURATION (REQUIRED)
# =============================================================================
# PostgreSQL connection URL for Docker Compose
# Format: postgresql://user:password@host:port/database
DATABASE_URL=postgresql://postgres:your-postgres-password@postgres:5432/autoclaude

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================
# Redis hostname (service name in docker-compose)
REDIS_HOST=redis

# Redis port
REDIS_PORT=6379

# Redis database number
REDIS_DB=0

# Redis password (optional but recommended for production)
# Leave empty if not using password authentication
REDIS_PASSWORD=

# =============================================================================
# CORS CONFIGURATION
# =============================================================================
# Allowed CORS origins (comma-separated list)
# For self-hosted with local frontend, include frontend URL
# For web deployment, include your domain
CORS_ORIGINS=http://localhost:3000,http://localhost:8000,https://autoclaude.yourcompany.com

# =============================================================================
# AI PROVIDER (Optional - for AI features)
# =============================================================================
# Anthropic Claude API key for AI-powered features
# Get your API key from: https://console.anthropic.com/
# Leave empty to disable AI features (air-gapped mode)
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# =============================================================================
# OAUTH CONFIGURATION (Optional - for Git provider integration)
# =============================================================================
# GitHub OAuth credentials (for GitHub.com or GitHub Enterprise)
# Register app at: https://github.com/settings/developers
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=

# GitLab OAuth credentials (for GitLab.com or self-hosted GitLab)
# Register app at: https://gitlab.com/-/profile/applications
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=

# OAuth redirect URI (must match your deployment URL)
OAUTH_REDIRECT_URI=http://localhost:8000/api/git/callback

# For internal GitLab/GitHub Enterprise, override default URLs:
# GITLAB_URL=https://gitlab.yourcompany.com
# GITHUB_URL=https://github.yourcompany.com

# =============================================================================
# TELEMETRY CONFIGURATION
# =============================================================================
# Disable all telemetry for privacy (recommended for self-hosted)
DISABLE_TELEMETRY=true

# =============================================================================
# WORKSPACE CONFIGURATION
# =============================================================================
# Default workspace location (mounted volume)
WORKSPACE_DIR=/workspace

# =============================================================================
# WEBSOCKET CONFIGURATION
# =============================================================================
# WebSocket heartbeat interval in seconds
# Helps detect disconnected clients
WS_HEARTBEAT_INTERVAL=30
```

**Important Notes:**
- **SECRET_KEY**: Never use the default value in production. Generate a secure random key.
- **POSTGRES_PASSWORD**: Use a strong password. The default "postgres" is only for development.
- **ANTHROPIC_API_KEY**: Required for AI features. Can be omitted in air-gapped environments.
- **CORS_ORIGINS**: Must include all frontend URLs that will access the backend.
- **DISABLE_TELEMETRY**: Set to `true` for privacy or compliance requirements.

**Step 4: Create `docker-compose.yml`**

Create `infrastructure/docker-compose.yml` with the following configuration:

```yaml
version: '3.8'

services:
  # PostgreSQL database for user data and repositories
  postgres:
    image: postgres:16-alpine
    container_name: autoclaude-postgres
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: autoclaude
      POSTGRES_INITDB_ARGS: "-E UTF8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - autoclaude-network
    restart: unless-stopped

  # Redis for usage tracking and caching
  redis:
    image: redis:7-alpine
    container_name: autoclaude-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - autoclaude-network
    restart: unless-stopped

  # Auto Code backend API
  backend:
    image: autoclaude/backend:latest
    container_name: autoclaude-backend
    environment:
      # Server configuration
      HOST: 0.0.0.0
      PORT: 8000
      DEBUG: "false"
      LOG_LEVEL: INFO

      # CORS configuration
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000,http://localhost:8000}

      # Authentication
      SECRET_KEY: ${SECRET_KEY}
      ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE_MINUTES:-60}

      # Database configuration (connects to postgres service)
      DATABASE_URL: postgresql://postgres:${POSTGRES_PASSWORD:-postgres}@postgres:5432/autoclaude

      # Redis configuration (connects to redis service)
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_DB: 0
      REDIS_PASSWORD: ${REDIS_PASSWORD:-}

      # OAuth configuration
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID:-}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET:-}
      GITLAB_CLIENT_ID: ${GITLAB_CLIENT_ID:-}
      GITLAB_CLIENT_SECRET: ${GITLAB_CLIENT_SECRET:-}
      OAUTH_REDIRECT_URI: ${OAUTH_REDIRECT_URI:-http://localhost:8000/api/git/callback}

      # WebSocket configuration
      WS_HEARTBEAT_INTERVAL: ${WS_HEARTBEAT_INTERVAL:-30}

      # Telemetry
      DISABLE_TELEMETRY: ${DISABLE_TELEMETRY:-true}

      # AI Provider (optional)
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY:-}
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - autoclaude-network
    restart: unless-stopped
    volumes:
      - workspace_data:/workspace
      - ./specs:/app/specs

networks:
  autoclaude-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  workspace_data:
    driver: local
```

**Key Features of This Configuration:**

1. **Health Checks**: All services have health checks to ensure they're running properly
2. **Service Dependencies**: Backend waits for PostgreSQL and Redis to be healthy before starting
3. **Persistent Volumes**: Data persists across container restarts
4. **Network Isolation**: Services communicate on a private bridge network
5. **Environment Variable Defaults**: Uses `${VAR:-default}` syntax for safe defaults
6. **Restart Policies**: Services automatically restart on failure (unless manually stopped)
7. **UTF8 Database**: PostgreSQL initialized with UTF-8 encoding for international character support

**Step 5: Start services**

```bash
# Start all services in detached mode (background)
docker-compose up -d

# Expected output:
# Creating network "infrastructure_autoclaude-network"  ... done
# Creating volume "infrastructure_postgres_data"        ... done
# Creating volume "infrastructure_redis_data"           ... done
# Creating volume "infrastructure_workspace_data"       ... done
# Creating autoclaude-postgres                          ... done
# Creating autoclaude-redis                             ... done
# Creating autoclaude-backend                           ... done
```

**Step 6: Monitor service startup**

```bash
# Watch logs in real-time (Ctrl+C to exit)
docker-compose logs -f

# Or watch specific service
docker-compose logs -f backend

# Check service status
docker-compose ps

# Expected output (after services are healthy):
# NAME                    STATUS              PORTS
# autoclaude-backend      running (healthy)   0.0.0.0:8000->8000/tcp
# autoclaude-postgres     running (healthy)   5432/tcp
# autoclaude-redis        running (healthy)   6379/tcp
```

**Note**: It may take 30-60 seconds for all services to become healthy. The backend service waits for PostgreSQL and Redis to be healthy before starting.

**Step 7: Initialize database**

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade ->  <revision_id>

# Verify migrations completed successfully
docker-compose exec backend alembic current

# Expected output:
# INFO  [alembic.runtime.migration] Current revision(s): <revision_id>
```

**Step 8: Verify deployment**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","redis":"connected"}

# Test with verbose output (for debugging)
curl -v http://localhost:8000/health

# Check all service health
docker-compose ps

# View recent backend logs
docker-compose logs --tail=50 backend
```

**Success Indicators:**
- ✅ All three services show `running (healthy)` status
- ✅ Health endpoint returns `{"status":"healthy",...}`
- ✅ No error messages in logs
- ✅ Database migrations completed successfully

#### Managing the Deployment

**Stop services:**
```bash
# Stop all services (preserves data)
docker-compose down

# Expected output:
# Stopping autoclaude-backend    ... done
# Stopping autoclaude-redis      ... done
# Stopping autoclaude-postgres   ... done
# Removing network infrastructure_autoclaude-network  ... done
```

**Stop and remove all data (⚠️ WARNING: Deletes all data):**
```bash
# Stop services and remove volumes (deletes database, workspace data)
docker-compose down -v

# ⚠️ Use this only if you want to completely reset the deployment
# All your data will be lost!
```

**Start services:**
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d backend
```

**Restart services:**
```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend

# Restart with force (recreate container)
docker-compose up -d --force-recreate backend
```

**View logs:**
```bash
# Follow all logs (real-time)
docker-compose logs -f

# Follow specific service logs
docker-compose logs -f backend

# View last 100 lines
docker-compose logs --tail=100 backend

# View logs with timestamps
docker-compose logs -t backend

# View logs since a specific time
docker-compose logs --since 2024-01-01T10:00:00 backend
```

**Update to latest version:**
```bash
# 1. Pull new images
docker-compose pull

# 2. Stop services
docker-compose down

# 3. Start with new images
docker-compose up -d

# 4. Run database migrations
docker-compose exec backend alembic upgrade head

# 5. Verify deployment
curl http://localhost:8000/health
```

**Backup and restore:**

```bash
# Backup PostgreSQL database
docker-compose exec postgres pg_dump -U postgres autoclaude > backup.sql

# Restore PostgreSQL database
docker-compose exec -T postgres psql -U postgres autoclaude < backup.sql

# Backup workspace data
docker run --rm -v infrastructure_workspace_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/workspace-backup.tar.gz -C /data .

# Restore workspace data
docker run --rm -v infrastructure_workspace_data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/workspace-backup.tar.gz -C /data
```

**Check resource usage:**
```bash
# View container resource usage
docker stats

# View disk usage
docker system df

# View volume details
docker volume ls
docker volume inspect infrastructure_postgres_data
```

---

#### Docker Compose Troubleshooting

**Problem: Services fail to start**

```bash
# Check service status
docker-compose ps

# View logs for errors
docker-compose logs

# Common issues:
# - Port already in use: Change port mapping in docker-compose.yml
# - Volume permission error: Run with appropriate permissions
# - Image not found: Run `docker-compose pull` first
```

**Problem: Backend service unhealthy**

```bash
# Check backend health status
docker-compose ps

# View backend logs
docker-compose logs backend

# Common causes:
# 1. Database connection failed → Check postgres is healthy
# 2. Redis connection failed → Check redis is healthy
# 3. SECRET_KEY not set → Check .env file
# 4. Port 8000 already in use → lsof -i :8000 to find process

# Manually test health endpoint from inside container
docker-compose exec backend python -c "import requests; print(requests.get('http://localhost:8000/health').json())"
```

**Problem: Database migrations fail**

```bash
# Check database connection
docker-compose exec backend python -c "
from sqlalchemy import create_engine
engine = create_engine('postgresql://postgres:postgres@postgres:5432/autoclaude')
print(engine.connect())
"

# Reset database (⚠️ WARNING: Deletes all data)
docker-compose exec postgres psql -U postgres -c "DROP DATABASE IF EXISTS autoclaude;"
docker-compose exec postgres psql -U postgres -c "CREATE DATABASE autoclaude;"
docker-compose exec backend alembic upgrade head
```

**Problem: High memory usage**

```bash
# Check resource usage
docker stats

# Limit memory in docker-compose.yml:
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 1G
        reservations:
          memory: 512M
```

**Problem: Can't access backend from host**

```bash
# Verify service is running
docker-compose ps

# Check port mapping
docker port autoclaude-backend

# Test from inside container
docker-compose exec backend curl http://localhost:8000/health

# Test from host
curl http://localhost:8000/health

# If failing, check:
# 1. Firewall settings
# 2. Port 8000 not blocked
# 3. Correct port mapping in docker-compose.yml
```

**Problem: Logs show "Telemetry disabled" but you want it enabled**

```bash
# Edit .env file
nano .env

# Change:
# DISABLE_TELEMETRY=true
# To:
# DISABLE_TELEMETRY=false

# Restart backend
docker-compose restart backend
```

**Problem: Need to completely reset deployment**

```bash
# Stop and remove everything (⚠️ DELETES ALL DATA)
docker-compose down -v

# Remove images (optional)
docker rmi autoclaude/backend:latest

# Start fresh
docker-compose up -d
```

**Get detailed diagnostics:**

```bash
# Export full diagnostics for support
docker-compose > diagnostics.txt
docker ps >> diagnostics.txt
docker stats --no-stream >> diagnostics.txt
docker system df >> diagnostics.txt
docker-compose logs >> diagnostics-full.log
```

---

### Kubernetes/Helm Deployment

**Best for:** Production, high availability, scaling, enterprise

#### Prerequisites

- Kubernetes cluster (1.27+)
- `kubectl` configured
- Helm 3+ installed
- Ingress controller (nginx, traefik, etc.)
- Persistent storage provisioner

#### Quick Deploy with Helm

```bash
# 1. Add Auto Code Helm repository (if hosting Helm chart)
helm repo add autoclaude https://charts.autoclaude.io
helm repo update

# 2. Create values file for your configuration
cat > autoclaude-values.yaml << EOF
backend:
  image:
    repository: your-registry/autoclaude-backend
    tag: v1.0.0
  replicaCount: 2

  ingress:
    enabled: true
    className: nginx
    hosts:
      - host: autoclaude.yourcompany.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: autoclaude-tls
        hosts:
          - autoclaude.yourcompany.com

  env:
    SECRET_KEY: "your-generated-secret-key"
    ANTHROPIC_API_KEY: "your-anthropic-api-key"
    DISABLE_TELEMETRY: "true"

postgresql:
  enabled: true
  auth:
    password: "your-postgres-password"

redis:
  enabled: true
  password: "your-redis-password"
EOF

# 3. Install the chart
helm install autoclaude autoclaude/autoclaude \
  --values autoclaude-values.yaml \
  --namespace autoclaude \
  --create-namespace

# 4. Wait for rollout
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=autoclaude \
  --namespace autoclaude --timeout=300s

# 5. Get backend URL
kubectl get ingress -n autoclaude
```

#### Detailed Helm Installation

**1. Install Helm Chart from Local Directory:**

```bash
cd infrastructure/helm/autoclaude

# Create custom values file
cat > my-values.yaml << EOF
backend:
  enabled: true
  replicaCount: 3

  image:
    repository: autoclaude/backend
    tag: v1.0.0
    pullPolicy: IfNotPresent

  service:
    type: LoadBalancer
    port: 80
    targetPort: 8000

  ingress:
    enabled: true
    className: nginx
    annotations:
      cert-manager.io/cluster-issuer: "letsencrypt-prod"
      nginx.ingress.kubernetes.io/ssl-redirect: "true"
    hosts:
      - host: autoclaude.yourcompany.com
        paths:
          - path: /
            pathType: Prefix
    tls:
      - secretName: autoclaude-tls
        hosts:
          - autoclaude.yourcompany.com

  resources:
    requests:
      memory: "1Gi"
      cpu: "500m"
    limits:
      memory: "2Gi"
      cpu: "1000m"

  env:
    SECRET_KEY: "your-64-char-hex-secret-key"
    ANTHROPIC_API_KEY: "your-api-key"
    DISABLE_TELEMETRY: "true"
    LOG_LEVEL: "INFO"

postgresql:
  enabled: true
  auth:
    password: "your-secure-postgres-password"
    database: "autoclaude"
  primary:
    persistence:
      enabled: true
      size: 20Gi

redis:
  enabled: true
  auth:
    password: "your-secure-redis-password"
  master:
    persistence:
      enabled: true
      size: 5Gi
EOF

# Install the chart
helm install autoclaude . \
  --values my-values.yaml \
  --namespace autoclaude \
  --create-namespace

# Check installation
helm status autoclaude -n autoclaude
kubectl get pods -n autoclaude
```

**2. Verify Installation:**

```bash
# Check all pods are running
kubectl get pods -n autoclaude

# Expected output:
# NAME                                READY   STATUS    RESTARTS   AGE
# autoclaude-postgresql-0             1/1     Running   0          2m
# autoclaude-redis-master-0           1/1     Running   0          2m
# autoclaude-backend-xxx              1/1     Running   0          1m
# autoclaude-backend-yyy              1/1     Running   0          1m

# Get backend service
kubectl get svc -n autoclaude

# Get ingress URL
kubectl get ingress -n autoclaude

# Test health endpoint
kubectl port-forward -n autoclaude svc/autoclaude-backend 8000:80 &
curl http://localhost:8000/health
```

**3. Initialize Database:**

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -n autoclaude -l app.kubernetes.io/name=autoclaude,app.kubernetes.io/component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -n autoclaude $BACKEND_POD -- alembic upgrade head

# Verify migrations
kubectl exec -n autoclaude $BACKEND_POD -- alembic current
```

#### Scaling with Helm

```bash
# Scale backend to 5 replicas
helm upgrade autoclaude . \
  --values my-values.yaml \
  --set backend.replicaCount=5 \
  --namespace autoclaude

# Enable horizontal pod autoscaler
helm upgrade autoclaude . \
  --values my-values.yaml \
  --set backend.autoscaling.enabled=true \
  --set backend.autoscaling.minReplicas=2 \
  --set backend.autoscaling.maxReplicas=10 \
  --set backend.autoscaling.targetCPUUtilizationPercentage=80 \
  --namespace autoclaude
```

#### Upgrading with Helm

```bash
# Pull new images and upgrade
helm upgrade autoclaude . \
  --values my-values.yaml \
  --set backend.image.tag=v1.1.0 \
  --namespace autoclaude

# Watch rollout status
kubectl rollout status deployment/autoclaude-backend -n autoclaude

# Rollback if needed
helm rollback autoclaude -n autoclaude
```

---

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `HOST` | Server bind address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `SECRET_KEY` | JWT signing key | - | **Yes** |
| `DATABASE_URL` | PostgreSQL connection | - | **Yes** |
| `REDIS_HOST` | Redis hostname | `localhost` | No |
| `REDIS_PORT` | Redis port | `6379` | No |
| `REDIS_PASSWORD` | Redis password | `` | No |
| `CORS_ORIGINS` | Allowed frontend origins | - | **Yes** |
| `ANTHROPIC_API_KEY` | Claude API key | - | Yes* |
| `DISABLE_TELEMETRY` | Disable all telemetry | `false` | No |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `DEBUG` | Debug mode | `false` | No |

*Required for AI features. Can be omitted in air-gapped mode.

### Secrets Management

**Docker Compose:**
```bash
# Generate secrets
openssl rand -hex 32 > .secret_key
openssl rand -base64 32 > .postgres_password

# Use in .env
SECRET_KEY=$(cat .secret_key)
POSTGRES_PASSWORD=$(cat .postgres_password)

# Never commit .secret_key or .postgres_password
echo ".secret_key" >> .gitignore
echo ".postgres_password" >> .gitignore
```

**Kubernetes Secrets:**
```bash
# Create secret from literals
kubectl create secret generic autoclaude-secrets \
  --from-literal=SECRET_KEY=$(openssl rand -hex 32) \
  --from-literal=ANTHROPIC_API_KEY=your-api-key \
  --namespace=autoclaude

# Create secret from file
kubectl create secret generic autoclaude-db-secret \
  --from-literal=POSTGRES_PASSWORD=$(openssl rand -base64 32) \
  --namespace=autoclaude

# Reference in Helm values
env:
  SECRET_KEY:
    secretKeyRef:
      name: autoclaude-secrets
      key: SECRET_KEY
```

### Git Provider Integration

**Internal GitLab:**
```env
# For self-hosted GitLab
GITLAB_URL=https://gitlab.yourcompany.com
GITLAB_CLIENT_ID=your-gitlab-app-id
GITLAB_CLIENT_SECRET=your-gitlab-secret
OAUTH_REDIRECT_URI=https://autoclaude.yourcompany.com/api/git/gitlab/callback
```

**Internal GitHub Enterprise:**
```env
# For GitHub Enterprise Server
GITHUB_URL=https://github.yourcompany.com
GITHUB_CLIENT_ID=your-github-client-id
GITHUB_CLIENT_SECRET=your-github-client-secret
OAUTH_REDIRECT_URI=https://autoclaude.yourcompany.com/api/git/github/callback
```

---

## Air-Gapped Environments

For complete isolation from the internet, deploy in air-gapped mode.

### Preparing for Air-Gapped Deployment

**1. Export Docker Images:**

```bash
# On internet-connected machine
docker pull autoclaude/backend:v1.0.0
docker pull postgres:16-alpine
docker pull redis:7-alpine

# Save images to tar file
docker save \
  autoclaude/backend:v1.0.0 \
  postgres:16-alpine \
  redis:7-alpine \
  -o autoclaude-images.tar

# Transfer to air-gapped environment (sneakernet, secure file transfer)
scp autoclaude-images.tar user@air-gapped-server:/tmp/
```

**2. Load Images in Air-Gapped Environment:**

```bash
# On air-gapped server
docker load -i /tmp/autoclaude-images.tar

# Verify images loaded
docker images | grep -E "autoclaude|postgres|redis"

# Push to private registry (if using)
docker tag autoclaude/backend:v1.0.0 private-registry.local/autoclaude/backend:v1.0.0
docker push private-registry.local/autoclaude/backend:v1.0.0
```

**3. Set Up Private Registry (Optional):**

```bash
# Run local registry
docker run -d \
  --name registry \
  --restart=unless-stopped \
  -p 5000:5000 \
  -v /data/registry:/var/lib/registry \
  registry:2

# Push images to local registry
docker tag autoclaude/backend:v1.0.0 localhost:5000/autoclaude/backend:v1.0.0
docker push localhost:5000/autoclaude/backend:v1.0.0
```

**4. Configure Air-Gapped Deployment:**

Create `docker-compose.airgap.yml`:

```yaml
version: '3.8'

services:
  backend:
    image: localhost:5000/autoclaude/backend:v1.0.0
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/autoclaude
      - REDIS_HOST=redis
      - SECRET_KEY=${SECRET_KEY}
      - DISABLE_TELEMETRY=true
      - ANTHROPIC_API_KEY=  # Leave empty - no AI in air-gapped mode
    volumes:
      - workspace_data:/workspace
      - ./specs:/app/specs
    depends_on:
      - postgres
      - redis

  postgres:
    image: localhost:5000/postgres:16-alpine
    environment:
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: localhost:5000/redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
  workspace_data:
```

**5. Deploy:**

```bash
# Generate secrets
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Start services
docker-compose -f docker-compose.airgap.yml up -d

# Initialize database
docker-compose -f docker-compose.airgap.yml exec backend alembic upgrade head
```

### Air-Gapped Kubernetes Deployment

**1. Export Helm Chart:**

```bash
# On internet-connected machine
helm pull autoclaude/autoclaude --version v1.0.0

# Transfer chart to air-gapped environment
scp autoclaude-v1.0.0.tgz user@air-gapped-server:/tmp/
```

**2. Load Images:**

```bash
# On air-gapped cluster
# Load images into all nodes (run on each node)
docker load -i /tmp/autoclaude-images.tar

# Or use private registry
kubectl create namespace docker-registry
helm install registry \
  --set service.type=NodePort \
  oci://ghcr.io/bitnami-charts/registry
```

**3. Install Chart:**

```bash
# Extract chart
tar -xzf autoclaude-v1.0.0.tgz
cd autoclaude

# Create values for air-gapped
cat > airgap-values.yaml << EOF
backend:
  image:
    repository: private-registry.local/autoclaude/backend
    tag: v1.0.0
  env:
    DISABLE_TELEMETRY: "true"
    ANTHROPIC_API_KEY: ""  # No AI in air-gapped mode

postgresql:
  image:
    registry: private-registry.local
  redis:
    image:
      registry: private-registry.local
EOF

# Install
helm install autoclaude . \
  --values airgap-values.yaml \
  --namespace autoclaude \
  --create-namespace
```

---

## Telemetry and Privacy

Auto Code provides full control over telemetry and data collection.

### Disabling Telemetry

**Environment Variable:**
```env
# Disable all telemetry, analytics, and usage tracking
DISABLE_TELEMETRY=true
```

**Docker Compose:**
```yaml
services:
  backend:
    environment:
      - DISABLE_TELEMETRY=true
```

**Helm:**
```yaml
backend:
  env:
    DISABLE_TELEMETRY: "true"
```

### What Telemetry Collects (When Enabled)

By default, Auto Code may collect:
- **Anonymous usage metrics**: Feature usage frequency
- **Performance metrics**: Response times, error rates
- **Version information**: Auto Code version for compatibility tracking
- **Error reports**: Anonymous crash reports

**What is NEVER collected:**
- Code content
- User data
- Repository names or URLs
- File names or paths
- AI prompts or responses

### Privacy Guarantee

In self-hosted mode:
- **All code stays in your infrastructure**
- No code sent to external servers (except AI provider)
- AI provider only receives code context you explicitly send
- Telemetry is completely optional and disableable
- Full audit trail in your logs

### Compliance

Auto Code self-hosted deployment supports compliance with:
- **GDPR**: Full data control, right to deletion
- **HIPAA**: Healthcare data protection
- **SOC2**: Security controls for customer data
- **ITAR**: Defense contractor requirements
- **FedRAMP**: Government cloud compliance

For compliance audits:
- All data stored in your infrastructure
- Access logs in your systems
- No third-party data processing

---

## Verification

### Health Checks

**Docker Compose:**
```bash
# Check all services are healthy
docker-compose ps

# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","redis":"connected"}
```

**Kubernetes:**
```bash
# Check pod status
kubectl get pods -n autoclaude

# Describe pod for details
kubectl describe pod -n autoclaude -l app.kubernetes.io/component=backend

# Port-forward and test
kubectl port-forward -n autoclaude svc/autoclaude-backend 8000:80
curl http://localhost:8000/health
```

### Database Verification

```bash
# Docker Compose
docker-compose exec postgres psql -U postgres -d autoclaude -c "\dt"

# Kubernetes
kubectl exec -it -n autoclaude autoclaude-postgresql-0 \
  -- psql -U postgres -d autoclaude -c "\dt"

# Expected tables:
# alembic_version
# users
# repositories
# specs
```

### Redis Verification

```bash
# Docker Compose
docker-compose exec redis redis-cli ping
# Expected: PONG

# Kubernetes
kubectl exec -n autoclaude autoclaude-redis-master-0 -- redis-cli ping
# Expected: PONG
```

### Log Verification

**Check for errors:**
```bash
# Docker Compose
docker-compose logs backend | grep -i error

# Kubernetes
kubectl logs -n autoclaude -l app.kubernetes.io/component=backend | grep -i error
```

**Verify telemetry disabled:**
```bash
# Docker Compose
docker-compose logs backend | grep -i telemetry
# Expected: "Telemetry disabled" or no telemetry-related logs

# Kubernetes
kubectl logs -n autoclaude -l app.kubernetes.io/component=backend | grep -i telemetry
```

### End-to-End Test

**Create a test spec:**

```bash
# Docker Compose
docker-compose exec backend python -c "
import os
os.chdir('/workspace')
# Run spec creation
"

# Kubernetes
kubectl exec -it -n autoclaude <backend-pod> -- python /app/spec_runner.py --task "Test feature"
```

**Verify workspace creation:**
```bash
# Docker Compose
docker-compose exec backend ls -la /workspace/.auto-claude/specs/

# Kubernetes
kubectl exec -it -n autoclaude <backend-pod> -- ls -la /workspace/.auto-claude/specs/
```

---

## Next Steps

✅ **Your self-hosted deployment is now running!**

### Recommended Actions

1. **Review Security Settings:**
   - Verify strong `SECRET_KEY` is set
   - Ensure `DISABLE_TELEMETRY=true` if required
   - Check database password strength
   - Enable SSL/TLS for production

2. **Configure Backups:**
   - Set up automated PostgreSQL backups
   - Backup Redis persistence data
   - Backup workspace directories
   - Test restore procedures

3. **Set Up Monitoring:**
   - Enable application logging
   - Set up log aggregation (ELK, Loki)
   - Configure metrics (Prometheus)
   - Set up alerting (AlertManager)

4. **Scale Your Deployment:**
   - Increase backend replicas for high availability
   - Configure load balancer
   - Set up database replication
   - Enable Redis cluster if needed

5. **Configure Git Integration:**
   - Set up internal GitLab/GitHub Enterprise OAuth
   - Configure repository permissions
   - Test Git operations

6. **Configure AI Provider (Optional):**
   - Set up Anthropic API account
   - Configure API key
   - Test AI features
   - Set up usage limits

### Documentation

- [RESOURCE_REQUIREMENTS.md](../infrastructure/RESOURCE_REQUIREMENTS.md) - Hardware and scaling requirements
- [SELF_HOSTED_UPDATES.md](SELF_HOSTED_UPDATES.md) - Update and upgrade procedures
- [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) - Advanced deployment patterns

### Troubleshooting

If you encounter issues:
- Check logs: `docker-compose logs` or `kubectl logs`
- Verify environment variables are set correctly
- Ensure all services are healthy
- Check network connectivity (if not air-gapped)
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)

### Get Help

- **Documentation**: [guides/README.md](README.md)
- **GitHub Issues**: https://github.com/OBenner/Auto-Coding/issues
- **Community Support**: Discord/Slack (coming soon)
- **Enterprise Support**: Contact us for enterprise SLA

---

**Maintained by the Auto Code team. Last updated: 2026-02-06**
