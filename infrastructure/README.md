# Infrastructure Directory

Self-hosted deployment resources for Auto Code, including Kubernetes manifests, Helm charts, deployment scripts, and documentation.

## Overview

This directory contains everything needed to deploy Auto Code on your own infrastructure. Self-hosting ensures complete data privacy and control, making it ideal for enterprises, privacy-conscious teams, and air-gapped environments.

**Deployment Options:**
- **Docker Compose** - Single-server deployment, quick to set up
- **Kubernetes/Helm** - Scalable, production-ready, high-availability

## Directory Structure

| Directory/File | Purpose |
|----------------|---------|
| **[helm/](helm/)** | Helm chart for Kubernetes deployments |
| **[k8s/](k8s/)** | Raw Kubernetes manifests (for reference/manual deployment) |
| **[deploy-docker.sh](deploy-docker.sh)** | Automated Docker Compose deployment script |
| **[deploy-helm.sh](deploy-helm.sh)** | Automated Helm deployment script |
| **[update-docker.sh](update-docker.sh)** | Docker Compose update automation script |
| **[update-helm.sh](update-helm.sh)** | Helm upgrade automation script |
| **[RESOURCE_REQUIREMENTS.md](RESOURCE_REQUIREMENTS.md)** | Hardware specs, sizing, and performance tuning |

### Helm Chart (`helm/autoclaude/`)

Production-ready Helm chart for deploying Auto Code on Kubernetes:

| File | Purpose |
|------|---------|
| **Chart.yaml** | Chart metadata and dependencies |
| **values.yaml** | Default configuration values |
| **templates/** | Kubernetes resource templates |
| - `templates/_helpers.tpl` | Reusable template functions |
| - `templates/deployment.yaml` | Deployment manifests (Backend, PostgreSQL, Redis) |
| - `templates/service.yaml` | Service definitions |
| - `templates/configmap.yaml` | Application configuration |
| - `templates/secrets.yaml` | Sensitive data (passwords, API keys) |
| - `templates/ingress.yaml` | Ingress with TLS support |
| - `templates/NOTES.txt` | Post-installation instructions |

### Kubernetes Manifests (`k8s/`)

Raw Kubernetes manifests for reference or manual deployment:

| File | Purpose |
|------|---------|
| **deployment.yaml** | Backend, PostgreSQL, and Redis deployments |
| **service.yaml** | Service definitions |
| **configmap.yaml** | Application configuration |
| **secrets.example.yaml** | Secret template (copy and customize) |
| **ingress.yaml** | Ingress with TLS configuration |

## Quick Start

### Docker Compose Deployment

**Quick deployment with helper script:**
```bash
# Interactive deployment
bash infrastructure/deploy-docker.sh

# Quick deployment with defaults
bash infrastructure/deploy-docker.sh --quick
```

**Manual deployment:**
```bash
cd infrastructure
docker-compose up -d
```

See [Deployment Guide](../guides/SELF_HOSTED_DEPLOYMENT.md#docker-compose-deployment) for details.

### Kubernetes/Helm Deployment

**Quick deployment with helper script:**
```bash
# Interactive deployment
bash infrastructure/deploy-helm.sh

# Quick deployment with defaults
bash infrastructure/deploy-helm.sh --quick
```

**Manual deployment:**
```bash
# Install Helm chart
helm install autoclaude infrastructure/helm/autoclaude

# Install with custom values
helm install autoclaude infrastructure/helm/autoclaude \
  --values infrastructure/helm/autoclaude/values.yaml \
  --set backend.image.tag=latest \
  --set ingress.enabled=true
```

See [Deployment Guide](../guides/SELF_HOSTED_DEPLOYMENT.md#kubernetesthelm-deployment) for details.

## Configuration

### Environment Variables

Key configuration options for self-hosted deployments:

| Variable | Purpose | Default | Required |
|----------|---------|---------|----------|
| `SECRET_KEY` | JWT signing key | Auto-generated | Yes |
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://...` | Yes |
| `REDIS_URL` | Redis connection string | `redis://...` | Yes |
| `ANTHROPIC_API_KEY` | Claude SDK API key | - | Yes* |
| `DISABLE_TELEMETRY` | Disable telemetry for air-gapped | `false` | No |
| `CORS_ORIGINS` | Allowed CORS origins | `*` | No |

*Required unless using local LLMs.

See [Configuration Guide](../guides/SELF_HOSTED_DEPLOYMENT.md#configuration) for complete reference.

### Helm Values

Configure Helm chart via `values.yaml` or `--set` flags:

```yaml
backend:
  image:
    repository: ghcr.io/obenner/auto-claude/web-backend
    tag: latest
  replicas: 1
  resources:
    requests:
      cpu: 500m
      memory: 512Mi
    limits:
      cpu: 2000m
      memory: 2Gi

postgresql:
  enabled: true
  persistence:
    size: 20Gi

redis:
  enabled: true
  persistence:
    size: 5Gi

ingress:
  enabled: true
  className: nginx
  hosts:
    - host: autoclaude.example.com
      paths:
        - path: /
          pathType: Prefix
```

## Updates and Upgrades

### Docker Compose Updates

```bash
# Automated update with backup
bash infrastructure/update-docker.sh

# Manual update
docker-compose pull
docker-compose up -d --force-recreate
```

### Helm Upgrades

```bash
# Automated upgrade with backup
bash infrastructure/update-helm.sh

# Manual upgrade
helm upgrade autoclaude infrastructure/helm/autoclaude

# Upgrade with new values
helm upgrade autoclaude infrastructure/helm/autoclaude \
  --values custom-values.yaml \
  --set backend.image.tag=v2.0.0
```

See [Update Guide](../guides/SELF_HOSTED_UPDATES.md) for comprehensive update procedures.

## Resource Requirements

### Minimum Specifications

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Backend | 500m | 512Mi | 1Gi (workspace) |
| PostgreSQL | 250m | 256Mi | 20Gi |
| Redis | 100m | 128Mi | 5Gi |
| **Total** | **850m** | **896Mi** | **26Gi** |

### Production Specifications

| Component | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| Backend (3 replicas) | 1500m | 1.5Gi | 1Gi |
| PostgreSQL (HA) | 500m | 2Gi | 100Gi |
| Redis (HA) | 250m | 512Mi | 20Gi |
| **Total** | **2250m** | **4Gi** | **121Gi** |

See [RESOURCE_REQUIREMENTS.md](RESOURCE_REQUIREMENTS.md) for detailed sizing, scaling, and performance tuning.

## Air-Gapped Deployment

For environments without internet access:

1. **Export images and charts:**
   ```bash
   # Export Docker images
   docker save ghcr.io/obenner/auto-claude/web-backend:latest -o autoclaude-images.tar

   # Export Helm chart
   helm package infrastructure/helm/autoclaude
   ```

2. **Transfer to air-gapped environment** (via sneakernet, secure file transfer)

3. **Load images and deploy:**
   ```bash
   # Load images
   docker load -i autoclaude-images.tar

   # Deploy with DISABLE_TELEMETRY=true
   export DISABLE_TELEMETRY=true
   docker-compose up -d
   ```

**CRITICAL:** Set `DISABLE_TELEMETRY=true` for air-gapped deployments to prevent connection timeouts and error logs.

See [Air-Gapped Deployment Guide](../guides/SELF_HOSTED_DEPLOYMENT.md#air-gapped-environments) for detailed instructions.

## Security Considerations

### Secrets Management

**Docker Compose:**
```bash
# Generate secrets
openssl rand -hex 32 > .env.secret_key

# Use in .env
SECRET_KEY=$(cat .env.secret_key)
```

**Kubernetes:**
```bash
# Create secret from literal
kubectl create secret generic autoclaude-secrets \
  --from-literal=secret-key=$(openssl rand -hex 32) \
  --from-literal=postgres-password=$(openssl rand -hex 16)

# Create secret from file
kubectl create secret generic autoclaude-secrets \
  --from-env-file=infrastructure/k8s/secrets.example.yaml
```

### Network Security

| Port | Service | Purpose |
|------|---------|---------|
| 8000 | Backend API | HTTP API (use TLS in production) |
| 5432 | PostgreSQL | Database (internal only) |
| 6379 | Redis | Cache (internal only) |

**Recommendations:**
- Use ingress with TLS for external access
- Restrict database and Redis to internal cluster traffic
- Enable NetworkPolicies in Kubernetes
- Use pod security contexts

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| Services fail to start | Check resource limits in `RESOURCE_REQUIREMENTS.md` |
| Database migration errors | Verify PostgreSQL connection string and credentials |
| High memory usage | Tune `postgresql.shared_buffers` and worker counts |
| Image pull errors | Check image tags, registry credentials, network access |
| Helm chart fails to install | Run `helm lint` and `helm template --debug` |

For comprehensive troubleshooting, see:
- [Deployment Guide - Troubleshooting](../guides/SELF_HOSTED_DEPLOYMENT.md#troubleshooting)
- [Update Guide - Troubleshooting](../guides/SELF_HOSTED_UPDATES.md#troubleshooting)

## Documentation

| Document | Description |
|----------|-------------|
| **[Deployment Guide](../guides/SELF_HOSTED_DEPLOYMENT.md)** | Complete self-hosted deployment instructions |
| **[Update Guide](../guides/SELF_HOSTED_UPDATES.md)** | Update and upgrade procedures |
| **[Resource Requirements](RESOURCE_REQUIREMENTS.md)** | Hardware specs, sizing, and performance tuning |

## Architecture

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
└─────────────────────────────────────────────────────────────┘
         │
         ▼ (Optional, controlled by you)
   ┌────────────────┐
   │   External     │
   │  AI Provider   │
   │  (Claude SDK)  │
   └────────────────┘
```

## Support and Contributing

- **Issues**: Report bugs and request features via [GitHub Issues](https://github.com/OBenner/Auto-Coding/issues)
- **Contributions**: See [CONTRIBUTING.md](../CONTRIBUTING.md) for contribution guidelines
- **Documentation**: See [docs/STYLE_GUIDE.md](../docs/STYLE_GUIDE.md) for documentation conventions

## License

This infrastructure is part of Auto Code and is licensed under [AGPL-3.0](../LICENSE). See [LICENSE](../LICENSE) for details.
