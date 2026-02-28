#!/bin/bash

###############################################################################
# Auto Code - Web Backend Build and Start Script (Unix)
###############################################################################
#
# PURPOSE:
# This script automates the complete build and startup process for the
# web-backend FastAPI service on Unix-based systems (Linux/macOS).
#
# WHAT IT DOES:
# 1. Verifies Python 3.x is installed
# 2. Creates/activates Python virtual environment
# 3. Installs dependencies from requirements.txt
# 4. Checks for .env file (copies from .env.example if missing)
# 5. Starts uvicorn server on port 8000 with hot-reload
#
# USAGE:
#   ./build-and-start.sh
#
###############################################################################

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Change to script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║          Auto Code - Web Backend Build & Start                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# 1. CHECK FOR PYTHON
# =============================================================================

echo -e "${BLUE}🔍 Checking for Python...${NC}"

# Find Python 3.x
PYTHON_CMD=""
for cmd in python3.12 python3.13 python3.14 python3 python; do
    if command -v "$cmd" &> /dev/null; then
        # Get version
        VERSION=$("$cmd" --version 2>&1 | grep -oE '[0-9]+\.[0-9]+' | head -1)
        MAJOR=$(echo "$VERSION" | cut -d. -f1)
        MINOR=$(echo "$VERSION" | cut -d. -f2)

        # Check if Python 3.x
        if [ "$MAJOR" -eq 3 ]; then
            PYTHON_CMD="$cmd"
            echo -e "${GREEN}✅ Found Python $VERSION: $cmd${NC}"
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo -e "${RED}❌ Error: Python 3.x is required but not found.${NC}"
    echo ""
    echo -e "${YELLOW}Please install Python 3.x:${NC}"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo -e "  ${GREEN}brew install python@3.12${NC}"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo -e "  ${GREEN}sudo apt install python3 python3-venv${NC}"
    else
        echo -e "  Visit: ${GREEN}https://www.python.org/downloads/${NC}"
    fi
    echo ""
    exit 1
fi

# =============================================================================
# 2. CREATE/ACTIVATE VIRTUAL ENVIRONMENT
# =============================================================================

echo ""
echo -e "${BLUE}📦 Setting up virtual environment...${NC}"

VENV_DIR="venv"

# Detect activation script path (Unix uses bin/, Windows uses Scripts/)
if [ -f "$VENV_DIR/Scripts/activate" ]; then
    ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
    PYTHON_IN_VENV="$VENV_DIR/Scripts/python"
else
    ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
    PYTHON_IN_VENV="$VENV_DIR/bin/python"
fi

# Remove existing venv if corrupt or Python version changed
if [ -d "$VENV_DIR" ]; then
    # Check if venv is working
    if ! "$PYTHON_IN_VENV" --version &> /dev/null; then
        echo -e "${YELLOW}⚠️  Removing corrupt virtual environment...${NC}"
        rm -rf "$VENV_DIR"
    fi
fi

# Create venv if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo -e "${YELLOW}Creating new virtual environment...${NC}"
    "$PYTHON_CMD" -m venv "$VENV_DIR"
    echo -e "${GREEN}✅ Virtual environment created${NC}"

    # Re-detect activation script path after creation
    if [ -f "$VENV_DIR/Scripts/activate" ]; then
        ACTIVATE_SCRIPT="$VENV_DIR/Scripts/activate"
        PYTHON_IN_VENV="$VENV_DIR/Scripts/python"
    else
        ACTIVATE_SCRIPT="$VENV_DIR/bin/activate"
        PYTHON_IN_VENV="$VENV_DIR/bin/python"
    fi
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source "$ACTIVATE_SCRIPT"

# =============================================================================
# 3. INSTALL DEPENDENCIES
# =============================================================================

echo ""
echo -e "${BLUE}📦 Installing dependencies...${NC}"

if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ Error: requirements.txt not found${NC}"
    exit 1
fi

# Upgrade pip first
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "${YELLOW}Installing packages from requirements.txt...${NC}"
pip install -r requirements.txt --quiet

echo -e "${GREEN}✅ Dependencies installed${NC}"

# =============================================================================
# 4. CHECK/CREATE .ENV FILE
# =============================================================================

echo ""
echo -e "${BLUE}🔐 Checking environment configuration...${NC}"

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠️  .env file not found, creating from .env.example...${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo ""
        echo -e "${YELLOW}IMPORTANT: Please configure your .env file:${NC}"
        echo -e "  ${BLUE}•${NC} Edit: ${GREEN}apps/web-backend/.env${NC}"
        echo -e "  ${BLUE}•${NC} Set ${GREEN}SECRET_KEY${NC} (run: python -c \"import secrets; print(secrets.token_urlsafe(32))\")"
        echo -e "  ${BLUE}•${NC} Configure ${GREEN}CORS_ORIGINS${NC} for your frontend URL"
        echo ""
    else
        echo -e "${RED}❌ Error: No .env or .env.example file found${NC}"
        echo ""
        echo -e "${YELLOW}Please create a .env file with required variables:${NC}"
        echo -e "  ${GREEN}HOST${NC}=0.0.0.0"
        echo -e "  ${GREEN}PORT${NC}=8000"
        echo -e "  ${GREEN}DEBUG${NC}=true"
        echo -e "  ${GREEN}SECRET_KEY${NC}=your-secret-key-here"
        echo -e "  ${GREEN}CORS_ORIGINS${NC}=http://localhost:3000"
        echo ""
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env file found${NC}"
fi

# =============================================================================
# 5. START UVICORN SERVER
# =============================================================================

echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                    STARTING WEB BACKEND                        ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Read PORT from .env file, default to 8000 if not set
PORT=$(grep -E '^PORT=' .env 2>/dev/null | cut -d '=' -f2 | tr -d ' ')
PORT=${PORT:-8000}

# Read HOST from .env file, default to 0.0.0.0 if not set
HOST=$(grep -E '^HOST=' .env 2>/dev/null | cut -d '=' -f2 | tr -d ' ')
HOST=${HOST:-0.0.0.0}

# Check if port is already in use (non-blocking check)
if command -v lsof &> /dev/null; then
    if lsof -Pi :${PORT} -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Warning: Port ${PORT} is already in use${NC}"
        echo -e "${YELLOW}   The server may fail to start. Stop the existing process first.${NC}"
        echo ""
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tuln 2>/dev/null | grep -q ":${PORT} "; then
        echo -e "${YELLOW}⚠️  Warning: Port ${PORT} may be in use${NC}"
        echo ""
    fi
fi

echo -e "${GREEN}🚀 Starting FastAPI server with uvicorn...${NC}"
echo ""
echo -e "${BLUE}Service Info:${NC}"
echo -e "  ${BLUE}•${NC} Health: ${GREEN}http://localhost:${PORT}/health${NC}"
echo -e "  ${BLUE}•${NC} API Docs: ${GREEN}http://localhost:${PORT}/docs${NC}"
echo -e "  ${BLUE}•${NC} ReDoc: ${GREEN}http://localhost:${PORT}/redoc${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo -e "${BLUE}════════════════════════════════════════════════════════════════${NC}"
echo ""

# Start uvicorn with hot-reload
uvicorn main:app --reload --host "$HOST" --port "$PORT"
