# Cloud Setup Guide - Auto Claude

This guide walks you through the initial setup of Auto Claude's cloud-hosted infrastructure. Follow these steps to deploy your first cloud instance.

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Detailed Setup Steps](#detailed-setup-steps)
  - [1. Cloud Platform Setup](#1-cloud-platform-setup)
  - [2. OAuth Provider Configuration](#2-oauth-provider-configuration)
  - [3. Environment Configuration](#3-environment-configuration)
  - [4. Initial Deployment](#4-initial-deployment)
  - [5. Database Initialization](#5-database-initialization)
  - [6. Verification](#6-verification)
- [Next Steps](#next-steps)

---

## Architecture Overview

Auto Claude's cloud infrastructure consists of:

```
┌─────────────────────────────────────────────────────────────┐
│                      Cloud Infrastructure                     │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │              │  │              │  │              │      │
│  │  Web Backend │◄─┤  PostgreSQL  │  │    Redis     │      │
│  │   (FastAPI)  │  │   Database   │  │   (Cache)    │      │
│  │              │  │              │  │              │      │
│  └──────┬───────┘  └──────────────┘  └──────────────┘      │
│         │                                                     │
│         ├─────► GitHub OAuth                                │
│         ├─────► GitLab OAuth                                │
│         └─────► User Git Repositories                       │
│                                                               │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
   ┌──────────────┐
   │ Web Frontend │
   │  (React SPA) │
   └──────────────┘
```

**Key Components:**

- **Web Backend**: FastAPI server handling API requests, authentication, and agent orchestration
- **PostgreSQL**: User accounts, repository links, and metadata storage
- **Redis**: Usage tracking, rate limiting, and session caching
- **Web Frontend**: React-based UI for cloud users

---

## Prerequisites

### Required Accounts

1. **Cloud Platform Account** (choose one):
   - AWS (recommended for production)
   - Google Cloud Platform
   - Azure
   - DigitalOcean (easiest for getting started)

2. **Git Provider Accounts**:
   - GitHub account (for OAuth integration)
   - GitLab account (optional, for GitLab OAuth)

3. **Domain Name** (optional but recommended):
   - For production deployments with SSL/TLS
   - Required for OAuth callback URLs

### Required Tools

Install the following CLI tools:

```bash
# Docker and Docker Compose
docker --version  # Should be 20.10+
docker-compose --version  # Should be 1.29+

# kubectl (for Kubernetes deployments)
kubectl version --client  # Should be 1.27+

# Cloud provider CLI (choose one)
aws --version        # AWS CLI
gcloud --version     # Google Cloud CLI
az --version         # Azure CLI
doctl version        # DigitalOcean CLI

# Git
git --version

# OpenSSL (for generating secrets)
openssl version
```

### System Requirements

**Minimum (Development/Testing):**
- 2 vCPUs
- 4GB RAM
- 20GB storage

**Recommended (Production):**
- 4+ vCPUs
- 8GB+ RAM
- 50GB+ storage
- Load balancer
- Managed database service

---

## Quick Start

For testing or development, use Docker Compose for a local cloud stack:

```bash
# 1. Clone repository
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude

# 2. Navigate to web backend
cd apps/web-backend

# 3. Copy and configure environment
cp .env.example .env
# Edit .env with your settings (see below)

# 4. Generate secure secret key
export SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env

# 5. Start the cloud stack
docker-compose -f docker-compose.cloud.yml up -d

# 6. Run database migrations
docker-compose -f docker-compose.cloud.yml exec web-backend alembic upgrade head

# 7. Verify services are running
docker-compose -f docker-compose.cloud.yml ps
```

Access the API at `http://localhost:8000` and check health at `http://localhost:8000/health`.

---

## Detailed Setup Steps

### 1. Cloud Platform Setup

#### Option A: Docker Compose (Development/Testing)

**Advantages**: Easiest to set up, runs on any machine with Docker

```bash
# Ensure Docker is running
docker info

# Clone and navigate to project
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude/apps/web-backend
```

#### Option B: Kubernetes (Production)

**Advantages**: Scalable, highly available, production-ready

Choose a managed Kubernetes service:

**AWS EKS:**
```bash
# Create EKS cluster
eksctl create cluster \
  --name autoclaude-cluster \
  --region us-east-1 \
  --nodegroup-name standard-workers \
  --node-type t3.medium \
  --nodes 3 \
  --nodes-min 2 \
  --nodes-max 5

# Configure kubectl
aws eks update-kubeconfig --region us-east-1 --name autoclaude-cluster
```

**Google GKE:**
```bash
# Create GKE cluster
gcloud container clusters create autoclaude-cluster \
  --zone us-central1-a \
  --machine-type n1-standard-2 \
  --num-nodes 3 \
  --enable-autoscaling \
  --min-nodes 2 \
  --max-nodes 5

# Get credentials
gcloud container clusters get-credentials autoclaude-cluster --zone us-central1-a
```

**DigitalOcean Kubernetes:**
```bash
# Create DOKS cluster via CLI
doctl kubernetes cluster create autoclaude-cluster \
  --region nyc1 \
  --version latest \
  --size s-2vcpu-4gb \
  --count 3

# Get kubeconfig
doctl kubernetes cluster kubeconfig save autoclaude-cluster
```

**Verify cluster access:**
```bash
kubectl cluster-info
kubectl get nodes
```

---

### 2. OAuth Provider Configuration

You need to register OAuth applications with your Git providers to enable repository access.

#### GitHub OAuth Setup

1. **Navigate to GitHub Developer Settings:**
   - Go to https://github.com/settings/developers
   - Click "OAuth Apps" → "New OAuth App"

2. **Fill in application details:**
   - **Application name**: `Auto Claude Cloud`
   - **Homepage URL**: `https://your-domain.com` (or `http://localhost:8000` for testing)
   - **Authorization callback URL**: `https://your-domain.com/api/git/github/callback`
   - Click "Register application"

3. **Save credentials:**
   - Copy the **Client ID**
   - Generate a new **Client Secret** and copy it
   - Keep these secure - you'll need them for environment configuration

#### GitLab OAuth Setup (Optional)

1. **Navigate to GitLab Applications:**
   - Go to https://gitlab.com/-/profile/applications
   - Click "Add new application"

2. **Fill in application details:**
   - **Name**: `Auto Claude Cloud`
   - **Redirect URI**: `https://your-domain.com/api/git/gitlab/callback`
   - **Scopes**: Select `api`, `read_user`, `read_repository`, `write_repository`
   - Click "Save application"

3. **Save credentials:**
   - Copy the **Application ID**
   - Copy the **Secret**

---

### 3. Environment Configuration

#### Generate Secure Secrets

```bash
# Generate SECRET_KEY for JWT signing
openssl rand -hex 32

# Generate PostgreSQL password
openssl rand -base64 32

# Generate Redis password (optional but recommended)
openssl rand -base64 24
```

#### Configure .env File (Docker Compose)

Create `apps/web-backend/.env` from template:

```bash
cp apps/web-backend/.env.example apps/web-backend/.env
```

Edit `.env` with your configuration:

```env
# =============================================================================
# SERVER CONFIGURATION
# =============================================================================

HOST=0.0.0.0
PORT=8000
DEBUG=false  # CRITICAL: Set to false in production
LOG_LEVEL=INFO

# =============================================================================
# CORS CONFIGURATION
# =============================================================================

# Replace with your frontend domain
CORS_ORIGINS=https://your-frontend-domain.com

# =============================================================================
# AUTHENTICATION & SECURITY
# =============================================================================

# CRITICAL: Replace with generated secret key
SECRET_KEY=<paste-generated-secret-key-here>

# JWT token expiration (in minutes)
ACCESS_TOKEN_EXPIRE_MINUTES=60

# =============================================================================
# DATABASE CONFIGURATION
# =============================================================================

# For Docker Compose deployment
DATABASE_URL=postgresql://postgres:<your-postgres-password>@postgres:5432/autoclaude

# For Kubernetes/managed database
# DATABASE_URL=postgresql://user:password@db-host:5432/autoclaude

# =============================================================================
# REDIS CONFIGURATION
# =============================================================================

# For Docker Compose deployment
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# For Kubernetes/managed Redis
# REDIS_HOST=your-redis-host
# REDIS_PASSWORD=<your-redis-password>

# =============================================================================
# OAUTH CONFIGURATION
# =============================================================================

# GitHub OAuth (from Step 2)
GITHUB_CLIENT_ID=<your-github-client-id>
GITHUB_CLIENT_SECRET=<your-github-client-secret>

# GitLab OAuth (from Step 2, optional)
GITLAB_CLIENT_ID=<your-gitlab-client-id>
GITLAB_CLIENT_SECRET=<your-gitlab-client-secret>

# OAuth redirect URI (must match provider configuration)
OAUTH_REDIRECT_URI=https://your-domain.com/api/git/callback

# =============================================================================
# WEBSOCKET CONFIGURATION
# =============================================================================

WS_HEARTBEAT_INTERVAL=30
```

#### Configure Kubernetes Secrets (Kubernetes Deployment)

Create `infrastructure/k8s/secrets.yaml` from template:

```bash
cp infrastructure/k8s/secrets.example.yaml infrastructure/k8s/secrets.yaml
```

**IMPORTANT**: Never commit `secrets.yaml` to version control!

Edit `secrets.yaml` and base64-encode your secrets:

```bash
# Encode secrets to base64
echo -n 'your-secret-key' | base64
echo -n 'your-postgres-password' | base64
echo -n 'your-github-client-secret' | base64
```

Paste the encoded values into `secrets.yaml`:

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: autoclaude-secrets
type: Opaque
data:
  SECRET_KEY: <base64-encoded-secret-key>
  POSTGRES_PASSWORD: <base64-encoded-postgres-password>
  GITHUB_CLIENT_SECRET: <base64-encoded-github-secret>
  GITLAB_CLIENT_SECRET: <base64-encoded-gitlab-secret>
```

---

### 4. Initial Deployment

#### Deployment with Docker Compose

```bash
cd apps/web-backend

# Start all services
docker-compose -f docker-compose.cloud.yml up -d

# Check service status
docker-compose -f docker-compose.cloud.yml ps

# View logs
docker-compose -f docker-compose.cloud.yml logs -f web-backend

# Expected output:
# autoclaude-postgres    running    5432/tcp
# autoclaude-redis       running    6379/tcp
# autoclaude-backend     running    8000/tcp
```

#### Deployment with Kubernetes

```bash
# Navigate to Kubernetes manifests
cd infrastructure/k8s

# Create namespace (optional)
kubectl create namespace autoclaude
kubectl config set-context --current --namespace=autoclaude

# Apply all manifests
kubectl apply -f secrets.yaml
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods
kubectl get services
kubectl get ingress

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=autoclaude --timeout=300s

# View logs
kubectl logs -l app=autoclaude,component=backend --follow
```

---

### 5. Database Initialization

Initialize the PostgreSQL database with required tables and schema.

#### Docker Compose Deployment

```bash
# Run migrations
docker-compose -f docker-compose.cloud.yml exec web-backend alembic upgrade head

# Verify migrations
docker-compose -f docker-compose.cloud.yml exec web-backend alembic current

# Expected output:
# INFO  [alembic.runtime.migration] Running upgrade -> 001_create_users
# INFO  [alembic.runtime.migration] Running upgrade 001 -> 002_create_repositories
```

#### Kubernetes Deployment

```bash
# Get the backend pod name
BACKEND_POD=$(kubectl get pods -l app=autoclaude,component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -- alembic upgrade head

# Verify migrations
kubectl exec -it $BACKEND_POD -- alembic current
```

#### Manual Database Verification (Optional)

Connect to PostgreSQL to verify tables:

```bash
# Docker Compose
docker-compose -f docker-compose.cloud.yml exec postgres psql -U postgres -d autoclaude

# Kubernetes
kubectl exec -it $(kubectl get pods -l component=database -o jsonpath='{.items[0].metadata.name}') -- psql -U postgres -d autoclaude
```

Run verification queries:

```sql
-- List all tables
\dt

-- Expected tables:
-- users
-- repositories
-- alembic_version

-- Verify users table structure
\d users

-- Exit
\q
```

---

### 6. Verification

#### Health Check

Test the API health endpoint:

```bash
# Docker Compose
curl http://localhost:8000/health

# Kubernetes (port-forward first)
kubectl port-forward svc/web-backend 8000:8000
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "database": "connected", "redis": "connected"}
```

#### OAuth Status Check

Verify OAuth providers are configured:

```bash
curl http://localhost:8000/api/git/status

# Expected response:
# {
#   "github": {"configured": true},
#   "gitlab": {"configured": true}
# }
```

#### Test User Registration

Create a test user:

```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# Expected response (201 Created):
# {
#   "id": 1,
#   "email": "test@example.com",
#   "is_active": true,
#   "created_at": "2024-02-04T12:00:00Z"
# }
```

#### Test User Login

Authenticate the test user:

```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPassword123!"
  }'

# Expected response (200 OK):
# {
#   "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
#   "token_type": "bearer",
#   "user": {...}
# }
```

#### Usage Tracking Check

Verify usage tracking is working:

```bash
# Make a few API calls, then check usage
curl http://localhost:8000/api/usage/stats

# Expected response:
# {
#   "user_id": 1,
#   "period": "hourly",
#   "stats": [...],
#   "redis_healthy": true
# }
```

---

## Next Steps

✅ **Your cloud infrastructure is now set up!**

### Recommended Actions

1. **Review Security Settings**: See [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md#security-hardening) for production security best practices

2. **Set Up SSL/TLS**: Configure HTTPS for production deployments
   - Let's Encrypt with cert-manager (Kubernetes)
   - CloudFlare or AWS Certificate Manager

3. **Configure Monitoring**: Set up logging and metrics
   - Prometheus + Grafana (Kubernetes)
   - CloudWatch (AWS)
   - Cloud Logging (GCP)

4. **Enable Backups**: Configure automated database backups
   - See [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md#backup-and-disaster-recovery)

5. **Scale Your Deployment**: Increase replicas and resources as needed
   - See [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md#scaling-and-load-balancing)

6. **Test OAuth Flow**: Connect a GitHub/GitLab account through the frontend
   - Navigate to `/settings/git` in the web UI
   - Click "Connect GitHub" and authorize

### Troubleshooting

If you encounter issues, see:
- [CLOUD_DEPLOYMENT.md - Troubleshooting](CLOUD_DEPLOYMENT.md#troubleshooting)
- Check logs: `docker-compose logs -f` or `kubectl logs -f`
- Verify environment variables are set correctly
- Ensure OAuth callback URLs match your configuration

### Get Help

- Documentation: [guides/README.md](README.md)
- GitHub Issues: https://github.com/OBenner/Auto-Coding/issues
- Community Support: Join our Discord

---

**Next**: Read [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) for production deployment, scaling, and operations guidance.
