#!/bin/bash
#
# Auto Code Docker Compose Deployment Script
#
# This script automates the initial deployment of Auto Code using Docker Compose.
# It creates the necessary configuration files, pulls images, and starts services.
#
# Usage:
#   ./deploy-docker.sh [--compose-file COMPOSE_FILE] [--env-file ENV_FILE] [--quick]
#
# Options:
#   --compose-file COMPOSE_FILE  Path to docker-compose file (default: docker-compose.yml)
#   --env-file ENV_FILE          Path to .env file (default: .env)
#   --quick                      Skip prompts and use defaults
#   --help                       Show this help message
#
# Examples:
#   ./deploy-docker.sh
#   ./deploy-docker.sh --quick
#   ./deploy-docker.sh --compose-file /path/to/docker-compose.yml
#
# For more information, see guides/SELF_HOSTED_DEPLOYMENT.md
#

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default configuration
COMPOSE_FILE="${AUTOCLAUDE_DIR:-$SCRIPT_DIR}/docker-compose.yml"
ENV_FILE="${AUTOCLAUDE_DIR:-$SCRIPT_DIR}/.env"
PROJECT_NAME="${COMPOSE_PROJECT_NAME:-autoclaude}"
QUICK_MODE=false

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
            --compose-file)
                COMPOSE_FILE="$2"
                shift 2
                ;;
            --env-file)
                ENV_FILE="$2"
                shift 2
                ;;
            --quick)
                QUICK_MODE=true
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

    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        log_info "Please install Docker: https://docs.docker.com/get-docker/"
        return 1
    fi

    # Check if docker-compose is installed
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "docker-compose is not installed"
        log_info "Please install Docker Compose: https://docs.docker.com/compose/install/"
        return 1
    fi

    # Check if docker is running
    if ! docker info &> /dev/null; then
        log_error "Docker is not running"
        log_info "Please start Docker"
        return 1
    fi

    # Check available disk space (minimum 2GB)
    local available_space
    available_space=$(df -BG "$SCRIPT_DIR" | tail -1 | awk '{print $4}' | sed 's/G//')
    if [ "$available_space" -lt 2 ]; then
        log_warning "Low disk space: ${available_space}GB available (recommended: 2GB+)"
    fi

    log_success "Prerequisites check passed"
    return 0
}

# Detect compose command
get_compose_cmd() {
    if docker compose version &> /dev/null; then
        echo "docker compose"
    else
        echo "docker-compose"
    fi
}

# Generate secret key
generate_secret_key() {
    openssl rand -hex 32
}

# Create .env file
create_env_file() {
    log_info "Creating .env file..."

    if [ -f "$ENV_FILE" ]; then
        if [ "$QUICK_MODE" = false ]; then
            log_warning ".env file already exists: $ENV_FILE"
            read -rp "Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Keeping existing .env file"
                return 0
            fi
        else
            log_info "Skipping .env creation (already exists)"
            return 0
        fi
    fi

    # Generate secret key
    local secret_key
    secret_key=$(generate_secret_key)

    # Create .env file
    cat > "$ENV_FILE" << EOF
# Auto Code Environment Configuration
# Generated: $(date)

# Server Configuration
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,https://autoclaude.app

# Authentication
SECRET_KEY=$secret_key
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Database Configuration (PostgreSQL)
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/autoclaude
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=autoclaude

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=

# OAuth Configuration (Optional)
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITLAB_CLIENT_ID=
GITLAB_CLIENT_SECRET=
OAUTH_REDIRECT_URI=http://localhost:8000/api/git/callback

# WebSocket Configuration
WS_HEARTBEAT_INTERVAL=30

# Telemetry
DISABLE_TELEMETRY=false

# Workspace Directory
WORKSPACE_DIR=/app/backend/.auto-claude/specs
EOF

    log_success ".env file created: $ENV_FILE"
    log_warning "Please review and update .env with your configuration"
    return 0
}

# Create docker-compose.yml from template
create_compose_file() {
    log_info "Creating docker-compose.yml..."

    if [ -f "$COMPOSE_FILE" ]; then
        if [ "$QUICK_MODE" = false ]; then
            log_warning "Docker Compose file already exists: $COMPOSE_FILE"
            read -rp "Overwrite? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                log_info "Keeping existing docker-compose.yml"
                return 0
            fi
        else
            log_info "Skipping docker-compose.yml creation (already exists)"
            return 0
        fi
    fi

    # Create docker-compose.yml
    cat > "$COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  # PostgreSQL database for user data and repositories
  postgres:
    image: postgres:16-alpine
    container_name: autoclaude-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-autoclaude}
      POSTGRES_INITDB_ARGS: "-E UTF8"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-postgres}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - autoclaude-network
    restart: unless-stopped

  # Redis for usage tracking and caching
  redis:
    image: redis:7-alpine
    container_name: autoclaude-redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - autoclaude-network
    restart: unless-stopped

  # Auto Code web backend API
  web-backend:
    image: ghcr.io/obenner/autoclaude-backend:latest
    container_name: autoclaude-backend
    environment:
      # Server configuration
      HOST: ${HOST:-0.0.0.0}
      PORT: ${PORT:-8000}
      DEBUG: ${DEBUG:-false}
      LOG_LEVEL: ${LOG_LEVEL:-INFO}

      # CORS configuration
      CORS_ORIGINS: ${CORS_ORIGINS:-http://localhost:3000,https://autoclaude.app}

      # Authentication
      SECRET_KEY: ${SECRET_KEY}
      ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE_MINUTES:-60}

      # Database configuration (connect to postgres service)
      DATABASE_URL: postgresql://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-autoclaude}

      # Redis configuration (connect to redis service)
      REDIS_HOST: redis
      REDIS_PORT: 6379
      REDIS_DB: ${REDIS_DB:-0}
      REDIS_PASSWORD: ${REDIS_PASSWORD:-}

      # OAuth configuration
      GITHUB_CLIENT_ID: ${GITHUB_CLIENT_ID:-}
      GITHUB_CLIENT_SECRET: ${GITHUB_CLIENT_SECRET:-}
      GITLAB_CLIENT_ID: ${GITLAB_CLIENT_ID:-}
      GITLAB_CLIENT_SECRET: ${GITLAB_CLIENT_SECRET:-}
      OAUTH_REDIRECT_URI: ${OAUTH_REDIRECT_URI:-http://localhost:8000/api/git/callback}

      # WebSocket configuration
      WS_HEARTBEAT_INTERVAL: ${WS_HEARTBEAT_INTERVAL:-30}

      # Telemetry
      DISABLE_TELEMETRY: ${DISABLE_TELEMETRY:-false}

      # Workspace directory
      WORKSPACE_DIR: ${WORKSPACE_DIR:-/app/backend/.auto-claude/specs}
    ports:
      - "${PORT:-8000}:8000"
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - autoclaude-network
    restart: unless-stopped
    volumes:
      - workspace_data:/app/backend/.auto-claude/specs

networks:
  autoclaude-network:
    driver: bridge

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local
  workspace_data:
    driver: local
EOF

    log_success "Docker Compose file created: $COMPOSE_FILE"
    return 0
}

# Pull Docker images
pull_images() {
    log_info "Pulling Docker images..."

    local compose_cmd
    compose_cmd=$(get_compose_cmd)

    $compose_cmd -f "$COMPOSE_FILE" pull || {
        log_error "Failed to pull images"
        return 1
    }

    log_success "Images pulled successfully"
    return 0
}

# Start services
start_services() {
    log_info "Starting services..."

    local compose_cmd
    compose_cmd=$(get_compose_cmd)

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
        done < <(docker ps --filter "name=${PROJECT_NAME}" --format "{{.Status}}")

        if [ "$total_count" -gt 0 ] && [ "$healthy_count" -eq "$total_count" ]; then
            log_success "All services are healthy"
            return 0
        fi

        log_info "Waiting... ($healthy_count/$total_count healthy)"
        sleep $interval
        elapsed=$((elapsed + interval))
    done

    log_error "Timeout waiting for services to become healthy"
    log_warning "Some services may still be starting. Check logs with:"
    log_warning "  docker-compose -f $COMPOSE_FILE logs -f"
    return 1
}

# Verify deployment
verify_deployment() {
    log_info "Verifying deployment..."

    # Check if backend is responding
    local max_attempts=10
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if curl -f http://localhost:8000/health &> /dev/null; then
            log_success "Backend health check passed"
            break
        fi

        if [ $attempt -eq $max_attempts ]; then
            log_error "Backend health check failed after $max_attempts attempts"
            log_warning "Check logs with: docker-compose -f $COMPOSE_FILE logs web-backend"
            return 1
        fi

        log_info "Waiting for backend to be ready... (attempt $attempt/$max_attempts)"
        sleep 5
        attempt=$((attempt + 1))
    done

    # Check database connection
    if ! docker exec "${PROJECT_NAME}-postgres" \
        pg_isready -U postgres &> /dev/null; then
        log_error "Database health check failed"
        return 1
    fi
    log_success "Database connection verified"

    # Check Redis connection
    if ! docker exec "${PROJECT_NAME}-redis" \
        redis-cli ping &> /dev/null; then
        log_error "Redis health check failed"
        return 1
    fi
    log_success "Redis connection verified"

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

    log_info "Services:"
    local compose_cmd
    compose_cmd=$(get_compose_cmd)
    $compose_cmd -f "$COMPOSE_FILE" ps
    echo ""

    log_info "Service URLs:"
    log_info "  Backend API: http://localhost:8000"
    log_info "  Health Check: http://localhost:8000/health"
    log_info "  API Docs: http://localhost:8000/docs"
    echo ""

    log_info "Useful commands:"
    log_info "  View logs:     $compose_cmd -f $COMPOSE_FILE logs -f"
    log_info "  Stop services: $compose_cmd -f $COMPOSE_FILE down"
    log_info "  Restart:       $compose_cmd -f $COMPOSE_FILE restart"
    log_info "  Update:        ./update-docker.sh"
    echo ""

    log_info "Configuration files:"
    log_info "  Compose file: $COMPOSE_FILE"
    log_info "  Environment:  $ENV_FILE"
    echo ""

    log_warning "Next steps:"
    log_warning "1. Review and update $ENV_FILE with your configuration"
    log_warning "2. Configure OAuth providers (GitHub/GitLab) if needed"
    log_warning "3. Set up reverse proxy (nginx) for production deployment"
    log_warning "4. Configure backups for postgres_data and workspace_data volumes"
    echo ""
}

# Main deployment flow
main() {
    log_info "=========================================="
    log_info "Auto Code Docker Compose Deployment"
    log_info "=========================================="
    echo ""

    # Parse arguments
    parse_args "$@"

    # Show configuration
    log_info "Configuration:"
    log_info "  Compose File: $COMPOSE_FILE"
    log_info "  Environment:  $ENV_FILE"
    log_info "  Project Name: $PROJECT_NAME"
    log_info "  Quick Mode:   $QUICK_MODE"
    echo ""

    # Check prerequisites
    if ! check_prerequisites; then
        log_error "Prerequisites check failed"
        exit 1
    fi
    echo ""

    # Prompt user if not in quick mode
    if [ "$QUICK_MODE" = false ]; then
        log_info "This will deploy Auto Code using Docker Compose."
        log_info "Services: PostgreSQL, Redis, Backend"
        echo ""
        read -rp "Continue? (Y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            log_info "Deployment cancelled"
            exit 0
        fi
        echo ""
    fi

    # Create configuration files
    if ! create_compose_file; then
        log_error "Failed to create docker-compose.yml"
        exit 1
    fi
    echo ""

    if ! create_env_file; then
        log_error "Failed to create .env file"
        exit 1
    fi
    echo ""

    # Pull images
    if ! pull_images; then
        log_error "Failed to pull Docker images"
        exit 1
    fi
    echo ""

    # Start services
    if ! start_services; then
        log_error "Failed to start services"
        exit 1
    fi
    echo ""

    # Wait for services to be healthy
    if ! wait_for_healthy; then
        log_error "Services failed to become healthy"
        log_warning "Check logs with: docker-compose -f $COMPOSE_FILE logs -f"
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
