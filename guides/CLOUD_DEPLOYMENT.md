# Cloud Deployment Guide - Auto Claude

This guide covers deploying, operating, and maintaining Auto Claude's cloud-hosted infrastructure in production environments.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Deployment Methods](#deployment-methods)
  - [Docker Compose Deployment](#docker-compose-deployment)
  - [Kubernetes Deployment](#kubernetes-deployment)
- [Configuration Management](#configuration-management)
- [Security Hardening](#security-hardening)
- [Scaling and Load Balancing](#scaling-and-load-balancing)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [SSL/TLS Configuration](#ssltls-configuration)
- [OAuth Integration](#oauth-integration)
- [Database Management](#database-management)
- [Performance Optimization](#performance-optimization)
- [Troubleshooting](#troubleshooting)
- [Maintenance and Updates](#maintenance-and-updates)
- [Cost Optimization](#cost-optimization)

---

## Overview

Auto Claude's cloud-hosted option provides a fully managed platform where users can access Auto Claude without local installation. This guide focuses on production deployment and operations.

**Key Features:**
- Multi-user authentication and authorization
- Git repository integration (GitHub, GitLab)
- Usage tracking and rate limiting
- Scalable architecture
- High availability support

**Target Audience:**
- DevOps engineers deploying Auto Claude to production
- Platform administrators managing cloud infrastructure
- SREs maintaining uptime and performance

---

## Architecture

### High-Level Architecture

```
                          ┌─────────────────┐
                          │   Users/Web UI  │
                          └────────┬────────┘
                                   │ HTTPS
                          ┌────────▼────────┐
                          │  Load Balancer  │
                          │  (TLS/SSL)      │
                          └────────┬────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
        ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
        │  Backend    │    │  Backend    │    │  Backend    │
        │  Instance 1 │    │  Instance 2 │    │  Instance N │
        └──────┬──────┘    └──────┬──────┘    └──────┬──────┘
               │                   │                   │
               └───────────────────┼───────────────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
        ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
        │ PostgreSQL  │    │    Redis    │    │  Git OAuth  │
        │  (Primary)  │    │   (Cache)   │    │  Providers  │
        └─────────────┘    └─────────────┘    └─────────────┘
               │
        ┌──────▼──────┐
        │ PostgreSQL  │
        │  (Replica)  │
        └─────────────┘
```

### Component Responsibilities

| Component | Purpose | Scalability | State |
|-----------|---------|-------------|-------|
| **Web Backend** | API server, authentication, agent orchestration | Horizontal (stateless) | Stateless |
| **PostgreSQL** | User data, repositories, metadata | Vertical, read replicas | Stateful |
| **Redis** | Usage tracking, rate limiting, sessions | Horizontal (cluster mode) | In-memory |
| **Load Balancer** | Traffic distribution, SSL termination | Managed service | Stateless |

### Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Public Internet                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
         ┌─────────────▼──────────────┐
         │   Ingress / Load Balancer  │  (Public IP)
         │   - SSL/TLS Termination    │
         │   - Rate Limiting          │
         └─────────────┬──────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│  Application Tier    │                                       │
│                      │                                       │
│     ┌────────────────▼────────────────┐                     │
│     │  Web Backend Service            │                     │
│     │  - Port 8000 (internal)         │                     │
│     │  - Multiple replicas            │                     │
│     └────────────────┬────────────────┘                     │
│                      │                                       │
└──────────────────────┼──────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│  Data Tier           │                                       │
│                      │                                       │
│     ┌────────────────▼───────┐  ┌────────────────────────┐ │
│     │  PostgreSQL Service    │  │   Redis Service        │ │
│     │  - Port 5432 (internal)│  │   - Port 6379 (internal)│ │
│     │  - Private subnet      │  │   - Private subnet     │ │
│     └────────────────────────┘  └────────────────────────┘ │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## Deployment Methods

### Docker Compose Deployment

**Best for:** Development, staging, small-scale production

#### Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- 4GB+ RAM
- 20GB+ storage

#### Deployment Steps

1. **Clone repository and navigate to backend:**

```bash
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude/apps/web-backend
```

2. **Configure environment variables:**

```bash
cp .env.example .env
# Edit .env with production settings (see Configuration Management section)
```

3. **Generate secure secrets:**

```bash
# Generate SECRET_KEY
export SECRET_KEY=$(openssl rand -hex 32)
echo "SECRET_KEY=$SECRET_KEY" >> .env

# Generate database password
export POSTGRES_PASSWORD=$(openssl rand -base64 32)
echo "DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/autoclaude" >> .env
```

4. **Start services:**

```bash
# Pull latest images
docker-compose -f docker-compose.cloud.yml pull

# Start in detached mode
docker-compose -f docker-compose.cloud.yml up -d

# Check status
docker-compose -f docker-compose.cloud.yml ps
```

5. **Run database migrations:**

```bash
docker-compose -f docker-compose.cloud.yml exec web-backend alembic upgrade head
```

6. **Verify deployment:**

```bash
curl http://localhost:8000/health
# Expected: {"status": "healthy", "database": "connected", "redis": "connected"}
```

#### Production Docker Compose Configuration

For production, modify `docker-compose.cloud.yml`:

```yaml
services:
  web-backend:
    # Use specific version tags, not 'latest'
    image: autoclaude/web-backend:v1.0.0

    # Restart policy for high availability
    restart: always

    # Resource limits
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G

    # Health check
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

    # Logging
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

#### Updating with Docker Compose

```bash
# Pull latest images
docker-compose -f docker-compose.cloud.yml pull

# Recreate containers with new images
docker-compose -f docker-compose.cloud.yml up -d

# Run migrations if needed
docker-compose -f docker-compose.cloud.yml exec web-backend alembic upgrade head
```

---

### Kubernetes Deployment

**Best for:** Production at scale, high availability, enterprise deployments

#### Prerequisites

- Kubernetes cluster 1.27+
- kubectl configured
- Helm 3+ (optional but recommended)
- Ingress controller (NGINX, Traefik, etc.)
- cert-manager (for SSL/TLS)

#### Deployment Architecture

```
Kubernetes Cluster
├── Namespace: autoclaude
├── ConfigMap: autoclaude-config (non-sensitive config)
├── Secret: autoclaude-secrets (sensitive credentials)
├── PersistentVolumeClaim: postgres-pvc (10Gi)
├── PersistentVolumeClaim: redis-pvc (5Gi)
├── Deployment: postgres (1 replica, stateful)
├── Deployment: redis (1 replica, stateful)
├── Deployment: web-backend (2+ replicas, stateless)
├── Service: postgres (ClusterIP, internal)
├── Service: redis (ClusterIP, internal)
├── Service: web-backend (LoadBalancer, external)
└── Ingress: autoclaude-ingress (HTTPS, TLS)
```

#### Quick Deploy

```bash
# Navigate to Kubernetes manifests
cd infrastructure/k8s

# Create namespace
kubectl create namespace autoclaude

# Set default namespace
kubectl config set-context --current --namespace=autoclaude

# Create secrets (edit secrets.yaml first!)
kubectl apply -f secrets.yaml

# Deploy all resources
kubectl apply -f configmap.yaml
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl apply -f ingress.yaml

# Wait for pods to be ready
kubectl wait --for=condition=ready pod -l app=autoclaude --timeout=300s

# Check status
kubectl get pods
kubectl get services
kubectl get ingress
```

#### Step-by-Step Kubernetes Deployment

**1. Create and Configure Secrets**

```bash
# Copy template
cp secrets.example.yaml secrets.yaml

# Generate base64-encoded secrets
echo -n 'your-secret-key' | base64
echo -n 'your-postgres-password' | base64
echo -n 'your-github-client-secret' | base64

# Edit secrets.yaml with encoded values
vim secrets.yaml

# Apply secrets
kubectl apply -f secrets.yaml

# Verify (values will be hidden)
kubectl get secrets autoclaude-secrets
```

**2. Deploy ConfigMap**

```bash
# Review configmap.yaml and update values
vim configmap.yaml

# Apply ConfigMap
kubectl apply -f configmap.yaml

# Verify
kubectl describe configmap autoclaude-config
```

**3. Deploy Database (PostgreSQL)**

```bash
# Apply deployment (includes PVC)
kubectl apply -f deployment.yaml

# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l component=database --timeout=300s

# Check logs
kubectl logs -l component=database --tail=50
```

**4. Initialize Database**

```bash
# Get backend pod name
BACKEND_POD=$(kubectl get pods -l component=backend -o jsonpath='{.items[0].metadata.name}')

# Run migrations
kubectl exec -it $BACKEND_POD -- alembic upgrade head

# Verify migrations
kubectl exec -it $BACKEND_POD -- alembic current
```

**5. Deploy Services**

```bash
# Apply all services
kubectl apply -f service.yaml

# Verify services
kubectl get services

# Expected output:
# NAME           TYPE           CLUSTER-IP      EXTERNAL-IP     PORT(S)
# postgres       ClusterIP      10.x.x.x        <none>          5432/TCP
# redis          ClusterIP      10.x.x.x        <none>          6379/TCP
# web-backend    LoadBalancer   10.x.x.x        <pending>       8000:30000/TCP
```

**6. Deploy Ingress (SSL/TLS)**

Requires cert-manager for automatic SSL certificates:

```bash
# Install cert-manager (if not already installed)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=ready pod -n cert-manager -l app=cert-manager --timeout=300s

# Apply ingress
kubectl apply -f ingress.yaml

# Check ingress status
kubectl get ingress autoclaude-ingress

# Check certificate status
kubectl get certificate autoclaude-tls
```

**7. Verify Deployment**

```bash
# Get external IP or hostname
EXTERNAL_IP=$(kubectl get ingress autoclaude-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl http://$EXTERNAL_IP/health

# Or with domain (after DNS is configured)
curl https://your-domain.com/health
```

#### Scaling Backend Replicas

```bash
# Scale to 5 replicas
kubectl scale deployment web-backend --replicas=5

# Verify scaling
kubectl get pods -l component=backend

# Auto-scaling (HPA)
kubectl autoscale deployment web-backend --min=2 --max=10 --cpu-percent=80

# Check HPA status
kubectl get hpa
```

---

## Configuration Management

### Environment Variables Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `HOST` | Server bind address | `0.0.0.0` | No |
| `PORT` | Server port | `8000` | No |
| `DEBUG` | Debug mode (NEVER true in production) | `false` | No |
| `LOG_LEVEL` | Logging verbosity | `INFO` | No |
| `SECRET_KEY` | JWT signing key | - | **Yes** |
| `DATABASE_URL` | PostgreSQL connection string | - | **Yes** |
| `REDIS_HOST` | Redis hostname | `localhost` | No |
| `REDIS_PORT` | Redis port | `6379` | No |
| `REDIS_DB` | Redis database number | `0` | No |
| `REDIS_PASSWORD` | Redis password | `` | No |
| `CORS_ORIGINS` | Allowed frontend origins | - | **Yes** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT expiration time | `30` | No |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | - | **Yes** |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret | - | **Yes** |
| `GITLAB_CLIENT_ID` | GitLab OAuth client ID | - | No |
| `GITLAB_CLIENT_SECRET` | GitLab OAuth secret | - | No |
| `OAUTH_REDIRECT_URI` | OAuth callback URL | - | **Yes** |
| `WS_HEARTBEAT_INTERVAL` | WebSocket heartbeat interval (seconds) | `30` | No |

### Production Environment Template

```env
# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# Security - CRITICAL: Use secure values!
SECRET_KEY=<64-character-hex-string>

# Database
DATABASE_URL=postgresql://autoclaude:<strong-password>@db-host:5432/autoclaude

# Redis
REDIS_HOST=redis-host
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=<strong-password>

# CORS - Restrict to your domain
CORS_ORIGINS=https://app.yourdomain.com

# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=60

# GitHub OAuth
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_CLIENT_SECRET=<your-client-secret>

# GitLab OAuth (optional)
GITLAB_CLIENT_ID=<your-client-id>
GITLAB_CLIENT_SECRET=<your-client-secret>

# OAuth Callback
OAUTH_REDIRECT_URI=https://api.yourdomain.com/api/git/callback

# WebSocket
WS_HEARTBEAT_INTERVAL=30
```

### Secrets Management Best Practices

1. **Never commit secrets to version control:**
   ```bash
   # Add to .gitignore
   echo ".env" >> .gitignore
   echo "secrets.yaml" >> .gitignore
   ```

2. **Use secrets management tools:**
   - **AWS**: AWS Secrets Manager, Parameter Store
   - **GCP**: Secret Manager
   - **Azure**: Key Vault
   - **Kubernetes**: External Secrets Operator

3. **Rotate secrets regularly:**
   ```bash
   # Generate new SECRET_KEY
   NEW_SECRET=$(openssl rand -hex 32)

   # Update in Kubernetes secret
   kubectl create secret generic autoclaude-secrets \
     --from-literal=SECRET_KEY=$NEW_SECRET \
     --dry-run=client -o yaml | kubectl apply -f -

   # Rolling restart to pick up new secret
   kubectl rollout restart deployment web-backend
   ```

4. **Principle of least privilege:**
   - Separate secrets for different environments (dev, staging, prod)
   - Use separate OAuth apps per environment
   - Restrict database user permissions

---

## Security Hardening

### SSL/TLS Configuration

**Let's Encrypt with cert-manager (Kubernetes):**

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: autoclaude-ingress
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: autoclaude-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: web-backend
            port:
              number: 8000
```

**Create ClusterIssuer:**

```yaml
# letsencrypt-issuer.yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@yourdomain.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

```bash
kubectl apply -f letsencrypt-issuer.yaml
```

### Network Security

**1. Network Policies (Kubernetes):**

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: web-backend-policy
spec:
  podSelector:
    matchLabels:
      component: backend
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          component: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          component: redis
    ports:
    - protocol: TCP
      port: 6379
```

**2. Firewall Rules:**

```bash
# AWS Security Groups
aws ec2 authorize-security-group-ingress \
  --group-id sg-xxxxx \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0

# GCP Firewall
gcloud compute firewall-rules create allow-https \
  --allow tcp:443 \
  --source-ranges 0.0.0.0/0
```

### Application Security

**1. Rate Limiting (built-in):**

```python
# Already implemented in apps/web-backend/services/usage_tracker.py
# Configure in core/middleware.py:

middleware.add_middleware(
    UsageTrackingMiddleware,
    enable_rate_limiting=True,
    rate_limit_requests=100,  # requests per minute
    rate_limit_period=60
)
```

**2. CORS Configuration:**

```env
# Strict CORS for production
CORS_ORIGINS=https://app.yourdomain.com,https://www.yourdomain.com
```

**3. Security Headers (Ingress):**

```yaml
# ingress.yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/configuration-snippet: |
      more_set_headers "X-Frame-Options: DENY";
      more_set_headers "X-Content-Type-Options: nosniff";
      more_set_headers "X-XSS-Protection: 1; mode=block";
      more_set_headers "Strict-Transport-Security: max-age=31536000; includeSubDomains";
```

**4. Database Security:**

```sql
-- Create limited user for application
CREATE USER autoclaude WITH PASSWORD '<strong-password>';
GRANT CONNECT ON DATABASE autoclaude TO autoclaude;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO autoclaude;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO autoclaude;

-- Revoke dangerous permissions
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
```

### Security Checklist

- [ ] SSL/TLS enabled with valid certificate
- [ ] Strong `SECRET_KEY` (64+ characters, random)
- [ ] Database user has minimal permissions
- [ ] `DEBUG=false` in production
- [ ] CORS restricted to specific domains
- [ ] Rate limiting enabled
- [ ] Network policies in place (Kubernetes)
- [ ] Security headers configured
- [ ] Secrets stored securely (not in code)
- [ ] OAuth redirect URIs whitelisted
- [ ] Regular security updates scheduled

---

## Scaling and Load Balancing

### Horizontal Scaling (Backend)

**Kubernetes:**

```bash
# Manual scaling
kubectl scale deployment web-backend --replicas=5

# Auto-scaling based on CPU
kubectl autoscale deployment web-backend \
  --cpu-percent=70 \
  --min=2 \
  --max=10

# Auto-scaling based on memory
kubectl autoscale deployment web-backend \
  --memory-percent=80 \
  --min=2 \
  --max=10

# Check HPA status
kubectl get hpa
```

**Docker Compose (Swarm Mode):**

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.cloud.yml autoclaude

# Scale service
docker service scale autoclaude_web-backend=5

# Check service status
docker service ps autoclaude_web-backend
```

### Database Scaling

**Read Replicas (PostgreSQL):**

```yaml
# postgres-replica.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-replica
spec:
  replicas: 1
  template:
    spec:
      containers:
      - name: postgres
        image: postgres:16-alpine
        env:
        - name: POSTGRES_MASTER_HOST
          value: "postgres"
        - name: POSTGRES_REPLICA_MODE
          value: "replica"
```

**Connection Pooling (PgBouncer):**

```yaml
# pgbouncer.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: pgbouncer
spec:
  template:
    spec:
      containers:
      - name: pgbouncer
        image: pgbouncer/pgbouncer:latest
        env:
        - name: POOL_MODE
          value: "transaction"
        - name: MAX_CLIENT_CONN
          value: "1000"
        - name: DEFAULT_POOL_SIZE
          value: "25"
```

Update `DATABASE_URL` to use PgBouncer:
```env
DATABASE_URL=postgresql://user:pass@pgbouncer:6432/autoclaude
```

### Redis Scaling

**Redis Cluster Mode:**

```yaml
# redis-cluster.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: redis-cluster
spec:
  serviceName: redis-cluster
  replicas: 6  # 3 masters + 3 replicas
  template:
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command:
        - redis-server
        - --cluster-enabled yes
        - --cluster-config-file nodes.conf
        - --cluster-node-timeout 5000
        - --appendonly yes
```

### Load Balancer Configuration

**AWS ALB (Application Load Balancer):**

```bash
# Create target group
aws elbv2 create-target-group \
  --name autoclaude-backend \
  --protocol HTTP \
  --port 8000 \
  --vpc-id vpc-xxxxx \
  --health-check-path /health \
  --health-check-interval-seconds 30

# Create load balancer
aws elbv2 create-load-balancer \
  --name autoclaude-alb \
  --subnets subnet-xxxxx subnet-yyyyy \
  --security-groups sg-xxxxx
```

**NGINX Load Balancer:**

```nginx
# nginx.conf
upstream backend {
    least_conn;  # Connection-based load balancing
    server backend1:8000 max_fails=3 fail_timeout=30s;
    server backend2:8000 max_fails=3 fail_timeout=30s;
    server backend3:8000 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.yourdomain.com;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;

        # WebSocket support
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## Monitoring and Logging

### Health Checks

**Built-in Health Endpoint:**

```bash
# Check application health
curl http://localhost:8000/health

# Expected response:
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "timestamp": "2024-02-04T12:00:00Z"
}
```

**Kubernetes Liveness and Readiness Probes:**

Already configured in `deployment.yaml`:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3
```

### Application Logging

**Configure Log Level:**

```env
# Environment variable
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```

**View Logs:**

```bash
# Docker Compose
docker-compose -f docker-compose.cloud.yml logs -f web-backend

# Kubernetes
kubectl logs -f deployment/web-backend

# Kubernetes (all replicas)
kubectl logs -f -l component=backend

# Kubernetes (previous container, for crashloop debugging)
kubectl logs --previous deployment/web-backend
```

### Centralized Logging

**ELK Stack (Elasticsearch, Logstash, Kibana):**

```yaml
# filebeat-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: container
      paths:
        - /var/log/containers/*-backend-*.log
      processors:
      - add_kubernetes_metadata:
          host: ${NODE_NAME}
          matchers:
          - logs_path:
              logs_path: "/var/log/containers/"

    output.elasticsearch:
      hosts: ['${ELASTICSEARCH_HOST:elasticsearch}:${ELASTICSEARCH_PORT:9200}']
```

**Prometheus + Grafana (Metrics):**

```yaml
# prometheus-servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: autoclaude-backend
spec:
  selector:
    matchLabels:
      app: autoclaude
      component: backend
  endpoints:
  - port: metrics
    interval: 30s
```

**CloudWatch (AWS):**

```yaml
# deployment.yaml
spec:
  template:
    spec:
      containers:
      - name: web-backend
        env:
        - name: AWS_REGION
          value: "us-east-1"
        - name: CLOUDWATCH_LOG_GROUP
          value: "/ecs/autoclaude-backend"
```

### Metrics and Monitoring

**Key Metrics to Monitor:**

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| **Request Rate** | Requests per second | >1000 req/s |
| **Response Time** | Avg API response time | >500ms |
| **Error Rate** | 5xx errors per minute | >1% |
| **CPU Usage** | Backend pod CPU % | >80% |
| **Memory Usage** | Backend pod memory % | >85% |
| **Database Connections** | Active DB connections | >80% of max |
| **Redis Memory** | Redis memory usage | >90% |
| **WebSocket Connections** | Active WS connections | Monitor trend |

**Prometheus Queries:**

```promql
# Request rate
rate(http_requests_total[5m])

# Error rate
rate(http_requests_total{status=~"5.."}[5m])

# Response time (p95)
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# Pod CPU usage
container_cpu_usage_seconds_total{pod=~"web-backend.*"}

# Pod memory usage
container_memory_usage_bytes{pod=~"web-backend.*"}
```

### Alerting

**Prometheus AlertManager Example:**

```yaml
# alerts.yaml
groups:
- name: autoclaude
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value | humanize }}% over 5 minutes"

  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes{pod=~"web-backend.*"} / container_spec_memory_limit_bytes > 0.85
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage on {{ $labels.pod }}"

  - alert: DatabaseDown
    expr: up{job="postgres"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "PostgreSQL database is down"
```

---

## Backup and Disaster Recovery

### Database Backups

**Automated PostgreSQL Backups (Kubernetes CronJob):**

```yaml
# postgres-backup-cronjob.yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: postgres-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: pg-backup
            image: postgres:16-alpine
            command:
            - sh
            - -c
            - |
              BACKUP_FILE="/backups/backup-$(date +%Y%m%d-%H%M%S).sql.gz"
              pg_dump -h $POSTGRES_HOST -U $POSTGRES_USER $POSTGRES_DB | gzip > $BACKUP_FILE
              echo "Backup completed: $BACKUP_FILE"
            env:
            - name: POSTGRES_HOST
              value: "postgres"
            - name: POSTGRES_USER
              value: "postgres"
            - name: POSTGRES_PASSWORD
              valueFrom:
                secretKeyRef:
                  name: autoclaude-secrets
                  key: POSTGRES_PASSWORD
            - name: POSTGRES_DB
              value: "autoclaude"
            volumeMounts:
            - name: backup-storage
              mountPath: /backups
          restartPolicy: OnFailure
          volumes:
          - name: backup-storage
            persistentVolumeClaim:
              claimName: backup-pvc
```

**Manual Backup:**

```bash
# Docker Compose
docker-compose -f docker-compose.cloud.yml exec postgres \
  pg_dump -U postgres autoclaude | gzip > backup-$(date +%Y%m%d).sql.gz

# Kubernetes
kubectl exec -it $(kubectl get pods -l component=database -o jsonpath='{.items[0].metadata.name}') \
  -- pg_dump -U postgres autoclaude | gzip > backup-$(date +%Y%m%d).sql.gz
```

**Restore from Backup:**

```bash
# Docker Compose
gunzip < backup-20240204.sql.gz | \
  docker-compose -f docker-compose.cloud.yml exec -T postgres \
  psql -U postgres autoclaude

# Kubernetes
gunzip < backup-20240204.sql.gz | \
  kubectl exec -i $(kubectl get pods -l component=database -o jsonpath='{.items[0].metadata.name}') \
  -- psql -U postgres autoclaude
```

### Redis Persistence

**AOF (Append-Only File):**

Already configured in `docker-compose.cloud.yml`:

```yaml
redis:
  command: redis-server --appendonly yes
  volumes:
    - redis_data:/data
```

**RDB Snapshots:**

```yaml
redis:
  command: redis-server --appendonly yes --save 60 1000
  # Save if 1000 keys changed in 60 seconds
```

**Manual Redis Backup:**

```bash
# Docker Compose
docker-compose -f docker-compose.cloud.yml exec redis redis-cli BGSAVE
docker cp autoclaude-redis:/data/dump.rdb ./redis-backup-$(date +%Y%m%d).rdb

# Kubernetes
kubectl exec -it $(kubectl get pods -l component=redis -o jsonpath='{.items[0].metadata.name}') \
  -- redis-cli BGSAVE
```

### Disaster Recovery Plan

**1. Regular Backups:**
- Database: Daily automated backups, retained for 30 days
- Redis: AOF persistence + weekly RDB snapshots
- Configuration: Version controlled in Git

**2. Recovery Time Objective (RTO):**
- Target: < 1 hour for full recovery
- Critical services: < 15 minutes

**3. Recovery Point Objective (RPO):**
- Database: < 24 hours (daily backups)
- Redis: < 1 hour (AOF persistence)

**4. Disaster Recovery Runbook:**

```bash
# Step 1: Deploy infrastructure
kubectl apply -f infrastructure/k8s/

# Step 2: Restore database
gunzip < latest-backup.sql.gz | kubectl exec -i <postgres-pod> -- psql -U postgres autoclaude

# Step 3: Verify database
kubectl exec -it <postgres-pod> -- psql -U postgres autoclaude -c "\dt"

# Step 4: Run health checks
curl https://api.yourdomain.com/health

# Step 5: Verify OAuth status
curl https://api.yourdomain.com/api/git/status

# Step 6: Monitor logs
kubectl logs -f -l component=backend
```

---

## SSL/TLS Configuration

See [Security Hardening](#security-hardening) section for Let's Encrypt with cert-manager.

### Custom SSL Certificates

**Kubernetes:**

```bash
# Create TLS secret from existing certificate
kubectl create secret tls autoclaude-tls \
  --cert=path/to/tls.crt \
  --key=path/to/tls.key

# Update ingress to use the secret
# (already configured in ingress.yaml)
```

**Docker Compose with NGINX:**

```yaml
# docker-compose.cloud.yml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl/cert.pem:/etc/nginx/ssl/cert.pem:ro
      - ./ssl/key.pem:/etc/nginx/ssl/key.pem:ro
```

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /etc/nginx/ssl/cert.pem;
    ssl_certificate_key /etc/nginx/ssl/key.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    location / {
        proxy_pass http://web-backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## OAuth Integration

### GitHub OAuth Configuration

**Production Setup:**

1. Register OAuth App at https://github.com/settings/developers
2. Configure:
   - **Homepage URL**: `https://yourdomain.com`
   - **Authorization callback URL**: `https://api.yourdomain.com/api/git/github/callback`

3. Update environment:
```env
GITHUB_CLIENT_ID=<your-client-id>
GITHUB_CLIENT_SECRET=<your-client-secret>
OAUTH_REDIRECT_URI=https://api.yourdomain.com/api/git/callback
```

### GitLab OAuth Configuration

**Production Setup:**

1. Register application at https://gitlab.com/-/profile/applications
2. Configure:
   - **Redirect URI**: `https://api.yourdomain.com/api/git/gitlab/callback`
   - **Scopes**: `api`, `read_user`, `read_repository`, `write_repository`

3. Update environment:
```env
GITLAB_CLIENT_ID=<your-application-id>
GITLAB_CLIENT_SECRET=<your-secret>
```

### Testing OAuth Flow

```bash
# 1. Initiate GitHub OAuth
curl -L https://api.yourdomain.com/api/git/github/authorize

# 2. After authorization, verify callback works
# (callback URL will be called by GitHub with code parameter)

# 3. Check OAuth status
curl https://api.yourdomain.com/api/git/status

# Expected response:
{
  "github": {"configured": true, "available": true},
  "gitlab": {"configured": true, "available": true}
}
```

---

## Database Management

### Running Migrations

**Create New Migration:**

```bash
# Docker Compose
docker-compose -f docker-compose.cloud.yml exec web-backend \
  alembic revision --autogenerate -m "Add new feature"

# Kubernetes
kubectl exec -it $(kubectl get pods -l component=backend -o jsonpath='{.items[0].metadata.name}') \
  -- alembic revision --autogenerate -m "Add new feature"
```

**Apply Migrations:**

```bash
# Docker Compose
docker-compose -f docker-compose.cloud.yml exec web-backend alembic upgrade head

# Kubernetes
kubectl exec -it $(kubectl get pods -l component=backend -o jsonpath='{.items[0].metadata.name}') \
  -- alembic upgrade head
```

**Rollback Migration:**

```bash
# Downgrade one version
alembic downgrade -1

# Downgrade to specific version
alembic downgrade <revision>
```

### Database Maintenance

**Vacuum (PostgreSQL):**

```bash
# Full vacuum
kubectl exec -it <postgres-pod> -- psql -U postgres autoclaude -c "VACUUM FULL;"

# Analyze tables
kubectl exec -it <postgres-pod> -- psql -U postgres autoclaude -c "ANALYZE;"
```

**Check Database Size:**

```sql
-- Connect to database
kubectl exec -it <postgres-pod> -- psql -U postgres autoclaude

-- Check database size
SELECT pg_size_pretty(pg_database_size('autoclaude'));

-- Check table sizes
SELECT
  schemaname,
  tablename,
  pg_size_pretty(pg_total_relation_size(schemaname || '.' || tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname || '.' || tablename) DESC;
```

---

## Performance Optimization

### Application-Level Optimization

**1. Connection Pooling:**

Already implemented in `apps/web-backend/core/database.py`:

```python
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=20,  # Max connections in pool
    max_overflow=10,  # Additional connections when pool is full
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600  # Recycle connections after 1 hour
)
```

**2. Redis Caching:**

```python
# Example: Cache expensive queries
from services.usage_tracker import UsageTracker

@app.get("/api/expensive-operation")
async def expensive_operation():
    cache_key = "expensive:result"

    # Try cache first
    cached = await redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Compute result
    result = perform_expensive_operation()

    # Cache for 1 hour
    await redis_client.setex(cache_key, 3600, json.dumps(result))
    return result
```

**3. Database Query Optimization:**

```python
# Use eager loading to avoid N+1 queries
from sqlalchemy.orm import joinedload

users = db.query(User).options(joinedload(User.repositories)).all()

# Create indexes for frequently queried columns
# In migration file:
op.create_index('idx_users_email', 'users', ['email'])
op.create_index('idx_repositories_user_id', 'repositories', ['user_id'])
```

### Infrastructure Optimization

**1. Enable HTTP/2:**

```yaml
# ingress.yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/http2-push-preload: "true"
```

**2. Enable Compression:**

```yaml
# ingress.yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/enable-compression: "true"
    nginx.ingress.kubernetes.io/compression-types: "application/json text/plain"
```

**3. CDN Integration:**

Use CloudFlare, CloudFront, or similar for:
- Static asset caching
- DDoS protection
- Global distribution

---

## Troubleshooting

### Common Issues

#### 1. Pod Stuck in Pending State

**Symptoms:** Pods show `Pending` status indefinitely

**Diagnosis:**

```bash
kubectl describe pod <pod-name>
```

**Common Causes:**
- Insufficient resources (CPU/memory)
- PVC not bound
- Node selector mismatch

**Solution:**

```bash
# Check node resources
kubectl describe nodes

# Check PVC status
kubectl get pvc

# Increase resources or add nodes
kubectl scale nodes --replicas=4
```

#### 2. Database Connection Errors

**Symptoms:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Diagnosis:**

```bash
# Check PostgreSQL pod
kubectl get pods -l component=database
kubectl logs -l component=database

# Test connection from backend pod
kubectl exec -it <backend-pod> -- psql -h postgres -U postgres -d autoclaude
```

**Common Causes:**
- PostgreSQL not ready
- Wrong credentials
- Network policy blocking connection

**Solution:**

```bash
# Wait for PostgreSQL to be ready
kubectl wait --for=condition=ready pod -l component=database --timeout=300s

# Verify secrets
kubectl get secret autoclaude-secrets -o yaml

# Check network connectivity
kubectl exec -it <backend-pod> -- nc -zv postgres 5432
```

#### 3. OAuth Redirect Mismatch

**Symptoms:** `redirect_uri_mismatch` error during GitHub/GitLab OAuth

**Diagnosis:**

```bash
# Check OAuth configuration
curl http://localhost:8000/api/git/status

# Check environment variables
kubectl exec -it <backend-pod> -- env | grep OAUTH
```

**Solution:**

1. Verify `OAUTH_REDIRECT_URI` matches GitHub/GitLab configuration
2. Ensure protocol (http vs https) matches
3. Check for trailing slashes

```env
# Correct
OAUTH_REDIRECT_URI=https://api.yourdomain.com/api/git/callback

# Wrong
OAUTH_REDIRECT_URI=https://api.yourdomain.com/api/git/callback/
```

#### 4. High Memory Usage

**Symptoms:** Pods being OOMKilled

**Diagnosis:**

```bash
# Check memory usage
kubectl top pods

# Check memory limits
kubectl describe pod <pod-name> | grep -A 5 Limits
```

**Solution:**

```bash
# Increase memory limits in deployment.yaml
resources:
  limits:
    memory: "4Gi"  # Increase from 2Gi
  requests:
    memory: "2Gi"  # Increase from 1Gi

# Apply changes
kubectl apply -f deployment.yaml
```

#### 5. Redis Connection Timeout

**Symptoms:** `redis.exceptions.TimeoutError` in logs

**Diagnosis:**

```bash
# Check Redis status
kubectl exec -it <redis-pod> -- redis-cli ping

# Check Redis memory
kubectl exec -it <redis-pod> -- redis-cli info memory
```

**Solution:**

```bash
# Restart Redis
kubectl rollout restart deployment redis

# Check if Redis is reaching max memory
kubectl exec -it <redis-pod> -- redis-cli CONFIG GET maxmemory

# Increase Redis memory limit if needed
```

### Debug Mode

**Enable debug logging temporarily:**

```bash
# Docker Compose
# Edit .env: LOG_LEVEL=DEBUG
docker-compose -f docker-compose.cloud.yml restart web-backend

# Kubernetes
kubectl set env deployment/web-backend LOG_LEVEL=DEBUG
```

**Revert to INFO level after debugging:**

```bash
kubectl set env deployment/web-backend LOG_LEVEL=INFO
```

---

## Maintenance and Updates

### Rolling Updates (Kubernetes)

```bash
# Update image to new version
kubectl set image deployment/web-backend \
  web-backend=autoclaude/web-backend:v1.1.0

# Monitor rollout status
kubectl rollout status deployment/web-backend

# Rollback if issues occur
kubectl rollout undo deployment/web-backend
```

### Zero-Downtime Deployment

**Kubernetes (automatic with rolling updates):**

Already configured in `deployment.yaml`:

```yaml
spec:
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # One extra pod during update
      maxUnavailable: 0  # Zero downtime
```

**Docker Compose:**

```bash
# Blue-green deployment
docker-compose -f docker-compose.cloud.yml up -d --scale web-backend=2

# Update one instance at a time
docker-compose -f docker-compose.cloud.yml up -d --no-deps web-backend
```

### Maintenance Window

**Schedule Downtime (optional):**

```bash
# 1. Set maintenance mode (custom implementation)
kubectl set env deployment/web-backend MAINTENANCE_MODE=true

# 2. Perform maintenance
kubectl exec -it <postgres-pod> -- psql ...

# 3. Disable maintenance mode
kubectl set env deployment/web-backend MAINTENANCE_MODE=false
```

---

## Cost Optimization

### Resource Right-Sizing

**Monitor actual usage:**

```bash
# Check resource usage over time
kubectl top pods --namespace=autoclaude

# Analyze historical usage (Prometheus)
kubectl port-forward -n monitoring svc/prometheus 9090:9090
# Query: container_memory_usage_bytes{pod=~"web-backend.*"}
```

**Adjust resources:**

```yaml
# Start conservative, increase as needed
resources:
  requests:
    cpu: "500m"
    memory: "1Gi"
  limits:
    cpu: "1000m"
    memory: "2Gi"
```

### Auto-Scaling for Cost Savings

**Scale down during off-hours:**

```bash
# Create CronJob to scale down at night
kubectl create cronjob scale-down \
  --schedule="0 0 * * *" \
  --image=bitnami/kubectl \
  -- kubectl scale deployment web-backend --replicas=1

# Scale up in the morning
kubectl create cronjob scale-up \
  --schedule="0 8 * * *" \
  --image=bitnami/kubectl \
  -- kubectl scale deployment web-backend --replicas=3
```

### Use Spot/Preemptible Instances

**AWS:**

```bash
eksctl create nodegroup \
  --cluster autoclaude-cluster \
  --node-type t3.medium \
  --nodes 3 \
  --spot
```

**GCP:**

```bash
gcloud container node-pools create spot-pool \
  --cluster=autoclaude-cluster \
  --preemptible \
  --num-nodes=3
```

### Managed Services

**Cost-Effective Options:**

| Service | DIY Cost | Managed Service | Recommendation |
|---------|----------|-----------------|----------------|
| PostgreSQL | $50-100/mo | RDS/Cloud SQL: $100-200/mo | Managed for production |
| Redis | $20-40/mo | ElastiCache/Memorystore: $50-100/mo | Managed for production |
| Load Balancer | Included | $15-20/mo | Use cloud LB |

**Managed Database Benefits:**
- Automated backups
- High availability
- Automated updates
- Better performance
- Worth the extra cost

---

## Summary

This guide covered:

✅ **Deployment Methods**: Docker Compose and Kubernetes
✅ **Configuration**: Environment variables and secrets management
✅ **Security**: SSL/TLS, network policies, authentication
✅ **Scaling**: Horizontal scaling, load balancing
✅ **Monitoring**: Logging, metrics, alerting
✅ **Backup/Recovery**: Database backups, disaster recovery
✅ **Performance**: Optimization strategies
✅ **Troubleshooting**: Common issues and solutions
✅ **Maintenance**: Updates and rolling deployments
✅ **Cost Optimization**: Resource management

### Next Steps

1. Review [CLOUD_SETUP.md](CLOUD_SETUP.md) for initial setup instructions
2. Choose your deployment method (Docker Compose or Kubernetes)
3. Follow security hardening checklist
4. Set up monitoring and alerting
5. Configure automated backups
6. Perform load testing before production launch

### Support

- **Documentation**: [guides/README.md](README.md)
- **GitHub Issues**: https://github.com/OBenner/Auto-Coding/issues
- **Community**: Discord/Slack (coming soon)

---

**Maintained by the Auto Claude team. Last updated: 2024-02-04**
