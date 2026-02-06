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

#### Quick Start

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
echo "SECRET_KEY=$SECRET_KEY" >> .env
echo "POSTGRES_PASSWORD=$POSTGRES_PASSWORD" >> .env

# 6. Start services
docker-compose up -d

# 7. Initialize database
docker-compose exec backend alembic upgrade head

# 8. Verify deployment
curl http://localhost:8000/health
```

#### Detailed Configuration

**1. Create `.env` file:**

```bash
cd infrastructure
cp .env.example .env
```

**2. Edit `.env` with your settings:**

```env
# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# =============================================================================
# SECURITY
# =============================================================================

# CRITICAL: Generate with: openssl rand -hex 32
SECRET_KEY=your-generated-secret-key-here

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# PostgreSQL (Docker Compose)
DATABASE_URL=postgresql://postgres:your-postgres-password@postgres:5432/autoclaude

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================

REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# For self-hosted with local frontend
CORS_ORIGINS=http://localhost:3000,http://localhost:8000

# =============================================================================
# AI PROVIDER (Anthropic Claude API)
# =============================================================================

# Get API key from: https://console.anthropic.com/
ANTHROPIC_API_KEY=your-anthropic-api-key-here

# =============================================================================
# OAUTH CONFIGURATION (Optional - for Git provider integration)
# =============================================================================

# GitHub/GitLab OAuth (if using cloud Git providers)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=

# =============================================================================
# TELEMETRY CONFIGURATION
# =============================================================================

# Disable all telemetry for privacy
DISABLE_TELEMETRY=true

# =============================================================================
# WORKSPACE CONFIGURATION
# =============================================================================

# Default workspace location (mounted volume)
WORKSPACE_DIR=/workspace

# =============================================================================
# WEBSOCKET CONFIGURATION
# =============================================================================

WS_HEARTBEAT_INTERVAL=30
```

**3. Create `docker-compose.yml`:**

```yaml
version: '3.8'

services:
  backend:
    image: autoclaude/backend:latest
    container_name: autoclaude-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/autoclaude
      - REDIS_HOST=redis
      - SECRET_KEY=${SECRET_KEY}
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - DISABLE_TELEMETRY=${DISABLE_TELEMETRY:-true}
    volumes:
      - workspace_data:/workspace
      - ./specs:/app/specs
    depends_on:
      - postgres
      - redis
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  postgres:
    image: postgres:16-alpine
    container_name: autoclaude-postgres
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
      - POSTGRES_DB=autoclaude
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: autoclaude-redis
    restart: unless-stopped
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  workspace_data:
    driver: local
```

**4. Start services:**

```bash
# Start all services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f backend

# Expected output:
# NAME                    STATUS              PORTS
# autoclaude-backend      running (healthy)   0.0.0.0:8000->8000/tcp
# autoclaude-postgres     running (healthy)   5432/tcp
# autoclaude-redis        running (healthy)   6379/tcp
```

**5. Initialize database:**

```bash
# Run database migrations
docker-compose exec backend alembic upgrade head

# Verify migrations
docker-compose exec backend alembic current

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade -> <latest-revision>
```

**6. Access the deployment:**

```bash
# Test health endpoint
curl http://localhost:8000/health

# Expected response:
# {"status":"healthy","database":"connected","redis":"connected"}
```

#### Managing the Deployment

**Stop services:**
```bash
docker-compose down
```

**Stop and remove data:**
```bash
docker-compose down -v
```

**View logs:**
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
```

**Restart services:**
```bash
docker-compose restart backend
```

**Update to latest version:**
```bash
# Pull new images
docker-compose pull

# Recreate containers
docker-compose up -d

# Run migrations
docker-compose exec backend alembic upgrade head
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
