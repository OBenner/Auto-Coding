#!/bin/bash
#
# Cloud E2E Integration Test Runner
#
# This script automates the full end-to-end testing workflow:
# 1. Checks prerequisites (Docker, Python, curl)
# 2. Starts cloud stack (PostgreSQL, Redis, Backend)
# 3. Runs database migrations
# 4. Executes E2E tests
# 5. Reports results
#
# Usage:
#   bash tests/run_e2e_tests.sh [--skip-start] [--skip-cleanup]
#
# Options:
#   --skip-start    Skip starting Docker stack (assume already running)
#   --skip-cleanup  Skip cleanup after tests
#   --verbose       Show detailed output
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$(dirname "$SCRIPT_DIR")"
API_BASE_URL="http://localhost:8000"
TEST_USER_EMAIL="test@example.com"
TEST_USER_PASSWORD="testpass123"
SKIP_START=false
SKIP_CLEANUP=false
VERBOSE=false

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-start)
            SKIP_START=true
            shift
            ;;
        --skip-cleanup)
            SKIP_CLEANUP=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-start] [--skip-cleanup] [--verbose]"
            exit 1
            ;;
    esac
done

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_section() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Wait for service to be ready
wait_for_service() {
    local url=$1
    local service_name=$2
    local timeout=${3:-60}
    local elapsed=0

    log_info "Waiting for $service_name to be ready..."

    while [ $elapsed -lt $timeout ]; do
        if curl -s -f "$url" >/dev/null 2>&1; then
            log_success "$service_name is ready!"
            return 0
        fi
        sleep 2
        elapsed=$((elapsed + 2))
    done

    log_error "$service_name did not become ready within ${timeout}s"
    return 1
}

# Check prerequisites
check_prerequisites() {
    log_section "Checking Prerequisites"

    local missing=()

    if ! command_exists docker; then
        missing+=("docker")
    else
        log_success "Docker is installed: $(docker --version)"
    fi

    if ! command_exists docker-compose; then
        missing+=("docker-compose")
    else
        log_success "Docker Compose is installed: $(docker-compose --version)"
    fi

    if ! command_exists curl; then
        missing+=("curl")
    else
        log_success "curl is installed"
    fi

    if ! command_exists python3; then
        missing+=("python3")
    else
        log_success "Python is installed: $(python3 --version)"
    fi

    if [ ${#missing[@]} -gt 0 ]; then
        log_error "Missing required tools: ${missing[*]}"
        log_info "Please install the missing tools and try again"
        return 1
    fi

    return 0
}

# Start Docker stack
start_docker_stack() {
    if [ "$SKIP_START" = true ]; then
        log_info "Skipping Docker stack startup (--skip-start)"
        return 0
    fi

    log_section "Starting Cloud Stack"

    cd "$BACKEND_DIR"

    # Check if containers are already running
    if docker ps | grep -q "autoclaude-backend"; then
        log_warning "Cloud stack is already running"
        log_info "Use --skip-start to skip this check"
        read -p "Restart the stack? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Continuing with existing stack..."
            return 0
        fi
        log_info "Stopping existing stack..."
        docker-compose -f docker-compose.cloud.yml down
    fi

    log_info "Starting services (PostgreSQL, Redis, Backend)..."
    docker-compose -f docker-compose.cloud.yml up -d

    log_info "Waiting for services to become healthy (this may take 30-60 seconds)..."
    sleep 10  # Give containers time to initialize

    # Wait for backend API
    if ! wait_for_service "$API_BASE_URL/health" "Backend API" 60; then
        log_error "Backend API failed to start"
        log_info "Check logs with: docker-compose -f docker-compose.cloud.yml logs"
        return 1
    fi

    log_success "Cloud stack is running!"
    return 0
}

# Run database migrations
run_migrations() {
    log_section "Running Database Migrations"

    cd "$BACKEND_DIR"

    log_info "Applying migrations..."
    if docker exec autoclaude-backend alembic upgrade head 2>&1; then
        log_success "Migrations applied successfully"
    else
        log_error "Migration failed"
        return 1
    fi

    log_info "Checking migration status..."
    docker exec autoclaude-backend alembic current

    return 0
}

# Test functions
test_health_check() {
    log_info "Test 1: Health Check"

    response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        log_success "Health check passed"
        [ "$VERBOSE" = true ] && echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        log_error "Health check failed (HTTP $http_code)"
        return 1
    fi
}

test_user_signup() {
    log_info "Test 2: User Signup"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/api/users/register" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "201" ]; then
        log_success "User signup succeeded"
        [ "$VERBOSE" = true ] && echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    elif [ "$http_code" = "400" ]; then
        log_warning "User already exists (continuing...)"
        return 0
    else
        log_error "User signup failed (HTTP $http_code)"
        [ "$VERBOSE" = true ] && echo "$body"
        return 1
    fi
}

test_user_login() {
    log_info "Test 3: User Login"

    response=$(curl -s -w "\n%{http_code}" -X POST "$API_BASE_URL/api/users/login" \
        -H "Content-Type: application/json" \
        -d "{\"email\":\"$TEST_USER_EMAIL\",\"password\":\"$TEST_USER_PASSWORD\"}")

    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        log_success "User login succeeded"

        # Extract access token
        ACCESS_TOKEN=$(echo "$body" | jq -r '.access_token' 2>/dev/null || echo "")

        if [ -n "$ACCESS_TOKEN" ] && [ "$ACCESS_TOKEN" != "null" ]; then
            log_success "Access token received"
            [ "$VERBOSE" = true ] && echo "Token: ${ACCESS_TOKEN:0:50}..."
        fi

        return 0
    else
        log_error "User login failed (HTTP $http_code)"
        [ "$VERBOSE" = true ] && echo "$body"
        return 1
    fi
}

test_oauth_status() {
    log_info "Test 4: OAuth Status"

    response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/git/status")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        log_success "OAuth status check passed"
        [ "$VERBOSE" = true ] && echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        log_error "OAuth status check failed (HTTP $http_code)"
        return 1
    fi
}

test_oauth_redirect() {
    log_info "Test 5: GitHub OAuth Redirect"

    http_code=$(curl -s -o /dev/null -w "%{http_code}" "$API_BASE_URL/api/git/github/authorize")

    if [ "$http_code" = "302" ]; then
        log_success "GitHub OAuth redirect working (HTTP 302)"
        return 0
    else
        log_error "GitHub OAuth redirect failed (HTTP $http_code)"
        return 1
    fi
}

test_usage_tracking() {
    log_info "Test 6: Usage Tracking Dashboard"

    response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/usage/dashboard?user_id=1")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        log_success "Usage dashboard working"
        [ "$VERBOSE" = true ] && echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        log_error "Usage dashboard failed (HTTP $http_code)"
        return 1
    fi
}

test_usage_stats() {
    log_info "Test 7: Usage Statistics"

    response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/usage/stats?user_id=1&period=daily&days_back=7")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        log_success "Usage statistics working"
        [ "$VERBOSE" = true ] && echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        log_error "Usage statistics failed (HTTP $http_code)"
        return 1
    fi
}

test_usage_health() {
    log_info "Test 8: Usage Health (Redis)"

    response=$(curl -s -w "\n%{http_code}" "$API_BASE_URL/api/usage/health")
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | head -n-1)

    if [ "$http_code" = "200" ]; then
        redis_healthy=$(echo "$body" | jq -r '.redis_healthy' 2>/dev/null || echo "unknown")

        if [ "$redis_healthy" = "true" ]; then
            log_success "Redis connection healthy"
        else
            log_warning "Redis connection not available"
        fi

        [ "$VERBOSE" = true ] && echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        log_error "Usage health check failed (HTTP $http_code)"
        return 1
    fi
}

# Run all tests
run_tests() {
    log_section "Running E2E Tests"

    local tests_passed=0
    local tests_failed=0

    # Array of test functions
    declare -a tests=(
        "test_health_check"
        "test_user_signup"
        "test_user_login"
        "test_oauth_status"
        "test_oauth_redirect"
        "test_usage_tracking"
        "test_usage_stats"
        "test_usage_health"
    )

    # Run each test
    for test_func in "${tests[@]}"; do
        echo ""
        if $test_func; then
            tests_passed=$((tests_passed + 1))
        else
            tests_failed=$((tests_failed + 1))
        fi
        sleep 1  # Brief pause between tests
    done

    # Print summary
    log_section "Test Results Summary"

    local total=$((tests_passed + tests_failed))
    echo ""
    echo "Total Tests: $total"
    echo -e "${GREEN}Passed: $tests_passed${NC}"
    echo -e "${RED}Failed: $tests_failed${NC}"
    echo ""

    if [ $tests_failed -eq 0 ]; then
        log_success "All tests passed! 🎉"
        return 0
    else
        log_error "$tests_failed test(s) failed"
        return 1
    fi
}

# Cleanup
cleanup() {
    if [ "$SKIP_CLEANUP" = true ]; then
        log_info "Skipping cleanup (--skip-cleanup)"
        return 0
    fi

    log_section "Cleanup"

    read -p "Stop the Docker stack? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cd "$BACKEND_DIR"
        log_info "Stopping cloud stack..."
        docker-compose -f docker-compose.cloud.yml down
        log_success "Stack stopped"
    else
        log_info "Stack left running"
        log_info "To stop manually: cd apps/web-backend && docker-compose -f docker-compose.cloud.yml down"
    fi
}

# Main execution
main() {
    log_section "Cloud E2E Integration Test Runner"

    # Check prerequisites
    if ! check_prerequisites; then
        exit 1
    fi

    # Start Docker stack
    if ! start_docker_stack; then
        log_error "Failed to start Docker stack"
        exit 1
    fi

    # Run migrations
    if ! run_migrations; then
        log_error "Failed to run migrations"
        exit 1
    fi

    # Run tests
    if ! run_tests; then
        log_error "Some tests failed"
        cleanup
        exit 1
    fi

    # Cleanup
    cleanup

    log_success "E2E testing complete!"
    exit 0
}

# Run main function
main
