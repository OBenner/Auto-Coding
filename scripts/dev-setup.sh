#!/bin/bash

###############################################################################
# Auto Code - Development Environment Setup Script (Unix)
###############################################################################
#
# PURPOSE:
# Sets up the complete development environment by installing all dependencies
# and verifying prerequisites.
#
# USAGE:
#   ./scripts/dev-setup.sh
#
# PREREQUISITES:
#   - Node.js >= 24.0.0
#   - Python 3.12+
#   - npm >= 10.0.0
#
###############################################################################

set -euo pipefail

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

# Track errors
ERRORS=0

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Auto Code - Development Setup                      ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

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
    echo -e "${YELLOW}⚠${NC} $1"
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

version_gte() {
    # Compare version strings: returns 0 if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

###############################################################################
# Prerequisites Check
###############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}CHECKING PREREQUISITES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Check Node.js
print_step "Checking Node.js..."
if check_command node; then
    NODE_VERSION=$(node --version | sed 's/v//')
    NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
    if [ "$NODE_MAJOR" -ge 24 ]; then
        print_success "Node.js v$NODE_VERSION (>= 24.0.0 required)"
    else
        print_error "Node.js v$NODE_VERSION found, but v24.0.0+ is required"
        echo "       Install Node.js 24+: https://nodejs.org/"
    fi
else
    print_error "Node.js not found"
    echo "       Install Node.js 24+: https://nodejs.org/"
fi

# Check npm
print_step "Checking npm..."
if check_command npm; then
    NPM_VERSION=$(npm --version)
    NPM_MAJOR=$(echo "$NPM_VERSION" | cut -d. -f1)
    if [ "$NPM_MAJOR" -ge 10 ]; then
        print_success "npm v$NPM_VERSION (>= 10.0.0 required)"
    else
        print_error "npm v$NPM_VERSION found, but v10.0.0+ is required"
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
    print_success "$PY_FULL_VERSION (>= 3.12 required)"
else
    print_error "Python 3.12+ not found"
    echo "       Install Python 3.12+:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "         brew install python@3.12"
    else
        echo "         sudo apt install python3.12 python3.12-venv"
    fi
fi

echo ""

# Exit early if prerequisites are missing
if [ $ERRORS -gt 0 ]; then
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${RED}SETUP ABORTED: $ERRORS prerequisite(s) missing${NC}"
    echo -e "${RED}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Please install the missing prerequisites and run this script again."
    exit 1
fi

###############################################################################
# Installation
###############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}INSTALLING DEPENDENCIES${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

cd "$PROJECT_ROOT"

# Install all Node.js dependencies
print_step "Installing Node.js dependencies (frontend + root)..."
if npm run install:all; then
    print_success "Node.js dependencies installed"
else
    print_error "Failed to install Node.js dependencies"
fi

echo ""

###############################################################################
# Summary
###############################################################################

echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}SETUP COMPLETE${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✓ Development environment is ready!${NC}"
    echo ""
    echo -e "  ${CYAN}Next steps:${NC}"
    echo -e "    1. Configure environment: ${YELLOW}cp apps/backend/.env.example apps/backend/.env${NC}"
    echo -e "    2. Edit .env with your API keys"
    echo -e "    3. Start development: ${YELLOW}./scripts/dev-run.sh${NC}"
    echo -e "    4. Verify setup: ${YELLOW}./scripts/dev-check.sh${NC}"
    echo ""
    exit 0
else
    echo -e "${RED}✗ Setup completed with $ERRORS error(s)${NC}"
    echo ""
    echo "Please fix the errors above and run the script again."
    exit 1
fi
