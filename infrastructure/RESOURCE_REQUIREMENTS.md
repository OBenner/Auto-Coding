# Resource Requirements - Auto Code Self-Hosted

This document outlines hardware and infrastructure requirements for running Auto Code in self-hosted environments. Requirements vary based on deployment method, team size, and usage patterns.

## Table of Contents

- [Overview](#overview)
- [Deployment Methods](#deployment-methods)
- [Hardware Requirements](#hardware-requirements)
  - [Docker Compose Requirements](#docker-compose-requirements)
  - [Kubernetes Requirements](#kubernetes-requirements)
- [Service-Specific Resources](#service-specific-resources)
- [Storage Requirements](#storage-requirements)
- [Network Requirements](#network-requirements)
- [Scaling Considerations](#scaling-considerations)
- [Performance Tuning](#performance-tuning)
- [Sizing Examples](#sizing-examples)
- [Monitoring Resource Usage](#monitoring-resource-usage)

---

## Overview

Auto Code consists of three main services, each with distinct resource needs:

| Service | Purpose | Base CPU | Base Memory | Storage Type |
|---------|---------|----------|-------------|--------------|
| **Backend** | API server, agent orchestration | 500m - 1000m | 512Mi - 1Gi | Ephemeral |
| **PostgreSQL** | User data, specs, metadata | 250m - 500m | 256Mi - 512Mi | Persistent |
| **Redis** | Caching, sessions | 100m - 200m | 128Mi - 256Mi | Persistent |

**Total Minimum Resources:**
- CPU: 850m - 1700m
- Memory: 896Mi - 1.75Gi
- Storage: 15Gi+ (PostgreSQL + Redis)

**Resource planning depends on:**
- Number of concurrent users
- Size of repositories being processed
- Frequency of spec creation and builds
- Desired performance and response times

---

## Deployment Methods

### Docker Compose Deployment

**Use Case:** Single-server deployment, small teams (1-10 users), development/testing

**Pros:**
- Simple setup on a single machine
- Lower hardware overhead (no Kubernetes control plane)
- Easier to troubleshoot
- Suitable for vertical scaling

**Cons:**
- Single point of failure
- Manual scaling (vertical only)
- Limited high-availability options

### Kubernetes/Helm Deployment

**Use Case:** Production deployments, larger teams (10+ users), high availability requirements

**Pros:**
- Horizontal scaling
- Built-in high availability
- Rolling updates and rollbacks
- Resource management and scheduling
- Self-healing capabilities

**Cons:**
- Higher resource overhead (Kubernetes control plane)
- More complex setup and maintenance
- Requires cluster management expertise

---

## Hardware Requirements

### Docker Compose Requirements

#### Minimum Configuration

**Suitable for:** Development, testing, 1-3 concurrent users

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **Memory** | 4 GiB | 8 GiB |
| **Storage** | 20 GiB SSD | 50 GiB SSD |
| **Network** | 100 Mbps | 1 Gbps |

**Expected Performance:**
- Response time: 500ms - 2s
- Concurrent users: 1-3
- Small repositories (<100K LOC)
- Occasional spec creation

#### Recommended Configuration

**Suitable for:** Small teams, 3-10 concurrent users

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 4 cores | 8 cores |
| **Memory** | 8 GiB | 16 GiB |
| **Storage** | 50 GiB SSD | 100 GiB NVMe SSD |
| **Network** | 1 Gbps | 10 Gbps |

**Expected Performance:**
- Response time: 200ms - 500ms
- Concurrent users: 3-10
- Medium repositories (100K - 500K LOC)
- Regular spec creation and builds

#### Production Configuration

**Suitable for:** Larger teams, 10-20 concurrent users

| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 8 cores | 16 cores |
| **Memory** | 16 GiB | 32 GiB |
| **Storage** | 100 GiB NVMe SSD | 500 GiB NVMe SSD |
| **Network** | 10 Gbps | 10 Gbps |

**Expected Performance:**
- Response time: <200ms
- Concurrent users: 10-20
- Large repositories (500K - 1M LOC)
- Continuous spec creation and builds

---

### Kubernetes Requirements

#### Minimum Cluster Configuration

**Suitable for:** Small production deployments, 5-15 concurrent users

**Master Node (Control Plane):**
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 2 cores | 4 cores |
| **Memory** | 4 GiB | 8 GiB |
| **Storage** | 20 GiB SSD | 50 GiB SSD |

**Worker Node (Single Node):**
| Resource | Minimum | Recommended |
|----------|---------|-------------|
| **CPU** | 4 cores | 8 cores |
| **Memory** | 8 GiB | 16 GiB |
| **Storage** | 50 GiB SSD | 100 GiB SSD |

**Total Cluster:**
- CPU: 6 cores (2 master + 4 worker)
- Memory: 12 GiB (4 GiB master + 8 GiB worker)
- Storage: 70 GiB (20 GiB master + 50 GiB worker)

#### Recommended Production Cluster

**Suitable for:** Production deployments, 15-50 concurrent users, high availability

**Master Nodes (3 nodes for HA):**
| Resource | Per Node | Cluster Total |
|----------|----------|---------------|
| **CPU** | 4 cores | 12 cores |
| **Memory** | 8 GiB | 24 GiB |
| **Storage** | 50 GiB SSD | 150 GiB SSD |

**Worker Nodes (3 nodes):**
| Resource | Per Node | Cluster Total |
|----------|----------|---------------|
| **CPU** | 8 cores | 24 cores |
| **Memory** | 16 GiB | 48 GiB |
| **Storage** | 100 GiB SSD | 300 GiB SSD |

**Total Cluster:**
- CPU: 36 cores (12 master + 24 worker)
- Memory: 72 GiB (24 GiB master + 48 GiB worker)
- Storage: 450 GiB (150 GiB master + 300 GiB worker)

**Capacity:**
- Supports 2-3 backend replicas per worker node
- PostgreSQL and Redis distributed across nodes
- High availability with failover
- Horizontal scaling via additional worker nodes

---

## Service-Specific Resources

### Backend Service

**Base Resource Requirements:**
```yaml
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

**Memory Usage Factors:**
- Base memory: ~400Mi
- Per active user: +50-100Mi
- Per spec creation: +100-200Mi (temporary)
- Graphiti memory (enabled): +200-500Mi

**CPU Usage Factors:**
- Idle: 50-100m
- Per active user: +100-200m
- Spec creation: +500-800m (burst)
- Code analysis: +300-500m

**Scaling Guidelines:**
- 1 replica: 1-5 concurrent users
- 2 replicas: 5-15 concurrent users
- 3+ replicas: 15+ concurrent users

### PostgreSQL Database

**Base Resource Requirements:**
```yaml
resources:
  requests:
    memory: "256Mi"
    cpu: "250m"
  limits:
    memory: "512Mi"
    cpu: "500m"
```

**Memory Usage Factors:**
- Base memory: ~200Mi
- Shared buffers: 25% of total memory
- Effective cache: 75% of remaining memory
- Per active connection: +1-5Mi

**Storage Requirements:**
- Base installation: ~100Mi
- Per user: ~10-50Mi
- Per spec: ~5-20Mi
- Workspace metadata: ~100-500Mi per project
- Recommended growth: 2-3x current usage

**Performance Tuning:**
```bash
# For 512Mi memory limit
shared_buffers = 128Mi
effective_cache_size = 384Mi
maintenance_work_mem = 64Mi
work_mem = 16Mi
```

**Scaling Guidelines:**
- Single instance: Up to 50 concurrent connections
- For higher loads: Use connection pooling (PgBouncer)
- Consider read replicas for reporting/analysis

### Redis Cache

**Base Resource Requirements:**
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

**Memory Usage Factors:**
- Base memory: ~50Mi
- Per active session: ~1-5Mi
- Per cached result: ~100Ki - 1Mi
- WebSocket connections: ~10Ki per connection

**Storage Requirements:**
- AOF file: ~10-100Mi (depends on write load)
- RDB snapshots: ~5-50Mi
- Recommended growth: 2x current usage

**Scaling Guidelines:**
- Single instance: Up to 1000 concurrent connections
- For higher loads: Use Redis Cluster
- Consider separate Redis instances for different data types

---

## Storage Requirements

### Docker Compose Storage

**Local Volume Requirements:**
| Volume | Minimum | Recommended | Growth Rate |
|--------|---------|-------------|-------------|
| **PostgreSQL** | 10 GiB | 50 GiB | ~1 GiB/month |
| **Redis** | 5 GiB | 10 GiB | ~100 MiB/month |
| **Workspace Data** | 5 GiB | 50 GiB | ~5 GiB/month |

**Total Minimum:** 20 GiB
**Total Recommended:** 110 GiB

**Storage Performance:**
- Minimum: SSD with 500 IOPS
- Recommended: NVMe SSD with 3000+ IOPS
- Latency: <10ms read, <10ms write

### Kubernetes Storage

**Persistent Volume Claims:**
```yaml
# PostgreSQL PVC
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi  # Minimum
      storage: 50Gi  # Recommended

# Redis PVC
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 5Gi  # Minimum
      storage: 10Gi  # Recommended
```

**Storage Class Considerations:**
- **ReadWriteOnce**: Fast, block storage (AWS EBS, GCE PD, Azure Disk)
- **ReadWriteMany**: NFS, Ceph, GlusterFS (for distributed deployments)
- **Storage Class**: Use fast SSD storage classes for production

**Backup Storage:**
- Daily backups: ~2x current database size
- Weekly backups: ~4x current database size
- Retention: 30 days = ~10x current database size

---

## Network Requirements

### Bandwidth Requirements

**Per User (Average):**
- Idle: <1 Kbps
- Active browsing: 10-100 Kbps
- Spec creation: 1-5 Mbps (burst)
- Code analysis: 500 Kbps - 2 Mbps

**Cluster Internal Traffic:**
- Backend → PostgreSQL: 10-100 Mbps
- Backend → Redis: 10-50 Mbps
- Backend ↔ Backend (WebSocket): 1-10 Mbps per connection

**External Connectivity:**
- Users → Backend: 1-10 Mbps per user
- Backend → AI Provider (Claude SDK): 10-100 Mbps (if enabled)
- Backend → Git repositories: 1-10 Mbps per operation

### Latency Requirements

**Internal Cluster:**
- Backend → Database: <5ms
- Backend → Redis: <2ms
- Inter-pod communication: <10ms

**User Experience:**
- API response: <200ms
- Page load: <1s
- WebSocket: <50ms latency

**Recommended Network:**
- Minimum: 1 Gbps internal network
- Recommended: 10 Gbps internal network
- Low-latency switches (<1ms)

### Firewall Configuration

**Required Ports:**
| Port | Protocol | Service | Direction |
|------|----------|---------|-----------|
| 80 | TCP | HTTP (Ingress) | Inbound |
| 443 | TCP | HTTPS (Ingress) | Inbound |
| 8000 | TCP | Backend API | Internal |
| 5432 | TCP | PostgreSQL | Internal |
| 6379 | TCP | Redis | Internal |

**Network Policies (Kubernetes):**
```yaml
# Allow backend to access PostgreSQL
- from:
  - podSelector:
      matchLabels:
        app: autoclaude
        component: backend
  to:
  - podSelector:
      matchLabels:
        app: autoclaude
        component: database
  ports:
  - protocol: TCP
    port: 5432
```

---

## Scaling Considerations

### Vertical Scaling (Scale Up)

**When to Scale Vertically:**
- Small deployments (<20 users)
- Single-server deployments (Docker Compose)
- Before implementing horizontal scaling

**Scaling Factors:**
- CPU: 2x → 1.5-1.8x performance gain
- Memory: 2x → 1.8-2.0x capacity increase
- Storage: SSD → NVMe SSD → 2-3x IOPS improvement

**Limitations:**
- Single point of failure
- Diminishing returns after certain point
- Maximum CPU per container (typically 8-16 cores)

### Horizontal Scaling (Scale Out)

**When to Scale Horizontally:**
- Production deployments (>20 users)
- High availability requirements
- Kubernetes deployments

**Backend Scaling:**
```yaml
# Update replica count in values.yaml
backend:
  replicaCount: 3  # Scale to 3 replicas

# Enable autoscaling (HPA)
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80
```

**Scaling Factors:**
- 2 replicas: ~1.8x capacity (not 2x due to coordination overhead)
- 3 replicas: ~2.5x capacity
- 5+ replicas: Use autoscaling based on load

**Stateful Services (PostgreSQL, Redis):**
- Primary-replica replication
- Connection pooling (PgBouncer for PostgreSQL)
- Redis Cluster for horizontal scaling

### Load-Based Scaling

**Horizontal Pod Autoscaler (HPA) Configuration:**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: autoclaude-backend
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-backend
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

---

## Performance Tuning

### Backend Tuning

**Worker Processes:**
```python
# Adjust in deployment configuration
workers = (cpu_count * 2) + 1  # For CPU-bound
workers = 2 * cpu_count + 1     # For I/O-bound
```

**Connection Pooling:**
```python
# Database connection pool
pool_size = 20  # Per worker
max_overflow = 40  # Additional connections

# Redis connection pool
connection_pool_size = 50
```

**Memory Optimization:**
- Limit Graphiti memory usage: `GRAPHITI_MAX_MEMORY=2Gi`
- Cache size limits: `CACHE_MAX_SIZE=10000`
- Session timeout: `SESSION_TIMEOUT=3600` (1 hour)

### PostgreSQL Tuning

**Configuration for 512Mi Memory:**
```ini
# postgresql.conf
shared_buffers = 128Mi
effective_cache_size = 384Mi
maintenance_work_mem = 64Mi
work_mem = 16Mi
max_connections = 50
```

**Configuration for 2Gi Memory:**
```ini
shared_buffers = 512Mi
effective_cache_size = 1536Mi
maintenance_work_mem = 256Mi
work_mem = 64Mi
max_connections = 100
```

**Index Optimization:**
- Create indexes on frequently queried columns
- Use `EXPLAIN ANALYZE` to identify slow queries
- Reindex regularly: `REINDEX DATABASE autoclaude;`

### Redis Tuning

**Memory Management:**
```ini
# redis.conf
maxmemory 256mb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
```

**Persistence Options:**
- AOF (Append Only File): Better durability, more disk usage
- RDB (Snapshots): Less disk usage, potential data loss
- Hybrid: RDB for snapshots, AOF for real-time

---

## Sizing Examples

### Small Team (1-5 Users)

**Docker Compose Deployment:**
```
Hardware: 4-core CPU, 8 GiB RAM, 50 GiB SSD
Backend: 1 replica, 512Mi/1Gi, 500m/1000m CPU
PostgreSQL: 256Mi/512Mi, 250m/500m CPU, 10 GiB storage
Redis: 128Mi/256Mi, 100m/200m CPU, 5 GiB storage

Total: ~896 MiB memory, 850m CPU, 15 GiB storage
Expected: 200-500ms response time
```

### Medium Team (5-20 Users)

**Kubernetes Deployment:**
```
Hardware: 16-core CPU, 32 GiB RAM, 200 GiB SSD
Backend: 2 replicas, 1 Gi/2Gi each, 1000m/2000m CPU
PostgreSQL: 512Mi/1Gi, 500m/1000m CPU, 50 GiB storage
Redis: 256Mi/512Mi, 200m/400m CPU, 10 GiB storage

Total: ~2.75 GiB memory, 2.7 CPU cores, 60 GiB storage
Expected: 100-300ms response time
```

### Large Team (20-50 Users)

**Kubernetes Deployment with HPA:**
```
Hardware: 36-core CPU, 72 GiB RAM, 500 GiB SSD
Backend: 3-5 replicas (autoscaled), 1 Gi/2Gi each
PostgreSQL: 1 Gi/2 Gi, 1000m/2000m CPU, 100 GiB storage
Redis: 512Mi/1 Gi, 400m/800m CPU, 20 GiB storage

Total: ~5-9 GiB memory, 4-7 CPU cores, 120 GiB storage
Expected: <200ms response time
```

### Enterprise (50+ Users)

**Kubernetes Deployment with Full HA:**
```
Hardware: 3-node cluster (HA)
- Master: 3 nodes × 4 cores, 8 GiB RAM
- Worker: 3 nodes × 16 cores, 64 GiB RAM, 500 GiB SSD

Backend: 5-10 replicas (HPA 2-15)
PostgreSQL: Primary + 2 replicas (Patroni)
Redis: Redis Cluster (3 master + 3 replica)

Total: ~15-30 GiB memory, 10-20 CPU cores, 200 GiB storage
Expected: <100ms response time, 99.9% uptime
```

---

## Monitoring Resource Usage

### Key Metrics to Monitor

**Backend:**
- CPU usage (target: <70%)
- Memory usage (target: <80%)
- Request rate and response times
- Active user sessions
- Error rate

**PostgreSQL:**
- Database size and growth rate
- Connection count
- Query performance (slow queries)
- Replication lag (if using replicas)
- Disk I/O

**Redis:**
- Memory usage
- Hit ratio (target: >80%)
- Connection count
- Operations per second
- Key expiration rate

### Monitoring Tools

**Kubernetes:**
- Prometheus + Grafana for metrics
- Kubernetes Dashboard for cluster overview
- kubectl top pods for real-time usage

**Docker Compose:**
- docker stats for container resource usage
- Prometheus exporters (postgres_exporter, redis_exporter)
- Grafana for visualization

### Alerts

**Recommended Alerts:**
- CPU > 80% for 5 minutes
- Memory > 85% for 5 minutes
- Disk space > 80% used
- API response time > 1s
- Database connection errors
- Redis memory > 90%

---

## Next Steps

- [Self-Hosted Deployment Guide](../guides/SELF_HOSTED_DEPLOYMENT.md) - Complete deployment instructions
- [Self-Hosted Updates Guide](../guides/SELF_HOSTED_UPDATES.md) - Update and upgrade procedures
- [Helm Chart](./helm/autoclaude/README.md) - Kubernetes deployment with Helm
- [Docker Compose](../apps/web-backend/docker-compose.cloud.yml) - Single-server deployment

---

**Need help sizing your deployment?** Consider starting with the recommended configuration for your team size and scaling up based on actual usage patterns. Monitor resource usage for 1-2 weeks before production deployment to identify bottlenecks.
