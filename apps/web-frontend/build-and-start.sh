#!/bin/bash

###############################################################################
# Auto Code - Web Frontend Build and Start Script (Unix/Linux/macOS)
###############################################################################
#
# PURPOSE:
# This script automates the complete build and startup process for the
# web-frontend service (React/Vite). It handles dependency installation,
# environment configuration, and launches the Vite development server.
#
# USAGE:
#   ./build-and-start.sh
#
# REQUIREMENTS:
# - Node.js >= 24.0.0
# - npm >= 10.0.0
#
# WHAT THIS SCRIPT DOES:
# 1. Detects Node.js and npm installation
# 2. Installs npm dependencies from package.json
# 3. Checks for .env file (copies from .env.example if missing)
# 4. Checks if port 3000 is available
# 5. Starts Vite development server on port 3000
#
###############################################################################

set -eo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory (handle spaces in paths)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║     Auto Code - Web Frontend Build and Start (Unix)           ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# =============================================================================
# STEP 1: Check for Node.js and npm
# =============================================================================

echo -e "${BLUE}[1/5]${NC} 🔍 Checking for Node.js and npm..."

if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ Error: Node.js is not installed${NC}"
    echo ""
    echo "Please install Node.js (>= 24.0.0) from:"
    echo "  - https://nodejs.org/"
    echo "  - Or use a version manager like nvm: https://github.com/nvm-sh/nvm"
    echo ""
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ Error: npm is not installed${NC}"
    echo ""
    echo "npm should come with Node.js. Please reinstall Node.js from:"
    echo "  - https://nodejs.org/"
    echo ""
    exit 1
fi

NODE_VERSION=$(node --version)
NPM_VERSION=$(npm --version)
echo -e "${GREEN}✅ Node.js ${NODE_VERSION} found${NC}"
echo -e "${GREEN}✅ npm ${NPM_VERSION} found${NC}"
echo ""

# =============================================================================
# STEP 2: Install Dependencies
# =============================================================================

echo -e "${BLUE}[2/5]${NC} 📦 Installing npm dependencies..."
echo ""

if [ ! -f "package.json" ]; then
    echo -e "${RED}❌ Error: package.json not found${NC}"
    echo "Make sure you're running this script from the web-frontend directory."
    exit 1
fi

# Install dependencies
if npm install; then
    echo ""
    echo -e "${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo ""
    echo -e "${RED}❌ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# =============================================================================
# STEP 3: Environment Configuration
# =============================================================================

echo -e "${BLUE}[3/5]${NC} ⚙️  Checking environment configuration..."

if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo -e "${YELLOW}⚠️  .env file not found, creating from .env.example${NC}"
        cp .env.example .env
        echo -e "${GREEN}✅ Created .env file${NC}"
        echo ""
        echo -e "${YELLOW}📝 IMPORTANT: Please review and configure your .env file:${NC}"
        echo "   - VITE_API_URL: Backend API URL (default: http://localhost:8000)"
        echo "   - VITE_WS_URL: Backend WebSocket URL (default: ws://localhost:8000/ws)"
        echo ""
        echo "You can edit: $SCRIPT_DIR/.env"
        echo ""
    else
        echo -e "${RED}❌ Error: Neither .env nor .env.example found${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}✅ .env file found${NC}"
fi
echo ""

# =============================================================================
# STEP 4: Check Port Availability
# =============================================================================

echo -e "${BLUE}[4/5]${NC} 🔌 Checking if port 3000 is available..."

# Check if port 3000 is in use
if command -v lsof &> /dev/null; then
    if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠️  Warning: Port 3000 is already in use${NC}"
        echo ""
        echo "Another process is using port 3000. Options:"
        echo "  1. Stop the other process using: kill \$(lsof -t -i:3000)"
        echo "  2. Vite will automatically try port 3001, 3002, etc."
        echo ""
    else
        echo -e "${GREEN}✅ Port 3000 is available${NC}"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tuln 2>/dev/null | grep -q ":3000 "; then
        echo -e "${YELLOW}⚠️  Warning: Port 3000 may be in use${NC}"
        echo ""
        echo "Another process might be using port 3000."
        echo "Vite will automatically try port 3001, 3002, etc. if needed."
        echo ""
    else
        echo -e "${GREEN}✅ Port 3000 is available${NC}"
    fi
else
    echo -e "${YELLOW}⚠️  Cannot check port availability (lsof/netstat not found)${NC}"
    echo "Vite will automatically use an alternative port if 3000 is busy."
fi
echo ""

# =============================================================================
# STEP 5: Start Development Server
# =============================================================================

echo -e "${BLUE}[5/5]${NC} 🚀 Starting Vite development server..."
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Frontend Starting...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${BLUE}Development server will be available at:${NC}"
echo -e "  ${GREEN}➜${NC} Local:   ${BLUE}http://localhost:3000${NC}"
echo ""
echo -e "${YELLOW}Press Ctrl+C to stop the server${NC}"
echo ""

# Start the Vite dev server
npm run dev
