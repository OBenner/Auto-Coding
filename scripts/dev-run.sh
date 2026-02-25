#!/bin/bash

###############################################################################
# Auto Claude - Development Server Start Script (Unix)
###############################################################################
#
# PURPOSE:
# Starts the development environment (Electron frontend in dev mode).
#
# USAGE:
#   ./scripts/dev-run.sh           - Start dev server
#   ./scripts/dev-run.sh --mcp     - Start with MCP debugging enabled
#   ./scripts/dev-run.sh --help    - Show help message
#
# PREREQUISITES:
#   - Run ./scripts/dev-setup.sh first
#   - Configure apps/backend/.env with API keys
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

# Default mode
MODE="dev"
SHOW_HELP=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --mcp|-m)
            MODE="dev:mcp"
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
    echo "Auto Claude - Development Server"
    echo ""
    echo "USAGE:"
    echo "  ./scripts/dev-run.sh           Start dev server"
    echo "  ./scripts/dev-run.sh --mcp     Start with MCP debugging enabled"
    echo "  ./scripts/dev-run.sh --help    Show this help message"
    echo ""
    echo "OPTIONS:"
    echo "  --mcp, -m    Enable MCP debugging (uses npm run dev:mcp)"
    echo "  --help, -h   Show this help message"
    echo ""
    exit 0
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║        Auto Claude - Starting Development Server               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Quick prerequisite check
echo -e "${CYAN}➤${NC} Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗${NC} Node.js not found. Run ./scripts/dev-setup.sh first."
    exit 1
fi

cd "$PROJECT_ROOT"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo -e "${RED}✗${NC} Dependencies not installed. Run ./scripts/dev-setup.sh first."
    exit 1
fi

# Check frontend dependencies (npm workspaces hoists to root node_modules)
if [ ! -d "node_modules/electron" ] && [ ! -d "apps/frontend/node_modules" ]; then
    echo -e "${RED}✗${NC} Frontend dependencies not installed. Run ./scripts/dev-setup.sh first."
    exit 1
fi

echo -e "${GREEN}✓${NC} Prerequisites OK"
echo ""

# Display mode info
if [ "$MODE" = "dev:mcp" ]; then
    echo -e "${CYAN}➤${NC} Starting dev server with MCP debugging..."
    echo -e "  ${YELLOW}Remote debugging port: 9222${NC}"
else
    echo -e "${CYAN}➤${NC} Starting dev server..."
fi
echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${YELLOW}TIP:${NC} Press Ctrl+C to stop the server"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

# Start the dev server (disable errexit so we can handle the exit gracefully)
set +e
npm run "$MODE"
EXIT_CODE=$?
set -e

# Handle exit
if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ]; then
    # 130 = Ctrl+C (SIGINT)
    echo ""
    echo -e "${GREEN}✓${NC} Dev server stopped."
    exit 0
else
    echo ""
    echo -e "${RED}✗${NC} Dev server exited with error code $EXIT_CODE"
    exit $EXIT_CODE
fi
