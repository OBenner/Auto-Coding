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

### Load Testing

**Why Load Test?**
- Validate deployment capacity before production
- Identify performance bottlenecks
- Establish baseline metrics
- Test autoscaling behavior
- Verify high availability configuration

**Load Testing Tools:**

| Tool | Best For | Complexity |
|------|----------|------------|
| **Locust** | Python-based, distributed testing | Medium |
| **k6** | Scriptable, modern, developer-friendly | Low |
| **Apache JMeter** | Comprehensive, GUI-based | High |
| **hey** | Quick CLI-based testing | Low |

**Load Testing Scenarios:**

1. **Baseline Test (Single User):**
```bash
# Establish baseline performance
hey -n 100 -c 1 https://autoclaude.example.com/api/health
# Expected: <200ms response time, 0% errors
```

2. **Ramp-Up Test (Gradual Load):**
```bash
# Gradually increase load from 1 to 50 users over 5 minutes
locust -f loadtest.py --headless --users 50 --spawn-rate 1 --run-time 5m
# Monitor: CPU, memory, response times, error rate
```

3. **Sustained Load Test (Steady State):**
```bash
# Test sustained load for 30 minutes
hey -n 18000 -c 10 https://autoclaude.example.com/api/specs
# Monitor: Memory leaks, connection pool exhaustion
```

4. **Peak Load Test (Maximum Capacity):**
```bash
# Test with expected peak concurrent users
hey -n 1000 -c 50 https://autoclaude.example.com/api/specs
# Target: <1s response time, <1% error rate
```

5. **Spike Test (Sudden Load Increase):**
```bash
# Simulate sudden traffic spike
hey -n 5000 -c 100 -z 30s https://autoclaude.example.com/api/specs
# Monitor: Autoscaling response, service degradation
```

**Example Locust Test Script:**
```python
# locustfile.py
from locust import HttpUser, task, between

class AutoClaudeUser(HttpUser):
    wait_time = between(1, 3)

    def on_start(self):
        # Login before running tasks
        response = self.client.post("/api/auth/login", json={
            "email": "test@example.com",
            "password": "password123"
        })
        self.token = response.json()["access_token"]

    @task(3)
    def view_specs(self):
        self.client.get("/api/specs", headers={
            "Authorization": f"Bearer {self.token}"
        })

    @task(2)
    def create_spec(self):
        self.client.post("/api/specs", json={
            "task": "Test task for load testing",
            "complexity": "simple"
        }, headers={
            "Authorization": f"Bearer {self.token}"
        })

    @task(1)
    def view_repositories(self):
        self.client.get("/api/repositories", headers={
            "Authorization": f"Bearer {self.token}"
        })
```

**Load Testing Metrics to Track:**

| Metric | Target | Critical Threshold |
|--------|--------|-------------------|
| **Response Time (p50)** | <200ms | >500ms |
| **Response Time (p95)** | <500ms | >1000ms |
| **Response Time (p99)** | <1000ms | >2000ms |
| **Error Rate** | <0.1% | >1% |
| **Throughput** | >100 req/s | <50 req/s |
| **CPU Usage** | <70% | >90% |
| **Memory Usage** | <80% | >95% |

**Load Testing Checklist:**
- [ ] Test against staging environment first
- [ ] Use realistic test data (not production data)
- [ ] Simulate realistic user behavior (think time, navigation patterns)
- [ ] Monitor all services (backend, database, redis)
- [ ] Test during off-peak hours if using shared infrastructure
- [ ] Document baseline metrics for comparison
- [ ] Test autoscaling behavior (if enabled)
- [ ] Test failover scenarios (if HA configured)
- [ ] Review database query performance during load
- [ ] Verify no memory leaks or resource exhaustion

**Interpreting Results:**

| Symptom | Likely Cause | Solution |
|---------|--------------|----------|
| High CPU, low throughput | CPU-bound workload | Scale horizontally, optimize code |
| High memory, OOM kills | Memory leak or insufficient memory | Increase limits, investigate memory usage |
| Slow queries (p95 >1s) | Database bottleneck | Optimize queries, add indexes, scale DB |
| High error rate (5xx) | Service overload or unhandled errors | Scale replicas, check logs for errors |
| Connection timeouts | Database connection pool exhaustion | Increase pool size, add replicas |

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

### Common Bottlenecks

**Identifying Bottlenecks:**

Use monitoring tools to identify the limiting factor in your deployment:

```bash
# Kubernetes: Check resource usage
kubectl top pods
kubectl top nodes

# Docker Compose: Check container stats
docker stats

# Database: Check slow queries
docker exec postgres psql -U postgres -d autoclaude -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"

# Backend: Check application logs
kubectl logs -l app=autoclaude,component=backend --tail=100
```

**1. Database Bottlenecks**

**Symptoms:**
- High CPU on PostgreSQL container/pod
- Slow query responses (>500ms p95)
- Database connection pool exhaustion
- High disk I/O wait

**Common Causes:**
| Cause | Detection | Solution |
|-------|-----------|----------|
| Missing indexes | `EXPLAIN ANALYZE` shows seq scans | Add indexes on frequently queried columns |
| N+1 queries | Database query count > HTTP requests | Use eager loading (`joinedload`) |
| Large result sets | Queries return >1000 rows | Implement pagination, limit fields |
| Connection exhaustion | "Pool exhausted" errors | Increase pool size, add PgBouncer |
| Lock contention | High `lock waits` in pg_stat | Reduce transaction duration, optimize queries |

**Solutions:**

```sql
-- 1. Add indexes for frequently queried columns
CREATE INDEX CONCURRENTLY idx_users_email ON users(email);
CREATE INDEX CONCURRENTLY idx_specs_user_id ON specs(user_id);
CREATE INDEX CONCURRENTLY idx_specs_created_at ON specs(created_at DESC);

-- 2. Analyze slow queries
SELECT query, calls, mean_exec_time, total_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

-- 3. Check for missing indexes
SELECT schemaname, tablename, attname, n_distinct, correlation
FROM pg_stats
WHERE schemaname = 'public'
ORDER BY n_distinct DESC;

-- 4. Monitor connection pool
SELECT count(*), state
FROM pg_stat_activity
GROUP BY state;
```

**Scaling PostgreSQL:**
- Vertical: Increase CPU/memory (up to 8 cores, 16GiB)
- Horizontal: Add read replicas for reporting/analytics
- Connection pooling: Deploy PgBouncer (1:100 connection ratio)

**2. Redis Bottlenecks**

**Symptoms:**
- High memory usage (>90%)
- Low cache hit ratio (<80%)
- Slow Redis operations (>10ms)
- Eviction of active keys

**Common Causes:**
| Cause | Detection | Solution |
|-------|-----------|----------|
| Memory exhaustion | `used_memory > maxmemory` | Increase maxmemory, enable eviction policy |
| Large keys | `MEMORY USAGE key` shows large values | Compress values, shard data |
| Too many connections | `connected_clients > 1000` | Use connection pooling, reduce timeout |
| Expired keys not evicting | Keys accumulate | Set appropriate TTL, enable active expiration |

**Solutions:**

```bash
# 1. Check memory usage
redis-cli INFO memory | grep used_memory_human

# 2. Check largest keys
redis-cli --bigkeys

# 3. Check cache hit ratio
redis-cli INFO stats | grep keyspace_hits
# Calculate: hits / (hits + misses) = hit ratio
# Target: >80%

# 4. Enable memory optimization
redis-cli CONFIG SET maxmemory-policy allkeys-lru
redis-cli CONFIG SET maxmemory 256mb

# 5. Check slow operations
redis-cli SLOWLOG GET 10
```

**Scaling Redis:**
- Vertical: Increase memory (up to 8GiB effective)
- Horizontal: Use Redis Cluster (3+ master nodes)
- Separate instances: Use different Redis instances for cache, sessions, and pub/sub

**3. Backend Bottlenecks**

**Symptoms:**
- High CPU usage on backend pods/containers
- High memory usage with OOM kills
- Slow API responses (>500ms p95)
- High request queueing

**Common Causes:**
| Cause | Detection | Solution |
|-------|-----------|----------|
| Insufficient replicas | CPU >80%, memory >85% | Increase replica count |
| Memory leaks | Memory grows over time | Restart pods, investigate with memory profiler |
| Synchronous operations | Blocking I/O in request handlers | Use async/await, offload to background tasks |
| Large request payloads | Requests >10MB | Implement pagination, limit payload size |
| No connection pooling | New connection per request | Configure connection pooling |

**Solutions:**

```python
# 1. Enable connection pooling
from sqlalchemy.pool import QueuePool

engine = create_engine(
    settings.DATABASE_URL,
    poolclass=QueuePool,
    pool_size=20,  # Per worker
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 2. Use async operations
@app.get("/api/specs")
async def get_specs():
    # Use async database queries
    specs = await db.execute(select(Spec))
    return specs

# 3. Implement caching
from functools import lru_cache

@lru_cache(maxsize=1000)
def get_expensive_operation(key):
    # Expensive computation
    return result

# 4. Use background tasks for long operations
from fastapi import BackgroundTasks

@app.post("/api/specs")
async def create_spec(spec: SpecCreate, background_tasks: BackgroundTasks):
    db_spec = create_spec_in_db(spec)
    background_tasks.add_task(process_spec_async, db_spec.id)
    return db_spec
```

**Scaling Backend:**
- Vertical: Increase CPU/memory requests/limits
- Horizontal: Increase replica count (2-10 replicas)
- Autoscaling: Enable HPA with CPU/memory targets

**4. Network Bottlenecks**

**Symptoms:**
- High latency between services (>10ms)
- Packet loss or retransmissions
- Bandwidth saturation
- Connection timeouts

**Common Causes:**
| Cause | Detection | Solution |
|-------|-----------|----------|
| Network latency | `ping` shows >10ms between pods | Use same node/zone affinity |
| Bandwidth limits | Interface at 100% utilization | Upgrade to 10 Gbps network |
| DNS resolution delays | Slow DNS lookups | Use local DNS cache, CoreDNS |
| MTU issues | Packet fragmentation | Adjust MTU size (usually 9000 for internal) |

**Solutions:**

```bash
# 1. Test network latency between pods
kubectl exec -it backend-pod -- ping postgres-service

# 2. Check bandwidth
kubectl exec -it backend-pod -- ifstat

# 3. Check DNS resolution time
kubectl exec -it backend-pod -- time nslookup postgres-service

# 4. Use node affinity for low latency
# In values.yaml:
backend:
  nodeAffinity:
    requiredDuringSchedulingIgnoredDuringExecution:
      nodeSelectorTerms:
      - matchExpressions:
        - key: topology.kubernetes.io/zone
          operator: In
          values:
          - us-east-1a
```

**5. Storage Bottlenecks**

**Symptoms:**
- High disk I/O wait (>10%)
- Slow disk reads/writes
- Disk space running out (>80% used)
- High iowait in top/htop

**Common Causes:**
| Cause | Detection | Solution |
|-------|-----------|----------|
| Slow storage | fstrim shows <100 MB/s | Use NVMe SSD instead of HDD |
| Insufficient IOPS | I/O wait >10% | Upgrade to higher IOPS storage class |
| Full disk | df -h shows >80% used | Expand PVC, implement log rotation |
- Fragmentation | High seek times | Reclaim space, optimize database |

**Solutions:**

```bash
# 1. Check disk performance
kubectl exec -it postgres-pod -- hdparm -Tt /dev/var-lib-postgresql

# 2. Check disk I/O
kubectl exec -it postgres-pod -- iostat -x 1

# 3. Check disk usage
kubectl exec -it postgres-pod -- df -h

# 4. Expand PVC (if supported)
kubectl patch pvc postgres-data -p '{"spec":{"resources":{"requests":{"storage":"100Gi"}}}}'

# 5. Enable storage IOPS optimization
# In storage class:
allowVolumeExpansion: true
parameters:
  type: pd-ssd  # GKE
  iops-per-gb: "10"  # AWS EBS io1
```

**Preventing Storage Bottlenecks:**
- Use fast SSD/NVMe storage for databases
- Allocate 2-3x expected storage needs
- Implement log rotation (prevent unbounded growth)
- Archive old data regularly
- Monitor disk usage trends

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
