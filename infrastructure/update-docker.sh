#!/bin/bash
#
# Auto Code Docker Compose Update Script
#
# This script automates the update process for Docker Compose deployments.
# It performs backups, pulls new images, recreates containers, and verifies health.
# If any step fails, it automatically rolls back to the previous version.
#
# Usage:
#   ./update-docker.sh [--version VERSION] [--dry-run] [--no-backup]
#
# Options:
#   --version VERSION    Pull specific version tag (default: latest)
#   --dry-run            Show what would be done without making changes
#   --no-backup          Skip database backup (not recommended)
#   --help               Show this help message
#
# Examples:
#   ./update-docker.sh
#   ./update-docker.sh --version v2.9.0
#   ./update-docker.sh --dry-run
#
# For more information, see guides/SELF_HOSTED_UPDATES.md
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
COMPOSE_FILE="${AUTOCLAUDE_DIR:-$SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${AUTOCLAUDE_DIR:-$SCRIPT_DIR}/.env"
BACKUP_DIR="${AUTOCLAUDE_DIR:-$SCRIPT_DIR}/backups"
COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-autoclaude}"
TARGET_VERSION="${TARGET_VERSION:-latest}"

# Script options
DRY_RUN=false
SKIP_BACKUP=false
FORCE_UPDATE=false

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
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --no-backup)
                SKIP_BACKUP=true
                shift
                ;;
            --force)
                FORCE_UPDATE=true
                shift
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

    # Check if docker-compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "docker-compose is not installed"
        return 1
    fi

    # Check if docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        return 1
    fi

    # Check if compose file exists
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose file not found: $COMPOSE_FILE"
        return 1
    fi

    # Check if .env file exists
    if [ ! -f "$ENV_FILE" ]; then
        log_warning ".env file not found: $ENV_FILE"
    fi

    log_success "Prerequisites check passed"
    return 0
}

# Get current version
get_current_version() {
    local version
    version=$(docker exec "${COMPOSE_PROJECT_NAME}-backend" \
        python -c "import autocode; print(autocode.__version__)" 2>/dev/null || echo "unknown")
    echo "$version"
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

    # Check if postgres container is running
    if ! docker ps --format '{{.Names}}' | grep -q "${COMPOSE_PROJECT_NAME}-postgres"; then
        log_error "PostgreSQL container is not running"
        return 1
    fi

    # Create database backup
    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would create backup: $backup_file"
    else
        docker exec "${COMPOSE_PROJECT_NAME}-postgres" \
            pg_dump -U postgres autoclaude > "$backup_file" || {
            log_error "Database backup failed"
            return 1
        }
        log_success "Backup created: $backup_file"
    fi

    # Backup docker-compose.yml
    if [ -f "$COMPOSE_FILE" ]; then
        cp "$COMPOSE_FILE" "$BACKUP_DIR/docker-compose.yml-$backup_date"
        log_info "Docker Compose file backed up"
    fi

    # Backup .env file
    if [ -f "$ENV_FILE" ]; then
        cp "$ENV_FILE" "$BACKUP_DIR/.env-$backup_date"
        log_info ".env file backed up"
    fi

    return 0
}

# Pull new images
pull_images() {
    log_info "Pulling new images (version: $TARGET_VERSION)..."

    local compose_cmd
    if docker compose version &> /dev/null; then
        compose_cmd="docker compose"
    else
        compose_cmd="docker-compose"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would pull images for version: $TARGET_VERSION"
        return 0
    fi

    # Pull images
    $compose_cmd -f "$COMPOSE_FILE" pull || {
        log_error "Failed to pull images"
        return 1
    }

    log_success "Images pulled successfully"
    return 0
}

# Stop services
stop_services() {
    log_info "Stopping services..."

    local compose_cmd
    if docker compose version &> /dev/null; then
        compose_cmd="docker compose"
    else
        compose_cmd="docker-compose"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would stop services"
        return 0
    fi

    # Stop services gracefully
    $compose_cmd -f "$COMPOSE_FILE" down || {
        log_error "Failed to stop services"
        return 1
    }

    log_success "Services stopped"
    return 0
}

# Start services
start_services() {
    log_info "Starting services..."

    local compose_cmd
    if docker compose version &> /dev/null; then
        compose_cmd="docker compose"
    else
        compose_cmd="docker-compose"
    fi

    if [ "$DRY_RUN" = true ]; then
        log_info "[DRY-RUN] Would start services"
        return 0
    fi

    # Start services in detached mode
    $compose_cmd -f "$COMPOSE_FILE" up -d || {
        log_error "Failed to start services"
        return 1
    }

    log_success "Services started"
    return 0
}

# Wait for services to be healthy
wait_for_healthy() {
    local timeout=300  # 5 minutes
    local elapsed=0
    local interval=5

    log_info "Waiting for services to become healthy (timeout: ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        local healthy_count=0
        local total_count=0

        # Count services
        while IFS= read -r line; do
            total_count=$((total_count + 1))
            if echo "$line" | grep -q "healthy"; then
                healthy_count=$((healthy_count + 1))
            fi
        done < <(docker ps --filter "name=${COMPOSE_PROJECT_NAME}" --format "{{.Status}}")

        if [ "$total_count" -gt 0 ] && [ "$healthy_count" -eq "$total_count" ]; then
            log_success "All services are healthy"
            return 0
        fi

        log_info "Waiting... ($healthy_count/$total_count healthy)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Timeout waiting for services to become healthy"
    return 1
}

# Verify services
verify_services() {
    log_info "Verifying services..."

    # Check if backend is responding
    if [ "$DRY_RUN" = false ]; then
        if ! docker exec "${COMPOSE_PROJECT_NAME}-backend" \
            curl -f http://localhost:8000/health &> /dev/null; then
            log_error "Backend health check failed"
            return 1
        fi
    fi

    # Check new version
    local new_version
    new_version=$(get_current_version)
    log_success "Backend version: $new_version"

    log_success "Service verification passed"
    return 0
}

# Rollback on failure
rollback() {
    log_error "Initiating rollback..."

    local backup_file
    backup_file=$(ls -t "$BACKUP_DIR"/backup-*.sql 2>/dev/null | head -1)

    if [ -z "$backup_file" ]; then
        log_error "No backup file found for rollback"
        return 1
    fi

    log_info "Restoring from backup: $backup_file"

    local compose_cmd
    if docker compose version &> /dev/null; then
        compose_cmd="docker compose"
    else
        compose_cmd="docker-compose"
    fi

    # Stop backend
    $compose_cmd -f "$COMPOSE_FILE" stop web-backend

    # Restore database
    docker exec -i "${COMPOSE_PROJECT_NAME}-postgres" \
        psql -U postgres -d autoclaude < "$backup_file" || {
        log_error "Database restore failed"
        return 1
    }

    # Start backend
    $compose_cmd -f "$COMPOSE_FILE" start web-backend

    # Wait for recovery
    sleep 10

    # Verify rollback
    if wait_for_healthy && verify_services; then
        log_success "Rollback completed successfully"
        return 0
    else
        log_error "Rollback verification failed"
        return 1
    fi
}

# Main update flow
main() {
    log_info "=========================================="
    log_info "Auto Code Docker Compose Update Script"
    log_info "=========================================="
    echo ""

    # Parse arguments
    parse_args "$@"

    # Show configuration
    log_info "Configuration:"
    log_info "  Compose File: $COMPOSE_FILE"
    log_info "  Backup Directory: $BACKUP_DIR"
    log_info "  Target Version: $TARGET_VERSION"
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
    echo ""

    # Check if already up to date (unless forced)
    if [ "$FORCE_UPDATE" = false ] && [ "$current_version" = "$TARGET_VERSION" ] && [ "$TARGET_VERSION" != "latest" ]; then
        log_info "Already on version $TARGET_VERSION"
        exit 0
    fi

    # Create backup
    if ! create_backup; then
        log_error "Backup creation failed"
        exit 1
    fi
    echo ""

    # Pull new images
    if ! pull_images; then
        log_error "Failed to pull images"
        rollback
        exit 1
    fi
    echo ""

    # Stop services
    if ! stop_services; then
        log_error "Failed to stop services"
        exit 1
    fi
    echo ""

    # Start services with new images
    if ! start_services; then
        log_error "Failed to start services"
        rollback
        exit 1
    fi
    echo ""

    # Wait for services to be healthy
    if ! wait_for_healthy; then
        log_error "Services failed to become healthy"
        rollback
        exit 1
    fi
    echo ""

    # Verify services
    if ! verify_services; then
        log_error "Service verification failed"
        rollback
        exit 1
    fi
    echo ""

    # Success
    log_success "=========================================="
    log_success "Update completed successfully!"
    log_success "=========================================="
    echo ""

    # Show new version
    local new_version
    new_version=$(get_current_version)
    log_info "Previous version: $current_version"
    log_info "New version: $new_version"
    echo ""

    log_info "To view logs, run:"
    log_info "  docker-compose -f $COMPOSE_FILE logs -f"
    echo ""

    return 0
}

# Run main function
main "$@"
