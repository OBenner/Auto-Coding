#!/bin/bash
#
# Auto Code Helm Deployment Script
#
# This script automates the initial deployment of Auto Code using Helm.
# It creates the necessary configuration, namespace, and installs the Helm chart.
#
# Usage:
#   ./deploy-helm.sh [--namespace NAMESPACE] [--values VALUES_FILE] [--chart CHART_PATH] [--quick]
#
# Options:
#   --namespace NAMESPACE   Kubernetes namespace (default: autoclaude)
#   --values VALUES_FILE    Custom values file (default: autoclaude-values.yaml)
#   --chart CHART_PATH      Path to Helm chart or chart URL (default: ./helm/autoclaude)
#   --release RELEASE_NAME  Helm release name (default: autoclaude)
#   --create-namespace      Create namespace if it doesn't exist
#   --quick                 Skip prompts and use defaults
#   --help                  Show this help message
#
# Examples:
#   ./deploy-helm.sh
#   ./deploy-helm.sh --quick
#   ./deploy-helm.sh --namespace production --values prod-values.yaml
#   ./deploy-helm.sh --chart ./helm/autoclaude --create-namespace
#
# For more information, see guides/SELF_HOSTED_DEPLOYMENT.md
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
RELEASE_NAME="${AUTOCLAUDE_RELEASE:-autoclaude}"
NAMESPACE="${AUTOCLAUDE_NAMESPACE:-autoclaude}"
CHART="${AUTOCLAUDE_CHART:-$SCRIPT_DIR/helm/autoclaude}"
VALUES_FILE="${AUTOCLAUDE_VALUES:-autoclaude-values.yaml}"
CREATE_NAMESPACE=false
QUICK_MODE=false
WAIT_TIMEOUT=10m

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Print help message
show_help() {
    grep '^#' "$0" | grep -v '!/bin/' | sed 's/^# //' | sed 's/^#//'
    exit 0
}

# Parse command line arguments
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --namespace)
                NAMESPACE="$2"
                shift 2
                ;;
            --values)
                VALUES_FILE="$2"
                shift 2
                ;;
            --chart)
                CHART="$2"
                shift 2
                ;;
            --release)
                RELEASE_NAME="$2"
                shift 2
                ;;
            --create-namespace)
                CREATE_NAMESPACE=true
                shift
                ;;
            --quick)
                QUICK_MODE=true
                shift
                ;;
            --timeout)
                WAIT_TIMEOUT="$2"
                shift 2
                ;;
            --help)
                show_help
                ;;
            *)
                log_error "Unknown option: $1"
                show_help
                ;;
        esac
    done
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."

    # Check if helm is installed
    if ! command -v helm &> /dev/null; then
        log_error "helm is not installed"
        log_info "Please install Helm: https://helm.sh/docs/intro/install/"
        return 1
    fi

    # Check helm version
    local helm_version
    helm_version=$(helm version --short 2>/dev/null | grep -oE 'v[0-9]+\.[0-9]+' | head -1 || echo "v3.0.0")
    log_info "Helm version: $helm_version"

    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        log_info "Please install kubectl: https://kubernetes.io/docs/tasks/tools/"
        return 1
    fi

    # Check if kubeconfig is configured
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes cluster is not accessible"
        log_info "Please configure kubeconfig or check cluster connectivity"
        return 1
    fi

    # Check cluster connection
    local cluster_name
    cluster_name=$(kubectl config current-context 2>/dev/null || echo "unknown")
    log_info "Kubernetes cluster: $cluster_name"

    # Check if chart exists
    if [ ! -d "$CHART" ] && [[ ! "$CHART" == */* ]]; then
        log_error "Chart not found: $CHART"
        log_info "Please provide a valid chart path or repository"
        return 1
    fi

    log_success "Prerequisites check passed"
    return 0
}

# Generate secret key
generate_secret_key() {
    if command -v openssl &> /dev/null; then
        openssl rand -hex 32
    else
        # Fallback if openssl is not available
        head /dev/urandom | tr -dc A-Za-z0-9 | head -c 64
    fi
}

# Create values file
create_values_file() {
    log_info "Creating values file..."

    if [ -f "$VALUES_FILE" ]; then
        if [ "$QUICK_MODE" = false ]; then
            log_warning "Values file already exists: $VALUES_FILE"
            read -rp "Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Keeping existing values file"
                return 0
            fi
        else
            log_info "Skipping values creation (already exists)"
            return 0
        fi
    fi

    # Generate secret key
    local secret_key
    secret_key=$(generate_secret_key)

    # Generate database passwords
    local postgres_password
    postgres_password=$(generate_secret_key)

    local redis_password
    redis_password=$(generate_secret_key)

    # Create values file
    cat > "$VALUES_FILE" << EOF
# Auto Code Helm Values
# Generated: $(date)

# Backend Configuration
backend:
  enabled: true

  # Container image - update with your registry
  image:
    repository: ghcr.io/obenner/autoclaude-backend
    tag: latest
    pullPolicy: Always

  # Number of replicas
  replicaCount: 2

  # Service configuration
  service:
    type: LoadBalancer
    port: 80
    targetPort: 8000

  # Ingress configuration
  ingress:
    enabled: false
    className: "nginx"
    hosts:
      - host: autoclaude.example.com
        paths:
          - path: /
            pathType: Prefix

  # Resource limits and requests
  resources:
    requests:
      memory: "512Mi"
      cpu: "500m"
    limits:
      memory: "1Gi"
      cpu: "1000m"

  # Environment variables
  env:
    # Server configuration
    HOST: "0.0.0.0"
    PORT: "8000"
    DEBUG: "false"
    LOG_LEVEL: "INFO"

    # CORS configuration
    CORS_ORIGINS: "http://localhost:3000,https://autoclaude.app"

    # Authentication
    SECRET_KEY: "$secret_key"
    ACCESS_TOKEN_EXPIRE_MINUTES: "60"

    # WebSocket configuration
    WS_HEARTBEAT_INTERVAL: "30"

    # Telemetry
    DISABLE_TELEMETRY: "false"

    # Workspace directory
    WORKSPACE_DIR: "/app/backend/.auto-claude/specs"

  # OAuth configuration (optional)
  oauth:
    github:
      clientId: ""
      clientSecret: ""
    gitlab:
      clientId: ""
      clientSecret: ""
    redirectUri: "http://localhost:8000/api/git/callback"

# PostgreSQL Database
postgresql:
  enabled: true

  image:
    repository: postgres
    tag: "16-alpine"

  # PostgreSQL credentials
  auth:
    username: postgres
    database: autoclaude
    password: "$postgres_password"

  # Persistence
  persistence:
    enabled: true
    size: 10Gi
    storageClass: ""

  # Resource limits
  resources:
    requests:
      memory: "256Mi"
      cpu: "250m"
    limits:
      memory: "512Mi"
      cpu: "500m"

# Redis Cache
redis:
  enabled: true

  image:
    repository: redis
    tag: "7-alpine"

  # Redis password
  password: "$redis_password"

  # Persistence
  persistence:
    enabled: true
    size: 5Gi
    storageClass: ""

  # Resource limits
  resources:
    requests:
      memory: "128Mi"
      cpu: "100m"
    limits:
      memory: "256Mi"
      cpu: "200m"
EOF

    log_success "Values file created: $VALUES_FILE"
    log_warning "Please review and update $VALUES_FILE with your configuration"
    log_warning "Important: Update image.repository, ingress hosts, and OAuth settings"
    return 0
}

# Create namespace
create_namespace() {
    log_info "Checking namespace..."

    if kubectl get namespace "$NAMESPACE" &> /dev/null; then
        log_info "Namespace already exists: $NAMESPACE"
        return 0
    fi

    if [ "$CREATE_NAMESPACE" = false ]; then
        log_warning "Namespace '$NAMESPACE' does not exist"
        log_info "Create it manually with: kubectl create namespace $NAMESPACE"
        log_info "Or use --create-namespace flag to auto-create"
        return 1
    fi

    log_info "Creating namespace: $NAMESPACE"
    kubectl create namespace "$NAMESPACE" || {
        log_error "Failed to create namespace"
        return 1
    }

    log_success "Namespace created: $NAMESPACE"
    return 0
}

# Check if release already exists
check_release() {
    log_info "Checking for existing release..."

    if helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
        log_warning "Helm release '$RELEASE_NAME' already exists in namespace '$NAMESPACE'"
        log_info "To upgrade the existing release, use: ./update-helm.sh"
        log_info "Or uninstall first with: helm uninstall $RELEASE_NAME -n $NAMESPACE"
        return 1
    fi

    log_success "Release name available: $RELEASE_NAME"
    return 0
}

# Install Helm chart
install_chart() {
    log_info "Installing Helm chart..."

    # Build install command
    local install_cmd=(
        helm install
        "$RELEASE_NAME"
        "$CHART"
        --namespace "$NAMESPACE"
        --values "$VALUES_FILE"
        --wait
        --timeout "$WAIT_TIMEOUT"
    )

    log_info "Running: ${install_cmd[*]}"

    # Perform installation
    "${install_cmd[@]}" || {
        log_error "Helm install failed"
        return 1
    }

    log_success "Helm chart installed"
    return 0
}

# Wait for pods to be ready
wait_for_pods() {
    local timeout=300  # 5 minutes
    local elapsed=0
    local interval=5

    log_info "Waiting for pods to become ready (timeout: ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        local ready_count=0
        local total_count=0

        # Count pods
        while IFS= read -r line; do
            total_count=$((total_count + 1))
            if echo "$line" | grep -q "Running"; then
                # Check if ready
                local ready=$(echo "$line" | awk '{print $2}' | cut -d'/' -f1)
                local desired=$(echo "$line" | awk '{print $2}' | cut -d'/' -f2)
                if [ "$ready" = "$desired" ]; then
                    ready_count=$((ready_count + 1))
                fi
            fi
        done < <(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" --no-headers 2>/dev/null || true)

        if [ "$total_count" -gt 0 ] && [ "$ready_count" -eq "$total_count" ]; then
            log_success "All pods are ready"
            return 0
        fi

        if [ "$total_count" -gt 0 ]; then
            log_info "Waiting... ($ready_count/$total_count ready)"
        fi

        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Timeout waiting for pods to become ready"
    log_warning "Some pods may still be starting. Check status with:"
    log_warning "  kubectl get pods -n $NAMESPACE"
    return 1
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check Helm release status
    local release_status
    release_status=$(helm status "$RELEASE_NAME" -n "$NAMESPACE" -o json 2>/dev/null | \
        jq -r '.info.status' // echo "unknown")

    if [ "$release_status" != "deployed" ]; then
        log_error "Helm release status: $release_status"
        return 1
    fi

    log_success "Helm release status: deployed"

    # Check if all pods are running
    local not_running
    not_running=$(kubectl get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/instance=$RELEASE_NAME" \
        --no-headers 2>/dev/null | grep -v "Running" | grep -v "Completed" || true)

    if [ -n "$not_running" ]; then
        log_warning "Some pods are not yet running:"
        echo "$not_running"
        log_warning "This is normal during initial startup"
    fi

    # Get service endpoint
    local service_endpoint
    service_endpoint=$(kubectl get service "$RELEASE_NAME-backend" -n "$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || \
        kubectl get service "$RELEASE_NAME-backend" -n "$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "pending")

    if [ "$service_endpoint" != "pending" ] && [ -n "$service_endpoint" ]; then
        log_success "Service endpoint: $service_endpoint"
    fi

    # Show pods
    log_info "Pods:"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" || true

    log_success "Deployment verification passed"
    return 0
}

# Show deployment info
show_deployment_info() {
    echo ""
    log_success "=========================================="
    log_success "Deployment completed successfully!"
    log_success "=========================================="
    echo ""

    log_info "Release Information:"
    helm status "$RELEASE_NAME" -n "$NAMESPACE"
    echo ""

    log_info "Pods:"
    kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    echo ""

    log_info "Services:"
    kubectl get services -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME"
    echo ""

    # Get service endpoint
    local service_endpoint
    service_endpoint=$(kubectl get service "$RELEASE_NAME-backend" -n "$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null || \
        kubectl get service "$RELEASE_NAME-backend" -n "$NAMESPACE" \
        -o jsonpath='{.status.loadBalancer.ingress[0].hostname}' 2>/dev/null || echo "<pending>")

    local service_port
    service_port=$(kubectl get service "$RELEASE_NAME-backend" -n "$NAMESPACE" \
        -o jsonpath='{.spec.ports[0].port}' 2>/dev/null || echo "80")

    if [ "$service_endpoint" != "<pending>" ] && [ -n "$service_endpoint" ]; then
        log_info "Service URLs:"
        log_info "  Backend API: http://$service_endpoint:$service_port"
        log_info "  Health Check: http://$service_endpoint:$service_port/health"
        log_info "  API Docs: http://$service_endpoint:$service_port/docs"
    else
        log_warning "Service endpoint is still provisioning..."
        log_info "Check status with: kubectl get svc $RELEASE_NAME-backend -n $NAMESPACE"
    fi
    echo ""

    log_info "Useful commands:"
    log_info "  View logs:      kubectl logs -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME -f"
    log_info "  Get status:     helm status $RELEASE_NAME -n $NAMESPACE"
    log_info "  List pods:      kubectl get pods -n $NAMESPACE"
    log_info "  Get services:   kubectl get svc -n $NAMESPACE"
    log_info "  Port forward:   kubectl port-forward -n $NAMESPACE svc/$RELEASE_NAME-backend 8000:80"
    log_info "  Uninstall:      helm uninstall $RELEASE_NAME -n $NAMESPACE"
    log_info "  Update:         ./update-helm.sh"
    echo ""

    log_info "Configuration files:"
    log_info "  Values file:   $VALUES_FILE"
    log_info "  Chart path:    $CHART"
    log_info "  Namespace:     $NAMESPACE"
    log_info "  Release name:  $RELEASE_NAME"
    echo ""

    log_warning "Next steps:"
    log_warning "1. Review and update $VALUES_FILE with your configuration"
    log_warning "2. Configure ingress for external access (if using LoadBalancer, wait for endpoint)"
    log_warning "3. Configure OAuth providers (GitHub/GitLab) in the values file"
    log_warning "4. Set up backups for PostgreSQL persistence volume"
    log_warning "5. Review resource limits and adjust based on your needs"
    echo ""
}

# Main deployment flow
main() {
    log_info "=========================================="
    log_info "Auto Code Helm Deployment"
    log_info "=========================================="
    echo ""

    # Parse arguments
    parse_args "$@"

    # Show configuration
    log_info "Configuration:"
    log_info "  Release Name:   $RELEASE_NAME"
    log_info "  Namespace:      $NAMESPACE"
    log_info "  Chart:          $CHART"
    log_info "  Values File:    $VALUES_FILE"
    log_info "  Wait Timeout:   $WAIT_TIMEOUT"
    log_info "  Quick Mode:     $QUICK_MODE"
    echo ""

    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    echo ""

    # Create values file
    if ! create_values_file; then
        log_error "Failed to create values file"
        exit 1
    fi
    echo ""

    # Create namespace
    if ! create_namespace; then
        log_error "Failed to create namespace"
        exit 1
    fi
    echo ""

    # Check if release exists
    if ! check_release; then
        log_error "Release already exists"
        exit 1
    fi
    echo ""

    # Prompt user if not in quick mode
    if [ "$QUICK_MODE" = false ]; then
        log_info "This will deploy Auto Code using Helm to namespace '$NAMESPACE'."
        log_info "Release name: $RELEASE_NAME"
        log_info "Chart: $CHART"
        echo ""
        read -rp "Continue? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
        echo ""
    fi

    # Install chart
    if ! install_chart; then
        log_error "Failed to install Helm chart"
        log_warning "Check logs with: kubectl get pods -n $NAMESPACE"
        exit 1
    fi
    echo ""

    # Wait for pods to be ready
    if ! wait_for_pods; then
        log_error "Pods failed to become ready"
        log_warning "Check pod status with: kubectl get pods -n $NAMESPACE"
        log_warning "Check pod logs with: kubectl logs -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME"
        exit 1
    fi
    echo ""

    # Verify deployment
    if ! verify_deployment; then
        log_error "Deployment verification failed"
        exit 1
    fi
    echo ""

    # Show deployment info
    show_deployment_info

    return 0
}

# Run main function
main "$@"
