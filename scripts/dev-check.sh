#!/bin/bash

###############################################################################
# Auto Claude - Development Environment Verification Script (Unix)
###############################################################################
#
# PURPOSE:
# Verifies that the development environment is correctly configured and
# all dependencies are installed. Runs basic smoke tests.
#
# USAGE:
#   ./scripts/dev-check.sh           - Run all checks
#   ./scripts/dev-check.sh --quick   - Skip smoke tests (faster)
#   ./scripts/dev-check.sh --help    - Show help message
#
# EXIT CODES:
#   0 - All checks passed
#   1 - One or more checks failed
#
###############################################################################

# Don't exit on error - we want to collect all failures
# Note: Not using -u (nounset) because npm scripts on Windows may have unbound variables
set -o pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Get script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Track results
ERRORS=0
WARNINGS=0

# Default options
QUICK_MODE=0
SHOW_HELP=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --quick|-q)
            QUICK_MODE=1
            shift
            ;;
        --help|-h)
            SHOW_HELP=1
            shift
            ;;
        *)
            shift
            ;;
    esac
done

# Show help if requested
if [ $SHOW_HELP -eq 1 ]; then
    echo ""
    echo "Auto Claude - Development Environment Check"
    echo ""
    echo "USAGE:"
    echo "  ./scripts/dev-check.sh           Run all checks"
    echo "  ./scripts/dev-check.sh --quick   Skip smoke tests (faster)"
    echo "  ./scripts/dev-check.sh --help    Show this help message"
    echo ""
    echo "OPTIONS:"
    echo "  --quick, -q  Skip lint and type checks (faster verification)"
    echo "  --help, -h   Show this help message"
    echo ""
    echo "EXIT CODES:"
    echo "  0 - All checks passed"
    echo "  1 - One or more checks failed"
    echo ""
    exit 0
fi

###############################################################################
# Utility Functions
###############################################################################

print_step() {
    echo -e "${CYAN}➤${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}~${NC} $1"
    WARNINGS=$((WARNINGS + 1))
}

print_error() {
    echo -e "${RED}✗${NC} $1"
    ERRORS=$((ERRORS + 1))
}

check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Auto Claude - Development Environment Check             ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

###############################################################################
# Runtime Prerequisites
###############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}RUNTIME PREREQUISITES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check Node.js
print_step "Checking Node.js..."
if check_command node; then
    NODE_VERSION=$(node --version | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 24 ]; then
        print_success "Node.js v$NODE_VERSION"
    else
        print_error "Node.js v$NODE_VERSION (v24+ required)"
    fi
else
    print_error "Node.js not found"
fi

# Check npm
print_step "Checking npm..."
if check_command npm; then
    NPM_VERSION=$(npm --version 2>/dev/null | head -1)
    if [ -n "$NPM_VERSION" ]; then
        NPM_MAJOR=$(echo "$NPM_VERSION" | cut -d. -f1)
        if [ "$NPM_MAJOR" -ge 10 ]; then
            print_success "npm v$NPM_VERSION"
        else
            print_error "npm v$NPM_VERSION (v10+ required)"
        fi
    else
        print_error "npm version check failed"
    fi
else
    print_error "npm not found"
fi

# Check Python
print_step "Checking Python..."
PYTHON_CMD=""
for cmd in python3.12 python3.13 python3.14 python3 python; do
    if check_command "$cmd"; then
        PY_VERSION=$($cmd --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
        PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
        if [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -ge 12 ]; then
            PYTHON_CMD="$cmd"
            break
        fi
    fi
done

if [ -n "$PYTHON_CMD" ]; then
    PY_FULL_VERSION=$($PYTHON_CMD --version 2>&1)
    print_success "$PY_FULL_VERSION"
else
    print_error "Python 3.12+ not found"
fi

# Check uv (optional)
print_step "Checking uv (Python package manager)..."
if check_command uv; then
    UV_VERSION=$(uv --version 2>&1 | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    print_success "uv v$UV_VERSION"
else
    print_warning "uv not found (optional, but recommended for backend development)"
fi

echo ""

###############################################################################
# Dependencies Check
###############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}INSTALLED DEPENDENCIES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

cd "$PROJECT_ROOT"

# Check root node_modules
print_step "Checking root dependencies..."
if [ -d "node_modules" ]; then
    print_success "Root node_modules present"
else
    print_error "Root node_modules missing - run ./scripts/dev-setup.sh"
fi

# Check frontend dependencies (npm workspaces hoists to root)
print_step "Checking frontend dependencies..."
# In npm workspaces, dependencies are hoisted to root node_modules
# Check if electron package exists in root node_modules (key frontend dependency)
if [ -d "$PROJECT_ROOT/node_modules/electron" ]; then
    print_success "Frontend dependencies accessible (workspaces mode)"
elif [ -d "$PROJECT_ROOT/apps/frontend/node_modules" ]; then
    print_success "Frontend node_modules present"
else
    print_error "Frontend dependencies missing - run ./scripts/dev-setup.sh"
fi

# Check backend venv (optional)
print_step "Checking backend virtual environment..."
if [ -d "apps/backend/.venv" ]; then
    print_success "Backend .venv present"
else
    print_warning "Backend .venv not found (needed for Python development)"
fi

# Check .env file
print_step "Checking backend .env configuration..."
if [ -f "apps/backend/.env" ]; then
    print_success "Backend .env file present"
else
    print_warning "Backend .env missing - copy from apps/backend/.env.example"
fi

echo ""

###############################################################################
# Smoke Tests (unless --quick)
###############################################################################

if [ $QUICK_MODE -eq 0 ]; then
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}SMOKE TESTS${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Run lint check
    print_step "Running lint check..."
    cd "$PROJECT_ROOT/apps/frontend"
    npm run lint > /dev/null 2>&1
    LINT_EXIT=$?
    if [ $LINT_EXIT -eq 0 ]; then
        print_success "Lint check passed"
    else
        print_error "Lint check failed - run: cd apps/frontend && npm run lint"
    fi

    # Run type check (only fail on production code errors, not test files)
    print_step "Running TypeScript type check..."
    PROD_ERRORS=$(npm run typecheck 2>&1 | grep "error TS" | grep -v "\.test\." | grep -v "__tests__" | wc -l)
    if [ "$PROD_ERRORS" -eq 0 ]; then
        print_success "TypeScript type check passed (production code)"
    else
        print_error "TypeScript type check failed - run: cd apps/frontend && npm run typecheck"
    fi

    cd "$PROJECT_ROOT"
    echo ""
else
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${BLUE}SMOKE TESTS${NC} ${YELLOW}(skipped - use without --quick to run)${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
fi

###############################################################################
# Summary
###############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SUMMARY${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    if [ $WARNINGS -eq 0 ]; then
        echo -e "${GREEN}✓ All checks passed! Environment is ready.${NC}"
    else
        echo -e "${GREEN}✓ All required checks passed!${NC}"
        echo -e "${YELLOW}~ $WARNINGS warning(s) - see optional items above${NC}"
    fi
    echo ""
    echo -e "  ${CYAN}Quick commands:${NC}"
    echo -e "    Start dev server:    ${YELLOW}./scripts/dev-run.sh${NC}"
    echo -e "    Start with MCP:      ${YELLOW}./scripts/dev-run.sh --mcp${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ $ERRORS check(s) failed, $WARNINGS warning(s)${NC}"
    echo ""
    echo -e "Please fix the issues above. Common fixes:"
    echo -e "  - Run ${YELLOW}./scripts/dev-setup.sh${NC} to install dependencies"
    echo -e "  - Copy ${YELLOW}apps/backend/.env.example${NC} to ${YELLOW}apps/backend/.env${NC}"
    echo ""
    exit 1
fi
