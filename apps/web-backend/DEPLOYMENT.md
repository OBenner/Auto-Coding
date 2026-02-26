# Deployment Guide - Auto Code Web Backend

This guide covers deploying the Auto Code Web Backend (FastAPI server) to production environments.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Configuration](#environment-configuration)
- [Deployment Options](#deployment-options)
  - [Docker Deployment](#docker-deployment)
  - [Systemd Service (Linux)](#systemd-service-linux)
  - [Traditional Hosting](#traditional-hosting)
  - [Cloud Platforms](#cloud-platforms)
- [Security Hardening](#security-hardening)
- [Monitoring & Logging](#monitoring--logging)
- [Troubleshooting](#troubleshooting)
- [Scaling Considerations](#scaling-considerations)

---

## Prerequisites

### System Requirements

- **OS**: Linux (recommended), macOS, Windows Server
- **Python**: 3.12 or higher
- **Memory**: Minimum 1GB RAM, recommended 2GB+
- **Storage**: Minimum 1GB free space
- **Network**: Outbound internet access for API calls

### Required Software

```bash
# Python 3.12+ with pip
python3 --version

# Git (for deployment)
git --version

# (Optional) Docker for containerized deployment
docker --version
```

---

## Environment Configuration

### 1. Clone Repository

```bash
git clone https://github.com/OBenner/Auto-Coding.git
cd Auto-Claude/apps/web-backend
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create `.env` file from template:

```bash
cp .env.example .env
```

**Critical production settings** (edit `.env`):

```env
# CRITICAL: Change in production!
DEBUG=false
SECRET_KEY=<generate-strong-key-see-below>

# Server configuration
HOST=0.0.0.0  # Listen on all interfaces
PORT=8000

# CORS - restrict to your frontend domain
CORS_ORIGINS=https://your-frontend-domain.com

# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Logging
LOG_LEVEL=info
LOG_FILE=/var/log/auto-claude-web/app.log

# WebSocket
WS_HEARTBEAT_INTERVAL=30
```

### 5. Generate Secure Secret Key

```bash
# Generate a cryptographically secure secret key
openssl rand -hex 32
```

Copy the output and set it as `SECRET_KEY` in `.env`.

---

## Deployment Options

### Docker Deployment

#### 1. Create Dockerfile

Create `Dockerfile` in `apps/web-backend/`:

```dockerfile
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user for security
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=40s --retries=3 \
  CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2. Create docker-compose.yml

```yaml
version: '3.8'

services:
  web-backend:
    build: .
    container_name: auto-claude-backend
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - SECRET_KEY=${SECRET_KEY}
      - CORS_ORIGINS=${CORS_ORIGINS}
      - LOG_LEVEL=info
    volumes:
      - ./logs:/var/log/auto-claude-web
      - ../.auto-claude:/app/.auto-claude:ro  # Read-only access to specs
    networks:
      - auto-claude-network
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

networks:
  auto-claude-network:
    driver: bridge
```

#### 3. Deploy with Docker Compose

```bash
# Set environment variables
export SECRET_KEY=$(openssl rand -hex 32)
export CORS_ORIGINS=https://your-frontend-domain.com

# Build and start
docker-compose up -d

# View logs
docker-compose logs -f

# Stop
docker-compose down
```

---

### Systemd Service (Linux)

#### 1. Create systemd service file

Create `/etc/systemd/system/auto-claude-web.service`:

```ini
[Unit]
Description=Auto Code Web Backend
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/auto-claude/apps/web-backend
Environment="PATH=/opt/auto-claude/apps/web-backend/venv/bin"
EnvironmentFile=/opt/auto-claude/apps/web-backend/.env
ExecStart=/opt/auto-claude/apps/web-backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/log/auto-claude-web /opt/auto-claude/.auto-claude

# Restart policy
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

#### 2. Deploy the service

```bash
# Copy application to /opt
sudo mkdir -p /opt/auto-claude
sudo cp -r . /opt/auto-claude/apps/web-backend

# Set up virtual environment
cd /opt/auto-claude/apps/web-backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create log directory
sudo mkdir -p /var/log/auto-claude-web
sudo chown www-data:www-data /var/log/auto-claude-web

# Set permissions
sudo chown -R www-data:www-data /opt/auto-claude

# Configure .env (see Environment Configuration section)
sudo nano /opt/auto-claude/apps/web-backend/.env

# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable auto-claude-web
sudo systemctl start auto-claude-web

# Check status
sudo systemctl status auto-claude-web

# View logs
sudo journalctl -u auto-claude-web -f
```

---

### Traditional Hosting

#### Using Gunicorn (recommended for production)

Install gunicorn:

```bash
pip install gunicorn
```

Create `gunicorn_config.py`:

```python
# Gunicorn configuration file
import multiprocessing

# Bind to host and port
bind = "0.0.0.0:8000"

# Worker configuration
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeouts
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/auto-claude-web/access.log"
errorlog = "/var/log/auto-claude-web/error.log"
loglevel = "info"

# Process naming
proc_name = "auto-claude-web"

# Daemon mode (set to False when using systemd)
daemon = False

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190
```

Run with gunicorn:

```bash
gunicorn -c gunicorn_config.py main:app
```

#### Using Nginx as Reverse Proxy

Create `/etc/nginx/sites-available/auto-claude-web`:

```nginx
upstream auto_claude_backend {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name api.your-domain.com;

    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.your-domain.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/api.your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.your-domain.com/privkey.pem;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

    # Client body size limit
    client_max_body_size 10M;

    # Proxy settings
    location / {
        proxy_pass http://auto_claude_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # WebSocket support
    location /ws {
        proxy_pass http://auto_claude_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeouts
        proxy_connect_timeout 7d;
        proxy_send_timeout 7d;
        proxy_read_timeout 7d;
    }

    # Health check endpoint
    location /health {
        proxy_pass http://auto_claude_backend/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/auto-claude-web /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

### Cloud Platforms

#### AWS (EC2 + Application Load Balancer)

1. **Launch EC2 instance** (t3.medium or larger)
2. **Install dependencies** (see Prerequisites)
3. **Configure security groups**:
   - Allow inbound: 80 (HTTP), 443 (HTTPS)
   - Allow outbound: All traffic
4. **Deploy with systemd** (see systemd section)
5. **Set up ALB** for load balancing and SSL termination
6. **Configure CloudWatch** for logs and metrics

#### Google Cloud Platform (Cloud Run)

Create `Dockerfile` (see Docker section), then:

```bash
# Build and push container
gcloud builds submit --tag gcr.io/PROJECT_ID/auto-claude-web

# Deploy to Cloud Run
gcloud run deploy auto-claude-web \
  --image gcr.io/PROJECT_ID/auto-claude-web \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars SECRET_KEY=your-secret-key,DEBUG=false \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 10
```

#### Heroku

Create `Procfile`:

```
web: uvicorn main:app --host 0.0.0.0 --port $PORT
```

Deploy:

```bash
# Login to Heroku
heroku login

# Create app
heroku create auto-claude-web

# Set config vars
heroku config:set SECRET_KEY=$(openssl rand -hex 32)
heroku config:set DEBUG=false
heroku config:set CORS_ORIGINS=https://your-frontend.com

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

#### DigitalOcean (App Platform)

Create `app.yaml`:

```yaml
name: auto-claude-web
services:
  - name: backend
    github:
      repo: OBenner/Auto-Coding
      branch: main
      deploy_on_push: true
    source_dir: /apps/web-backend
    run_command: uvicorn main:app --host 0.0.0.0 --port 8080
    http_port: 8080
    instance_count: 2
    instance_size_slug: basic-xs
    envs:
      - key: DEBUG
        value: "false"
      - key: SECRET_KEY
        value: ${SECRET_KEY}
        type: SECRET
      - key: CORS_ORIGINS
        value: ${CORS_ORIGINS}
    health_check:
      http_path: /health
```

Deploy via DigitalOcean dashboard or CLI.

---

## Security Hardening

### 1. Authentication

**Enable JWT authentication for all endpoints**:

```python
# In main.py, protect sensitive routes
from api.routes.auth import verify_token

@app.get("/api/tasks", dependencies=[Depends(verify_token)])
async def get_tasks():
    # ...
```

### 2. Rate Limiting

Install slowapi:

```bash
pip install slowapi
```

Add to `main.py`:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Apply to routes
@app.post("/api/agents/run")
@limiter.limit("10/minute")
async def run_agent(request: Request, ...):
    # ...
```

### 3. HTTPS Only

**Always use HTTPS in production**. Configure your reverse proxy (nginx, Caddy) or cloud load balancer for SSL/TLS.

Example with Caddy (automatic HTTPS):

```
api.your-domain.com {
    reverse_proxy localhost:8000
}
```

### 4. Firewall Configuration

```bash
# UFW (Ubuntu/Debian)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw enable
```

### 5. Security Headers

Already included in nginx configuration (see above):
- `X-Frame-Options`
- `X-Content-Type-Options`
- `X-XSS-Protection`
- `Strict-Transport-Security`

### 6. Environment Variables

**Never commit `.env` files**. Use secrets management:

- **AWS**: AWS Secrets Manager
- **GCP**: Google Cloud Secret Manager
- **Azure**: Azure Key Vault
- **Kubernetes**: Kubernetes Secrets
- **Docker**: Docker Secrets

---

## Monitoring & Logging

### Application Logs

Configure structured logging in `main.py`:

```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging for production
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(logHandler)
logger.setLevel(logging.INFO)
```

### Health Checks

The API exposes health endpoints:

- `GET /health` - Overall system health
- `GET /api/tasks/health` - Task API health
- `GET /api/specs/health` - Spec API health
- `GET /api/agents/health` - Agent execution health

**Configure monitoring tools** to poll these endpoints:

```bash
# Example with curl
curl -f http://localhost:8000/health || exit 1
```

### Metrics Collection

Install Prometheus client:

```bash
pip install prometheus-fastapi-instrumentator
```

Add to `main.py`:

```python
from prometheus_fastapi_instrumentator import Instrumentator

instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app)
```

Access metrics at `/metrics`.

### Log Aggregation

**Options**:
- **ELK Stack** (Elasticsearch, Logstash, Kibana)
- **Grafana Loki**
- **Cloud-native**: CloudWatch Logs, Stackdriver, Azure Monitor

### Alerts

Set up alerts for:
- High error rates (> 5% of requests)
- Slow response times (> 2s p95)
- Health check failures
- High memory/CPU usage (> 80%)
- WebSocket disconnections

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port
sudo lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process or change PORT in .env
PORT=8001 uvicorn main:app
```

### CORS Errors

**Check**:
1. Frontend origin is in `CORS_ORIGINS` environment variable
2. Credentials are properly configured
3. Preflight OPTIONS requests are handled

**Test CORS**:
```bash
curl -H "Origin: https://your-frontend.com" \
     -H "Access-Control-Request-Method: GET" \
     -H "Access-Control-Request-Headers: Content-Type" \
     -X OPTIONS \
     http://localhost:8000/api/tasks
```

### WebSocket Connection Failures

**Check**:
1. WebSocket URL uses `ws://` (dev) or `wss://` (production)
2. Reverse proxy (nginx) has WebSocket support enabled
3. Firewall allows WebSocket connections
4. No timeout issues (adjust `WS_HEARTBEAT_INTERVAL`)

**Test WebSocket**:
```bash
# Using wscat
npm install -g wscat
wscat -c ws://localhost:8000/ws/agent-events
```

### High Memory Usage

**Solutions**:
1. Reduce number of workers (`workers` in gunicorn config)
2. Implement connection pooling for database/external APIs
3. Add memory limits in Docker/Kubernetes
4. Monitor for memory leaks (use `memory_profiler`)

### Slow API Responses

**Debug**:
1. Enable debug logging: `LOG_LEVEL=debug`
2. Check database query performance
3. Profile with `py-spy`:
   ```bash
   pip install py-spy
   py-spy top --pid <process-id>
   ```
4. Add caching for expensive operations

---

## Scaling Considerations

### Horizontal Scaling

**Run multiple instances** behind a load balancer:

```yaml
# docker-compose.yml
services:
  web-backend-1:
    # ...
  web-backend-2:
    # ...
  nginx-lb:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - web-backend-1
      - web-backend-2
```

### Database Considerations

**Current**: File-based storage (specs, tasks in `.auto-claude/`)

**For scale**:
- Migrate to PostgreSQL or MongoDB
- Implement connection pooling
- Use read replicas for heavy read workloads

### WebSocket Scaling

**Challenge**: WebSocket connections are stateful

**Solutions**:
1. **Sticky sessions** at load balancer
2. **Redis pub/sub** for broadcasting events across instances
3. **Dedicated WebSocket servers** separate from API servers

### Caching

Implement caching for expensive operations:

```python
from functools import lru_cache
from cachetools import cached, TTLCache

# In-memory cache with TTL
@cached(cache=TTLCache(maxsize=1024, ttl=300))
def get_task_list():
    # ...
```

Or use Redis:

```bash
pip install redis
```

```python
import redis

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_task_list():
    cache_key = "tasks:list"
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Fetch from source
    tasks = fetch_tasks()
    redis_client.setex(cache_key, 300, json.dumps(tasks))
    return tasks
```

### Auto-scaling

**Cloud platforms**:
- **AWS**: Auto Scaling Groups with ECS/EKS
- **GCP**: Cloud Run autoscaling
- **Kubernetes**: Horizontal Pod Autoscaler (HPA)

Example HPA configuration:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: auto-claude-web
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: auto-claude-web
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

---

## Backup and Disaster Recovery

### What to Back Up

1. **Spec data**: `.auto-claude/specs/`
2. **Configuration**: `.env` (store securely)
3. **Logs**: `/var/log/auto-claude-web/`

### Backup Strategy

```bash
#!/bin/bash
# backup.sh - Daily backup script

BACKUP_DIR="/backup/auto-claude"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Backup specs
tar -czf "$BACKUP_DIR/specs_$TIMESTAMP.tar.gz" .auto-claude/specs/

# Backup configuration (encrypted)
openssl enc -aes-256-cbc -salt -in .env -out "$BACKUP_DIR/env_$TIMESTAMP.enc" -k "$BACKUP_PASSWORD"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "specs_*.tar.gz" -mtime +30 -delete
find "$BACKUP_DIR" -name "env_*.enc" -mtime +30 -delete
```

Add to cron:

```bash
# Run daily at 2 AM
0 2 * * * /opt/auto-claude/backup.sh
```

---

## Support

For deployment issues:

- **GitHub Issues**: https://github.com/OBenner/Auto-Coding/issues
- **Documentation**: See main repository README
- **Community**: Join discussions on GitHub

---

**Next Steps**: See [DEPLOYMENT.md](../web-frontend/DEPLOYMENT.md) for frontend deployment.
