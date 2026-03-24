# Update Strategy Guide

Comprehensive guide for updating Auto Code deployments with zero downtime using rolling updates, blue-green deployments, and canary releases.

## Overview

Auto Code supports multiple update strategies for both Docker Compose and Kubernetes deployments:

- **Rolling Updates** - Gradual replacement of old instances with new ones
- **Blue-Green Deployments** - Switch traffic between two identical environments
- **Canary Releases** - Gradual rollout to subset of users before full deployment
- **Recreate Strategy** - Stop old version, start new version (downtime acceptable)

**Recommended strategies by deployment type:**
- **Development/Staging:** Rolling updates (default)
- **Production (small scale):** Blue-green deployments
- **Production (large scale):** Canary releases with gradual rollout

## Version Management

### Semantic Versioning

Auto Code follows semantic versioning (MAJOR.MINOR.PATCH):

```
2.8.0 → 2.8.1  (patch: bug fixes, backwards compatible)
2.8.0 → 2.9.0  (minor: new features, backwards compatible)
2.8.0 → 3.0.0  (major: breaking changes)
```

### Tagging Strategy

Docker images are tagged with:
- **Version tags:** `auto-code-backend:2.8.1`, `auto-code-web-backend:2.8.1`
- **Latest tag:** `auto-code-backend:latest` (always points to latest stable)
- **Branch tags:** `auto-code-backend:develop` (for testing pre-release builds)

```bash
# Build and tag images
docker build -t auto-code-backend:2.8.1 -t auto-code-backend:latest apps/backend
docker build -t auto-code-web-backend:2.8.1 -t auto-code-web-backend:latest apps/web-backend
docker build -t auto-code-web-frontend:2.8.1 -t auto-code-web-frontend:latest apps/web-frontend

# Push to registry
docker push auto-code-backend:2.8.1
docker push auto-code-backend:latest
```

### Pre-Update Checklist

Before any update:

1. **Backup data:**
   ```bash
   # Docker Compose
   docker-compose exec postgres pg_dump -U postgres autoclaude > backup-$(date +%Y%m%d).sql

   # Kubernetes
   kubectl exec -n auto-claude postgres-0 -- pg_dump -U postgres autoclaude > backup-$(date +%Y%m%d).sql
   ```

2. **Review changelog:**
   - Check CHANGELOG.md for breaking changes
   - Review migration scripts (if any)
   - Identify required configuration changes

3. **Test in staging:**
   - Deploy to staging environment first
   - Run smoke tests and integration tests
   - Verify all services healthy

4. **Plan rollback:**
   - Document rollback steps
   - Keep previous version images available
   - Ensure backups are restorable

## Rolling Updates

### Docker Compose Rolling Updates

Docker Compose doesn't support true rolling updates out-of-the-box, but you can achieve gradual updates with orchestration:

#### Basic Update (Brief Downtime)

```bash
# Pull new images
docker-compose pull

# Restart services one at a time
docker-compose up -d --no-deps --scale web-backend=2 web-backend
sleep 30  # Wait for new instance to be healthy
docker-compose up -d --no-deps --scale web-backend=1 web-backend

# Repeat for other services
docker-compose up -d --no-deps backend
docker-compose up -d --no-deps web-frontend
```

#### Zero-Downtime Update with Load Balancer

Requires external load balancer (nginx, HAProxy, Traefik):

```bash
# Scale up with new version
docker-compose up -d --no-deps --scale web-backend=3 web-backend

# Wait for health checks
sleep 30
docker-compose ps

# Gracefully stop old instances
docker stop $(docker ps -q --filter name=web-backend | tail -n 1)
sleep 10
docker stop $(docker ps -q --filter name=web-backend | tail -n 1)

# Verify only new version running
docker-compose ps
```

#### Script for Automated Rolling Update

Create `scripts/rolling-update-compose.sh`:

```bash
#!/bin/bash
set -e

SERVICE=$1
NEW_VERSION=$2

echo "Starting rolling update for $SERVICE to version $NEW_VERSION"

# Update image version in docker-compose.yml
sed -i "s|image: auto-code-$SERVICE:.*|image: auto-code-$SERVICE:$NEW_VERSION|" docker-compose.yml

# Pull new image
docker-compose pull $SERVICE

# Scale up to 2 instances
docker-compose up -d --no-deps --scale $SERVICE=2 $SERVICE

# Wait for new instance to be healthy
echo "Waiting for new instance to be healthy..."
sleep 30

# Check health
if docker-compose ps $SERVICE | grep -q "healthy"; then
    echo "New instance healthy, scaling down old instance"
    docker-compose up -d --no-deps --scale $SERVICE=1 $SERVICE
    echo "Rolling update complete"
else
    echo "New instance unhealthy, rolling back"
    docker-compose up -d --no-deps --scale $SERVICE=1 $SERVICE
    exit 1
fi
```

Usage:
```bash
chmod +x scripts/rolling-update-compose.sh
./scripts/rolling-update-compose.sh web-backend 2.8.1
```

### Kubernetes Rolling Updates

Kubernetes supports rolling updates natively with configurable strategies.

#### Configure Rolling Update Strategy

In `kubernetes/web-backend-deployment.yaml`:

```yaml
spec:
  replicas: 3
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1        # Max pods above desired count during update
      maxUnavailable: 0  # Max pods unavailable during update (zero-downtime)
  minReadySeconds: 10    # Wait 10s after pod ready before continuing
```

**Strategy parameters:**
- `maxSurge: 1` - Create 1 extra pod during rollout (3 → 4 → 3)
- `maxUnavailable: 0` - Never reduce below desired replica count
- `minReadySeconds: 10` - Gradual rollout with 10s wait between pods

#### Update Deployment Image

```bash
# Update image version
kubectl set image deployment/web-backend \
  web-backend=auto-code-web-backend:2.8.1 \
  -n auto-claude

# Alternative: Edit deployment directly
kubectl edit deployment web-backend -n auto-claude

# Or use kubectl apply with updated manifest
kubectl apply -f kubernetes/web-backend-deployment.yaml
```

#### Monitor Rolling Update

```bash
# Watch rollout status
kubectl rollout status deployment/web-backend -n auto-claude

# Watch pods being replaced
kubectl get pods -n auto-claude -w

# View rollout history
kubectl rollout history deployment/web-backend -n auto-claude
```

Example output:
```
Waiting for deployment "web-backend" rollout to finish: 1 out of 3 new replicas have been updated...
Waiting for deployment "web-backend" rollout to finish: 1 old replicas are pending termination...
Waiting for deployment "web-backend" rollout to finish: 2 of 3 updated replicas are available...
deployment "web-backend" successfully rolled out
```

#### Pause and Resume Rollout

Useful for testing mid-rollout:

```bash
# Pause rollout after first pod
kubectl rollout pause deployment/web-backend -n auto-claude

# Test new version
kubectl exec -n auto-claude web-backend-xxxxx-yyy -- curl http://localhost:8000/health

# Resume rollout
kubectl rollout resume deployment/web-backend -n auto-claude
```

#### Helm Rolling Update

With Helm charts:

```bash
# Update values.yaml or override during upgrade
helm upgrade auto-claude ./helm/auto-code \
  --namespace auto-claude \
  --set backend.image.tag=2.8.1 \
  --set webBackend.image.tag=2.8.1 \
  --set webFrontend.image.tag=2.8.1 \
  --wait \
  --timeout 5m

# Verify rollout
helm status auto-claude -n auto-claude
```

## Blue-Green Deployments

Blue-green deployments maintain two identical environments and switch traffic between them.

### Docker Compose Blue-Green

Requires manual orchestration with Docker Compose.

#### 1. Create Blue and Green Compose Files

**docker-compose.blue.yml:**
```yaml
version: '3.8'
services:
  web-backend-blue:
    image: auto-code-web-backend:2.8.0
    container_name: web-backend-blue
    ports:
      - "8001:8000"  # Blue environment on port 8001
    environment:
      - ENVIRONMENT=blue
    # ... other config same as docker-compose.yml

  web-frontend-blue:
    image: auto-code-web-frontend:2.8.0
    container_name: web-frontend-blue
    ports:
      - "3001:3000"  # Blue environment on port 3001
    # ... other config
```

**docker-compose.green.yml:**
```yaml
version: '3.8'
services:
  web-backend-green:
    image: auto-code-web-backend:2.8.1  # New version
    container_name: web-backend-green
    ports:
      - "8002:8000"  # Green environment on port 8002
    environment:
      - ENVIRONMENT=green
    # ... other config

  web-frontend-green:
    image: auto-code-web-frontend:2.8.1  # New version
    container_name: web-frontend-green
    ports:
      - "3002:3000"  # Green environment on port 3002
    # ... other config
```

#### 2. Deploy Green Environment

```bash
# Start green environment with new version
docker-compose -f docker-compose.green.yml up -d

# Wait for health checks
sleep 30

# Verify green environment
curl http://localhost:8002/health
curl http://localhost:3002/
```

#### 3. Switch Traffic with Load Balancer

Configure nginx/HAProxy to switch traffic:

**nginx.conf:**
```nginx
upstream backend {
    server localhost:8001;  # Blue (current)
    # server localhost:8002;  # Green (new) - comment out until ready
}

upstream frontend {
    server localhost:3001;  # Blue (current)
    # server localhost:3002;  # Green (new) - comment out until ready
}
```

**Switch to green:**
```nginx
upstream backend {
    # server localhost:8001;  # Blue (old) - commented out
    server localhost:8002;  # Green (new) - now active
}

upstream frontend {
    # server localhost:3001;  # Blue (old) - commented out
    server localhost:3002;  # Green (new) - now active
}
```

Reload nginx:
```bash
nginx -s reload
```

#### 4. Rollback if Needed

If issues detected, switch back to blue:

```bash
# Edit nginx.conf to point back to blue
nginx -s reload

# Or stop green environment
docker-compose -f docker-compose.green.yml down
```

### Kubernetes Blue-Green

Kubernetes makes blue-green deployments easier with Services and labels.

#### 1. Deploy Green Environment

**backend-deployment-green.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend-green
  namespace: auto-claude
spec:
  replicas: 3
  selector:
    matchLabels:
      app: backend
      version: green  # Green label
  template:
    metadata:
      labels:
        app: backend
        version: green
    spec:
      containers:
      - name: backend
        image: auto-code-backend:2.8.1  # New version
        # ... rest of spec
```

Deploy green:
```bash
kubectl apply -f kubernetes/backend-deployment-green.yaml
kubectl apply -f kubernetes/web-backend-deployment-green.yaml
kubectl apply -f kubernetes/web-frontend-deployment-green.yaml

# Wait for green pods to be ready
kubectl wait --for=condition=ready pod -l version=green -n auto-claude --timeout=300s
```

#### 2. Test Green Environment

```bash
# Port-forward to test green directly
kubectl port-forward -n auto-claude deployment/web-backend-green 8001:8000

# Test in another terminal
curl http://localhost:8001/health
```

#### 3. Switch Service to Green

Update Service selector to point to green:

```bash
# Patch service to use green version
kubectl patch service web-backend -n auto-claude -p '{"spec":{"selector":{"version":"green"}}}'
kubectl patch service web-frontend -n auto-claude -p '{"spec":{"selector":{"version":"green"}}}'

# Verify traffic is now going to green
kubectl get endpoints web-backend -n auto-claude
```

#### 4. Monitor and Rollback if Needed

```bash
# Monitor logs and metrics
kubectl logs -n auto-claude -l version=green --tail=100 -f

# If issues detected, rollback to blue
kubectl patch service web-backend -n auto-claude -p '{"spec":{"selector":{"version":"blue"}}}'
kubectl patch service web-frontend -n auto-claude -p '{"spec":{"selector":{"version":"blue"}}}'
```

#### 5. Cleanup Old Blue Environment

Once green is stable:

```bash
# Delete blue deployments
kubectl delete deployment backend-blue -n auto-claude
kubectl delete deployment web-backend-blue -n auto-claude
kubectl delete deployment web-frontend-blue -n auto-claude
```

## Canary Releases

Canary releases gradually roll out new version to subset of users, monitoring metrics before full rollout.

### Kubernetes Canary with Multiple Deployments

#### 1. Deploy Canary Deployment

Keep existing deployment (stable) and create canary with fewer replicas:

**web-backend-deployment-canary.yaml:**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web-backend-canary
  namespace: auto-claude
spec:
  replicas: 1  # Start with 1 canary pod (10% of traffic if stable has 9 replicas)
  selector:
    matchLabels:
      app: web-backend
      track: canary
  template:
    metadata:
      labels:
        app: web-backend
        track: canary
        version: 2.8.1  # New version
    spec:
      containers:
      - name: web-backend
        image: auto-code-web-backend:2.8.1  # New version
        # ... rest of spec
```

Deploy canary:
```bash
# Ensure stable deployment is running
kubectl apply -f kubernetes/web-backend-deployment.yaml  # 9 replicas, version 2.8.0

# Deploy canary
kubectl apply -f kubernetes/web-backend-deployment-canary.yaml  # 1 replica, version 2.8.1

# Service will load-balance across both (90% stable, 10% canary)
kubectl get pods -n auto-claude -l app=web-backend
```

#### 2. Monitor Canary Metrics

Monitor error rates, latency, and health metrics:

```bash
# Watch canary logs
kubectl logs -n auto-claude -l track=canary -f

# Check error rates (requires Prometheus/monitoring)
# Compare error rate of canary vs stable
kubectl exec -n auto-claude monitoring-pod -- \
  promtool query instant 'rate(http_requests_total{track="canary",status=~"5.."}[5m])'

# Check latency percentiles
kubectl exec -n auto-claude monitoring-pod -- \
  promtool query instant 'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{track="canary"}[5m]))'
```

#### 3. Gradual Rollout

If canary metrics are healthy, gradually increase canary traffic:

```bash
# Increase canary to 3 replicas (30% traffic)
kubectl scale deployment web-backend-canary --replicas=3 -n auto-claude

# Monitor for 15 minutes
sleep 900

# Increase to 5 replicas (50% traffic)
kubectl scale deployment web-backend-canary --replicas=5 -n auto-claude

# Monitor for 15 minutes
sleep 900

# Promote canary to stable
kubectl scale deployment web-backend-canary --replicas=9 -n auto-claude
kubectl delete deployment web-backend -n auto-claude  # Remove old stable
kubectl patch deployment web-backend-canary -n auto-claude -p '{"metadata":{"name":"web-backend"}}'
```

#### 4. Automated Canary with Flagger

For production canary deployments, use Flagger for automated progressive delivery:

**Install Flagger:**
```bash
# Add Flagger Helm repo
helm repo add flagger https://flagger.app

# Install Flagger (requires Istio, Linkerd, or other service mesh)
kubectl apply -f https://raw.githubusercontent.com/fluxcd/flagger/main/artifacts/flagger/crd.yaml
helm upgrade -i flagger flagger/flagger \
  --namespace flagger-system \
  --set meshProvider=istio \
  --set metricsServer=http://prometheus:9090
```

**Flagger Canary resource:**

**web-backend-canary-flagger.yaml:**
```yaml
apiVersion: flagger.app/v1beta1
kind: Canary
metadata:
  name: web-backend
  namespace: auto-claude
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-backend
  service:
    port: 8000
  analysis:
    interval: 1m
    threshold: 5  # Number of failed checks before rollback
    maxWeight: 50  # Max percentage of traffic to canary
    stepWeight: 10  # Increase traffic by 10% each interval
    metrics:
    - name: request-success-rate
      thresholdRange:
        min: 99  # Require 99% success rate
      interval: 1m
    - name: request-duration
      thresholdRange:
        max: 500  # Max 500ms latency
      interval: 1m
    webhooks:
    - name: load-test
      url: http://flagger-loadtester/
      timeout: 5s
      metadata:
        cmd: "hey -z 1m -q 10 -c 2 http://web-backend-canary:8000/health"
```

Apply and update deployment:
```bash
kubectl apply -f kubernetes/web-backend-canary-flagger.yaml

# Trigger canary by updating deployment image
kubectl set image deployment/web-backend web-backend=auto-code-web-backend:2.8.1 -n auto-claude

# Flagger will automatically:
# 1. Deploy canary pods
# 2. Gradually increase traffic (0% → 10% → 20% → ... → 50%)
# 3. Monitor metrics at each step
# 4. Promote or rollback based on success criteria
```

Monitor Flagger canary:
```bash
# Watch canary progress
kubectl get canary -n auto-claude -w

# View events
kubectl describe canary web-backend -n auto-claude
```

### Docker Compose Canary

Docker Compose canary requires external traffic management:

```bash
# Run stable version (3 instances)
docker-compose up -d --scale web-backend=3

# Run canary version (1 instance on different port)
docker run -d --name web-backend-canary \
  -p 8001:8000 \
  auto-code-web-backend:2.8.1

# Configure load balancer for weighted routing
# nginx: 90% to localhost:8000, 10% to localhost:8001
```

## Rollback Strategies

### Kubernetes Rollback

Kubernetes tracks rollout history and supports instant rollbacks.

#### View Rollout History

```bash
# View all revisions
kubectl rollout history deployment/web-backend -n auto-claude

# View specific revision details
kubectl rollout history deployment/web-backend -n auto-claude --revision=2
```

Example output:
```
REVISION  CHANGE-CAUSE
1         <none>
2         kubectl set image deployment/web-backend web-backend=auto-code-web-backend:2.8.1
3         kubectl set image deployment/web-backend web-backend=auto-code-web-backend:2.8.2
```

#### Rollback to Previous Version

```bash
# Rollback to previous revision
kubectl rollout undo deployment/web-backend -n auto-claude

# Rollback to specific revision
kubectl rollout undo deployment/web-backend -n auto-claude --to-revision=2

# Watch rollback progress
kubectl rollout status deployment/web-backend -n auto-claude
```

#### Helm Rollback

```bash
# List Helm releases
helm history auto-claude -n auto-claude

# Rollback to previous release
helm rollback auto-claude -n auto-claude

# Rollback to specific revision
helm rollback auto-claude 2 -n auto-claude
```

### Docker Compose Rollback

```bash
# Update docker-compose.yml to previous version
sed -i 's|auto-code-web-backend:2.8.1|auto-code-web-backend:2.8.0|' docker-compose.yml

# Pull old image (if not cached)
docker-compose pull web-backend

# Restart with old version
docker-compose up -d web-backend
```

### Database Rollback

If update includes database migrations, rollback requires reversing migrations:

```bash
# For Django migrations
docker-compose exec backend python manage.py migrate app_name 0003_previous_migration

# For Alembic migrations
docker-compose exec backend alembic downgrade -1

# For Kubernetes
kubectl exec -n auto-claude backend-xxxxx -- python manage.py migrate app_name 0003_previous_migration
```

**Best practices for database migrations:**
- Always make migrations backwards compatible
- Use multi-phase migrations for breaking changes
- Test rollback in staging before production

## Zero-Downtime Updates

### Requirements for Zero Downtime

1. **Multiple replicas** - At least 2 pods/containers per service
2. **Health checks** - Liveness and readiness probes configured
3. **Graceful shutdown** - Application handles SIGTERM properly
4. **Rolling update strategy** - `maxUnavailable: 0` in Kubernetes
5. **Backwards compatibility** - New version compatible with old version during rollout

### Graceful Shutdown

Ensure application handles SIGTERM for graceful shutdown:

**Python (FastAPI/Django):**
```python
import signal
import sys

def graceful_shutdown(signum, frame):
    print("Received SIGTERM, shutting down gracefully...")
    # Close database connections
    # Finish in-flight requests
    # Clean up resources
    sys.exit(0)

signal.signal(signal.SIGTERM, graceful_shutdown)
```

**Node.js:**
```javascript
process.on('SIGTERM', () => {
  console.log('Received SIGTERM, shutting down gracefully...');
  server.close(() => {
    // Close database connections
    // Finish in-flight requests
    process.exit(0);
  });
});
```

### Database Migration Strategy

For zero-downtime updates with database changes:

#### Phase 1: Additive Changes (Deploy v2.8.1)
1. Add new columns/tables (nullable or with defaults)
2. Deploy new application version
3. Old version ignores new columns, new version uses them

#### Phase 2: Dual-Write Period (Run v2.8.1 for days/weeks)
4. Write to both old and new columns
5. Backfill old data to new columns

#### Phase 3: Cleanup (Deploy v2.8.2)
6. Remove old columns/tables
7. Deploy new version that only uses new schema

**Example: Renaming column `user_id` to `account_id`**

**Phase 1: Add new column**
```sql
ALTER TABLE tasks ADD COLUMN account_id INTEGER;
```

**Phase 2: Dual-write (application code)**
```python
# v2.8.1: Write to both columns
task.user_id = user.id
task.account_id = user.id  # Also write to new column
task.save()

# Backfill existing data
UPDATE tasks SET account_id = user_id WHERE account_id IS NULL;
```

**Phase 3: Remove old column**
```sql
-- v2.8.2: Drop old column
ALTER TABLE tasks DROP COLUMN user_id;
```

## Best Practices

### General Update Practices

1. **Always test in staging first**
   - Deploy to staging environment
   - Run full test suite
   - Perform manual testing
   - Verify rollback procedure

2. **Use semantic versioning**
   - Tag all images with version numbers
   - Never use `:latest` in production
   - Keep old versions available for rollback

3. **Monitor during updates**
   - Watch error rates and latency
   - Check health endpoints
   - Monitor resource usage (CPU, memory)
   - Review application logs

4. **Automate updates**
   - Use CI/CD pipelines
   - Automate testing and validation
   - Use GitOps for declarative deployments

5. **Document changes**
   - Maintain CHANGELOG.md
   - Document breaking changes
   - Update runbooks and operational docs

### Kubernetes-Specific Practices

1. **Configure proper resource limits**
   ```yaml
   resources:
     requests:
       cpu: 500m
       memory: 512Mi
     limits:
       cpu: 1000m
       memory: 1Gi
   ```

2. **Use PodDisruptionBudgets**
   ```yaml
   apiVersion: policy/v1
   kind: PodDisruptionBudget
   metadata:
     name: web-backend-pdb
   spec:
     minAvailable: 2  # Keep at least 2 pods running during updates
     selector:
       matchLabels:
         app: web-backend
   ```

3. **Configure preStop hooks for graceful shutdown**
   ```yaml
   lifecycle:
     preStop:
       exec:
         command: ["/bin/sh", "-c", "sleep 15"]  # Wait for load balancer to deregister
   ```

4. **Set appropriate terminationGracePeriodSeconds**
   ```yaml
   spec:
     terminationGracePeriodSeconds: 30  # Give 30s for graceful shutdown
   ```

### Docker Compose Practices

1. **Use external load balancer**
   - nginx or HAProxy for traffic management
   - Health check endpoints for routing decisions

2. **Version lock images**
   ```yaml
   services:
     web-backend:
       image: auto-code-web-backend:2.8.1  # Specific version, not :latest
   ```

3. **Use healthchecks**
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
     interval: 30s
     timeout: 10s
     retries: 3
     start_period: 40s
   ```

## Monitoring Update Progress

### Key Metrics to Monitor

1. **Error rates** - HTTP 5xx responses
2. **Latency** - p50, p95, p99 response times
3. **Throughput** - Requests per second
4. **Resource usage** - CPU, memory, disk
5. **Health check status** - Liveness and readiness probe failures

### Prometheus Queries for Updates

```promql
# Error rate by version
rate(http_requests_total{status=~"5..",version="2.8.1"}[5m])

# Compare latency between versions
histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{version="2.8.1"}[5m]))

# Pod restart count (high restarts indicate issues)
kube_pod_container_status_restarts_total{namespace="auto-claude"}
```

### Alerting Rules

Configure alerts for update issues:

```yaml
groups:
- name: update_alerts
  rules:
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
    for: 2m
    annotations:
      summary: "High error rate during update"

  - alert: HighPodRestarts
    expr: rate(kube_pod_container_status_restarts_total[15m]) > 0
    for: 5m
    annotations:
      summary: "Pods restarting during update"
```

## Troubleshooting Updates

### Update Stuck or Slow

**Symptoms:**
- Rollout not progressing
- Pods stuck in Pending or ImagePullBackOff

**Diagnosis:**
```bash
# Check pod status
kubectl get pods -n auto-claude

# View pod events
kubectl describe pod web-backend-xxxxx -n auto-claude

# Check rollout status
kubectl rollout status deployment/web-backend -n auto-claude
```

**Solutions:**
- Verify image exists in registry
- Check resource availability (CPU, memory)
- Review node capacity: `kubectl describe node`
- Check image pull credentials

### New Version Unhealthy

**Symptoms:**
- Readiness probes failing
- Pods in CrashLoopBackOff
- High error rates after update

**Diagnosis:**
```bash
# Check pod logs
kubectl logs -n auto-claude web-backend-xxxxx --previous

# Check events
kubectl get events -n auto-claude --sort-by='.lastTimestamp'

# Verify health endpoint
kubectl exec -n auto-claude web-backend-xxxxx -- curl http://localhost:8000/health
```

**Solutions:**
- Rollback immediately: `kubectl rollout undo deployment/web-backend -n auto-claude`
- Check configuration changes (environment variables, secrets)
- Verify database migrations completed successfully
- Review application logs for errors

### Rollback Not Working

**Symptoms:**
- Rollback command succeeds but still seeing new version
- Rollback completes but application still broken

**Solutions:**
```bash
# Verify rollback completed
kubectl rollout status deployment/web-backend -n auto-claude

# Check deployment image
kubectl get deployment web-backend -n auto-claude -o jsonpath='{.spec.template.spec.containers[0].image}'

# Force rollback to specific revision
kubectl rollout undo deployment/web-backend -n auto-claude --to-revision=1

# If database issue, rollback migrations
kubectl exec -n auto-claude backend-xxxxx -- python manage.py migrate app_name 0003_previous
```

## Related Documentation

- **[Docker Deployment Guide](DOCKER_DEPLOYMENT.md)** - Docker Compose deployment instructions
- **[Kubernetes Deployment Guide](KUBERNETES_DEPLOYMENT.md)** - Kubernetes and Helm deployment
- **[Troubleshooting Guide](TROUBLESHOOTING.md)** - General troubleshooting

## Summary

This guide covered comprehensive update strategies for Auto Code:

- **Rolling updates** - Default strategy for gradual replacement
- **Blue-green deployments** - Zero-downtime with instant rollback
- **Canary releases** - Risk mitigation with gradual rollout
- **Rollback strategies** - Quick recovery from failed updates
- **Zero-downtime techniques** - Graceful shutdown and database migrations

**Recommended approach:**
1. Start with **rolling updates** for development/staging
2. Use **blue-green** for small-scale production deployments
3. Implement **canary releases** for large-scale production with automated tooling (Flagger)
4. Always test in staging and have rollback plan ready
