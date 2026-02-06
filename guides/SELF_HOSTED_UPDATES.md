# Self-Hosted Updates Guide - Auto Code

This guide covers updating and upgrading self-hosted Auto Code instances across different deployment methods. Follow these procedures to keep your installation up-to-date with the latest features, bug fixes, and security patches.

## Table of Contents

- [Overview](#overview)
- [Pre-Update Checklist](#pre-update-checklist)
- [Update Methods](#update-methods)
  - [Docker Compose Updates](#docker-compose-updates)
  - [Kubernetes/Helm Updates](#kuberneteshelm-updates)
- [Database Migrations](#database-migrations)
- [Rollback Procedures](#rollback-procedures)
- [Update Automation](#update-automation)
- [Troubleshooting](#troubleshooting)
- [Best Practices](#best-practices)

---

## Overview

Auto Code receives regular updates including new features, bug fixes, security patches, and performance improvements. Keeping your self-hosted instance current ensures you benefit from the latest improvements.

**Update Types:**

| Type | Description | Frequency | Downtime Required |
|------|-------------|-----------|-------------------|
| **Patch Updates** (x.y.Z) | Bug fixes, security patches | As needed | No (rolling updates) |
| **Minor Updates** (x.Y.z) | New features, improvements | Monthly | No (rolling updates) |
| **Major Updates** (X.y.z) | Breaking changes, major features | Quarterly | Yes (maintenance window) |

**Update Channels:**

- **Stable** - Recommended for production. Tested thoroughly.
- **Beta** - Pre-release versions for testing new features.
- **Development** - Latest commits from the main branch (not recommended for production).

**Important Notes:**
- Always review [release notes](https://github.com/OBenner/Auto-Coding/releases) before updating
- Test updates in a staging environment first
- Back up your data before any update
- Major version updates may require manual migration steps

---

## Pre-Update Checklist

Before starting any update, complete this checklist to ensure a smooth process.

### 1. Review Release Notes

**What to Check:**
- Breaking changes or deprecations
- New dependencies or requirements
- Configuration changes
- Database schema changes
- Migration requirements

**Example:**
```bash
# View release notes on GitHub
# Visit: https://github.com/OBenner/Auto-Coding/releases

# Or check via git
git log --oneline v2.8.0..v2.9.0
git show v2.9.0 --stat
```

### 2. Backup Data

**Critical:** Always backup before updating.

**Docker Compose:**
```bash
# Backup PostgreSQL database
docker exec autoclaude-postgres pg_dump -U postgres autoclaude > backup-$(date +%Y%m%d).sql

# Backup volumes
docker run --rm -v autoclaude_postgres_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/postgres-data-$(date +%Y%m%d).tar.gz -C /data .

docker run --rm -v autoclaude_redis_data:/data -v $(pwd):/backup \
  alpine tar czf /backup/redis-data-$(date +%Y%m%d).tar.gz -C /data .
```

**Kubernetes/Helm:**
```bash
# Backup PostgreSQL
kubectl exec -it deployment/autoclaude-postgres -- \
  pg_dump -U postgres autoclaude > backup-$(date +%Y%m%d).sql

# Backup persistent volumes
kubectl get pvc -n autoclaude
# For each PVC, create a snapshot or backup using your cloud provider's tools
```

### 3. Verify Current Version

**Docker Compose:**
```bash
docker exec autoclaude-backend python -c "import autocode; print(autocode.__version__)"
```

**Kubernetes/Helm:**
```bash
helm list -n autoclaude
helm get values autoclaude -n autoclaude
```

### 4. Check System Requirements

Verify your system meets the requirements for the new version:

```bash
# Check disk space (need at least 5GB free)
df -h

# Check memory (need at least 4GB available)
free -h

# Check Docker version
docker --version  # Should be 20.10+
```

### 5. Schedule Maintenance Window (For Major Updates)

For major version updates:
- Notify users of scheduled downtime
- Plan for at least 30 minutes of maintenance window
- Have rollback plan ready
- Test update process in staging environment

---

## Update Methods

### Docker Compose Updates

The Docker Compose deployment uses image tags to version the application.

#### Standard Update Procedure

**1. Pull Latest Images**

```bash
# Navigate to deployment directory
cd /opt/autoclaude

# Pull latest images
docker-compose -f docker-compose.yml pull
```

**2. Stop Services**

```bash
# Stop all services gracefully
docker-compose -f docker-compose.yml down
```

**3. Update Configuration (If Required)**

Review the release notes for any new environment variables or configuration changes:

```bash
# Compare your .env with the new .env.example
diff .env .env.example

# Add any new required variables
nano .env
```

**4. Update Docker Compose File (If Required)**

For major version updates, download the new docker-compose.yml:

```bash
# Backup current configuration
cp docker-compose.yml docker-compose.yml.backup

# Download new version
wget https://raw.githubusercontent.com/OBenner/Auto-Coding/v2.9.0/apps/web-backend/docker-compose.yml \
  -O docker-compose.yml
```

**5. Start Services**

```bash
# Start services with new images
docker-compose -f docker-compose.yml up -d
```

**6. Verify Update**

```bash
# Check service status
docker-compose ps

# Verify service health
docker-compose ps | grep "healthy"

# Check logs for errors
docker-compose logs --tail=50 web-backend

# Verify version
docker exec autoclaude-backend python -c "import autocode; print(autocode.__version__)"
```

#### Zero-Downtime Update (Optional)

For patch and minor updates, use zero-downtime rolling updates:

```bash
# Pull new images
docker-compose pull

# Update each backend instance one at a time
docker-compose up -d --no-deps --scale web-backend=2 web-backend
docker-compose up -d --no-deps --scale web-backend=1 web-backend
```

**Note:** This requires sufficient resources to run multiple instances temporarily.

#### Air-Gapped Updates

For air-gapped environments:

```bash
# On internet-connected machine:
docker save -o autoclaude-images.tar ghcr.io/obenner/autoclaude:latest
# Transfer autoclaude-images.tar to air-gapped system

# On air-gapped system:
docker load -i autoclaude-images.tar
docker-compose -f docker-compose.yml up -d
```

---

### Kubernetes/Helm Updates

Helm provides powerful update and rollback capabilities for Kubernetes deployments.

#### Standard Upgrade Procedure

**1. Update Helm Repository**

```bash
# If using a remote Helm repository
helm repo update
helm search repo autoclaude --versions
```

**2. Review Release Notes**

```bash
# View available versions
helm search repo autoclaude -l | head -20

# Read release notes at:
# https://github.com/OBenner/Auto-Coding/releases
```

**3. Backup Current Configuration**

```bash
# Save current Helm values
helm get values autoclaude -n autoclaude > autoclaude-values-backup.yaml

# Save current release manifest
helm get manifest autoclaude -n autoclaude > autoclaude-manifest-backup.yaml
```

**4. Update Helm Chart**

**Option A: Upgrade from Repository**

```bash
# Upgrade to latest version
helm upgrade autoclaude autoclaude/autoclaude \
  --namespace autoclaude \
  --values autoclaude-values.yaml \
  --wait \
  --timeout 10m
```

**Option B: Upgrade from Local Chart**

```bash
# Pull latest chart
git fetch --tags
git checkout v2.9.0
cd infrastructure/helm/autoclaude

# Upgrade with existing values
helm upgrade autoclaude . \
  --namespace autoclaude \
  --values autoclaude-values.yaml \
  --wait \
  --timeout 10m
```

**Option C: Upgrade with Specific Version**

```bash
# Upgrade to specific version
helm upgrade autoclaude autoclaude/autoclaude \
  --namespace autoclaude \
  --version 2.9.0 \
  --values autoclaude-values.yaml \
  --wait
```

**5. Monitor Upgrade**

```bash
# Watch rollout status
kubectl rollout status deployment/autoclaude-backend -n autoclaude

# Check pod status
kubectl get pods -n autoclaude -w

# View new pods
kubectl get pods -n autoclaude -l app.kubernetes.io/name=autoclaude
```

**6. Verify Upgrade**

```bash
# Check Helm release status
helm list -n autoclaude

# Verify all pods are running
kubectl get pods -n autoclaude

# Check service endpoints
kubectl get endpoints -n autoclaude

# Verify application version
kubectl exec -n autoclaude deployment/autoclaude-backend -- \
  python -c "import autocode; print(autocode.__version__)"
```

#### Upgrade Strategies

Helm supports multiple upgrade strategies:

**1. Rolling Update (Default)**

Updates pods gradually with zero downtime:

```yaml
# In values.yaml
backend:
  updateStrategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 1
```

```bash
helm upgrade autoclaude . --namespace autoclaude --values values.yaml
```

**2. Blue-Green Deployment**

Run new version alongside old, then switch traffic:

```bash
# Install new version as "autoclaude-new"
helm install autoclaude-new . --namespace autoclaude --create-namespace \
  --set backend.ingress.enabled=false

# Verify new version works
kubectl port-forward -n autoclaude deployment/autoclaude-new-backend 8080:8000

# Switch ingress traffic
kubectl patch ingress autoclaude -n autoclaude --type=json \
  -p='[{"op": "replace", "path": "/spec/rules/0/http/paths/0/backend/service/name", "value": "autoclaude-new-backend"}]'

# Clean up old version
helm uninstall autoclaude -n autoclaude
helm rename autoclaude-new autoclaude -n autoclaude
```

**3. Canary Deployment**

Route percentage of traffic to new version:

```bash
# Install canary with 10% traffic
helm install autoclaude-canary . --namespace autoclaude \
  --set backend.replicas=1 \
  --set backend.ingress.enabled=false

# Update ingress to split traffic (10% to canary)
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: autoclaude-canary
  namespace: autoclaude
  annotations:
    nginx.ingress.kubernetes.io/canary: "true"
    nginx.ingress.kubernetes.io/canary-weight: "10"
spec:
  rules:
  - host: autoclaude.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: autoclaude-canary-backend
            port:
              number: 8000
EOF

# Monitor metrics, then gradually increase canary weight
# If successful, migrate all traffic to new version
# If failed, remove canary immediately
```

#### Air-Gapped Updates

For air-gapped Kubernetes clusters:

```bash
# On internet-connected machine:
helm fetch autoclaude/autoclaude --version 2.9.0
docker save -o autoclaude-images.tar \
  ghcr.io/obenner/autoclaude:2.9.0 \
  postgres:16-alpine \
  redis:7-alpine
# Transfer files to air-gapped cluster

# On air-gapped cluster:
# Load images into registry
docker load -i autoclaude-images.tar
# Or push to private registry

# Upgrade from local chart
helm upgrade autoclaude ./autoclaude-2.9.0.tgz \
  --namespace autoclaude \
  --values values.yaml \
  --wait
```

---

## Database Migrations

Database migrations are automatically applied during updates for most cases. However, major version updates may require manual intervention.

### Automatic Migrations

**Docker Compose:**
```bash
# Migrations run automatically on container startup
docker-compose up -d web-backend

# Check migration logs
docker-compose logs web-backend | grep -i migration
```

**Kubernetes/Helm:**
```bash
# Migrations run as init containers or startup probes
kubectl logs -n autoclaude deployment/autoclaude-backend -c migrations

# Check migration status
kubectl exec -n autoclaude deployment/autoclaude-backend -- \
  alembic current
```

### Manual Migrations

If automatic migrations fail or you need more control:

**Docker Compose:**
```bash
# Run migrations manually
docker exec autoclaude-backend alembic upgrade head

# Verify migration status
docker exec autoclaude-backend alembic current

# View migration history
docker exec autoclaude-backend alembic history
```

**Kubernetes/Helm:**
```bash
# Port-forward to backend
kubectl port-forward -n autoclaude deployment/autoclaude-backend 8080:8000

# In another terminal, run migrations
docker exec -it $(kubectl get pods -n autoclaude -l app.kubernetes.io/name=autoclaude -o jsonpath='{.items[0].metadata.name}') \
  alembic upgrade head
```

### Troubleshooting Migrations

**Migration Fails:**

```bash
# Check current migration version
docker exec autoclaude-backend alembic current

# View error details
docker-compose logs web-backend | tail -100

# Identify failed migration
docker exec autoclaude-backend alembic history

# If needed, downgrade to previous version
docker exec autoclaude-backend alembic downgrade -1

# Fix issue manually, then retry
docker exec autoclaude-backend alembic upgrade head
```

**Schema Conflicts:**

If you have custom schema modifications:

```bash
# Export your database schema
docker exec autoclaude-postgres pg_dump -U postgres --schema-only autoclaude > schema.sql

# Create custom migration branch
docker exec autoclaude-backend alembic revision --autogenerate -m "Custom changes"

# Edit migration to preserve your changes
# Apply migration
docker exec autoclaude-backend alembic upgrade head
```

---

## Rollback Procedures

If an update causes issues, roll back to the previous version.

### Docker Compose Rollback

**Quick Rollback:**

```bash
# Stop services
docker-compose down

# Restore previous docker-compose.yml
cp docker-compose.yml.backup docker-compose.yml

# Pull previous image tags
# Edit docker-compose.yml to use previous image tags:
# web-backend:
#   image: ghcr.io/obenner/autoclaude:2.8.0

# Start services
docker-compose up -d

# Verify
docker-compose ps
docker-compose logs --tail=50 web-backend
```

**Database Rollback:**

```bash
# Stop backend
docker-compose stop web-backend

# Restore database backup
cat backup-YYYYMMDD.sql | docker exec -i autoclaude-postgres psql -U postgres -d autoclaude

# Start backend
docker-compose start web-backend
```

**Complete Rollback with Data:**

```bash
# Stop all services
docker-compose down -v

# Restore volumes
docker run --rm -v autoclaude_postgres_data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/postgres-data-backup.tar.gz"

docker run --rm -v autoclaude_redis_data:/data -v $(pwd):/backup \
  alpine sh -c "cd /data && tar xzf /backup/redis-data-backup.tar.gz"

# Restore docker-compose.yml
cp docker-compose.yml.backup docker-compose.yml

# Start services
docker-compose up -d
```

### Kubernetes/Helm Rollback

**Quick Rollback:**

```bash
# View release history
helm history autoclaude -n autoclaude

# Rollback to previous release
helm rollback autoclaude -n autoclaude

# Rollback to specific revision
helm rollback autoclaude 5 -n autoclaude

# Wait for rollback to complete
kubectl rollout status deployment/autoclaude-backend -n autoclaude

# Verify
helm list -n autoclaude
kubectl get pods -n autoclaude
```

**Rollback with Values:**

```bash
# Rollback and restore previous values
helm rollback autoclaude 5 -n autoclaude \
  --recreate-pods \
  --wait

# Or reinstall previous version with backup values
helm uninstall autoclaude -n autoclaude
helm install autoclaude autoclaude/autoclaude \
  --namespace autoclaude \
  --version 2.8.0 \
  --values autoclaude-values-backup.yaml \
  --wait
```

**Database Rollback:**

```bash
# Restore database backup
kubectl exec -i deployment/autoclaude-postgres -n autoclaude -- \
  psql -U postgres -d autoclaude < backup-YYYYMMDD.sql

# Verify database version
kubectl exec -it deployment/autoclaude-postgres -n autoclaude -- \
  psql -U postgres -d autoclaude -c "SELECT version FROM alembic_version;"
```

**Complete Disaster Recovery:**

```bash
# Uninstall current release
helm uninstall autoclaude -n autoclaude

# Restore PVCs from backup
# (Use your cloud provider's snapshot/restore tools)
kubectl restore pvc/autoclaude-postgres-data --from-snapshot postgres-snap-YYYYMMDD
kubectl restore pvc/autoclaude-redis-data --from-snapshot redis-snap-YYYYMMDD

# Reinstall previous version
helm install autoclaude autoclaude/autoclaude \
  --namespace autoclaude \
  --version 2.8.0 \
  --values autoclaude-values-backup.yaml \
  --wait
```

---

## Update Automation

Automate updates to reduce manual effort and human error.

### Docker Compose Automation

**Automated Update Script:**

See `infrastructure/update-docker.sh` for a complete update automation script.

**Basic automated update:**
```bash
#!/bin/bash
set -e

# Configuration
AUTOCLAUDE_DIR="/opt/autoclaude"
BACKUP_DIR="/opt/autoclaude/backups"
COMPOSE_FILE="$AUTOCLAUDE_DIR/docker-compose.yml"

# Create backup
mkdir -p "$BACKUP_DIR"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

echo "Creating backup..."
docker exec autoclaude-postgres pg_dump -U postgres autoclaude > \
  "$BACKUP_DIR/backup-$BACKUP_DATE.sql"

# Pull new images
echo "Pulling new images..."
cd "$AUTOCLAUDE_DIR"
docker-compose -f "$COMPOSE_FILE" pull

# Update services
echo "Updating services..."
docker-compose -f "$COMPOSE_FILE" up -d

# Verify health
echo "Verifying health..."
sleep 30
docker-compose ps | grep "healthy" || {
  echo "Health check failed! Rolling back..."
  docker-compose -f "$COMPOSE_FILE" down
  cat "$BACKUP_DIR/backup-$BACKUP_DATE.sql" | \
    docker exec -i autoclaude-postgres psql -U postgres -d autoclaude
  docker-compose -f "$COMPOSE_FILE" up -d
  exit 1
}

echo "Update successful!"
```

**Cron-based updates:**
```bash
# Add to crontab for weekly updates
# 0 2 * * 0 /opt/autoclaude/scripts/update.sh >> /var/log/autoclaude-update.log 2>&1
```

### Kubernetes/Helm Automation

**Automated Upgrade Script:**

See `infrastructure/update-helm.sh` for a complete Helm automation script.

**Basic automated upgrade:**
```bash
#!/bin/bash
set -e

# Configuration
RELEASE_NAME="autoclaude"
NAMESPACE="autoclaude"
CHART_REPO="autoclaude/autoclaude"
VALUES_FILE="autoclaude-values.yaml"
BACKUP_DIR="/opt/autoclaude/backups"

# Create backup
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
echo "Creating backup..."
mkdir -p "$BACKUP_DIR"
kubectl exec -n "$NAMESPACE" deployment/autoclaude-postgres -- \
  pg_dump -U postgres autoclaude > "$BACKUP_DIR/backup-$BACKUP_DATE.sql"
helm get values "$RELEASE_NAME" -n "$NAMESPACE" > \
  "$BACKUP_DIR/values-$BACKUP_DATE.yaml"

# Update chart repository
echo "Updating chart repository..."
helm repo update

# Get current version
CURRENT_VERSION=$(helm list -n "$NAMESPACE" -o json | \
  jq -r ".[] | select(.name == \"$RELEASE_NAME\") | .app_version")

# Get latest version
LATEST_VERSION=$(helm search repo "$CHART_REPO" -o json | \
  jq -r ".[0].version")

echo "Current version: $CURRENT_VERSION"
echo "Latest version: $LATEST_VERSION"

if [ "$CURRENT_VERSION" = "$LATEST_VERSION" ]; then
  echo "Already up to date!"
  exit 0
fi

# Upgrade
echo "Upgrading to $LATEST_VERSION..."
helm upgrade "$RELEASE_NAME" "$CHART_REPO" \
  --namespace "$NAMESPACE" \
  --version "$LATEST_VERSION" \
  --values "$VALUES_FILE" \
  --wait \
  --timeout 10m || {
    echo "Upgrade failed! Rolling back..."
    helm rollback "$RELEASE_NAME" -n "$NAMESPACE"
    exit 1
  }

echo "Upgrade successful!"
```

**CI/CD Pipeline Integration:**

```yaml
# Example GitHub Actions workflow
name: Auto Update Auto Code

on:
  schedule:
    - cron: '0 2 * * 0'  # Weekly at 2 AM Sunday
  workflow_dispatch:

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - name: Configure kubectl
        uses: azure/setup-kubectl@v3

      - name: Update Auto Code
        run: |
          ./scripts/update-helm.sh
        env:
          KUBECONFIG: ${{ secrets.KUBECONFIG }}
```

---

## Troubleshooting

### Update Fails to Start

**Symptom:** Services fail to start after update.

**Docker Compose:**
```bash
# Check logs
docker-compose logs web-backend

# Common issues:
# 1. Port conflicts - Check ports with `netstat -tulpn`
# 2. Volume mounting errors - Check volume paths in docker-compose.yml
# 3. Environment variable errors - Compare .env with .env.example
```

**Kubernetes/Helm:**
```bash
# Check pod status
kubectl get pods -n autoclaude
kubectl describe pod <pod-name> -n autoclaude

# Check logs
kubectl logs <pod-name> -n autoclaude

# Common issues:
# 1. Image pull errors - Check image names/tags in values.yaml
# 2. Resource limits - Check resource requests/limits
# 3. ConfigMap/Secret errors - Verify configuration
```

### Health Checks Fail

**Symptom:** Services start but health checks fail.

**Investigation:**
```bash
# Docker Compose
docker-compose ps
docker exec autoclaude-backend curl http://localhost:8000/health

# Kubernetes
kubectl get pods -n autoclaude
kubectl describe pod <pod-name> -n autoclaude
kubectl logs <pod-name> -n autoclaude
```

**Common Causes:**
- Database connection errors
- Migration failures
- Configuration errors
- Insufficient resources

### Migration Failures

**Symptom:** Database migration fails or hangs.

**Recovery:**
```bash
# Check current migration state
docker exec autoclaude-backend alembic current

# View migration logs
docker-compose logs web-backend | grep -i migration

# Manually run migration
docker exec autoclaude-backend alembic upgrade head

# If failed, downgrade and retry
docker exec autoclaude-backend alembic downgrade -1
docker exec autoclaude-backend alembic upgrade head
```

### Rollback Failures

**Symptom:** Rollback procedure fails.

**Docker Compose:**
```bash
# Manual rollback
docker-compose down
# Manually edit docker-compose.yml to use previous image tags
docker-compose up -d

# If database restore fails
docker-compose stop web-backend
cat backup-YYYYMMDD.sql | docker exec -i autoclaude-postgres psql -U postgres autoclaude
docker-compose start web-backend
```

**Kubernetes/Helm:**
```bash
# Force rollback
helm rollback autoclaude --force -n autoclaude

# If Helm rollback fails, manual reinstall
helm uninstall autoclaude -n autoclaude
helm install autoclaude autoclaude/autoclaude \
  --namespace autoclaude \
  --version 2.8.0 \
  --values autoclaude-values-backup.yaml
```

---

## Best Practices

### Update Strategy

1. **Test First:** Always test updates in a non-production environment
2. **Schedule Updates:** Plan updates during low-traffic periods
3. **Communicate:** Notify users of scheduled maintenance windows
4. **Monitor:** Watch logs and metrics during and after updates
5. **Document:** Record update results and any issues encountered

### Backup Strategy

1. **Automated Backups:** Set up automated daily backups
2. **Off-site Storage:** Store backups in a separate location
3. **Test Restores:** Periodically test backup restoration procedures
4. **Retention Policy:** Keep backups for at least 30 days

### Rollback Strategy

1. **Quick Rollback:** Aim for rollback time under 15 minutes
2. **Rollback Triggers:** Define clear criteria for when to rollback
3. **Post-Rollback Analysis:** Investigate why the update failed
4. **Recovery Plan:** Document steps to recover from rollback

### Monitoring

**Key Metrics to Monitor During Updates:**
- Pod/container health status
- Response times
- Error rates
- Database connection counts
- Resource utilization (CPU, memory, disk)

**Alerts to Configure:**
- Health check failures
- High error rates
- Migration failures
- Resource exhaustion

---

## Additional Resources

- [Self-Hosted Deployment Guide](SELF_HOSTED_DEPLOYMENT.md) - Initial deployment instructions
- [Troubleshooting Guide](TROUBLESHOOTING.md) - Common issues and solutions
- [Release Notes](https://github.com/OBenner/Auto-Coding/releases) - Update notes and breaking changes
- [GitHub Issues](https://github.com/OBenner/Auto-Coding/issues) - Report bugs or request features

---

**Questions or issues?** Open a [GitHub discussion](https://github.com/OBenner/Auto-Coding/discussions) or [issue](https://github.com/OBenner/Auto-Coding/issues).
