#!/bin/bash
#
# Auto Code Helm Update Script
#
# This script automates the upgrade process for Helm deployments.
# It performs backups, updates Helm charts, and verifies the deployment.
# If any step fails, it automatically rolls back to the previous version.
#
# Usage:
#   ./update-helm.sh [--version VERSION] [--namespace NAMESPACE] [--values VALUES_FILE] [--dry-run]
#
# Options:
#   --version VERSION       Upgrade to specific chart version (default: latest)
#   --namespace NAMESPACE   Kubernetes namespace (default: autoclaude)
#   --values VALUES_FILE    Custom values file (default: autoclaude-values.yaml)
#   --chart CHART           Chart location or repository (default: autoclaude/autoclaude)
#   --dry-run               Show what would be done without making changes
#   --no-backup             Skip database backup (not recommended)
#   --force                 Force upgrade even if already on target version
#   --help                  Show this help message
#
# Examples:
#   ./update-helm.sh
#   ./update-helm.sh --version 2.9.0
#   ./update-helm.sh --namespace production --values prod-values.yaml
#   ./update-helm.sh --dry-run
#
# For more information, see guides/SELF_HOSTED_UPDATES.md
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
RELEASE_NAME="${RELEASE_NAME:-autoclaude}"
NAMESPACE="${NAMESPACE:-autoclaude}"
CHART="${CHART:-autoclaude/autoclaude}"
VALUES_FILE="${VALUES_FILE:-autoclaude-values.yaml}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"
TARGET_VERSION="${TARGET_VERSION:-latest}"

# Script options
DRY_RUN=false
SKIP_BACKUP=false
FORCE_UPGRADE=false
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
            --version)
                TARGET_VERSION="$2"
                shift 2
                ;;
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
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                FORCE_UPGRADE=true
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
        return 1
    fi

    # Check if kubectl is installed
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed"
        return 1
    fi

    # Check if kubeconfig is configured
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Kubernetes cluster is not accessible"
        return 1
    fi

    # Check if values file exists
    if [ ! -f "$VALUES_FILE" ]; then
        log_warning "Values file not found: $VALUES_FILE"
        log_info "Will attempt to get values from existing release"
    fi

    # Check if release exists
    if ! helm list -n "$NAMESPACE" | grep -q "^$RELEASE_NAME"; then
        log_error "Helm release '$RELEASE_NAME' not found in namespace '$NAMESPACE'"
        return 1
    fi

    log_success "Prerequisites check passed"
    return 0
}

# Get current version
get_current_version() {
    local version
    version=$(helm list -n "$NAMESPACE" -o json | \
        jq -r ".[] | select(.name == \"$RELEASE_NAME\") | .app_version" 2>/dev/null || echo "unknown")
    echo "$version"
}

# Get latest available version
get_latest_version() {
    local latest_version

    if [[ "$CHART" == */* ]]; then
        # Repository chart
        latest_version=$(helm search repo "$CHART" -o json | \
            jq -r ".[0].version" 2>/dev/null || echo "unknown")
    else
        # Local chart
        latest_version=$(helm show chart "$CHART" | \
            grep "^version:" | awk '{print $2}' 2>/dev/null || echo "unknown")
    fi

    echo "$latest_version"
}

# Create database backup
create_backup() {
    if [ "$SKIP_BACKUP" = true ]; then
        log_warning "Skipping backup (--no-backup flag was used)"
        return 0
    fi

    log_info "Creating backup..."

    # Create backup directory
    mkdir -p "$BACKUP_DIR"

    local backup_date
    backup_date=$(date +%Y%m%d-%H%M%S)
    local backup_file="$BACKUP_DIR/backup-$backup_date.sql"

    # Create database backup
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create backup: $backup_file"
    else
        # Get postgres pod name
        local postgres_pod
        postgres_pod=$(kubectl get pods -n "$NAMESPACE" -l app.kubernetes.io/component=postgres \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

        if [ -z "$postgres_pod" ]; then
            log_error "PostgreSQL pod not found"
            return 1
        fi

        kubectl exec -n "$NAMESPACE" "$postgres_pod" -- \
            pg_dump -U postgres autoclaude > "$backup_file" || {
            log_error "Database backup failed"
            return 1
        }
        log_success "Backup created: $backup_file"
    fi

    # Backup current Helm values
    local values_backup="$BACKUP_DIR/values-$backup_date.yaml"
    helm get values "$RELEASE_NAME" -n "$NAMESPACE" > "$values_backup" || {
        log_warning "Failed to backup Helm values"
    }

    # Backup current manifest
    local manifest_backup="$BACKUP_DIR/manifest-$backup_date.yaml"
    helm get manifest "$RELEASE_NAME" -n "$NAMESPACE" > "$manifest_backup" || {
        log_warning "Failed to backup Helm manifest"
    }

    return 0
}

# Update Helm repository
update_repo() {
    if [[ "$CHART" != */* ]]; then
        # Local chart, no need to update
        return 0
    fi

    log_info "Updating Helm repository..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would update Helm repository"
        return 0
    fi

    helm repo update || {
        log_error "Failed to update Helm repository"
        return 1
    }

    log_success "Helm repository updated"
    return 0
}

# Perform Helm upgrade
perform_upgrade() {
    log_info "Upgrading Helm release..."

    # Build upgrade command
    local upgrade_cmd=(
        helm upgrade
        "$RELEASE_NAME"
        "$CHART"
        --namespace "$NAMESPACE"
        --wait
        --timeout "$WAIT_TIMEOUT"
    )

    # Add version if specified
    if [ "$TARGET_VERSION" != "latest" ]; then
        upgrade_cmd+=(--version "$TARGET_VERSION")
    fi

    # Add values file if exists
    if [ -f "$VALUES_FILE" ]; then
        upgrade_cmd+=(--values "$VALUES_FILE")
    fi

    # Add dry-run if specified
    if [ "$DRY_RUN" = true ]; then
        upgrade_cmd+=(--dry-run --debug)
        log_info "[DRY-RUN] Would run: ${upgrade_cmd[*]}"
        return 0
    fi

    # Perform upgrade
    "${upgrade_cmd[@]}" || {
        log_error "Helm upgrade failed"
        return 1
    }

    log_success "Helm upgrade completed"
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
        done < <(kubectl get pods -n "$NAMESPACE" -l "app.kubernetes.io/instance=$RELEASE_NAME" --no-headers)

        if [ "$total_count" -gt 0 ] && [ "$ready_count" -eq "$total_count" ]; then
            log_success "All pods are ready"
            return 0
        fi

        log_info "Waiting... ($ready_count/$total_count ready)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Timeout waiting for pods to become ready"
    return 1
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check Helm release status
    local release_status
    release_status=$(helm status "$RELEASE_NAME" -n "$NAMESPACE" -o json | \
        jq -r '.info.status' 2>/dev/null || echo "unknown")

    if [ "$release_status" != "deployed" ]; then
        log_error "Helm release status: $release_status"
        return 1
    fi

    # Check if all pods are running
    local not_running
    not_running=$(kubectl get pods -n "$NAMESPACE" \
        -l "app.kubernetes.io/instance=$RELEASE_NAME" \
        --no-headers | grep -v "Running" | grep -v "Completed" || true)

    if [ -n "$not_running" ]; then
        log_error "Some pods are not running:"
        echo "$not_running"
        return 1
    fi

    # Check backend health
    if [ "$DRY_RUN" = false ]; then
        local backend_pod
        backend_pod=$(kubectl get pods -n "$NAMESPACE" \
            -l "app.kubernetes.io/instance=$RELEASE_NAME,app.kubernetes.io/component=backend" \
            -o jsonpath='{.items[0].metadata.name}' 2>/dev/null)

        if [ -n "$backend_pod" ]; then
            if ! kubectl exec -n "$NAMESPACE" "$backend_pod" -- \
                curl -f http://localhost:8000/health &> /dev/null; then
                log_error "Backend health check failed"
                return 1
            fi
        fi
    fi

    # Get new version
    local new_version
    new_version=$(get_current_version)
    log_success "Backend version: $new_version"

    log_success "Deployment verification passed"
    return 0
}

# Rollback on failure
rollback() {
    log_error "Initiating rollback..."

    # Get previous revision
    local previous_revision
    previous_revision=$(helm history "$RELEASE_NAME" -n "$NAMESPACE" -o json | \
        jq -r "select(.status != \"pending-upgrade\") | .[-2].revision" 2>/dev/null || echo "unknown")

    if [ "$previous_revision" = "unknown" ] || [ -z "$previous_revision" ]; then
        log_error "No previous revision found for rollback"
        return 1
    fi

    log_info "Rolling back to revision $previous_revision..."

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would rollback to revision $previous_revision"
        return 0
    fi

    # Perform rollback
    helm rollback "$RELEASE_NAME" "$previous_revision" -n "$NAMESPACE" \
        --wait --timeout "$WAIT_TIMEOUT" || {
        log_error "Helm rollback failed"
        return 1
    }

    # Wait for pods to recover
    if ! wait_for_pods; then
        log_error "Pods did not recover after rollback"
        return 1
    fi

    # Verify rollback
    if ! verify_deployment; then
        log_error "Rollback verification failed"
        return 1
    fi

    log_success "Rollback completed successfully"
    return 0
}

# Show release history
show_history() {
    log_info "Release history:"
    helm history "$RELEASE_NAME" -n "$NAMESPACE" --output table
    echo ""
}

# Main update flow
main() {
    log_info "=========================================="
    log_info "Auto Code Helm Update Script"
    log_info "=========================================="
    echo ""

    # Parse arguments
    parse_args "$@"

    # Show configuration
    log_info "Configuration:"
    log_info "  Release Name: $RELEASE_NAME"
    log_info "  Namespace: $NAMESPACE"
    log_info "  Chart: $CHART"
    log_info "  Values File: $VALUES_FILE"
    log_info "  Target Version: $TARGET_VERSION"
    log_info "  Wait Timeout: $WAIT_TIMEOUT"
    log_info "  Dry Run: $DRY_RUN"
    log_info "  Skip Backup: $SKIP_BACKUP"
    echo ""

    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    echo ""

    # Get current version
    local current_version
    current_version=$(get_current_version)
    log_info "Current version: $current_version"

    # Get latest version if targeting latest
    if [ "$TARGET_VERSION" = "latest" ]; then
        local latest_version
        latest_version=$(get_latest_version)
        log_info "Latest version: $latest_version"
        TARGET_VERSION="$latest_version"
    else
        log_info "Target version: $TARGET_VERSION"
    fi
    echo ""

    # Check if already up to date
    if [ "$FORCE_UPGRADE" = false ] && [ "$current_version" = "$TARGET_VERSION" ]; then
        log_info "Already on version $TARGET_VERSION"
        exit 0
    fi

    # Show release history
    show_history

    # Update repository
    if ! update_repo; then
        log_error "Failed to update Helm repository"
        exit 1
    fi
    echo ""

    # Create backup
    if ! create_backup; then
        log_error "Backup creation failed"
        exit 1
    fi
    echo ""

    # Perform upgrade
    if ! perform_upgrade; then
        log_error "Helm upgrade failed"
        rollback
        exit 1
    fi
    echo ""

    # Wait for pods to be ready
    if ! wait_for_pods; then
        log_error "Pods failed to become ready"
        rollback
        exit 1
    fi
    echo ""

    # Verify deployment
    if ! verify_deployment; then
        log_error "Deployment verification failed"
        rollback
        exit 1
    fi
    echo ""

    # Show updated history
    show_history

    # Success
    log_success "=========================================="
    log_success "Upgrade completed successfully!"
    log_success "=========================================="
    echo ""

    # Show version info
    local new_version
    new_version=$(get_current_version)
    log_info "Previous version: $current_version"
    log_info "New version: $new_version"
    echo ""

    log_info "To view logs, run:"
    log_info "  kubectl logs -n $NAMESPACE -l app.kubernetes.io/instance=$RELEASE_NAME -f"
    echo ""

    log_info "To check release status, run:"
    log_info "  helm status $RELEASE_NAME -n $NAMESPACE"
    echo ""

    return 0
}

# Run main function
main "$@"
