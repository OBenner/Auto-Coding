# Kubernetes Deployment Guide

Comprehensive guide for deploying Auto Code on Kubernetes clusters using kubectl and Helm.

## Overview

Auto Code provides production-ready Kubernetes manifests and Helm charts for orchestrated deployment. This guide covers:

- **Kubectl Manifests** - Deploy using raw Kubernetes YAML files
- **Helm Charts** - Package management with configurable deployments
- **Persistent Storage** - PersistentVolumeClaims for data, worktrees, and databases
- **Health Checks** - Liveness and readiness probes
- **Auto-Scaling** - Horizontal Pod Autoscaler (HPA) configuration
- **Service Discovery** - ClusterIP, NodePort, and Ingress options

## Prerequisites

### Required
- **Kubernetes Cluster** 1.25+ (minikube, kind, GKE, EKS, AKS, or bare-metal)
- **kubectl** 1.25+ (configured to access your cluster)
- **Helm** 3.10+ (for Helm-based deployment)
- **Git** (for cloning the repository)

### Recommended
- **4+ CPU cores** - For running all services (backend, web-backend, postgres, redis)
- **8+ GB RAM** - PostgreSQL, Redis, and application pods
- **20+ GB persistent storage** - For PersistentVolumes
- **Ingress Controller** - nginx-ingress or traefik for external access
- **Cert Manager** - For TLS certificate management (optional)

### API Keys
- **Claude API** - OAuth token or API key (see [Authentication](#authentication))
- **Graphiti Memory** - OpenAI API key (or alternative provider)
- **Optional** - GitHub, Linear, GitLab tokens for integrations

### Verify Cluster Access

```bash
# Check kubectl is configured
kubectl cluster-info

# Verify you have admin permissions
kubectl auth can-i create deployments --all-namespaces

# Check available resources
kubectl get nodes
kubectl top nodes
```

## Quick Start

### Option 1: Deploy with kubectl

**Best for:**
- Simple deployments
- Custom configurations
- Learning Kubernetes

**Steps:**

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/Auto-Coding.git
cd Auto-Coding
```

#### 2. Create Namespace
```bash
kubectl create namespace auto-claude
```

#### 3. Create Secrets
```bash
# Create secrets from environment variables
kubectl create secret generic auto-claude-secrets \
  --from-literal=claude-oauth-token=your-oauth-token-here \
  --from-literal=openai-api-key=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx \
  --from-literal=secret-key=your-secret-key-here \
  --from-literal=database-url=postgresql://postgres:YOUR_PASSWORD@postgres-service:5432/autoclaude \
  --namespace auto-claude

# Optional: GitHub integration
kubectl create secret generic github-secrets \
  --from-literal=token=ghp_xxxxxxxxxxxxxxxxxxxxxxxx \
  --from-literal=client-id=your-client-id \
  --from-literal=client-secret=your-client-secret \
  --namespace auto-claude
```

#### 4. Create ConfigMap
```bash
# Create ConfigMap from file
kubectl create configmap auto-claude-config \
  --from-literal=GRAPHITI_ENABLED=true \
  --from-literal=GRAPHITI_LLM_PROVIDER=openai \
  --from-literal=CLAUDE_MODEL=claude-sonnet-4-5-20250929 \
  --from-literal=REDIS_HOST=redis-service \
  --from-literal=REDIS_PORT=6379 \
  --from-literal=HOST=0.0.0.0 \
  --from-literal=PORT=8000 \
  --from-literal=DEBUG=false \
  --from-literal=LOG_LEVEL=INFO \
  --namespace auto-claude
```

#### 5. Apply Manifests
```bash
# Apply all Kubernetes manifests
kubectl apply -f k8s/postgres.yaml --namespace auto-claude
kubectl apply -f k8s/redis.yaml --namespace auto-claude
kubectl apply -f k8s/backend.yaml --namespace auto-claude
kubectl apply -f k8s/web-backend.yaml --namespace auto-claude
kubectl apply -f k8s/web-frontend.yaml --namespace auto-claude
kubectl apply -f k8s/ingress.yaml --namespace auto-claude
```

#### 6. Wait for Pods
```bash
# Wait for all pods to be ready (may take 1-2 minutes)
kubectl wait --for=condition=ready pod --all -n auto-claude --timeout=300s

# Check pod status
kubectl get pods -n auto-claude
```

#### 7. Verify Deployment
```bash
# Check all resources
kubectl get all -n auto-claude

# Test web backend health
kubectl port-forward -n auto-claude svc/web-backend-service 8000:8000 &
curl http://localhost:8000/health

# View logs
kubectl logs -n auto-claude -l app=web-backend --tail=50
```

#### 8. Access Application
```bash
# Option 1: Port forwarding (development)
kubectl port-forward -n auto-claude svc/web-frontend-service 3000:3000
# Open http://localhost:3000

# Option 2: NodePort (if configured)
kubectl get svc -n auto-claude web-frontend-service
# Access via http://<node-ip>:<node-port>

# Option 3: Ingress (production)
# Access via configured ingress domain (e.g., https://autoclaude.yourdomain.com)
```

### Option 2: Deploy with Helm

**Best for:**
- Production deployments
- Easy configuration management
- Versioned releases
- Rollback capability

**Steps:**

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/Auto-Coding.git
cd Auto-Coding
```

#### 2. Create Namespace
```bash
kubectl create namespace auto-claude
```

#### 3. Create Secrets File
```bash
# Create values-secrets.yaml (DO NOT commit this file)
cat > values-secrets.yaml <<EOF
secrets:
  claudeOAuthToken: "your-oauth-token-here"
  openaiApiKey: "sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  secretKey: "your-secret-key-here"
  # Optional integrations
  githubToken: "ghp_xxxxxxxxxxxxxxxxxxxxxxxx"
  githubClientId: "your-client-id"
  githubClientSecret: "your-client-secret"
  linearApiKey: "lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  gitlabToken: "glpat-xxxxxxxxxxxxxxxxxxxx"
EOF

# Ensure it's in .gitignore
echo "values-secrets.yaml" >> .gitignore
```

#### 4. Install with Helm
```bash
# Install Auto Code chart with custom values
helm install auto-claude ./helm/auto-claude \
  --namespace auto-claude \
  --values values-secrets.yaml \
  --set webFrontend.ingress.enabled=true \
  --set webFrontend.ingress.hostname=autoclaude.yourdomain.com

# Wait for deployment
helm status auto-claude -n auto-claude
```

#### 5. Verify Installation
```bash
# Check Helm release
helm list -n auto-claude

# Check resources
kubectl get all -n auto-claude

# Test health
kubectl port-forward -n auto-claude svc/auto-claude-web-backend 8000:8000 &
curl http://localhost:8000/health
```

#### 6. Access Application
```bash
# Get ingress hostname (if configured)
kubectl get ingress -n auto-claude

# Or use port-forward for testing
kubectl port-forward -n auto-claude svc/auto-claude-web-frontend 3000:3000
```

## Configuration

### Secrets Management

**DO NOT store secrets in plain text ConfigMaps or manifests.**

#### Using kubectl Secrets

```bash
# Create from literals
kubectl create secret generic auto-claude-secrets \
  --from-literal=claude-oauth-token=xxx \
  --from-literal=openai-api-key=xxx \
  --from-literal=secret-key=xxx \
  --namespace auto-claude

# Create from file
kubectl create secret generic auto-claude-secrets \
  --from-env-file=.env \
  --namespace auto-claude

# Verify (values are base64-encoded)
kubectl get secret auto-claude-secrets -n auto-claude -o yaml
```

#### Using External Secrets Operator (Recommended for Production)

```yaml
# external-secret.yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: auto-claude-secrets
  namespace: auto-claude
spec:
  refreshInterval: 1h
  secretStoreRef:
    kind: SecretStore
    name: vault-backend
  target:
    name: auto-claude-secrets
  data:
    - secretKey: claude-oauth-token
      remoteRef:
        key: auto-claude/claude-oauth-token
    - secretKey: openai-api-key
      remoteRef:
        key: auto-claude/openai-api-key
```

#### Using Sealed Secrets

```bash
# Install Sealed Secrets controller
kubectl apply -f https://github.com/bitnami-labs/sealed-secrets/releases/download/v0.24.0/controller.yaml

# Create sealed secret
kubectl create secret generic auto-claude-secrets \
  --from-literal=claude-oauth-token=xxx \
  --dry-run=client -o yaml | \
  kubeseal -o yaml > sealed-secret.yaml

# Apply sealed secret (safe to commit)
kubectl apply -f sealed-secret.yaml -n auto-claude
```

### ConfigMaps

Non-sensitive configuration stored in ConfigMaps:

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: auto-claude-config
  namespace: auto-claude
data:
  # Graphiti configuration
  GRAPHITI_ENABLED: "true"
  GRAPHITI_LLM_PROVIDER: "openai"

  # Claude model
  CLAUDE_MODEL: "claude-sonnet-4-5-20250929"

  # NOTE: DATABASE_URL contains credentials and is stored in auto-claude-secrets Secret,
  # not in this ConfigMap. Reference it via secretKeyRef in your Deployment spec.

  # Redis connection
  REDIS_HOST: "redis-service"
  REDIS_PORT: "6379"
  REDIS_DB: "0"

  # Web backend settings
  HOST: "0.0.0.0"
  PORT: "8000"
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  CORS_ORIGINS: "http://localhost:3000,https://autoclaude.yourdomain.com"
  ACCESS_TOKEN_EXPIRE_MINUTES: "60"

  # CI/CD mode (optional)
  AUTO_CLAUDE_CI: "false"
  AUTO_CLAUDE_JSON_OUTPUT: "false"
```

Apply:
```bash
kubectl apply -f configmap.yaml
```

### Persistent Storage

#### PersistentVolumeClaims

Auto Code requires persistent storage for:
- PostgreSQL database
- Redis data
- Auto-Claude workspace (.auto-claude/)
- Git worktrees (.worktrees/)

**Storage Classes:**

```bash
# List available storage classes
kubectl get storageclass

# Common storage classes:
# - standard (default)
# - gp2, gp3 (AWS EBS)
# - pd-standard, pd-ssd (GCP)
# - managed-premium (Azure)
```

**Example PVCs:**

```yaml
# postgres-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: postgres-pvc
  namespace: auto-claude
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard  # Use your storage class
  resources:
    requests:
      storage: 10Gi
---
# redis-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
  namespace: auto-claude
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 1Gi
---
# backend-data-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-data-pvc
  namespace: auto-claude
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 5Gi
---
# backend-worktrees-pvc.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: backend-worktrees-pvc
  namespace: auto-claude
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: standard
  resources:
    requests:
      storage: 20Gi
```

Apply:
```bash
kubectl apply -f postgres-pvc.yaml
kubectl apply -f redis-pvc.yaml
kubectl apply -f backend-data-pvc.yaml
kubectl apply -f backend-worktrees-pvc.yaml

# Verify
kubectl get pvc -n auto-claude
```

#### Volume Snapshots (Backup)

> **Note:** The `$(date +%Y%m%d)` shell expansion below is not processed by `kubectl apply`.
> Generate the YAML with the date substituted using the `kubectl` command shown after the template.

```yaml
# snapshot.yaml (template — see command below to apply)
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot-YYYYMMDD
  namespace: auto-claude
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: postgres-pvc
```

```bash
# Create snapshot with today's date in the name
kubectl apply -f - <<EOF
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot-$(date +%Y%m%d)
  namespace: auto-claude
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: postgres-pvc
EOF

# List snapshots
kubectl get volumesnapshot -n auto-claude

# Restore from snapshot
kubectl apply -f restore-from-snapshot.yaml
```

### Network Configuration

#### Services

```yaml
# Service types:
# - ClusterIP: Internal only (default)
# - NodePort: Expose on node IP
# - LoadBalancer: Cloud load balancer
# - Ingress: HTTP/HTTPS routing

# Example: ClusterIP (internal)
apiVersion: v1
kind: Service
metadata:
  name: web-backend-service
  namespace: auto-claude
spec:
  type: ClusterIP
  selector:
    app: web-backend
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP

# Example: LoadBalancer (external)
apiVersion: v1
kind: Service
metadata:
  name: web-frontend-service
  namespace: auto-claude
spec:
  type: LoadBalancer
  selector:
    app: web-frontend
  ports:
    - port: 80
      targetPort: 3000
      protocol: TCP
```

#### Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: auto-claude-ingress
  namespace: auto-claude
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  tls:
    - hosts:
        - autoclaude.yourdomain.com
      secretName: autoclaude-tls
  rules:
    - host: autoclaude.yourdomain.com
      http:
        paths:
          - path: /api
            pathType: Prefix
            backend:
              service:
                name: web-backend-service
                port:
                  number: 8000
          - path: /
            pathType: Prefix
            backend:
              service:
                name: web-frontend-service
                port:
                  number: 3000
```

## Deployment Options

### Development Deployment

**Characteristics:**
- Single replica per service
- Debug mode enabled
- Less resource limits
- NodePort or port-forward access

**Deploy:**
```bash
# Deploy with development settings
helm install auto-claude ./helm/auto-claude \
  --namespace auto-claude \
  --values values-secrets.yaml \
  --set backend.replicas=1 \
  --set webBackend.replicas=1 \
  --set webBackend.config.DEBUG=true \
  --set webBackend.resources.limits.memory=1Gi

# Or with kubectl
kubectl apply -f k8s/dev/
```

### Production Deployment

**Characteristics:**
- Multiple replicas (HA)
- Debug mode disabled
- Resource limits enforced
- Ingress with TLS
- Auto-scaling enabled

**Deploy:**
```bash
# Deploy with production settings
helm install auto-claude ./helm/auto-claude \
  --namespace auto-claude \
  --values values-secrets.yaml \
  --set webBackend.replicas=3 \
  --set webBackend.config.DEBUG=false \
  --set webBackend.autoscaling.enabled=true \
  --set webBackend.autoscaling.minReplicas=3 \
  --set webBackend.autoscaling.maxReplicas=10 \
  --set webFrontend.ingress.enabled=true \
  --set webFrontend.ingress.hostname=autoclaude.yourdomain.com \
  --set webFrontend.ingress.tls.enabled=true

# Or with kubectl
kubectl apply -f k8s/prod/
```

### Multi-Region Deployment

**Deploy to multiple clusters:**

```bash
# Context 1: US cluster
kubectl config use-context us-cluster
helm install auto-claude ./helm/auto-claude \
  --namespace auto-claude \
  --values values-secrets.yaml \
  --set webFrontend.ingress.hostname=us.autoclaude.yourdomain.com

# Context 2: EU cluster
kubectl config use-context eu-cluster
helm install auto-claude ./helm/auto-claude \
  --namespace auto-claude \
  --values values-secrets.yaml \
  --set webFrontend.ingress.hostname=eu.autoclaude.yourdomain.com
```

Use global load balancer (AWS Route53, GCP Cloud DNS, Azure Traffic Manager) to route traffic.

## Health Checks

### Liveness and Readiness Probes

All services include Kubernetes health checks:

#### Web Backend Probes

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
  initialDelaySeconds: 10
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

#### PostgreSQL Probes

```yaml
livenessProbe:
  exec:
    command:
      - pg_isready
      - -U
      - postgres
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  exec:
    command:
      - pg_isready
      - -U
      - postgres
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

#### Redis Probes

```yaml
livenessProbe:
  exec:
    command:
      - redis-cli
      - ping
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  exec:
    command:
      - redis-cli
      - ping
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 3
  failureThreshold: 2
```

### Check Pod Health

```bash
# Check all pods
kubectl get pods -n auto-claude

# Describe pod for health status
kubectl describe pod <pod-name> -n auto-claude

# View health check logs
kubectl logs <pod-name> -n auto-claude --tail=50

# Test health endpoint directly
kubectl exec -it <web-backend-pod> -n auto-claude -- curl http://localhost:8000/health
```

## Auto-Scaling

### Horizontal Pod Autoscaler (HPA)

Automatically scale based on CPU/memory usage:

```yaml
# hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: web-backend-hpa
  namespace: auto-claude
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-backend
  minReplicas: 3
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
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
        - type: Percent
          value: 50  # Scale down max 50% at a time
          periodSeconds: 60
    scaleUp:
      stabilizationWindowSeconds: 0  # Scale up immediately
      policies:
        - type: Percent
          value: 100  # Double replicas if needed
          periodSeconds: 15
```

Apply:
```bash
kubectl apply -f hpa.yaml

# Check HPA status
kubectl get hpa -n auto-claude

# Describe HPA
kubectl describe hpa web-backend-hpa -n auto-claude
```

**Note:** Requires Metrics Server:
```bash
# Install metrics-server (if not already installed)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify
kubectl top nodes
kubectl top pods -n auto-claude
```

### Vertical Pod Autoscaler (VPA)

Automatically adjust resource requests/limits:

```yaml
# vpa.yaml
apiVersion: autoscaling.k8s.io/v1
kind: VerticalPodAutoscaler
metadata:
  name: web-backend-vpa
  namespace: auto-claude
spec:
  targetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: web-backend
  updatePolicy:
    updateMode: "Auto"  # Auto, Initial, Recreate, Off
  resourcePolicy:
    containerPolicies:
      - containerName: web-backend
        minAllowed:
          cpu: 100m
          memory: 256Mi
        maxAllowed:
          cpu: 2000m
          memory: 4Gi
```

## Monitoring & Logs

### View Logs

```bash
# All pods in namespace
kubectl logs -n auto-claude --all-containers=true --tail=100

# Specific pod
kubectl logs -n auto-claude <pod-name> --tail=50 --follow

# Specific container in multi-container pod
kubectl logs -n auto-claude <pod-name> -c web-backend

# Previous crashed pod
kubectl logs -n auto-claude <pod-name> --previous

# Logs from all replicas of a deployment
kubectl logs -n auto-claude -l app=web-backend --tail=20

# Stream logs from all pods
kubectl logs -n auto-claude -l app=web-backend -f
```

### Centralized Logging

#### Option 1: EFK Stack (Elasticsearch, Fluentd, Kibana)

```bash
# Install EFK stack
helm repo add elastic https://helm.elastic.co
helm install elasticsearch elastic/elasticsearch -n logging --create-namespace
helm install kibana elastic/kibana -n logging
helm install fluentd fluent/fluentd -n logging

# Access Kibana
kubectl port-forward -n logging svc/kibana-kibana 5601:5601
# Open http://localhost:5601
```

#### Option 2: Loki + Grafana

```bash
# Install Loki stack
helm repo add grafana https://grafana.github.io/helm-charts
helm install loki grafana/loki-stack \
  --namespace logging \
  --create-namespace \
  --set grafana.enabled=true

# Get Grafana password
kubectl get secret -n logging loki-grafana -o jsonpath="{.data.admin-password}" | base64 --decode

# Access Grafana
kubectl port-forward -n logging svc/loki-grafana 3000:80
# Open http://localhost:3000 (user: admin)
```

### Monitoring with Prometheus

```bash
# Install Prometheus stack
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace

# Access Prometheus
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

**Custom ServiceMonitor for Auto Code:**

```yaml
# servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: auto-claude-metrics
  namespace: auto-claude
spec:
  selector:
    matchLabels:
      app: web-backend
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

### Resource Monitoring

```bash
# Node resources
kubectl top nodes

# Pod resources
kubectl top pods -n auto-claude

# Sort by CPU
kubectl top pods -n auto-claude --sort-by=cpu

# Sort by memory
kubectl top pods -n auto-claude --sort-by=memory

# Detailed resource usage
kubectl describe nodes
```

## Troubleshooting

### Pods Not Starting

**Problem:** Pods stuck in `Pending`, `ContainerCreating`, or `CrashLoopBackOff`

**Solution:**

```bash
# Check pod status
kubectl get pods -n auto-claude

# Describe pod for events
kubectl describe pod <pod-name> -n auto-claude

# Common issues:
# 1. Insufficient resources
kubectl describe nodes | grep -A 5 "Allocated resources"

# 2. Image pull errors
kubectl describe pod <pod-name> -n auto-claude | grep -A 10 "Events"
# Fix: Verify image exists and pull secrets are configured

# 3. PVC binding issues
kubectl get pvc -n auto-claude
# Fix: Ensure storage class exists and has capacity

# 4. ConfigMap/Secret missing
kubectl get configmap -n auto-claude
kubectl get secret -n auto-claude

# Check pod logs
kubectl logs <pod-name> -n auto-claude
```

### Service Not Accessible

**Problem:** Cannot access service via ClusterIP, NodePort, or Ingress

**Solution:**

```bash
# Check service exists
kubectl get svc -n auto-claude

# Verify endpoints are created
kubectl get endpoints -n auto-claude
# Should show pod IPs

# Test from within cluster
kubectl run -it --rm debug --image=curlimages/curl --restart=Never -n auto-claude -- \
  curl http://web-backend-service:8000/health

# Check ingress configuration
kubectl get ingress -n auto-claude
kubectl describe ingress auto-claude-ingress -n auto-claude

# Verify ingress controller is running
kubectl get pods -n ingress-nginx  # Or your ingress namespace
```

### Database Connection Fails

**Problem:** `could not connect to server: Connection refused`

**Solution:**

```bash
# Check postgres pod is running
kubectl get pods -n auto-claude -l app=postgres

# Check postgres service
kubectl get svc -n auto-claude postgres-service

# Test postgres connection from backend pod
kubectl exec -it <backend-pod> -n auto-claude -- \
  psql -h postgres-service -U postgres -d autoclaude

# Check DATABASE_URL in Secret (stored as base64)
kubectl get secret auto-claude-secrets -n auto-claude -o jsonpath='{.data.database-url}' | base64 -d

# Check postgres logs
kubectl logs -n auto-claude -l app=postgres --tail=50

# Verify PVC is bound
kubectl get pvc postgres-pvc -n auto-claude
```

### Out of Disk Space

**Problem:** PVC full, pods crashing

**Solution:**

```bash
# Check PVC usage
kubectl exec -it <pod-name> -n auto-claude -- df -h

# Resize PVC (if storage class supports it)
kubectl patch pvc postgres-pvc -n auto-claude -p '{"spec":{"resources":{"requests":{"storage":"20Gi"}}}}'

# Or create new larger PVC and migrate data
# 1. Create snapshot of old PVC
# 2. Create new PVC from snapshot with larger size
# 3. Update deployment to use new PVC
```

### Health Checks Failing

**Problem:** Pods showing as unhealthy

**Solution:**

```bash
# Check liveness/readiness probe configuration
kubectl describe pod <pod-name> -n auto-claude | grep -A 10 "Liveness\|Readiness"

# Test health endpoint manually
kubectl exec -it <web-backend-pod> -n auto-claude -- \
  curl -v http://localhost:8000/health

# Check probe timing (may need longer initialDelaySeconds)
kubectl edit deployment web-backend -n auto-claude
# Adjust initialDelaySeconds if service takes longer to start

# View probe failure logs
kubectl describe pod <pod-name> -n auto-claude | grep -A 20 "Events"
```

### Secrets Not Loading

**Problem:** Pods can't read secrets

**Solution:**

```bash
# Verify secret exists
kubectl get secret auto-claude-secrets -n auto-claude

# Check secret data (base64 encoded)
kubectl get secret auto-claude-secrets -n auto-claude -o yaml

# Decode secret to verify content
kubectl get secret auto-claude-secrets -n auto-claude -o jsonpath='{.data.claude-oauth-token}' | base64 --decode

# Check pod has secret mounted
kubectl describe pod <pod-name> -n auto-claude | grep -A 10 "Mounts\|Environment"

# Test from within pod
kubectl exec -it <pod-name> -n auto-claude -- printenv CLAUDE_CODE_OAUTH_TOKEN
```

### Ingress Not Working

**Problem:** Ingress returns 404 or 502

**Solution:**

```bash
# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/component=controller --tail=50

# Verify ingress resource
kubectl describe ingress auto-claude-ingress -n auto-claude

# Check ingress rules
kubectl get ingress auto-claude-ingress -n auto-claude -o yaml

# Test backend service directly
kubectl port-forward -n auto-claude svc/web-backend-service 8000:8000
curl http://localhost:8000/health

# Verify DNS points to ingress external IP
kubectl get ingress auto-claude-ingress -n auto-claude
nslookup autoclaude.yourdomain.com
```

### HPA Not Scaling

**Problem:** Horizontal Pod Autoscaler not triggering

**Solution:**

```bash
# Check HPA status
kubectl get hpa -n auto-claude
kubectl describe hpa web-backend-hpa -n auto-claude

# Verify metrics-server is running
kubectl get deployment metrics-server -n kube-system

# Check metrics are available
kubectl top pods -n auto-claude

# If metrics are "unknown", restart metrics-server
kubectl rollout restart deployment metrics-server -n kube-system

# Generate load to test HPA
kubectl run -it load-generator --rm --image=busybox --restart=Never -- \
  /bin/sh -c "while sleep 0.01; do wget -q -O- http://web-backend-service.auto-claude:8000/health; done"
```

## Security Best Practices

### 1. Use RBAC

```yaml
# serviceaccount.yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: auto-claude-sa
  namespace: auto-claude
---
# role.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: auto-claude-role
  namespace: auto-claude
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list", "watch"]
---
# rolebinding.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: auto-claude-rolebinding
  namespace: auto-claude
subjects:
  - kind: ServiceAccount
    name: auto-claude-sa
    namespace: auto-claude
roleRef:
  kind: Role
  name: auto-claude-role
  apiGroup: rbac.authorization.k8s.io
```

Apply to deployments:
```yaml
spec:
  template:
    spec:
      serviceAccountName: auto-claude-sa
```

### 2. Network Policies

```yaml
# network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: auto-claude-network-policy
  namespace: auto-claude
spec:
  podSelector:
    matchLabels:
      app: web-backend
  policyTypes:
    - Ingress
    - Egress
  ingress:
    # Allow from ingress controller
    - from:
        - namespaceSelector:
            matchLabels:
              name: ingress-nginx
      ports:
        - protocol: TCP
          port: 8000
    # Allow from web-frontend
    - from:
        - podSelector:
            matchLabels:
              app: web-frontend
      ports:
        - protocol: TCP
          port: 8000
  egress:
    # Allow to postgres
    - to:
        - podSelector:
            matchLabels:
              app: postgres
      ports:
        - protocol: TCP
          port: 5432
    # Allow to redis
    - to:
        - podSelector:
            matchLabels:
              app: redis
      ports:
        - protocol: TCP
          port: 6379
    # Allow to external APIs (Claude, OpenAI)
    - to:
        - namespaceSelector: {}
      ports:
        - protocol: TCP
          port: 443
```

### 3. Pod Security Standards (Kubernetes 1.25+)

Pod Security Policies (PSP) were removed in Kubernetes 1.25. Use **Pod Security Admission (PSA)** namespace labels instead to enforce security standards:

```yaml
# pod-security-admission.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: auto-claude
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

### 4. Security Context

```yaml
# deployment.yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: web-backend
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop:
                - ALL
            readOnlyRootFilesystem: true
```

### 5. Resource Quotas

```yaml
# resourcequota.yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: auto-claude-quota
  namespace: auto-claude
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "2"
```

### 6. TLS Certificates

```yaml
# certificate.yaml (cert-manager)
apiVersion: cert-manager.io/v1
kind: Certificate
metadata:
  name: autoclaude-tls
  namespace: auto-claude
spec:
  secretName: autoclaude-tls
  issuerRef:
    name: letsencrypt-prod
    kind: ClusterIssuer
  dnsNames:
    - autoclaude.yourdomain.com
```

### 7. Image Security

```yaml
# Use specific image tags (not :latest)
image: auto-code-backend:v1.2.3

# Use image pull secrets for private registries
imagePullSecrets:
  - name: regcred

# Scan images for vulnerabilities
# kubectl run --rm -i --tty trivy --image=aquasec/trivy -- \
#   image auto-code-backend:v1.2.3
```

## Operations

### Scaling

```bash
# Manual scaling
kubectl scale deployment web-backend -n auto-claude --replicas=5

# Verify
kubectl get deployment web-backend -n auto-claude

# View replica set
kubectl get rs -n auto-claude
```

### Updates & Rollouts

```bash
# Update image
kubectl set image deployment/web-backend \
  web-backend=auto-code-backend:v1.2.4 \
  -n auto-claude

# Watch rollout
kubectl rollout status deployment/web-backend -n auto-claude

# View rollout history
kubectl rollout history deployment/web-backend -n auto-claude

# Rollback to previous version
kubectl rollout undo deployment/web-backend -n auto-claude

# Rollback to specific revision
kubectl rollout undo deployment/web-backend --to-revision=2 -n auto-claude

# Pause rollout
kubectl rollout pause deployment/web-backend -n auto-claude

# Resume rollout
kubectl rollout resume deployment/web-backend -n auto-claude
```

### Helm Upgrades

```bash
# Upgrade release
helm upgrade auto-claude ./helm/auto-claude \
  --namespace auto-claude \
  --values values-secrets.yaml \
  --set webBackend.image.tag=v1.2.4

# Rollback
helm rollback auto-claude -n auto-claude

# Rollback to specific revision
helm rollback auto-claude 2 -n auto-claude

# View history
helm history auto-claude -n auto-claude
```

### Database Migrations

```bash
# Run migrations manually
kubectl exec -it deployment/web-backend -n auto-claude -- \
  python -m alembic upgrade head

# Or create migration job
kubectl apply -f k8s/jobs/db-migration.yaml
```

### Backup & Restore

#### Backup with Velero

```bash
# Install Velero
velero install \
  --provider aws \
  --bucket auto-claude-backups \
  --secret-file ./credentials-velero

# Backup entire namespace
velero backup create auto-claude-backup-$(date +%Y%m%d) \
  --include-namespaces auto-claude

# Backup specific resources
velero backup create postgres-backup-$(date +%Y%m%d) \
  --include-namespaces auto-claude \
  --include-resources pvc,pv \
  --selector app=postgres

# List backups
velero backup get

# Restore
velero restore create --from-backup auto-claude-backup-20260305
```

#### Manual Database Backup

```bash
# Backup postgres
kubectl exec -it <postgres-pod> -n auto-claude -- \
  pg_dump -U postgres autoclaude > backup-$(date +%Y%m%d).sql

# Restore postgres
kubectl exec -i <postgres-pod> -n auto-claude -- \
  psql -U postgres autoclaude < backup-20260305.sql
```

### Cleanup

```bash
# Delete all resources in namespace
kubectl delete all --all -n auto-claude

# Delete PVCs (WARNING: deletes data)
kubectl delete pvc --all -n auto-claude

# Delete namespace (deletes everything)
kubectl delete namespace auto-claude

# Uninstall Helm release
helm uninstall auto-claude -n auto-claude
```

## Advanced Configuration

### Blue-Green Deployment

```bash
# Deploy green version
kubectl apply -f k8s/green/

# Test green version
kubectl port-forward -n auto-claude svc/web-backend-green 8001:8000

# Switch traffic to green
kubectl patch service web-backend-service -n auto-claude \
  -p '{"spec":{"selector":{"version":"green"}}}'

# Rollback if needed
kubectl patch service web-backend-service -n auto-claude \
  -p '{"spec":{"selector":{"version":"blue"}}}'
```

### Canary Deployment

```yaml
# Use Flagger for automated canary
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
    threshold: 5
    maxWeight: 50
    stepWeight: 10
    metrics:
      - name: request-success-rate
        thresholdRange:
          min: 99
        interval: 1m
```

### Custom Resource Definitions (CRDs)

```yaml
# Example: Custom spec resource
apiVersion: autoclaude.io/v1
kind: Spec
metadata:
  name: feature-123
  namespace: auto-claude
spec:
  taskDescription: "Add user authentication"
  complexity: "standard"
  priority: "high"
```

### Multi-Tenancy

```bash
# Create namespace per tenant
kubectl create namespace tenant-acme
kubectl create namespace tenant-beta

# Deploy with tenant-specific configs
helm install auto-claude-acme ./helm/auto-claude \
  --namespace tenant-acme \
  --values tenant-acme-values.yaml

helm install auto-claude-beta ./helm/auto-claude \
  --namespace tenant-beta \
  --values tenant-beta-values.yaml
```

## Cloud-Specific Configurations

### AWS EKS

```bash
# Install EBS CSI driver (for PersistentVolumes)
kubectl apply -k "github.com/kubernetes-sigs/aws-ebs-csi-driver/deploy/kubernetes/overlays/stable/?ref=master"

# Use EBS storage class
storageClassName: gp3

# Install AWS Load Balancer Controller
helm repo add eks https://aws.github.io/eks-charts
helm install aws-load-balancer-controller eks/aws-load-balancer-controller \
  -n kube-system \
  --set clusterName=auto-claude-cluster

# Use ALB ingress
annotations:
  kubernetes.io/ingress.class: alb
  alb.ingress.kubernetes.io/scheme: internet-facing
```

### Google GKE

```bash
# Enable GKE Ingress
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-gce/master/deploy/gce-ingress.yaml

# Use GCE persistent disk
storageClassName: pd-ssd

# Use GKE workload identity
kubectl annotate serviceaccount auto-claude-sa \
  iam.gke.io/gcp-service-account=auto-claude@project-id.iam.gserviceaccount.com \
  -n auto-claude
```

### Azure AKS

```bash
# Install Azure Disk CSI driver
kubectl apply -f https://raw.githubusercontent.com/kubernetes-sigs/azuredisk-csi-driver/master/deploy/install-driver.sh

# Use Azure disk storage class
storageClassName: managed-premium

# Use Azure Application Gateway Ingress
helm repo add application-gateway-kubernetes-ingress https://appgwingress.blob.core.windows.net/ingress-azure-helm-package/
helm install ingress-azure application-gateway-kubernetes-ingress/ingress-azure \
  --namespace default \
  --set appgw.subscriptionId=<subscription-id>
```

## Next Steps

- **Docker Deployment:** See [DOCKER_DEPLOYMENT.md](./DOCKER_DEPLOYMENT.md) for containerized deployment
- **Update Strategy:** See [UPDATE_STRATEGY.md](./UPDATE_STRATEGY.md) for rolling updates and blue-green deployments
- **CI/CD Integration:** See [ci-cd-integration.md](./ci-cd-integration.md) for automated builds
- **Cloud Deployment:** See [CLOUD_DEPLOYMENT.md](./CLOUD_DEPLOYMENT.md) for cloud-specific configurations

## Support

For issues or questions:

1. **Check logs:** `kubectl logs -n auto-claude -l app=web-backend`
2. **Review pod status:** `kubectl get pods -n auto-claude`
3. **Describe resources:** `kubectl describe pod <pod-name> -n auto-claude`
4. **Consult troubleshooting:** See [Troubleshooting](#troubleshooting) section above
5. **File an issue:** https://github.com/your-org/Auto-Coding/issues
6. **Discord/Slack:** Join our community for real-time help
