#!/bin/bash

###############################################################################
# Auto Code - Production Build Script (Unix)
###############################################################################
#
# PURPOSE:
# Builds the production version of Auto Code (Electron app with bundled Python).
#
# USAGE:
#   ./scripts/build.sh              - Build only (fast, for testing)
#   ./scripts/build.sh --package    - Package for current platform
#   ./scripts/build.sh --win        - Package for Windows
#   ./scripts/build.sh --mac        - Package for macOS
#   ./scripts/build.sh --linux      - Package for Linux
#   ./scripts/build.sh --all        - Package for all platforms
#   ./scripts/build.sh --sign       - Enable code signing (disabled by default)
#   ./scripts/build.sh --run        - Build and run production build
#   ./scripts/build.sh --help       - Show help message
#
# PREREQUISITES:
#   - Run ./scripts/dev-setup.sh first
#   - Node.js >= 24.0.0
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
FRONTEND_DIR="$PROJECT_ROOT/apps/frontend"

# Default options
ACTION="build"
PLATFORM=""
SIGN=0
SHOW_HELP=0

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --package|-p)
            ACTION="package"
            shift
            ;;
        --win|--windows)
            ACTION="package"
            PLATFORM="win"
            shift
            ;;
        --mac|--macos)
            ACTION="package"
            PLATFORM="mac"
            shift
            ;;
        --linux)
            ACTION="package"
            PLATFORM="linux"
            shift
            ;;
        --all)
            ACTION="package"
            PLATFORM="all"
            shift
            ;;
        --run|-r)
            ACTION="run"
            shift
            ;;
        --sign)
            SIGN=1
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
    echo "Auto Code - Production Build Script"
    echo ""
    echo "USAGE:"
    echo "  ./scripts/build.sh              Build only (fast, for testing)"
    echo "  ./scripts/build.sh --package    Package for current platform"
    echo "  ./scripts/build.sh --win        Package for Windows (.exe)"
    echo "  ./scripts/build.sh --mac        Package for macOS (.dmg)"
    echo "  ./scripts/build.sh --linux      Package for Linux (AppImage)"
    echo "  ./scripts/build.sh --all        Package for all platforms"
    echo "  ./scripts/build.sh --sign       Enable code signing"
    echo "  ./scripts/build.sh --run        Build and run production build"
    echo "  ./scripts/build.sh --help       Show this help message"
    echo ""
    echo "OPTIONS:"
    echo "  --package, -p  Package for current platform"
    echo "  --win          Create Windows installer (.exe NSIS + portable)"
    echo "  --mac          Create macOS installer (.dmg + .zip)"
    echo "  --linux        Create Linux packages (AppImage, deb)"
    echo "  --all          Create packages for all platforms"
    echo "  --sign         Enable code signing (disabled by default)"
    echo "  --run, -r      Run the production build after building"
    echo "  --help, -h     Show this help message"
    echo ""
    echo "OUTPUT:"
    echo "  Build only:    apps/frontend/out/"
    echo "  Package:       apps/frontend/dist/"
    echo ""
    echo "NOTES:"
    echo "  - Cross-compilation may require additional tools"
    echo "  - macOS signing requires Apple Developer certificate"
    echo "  - First package run downloads Python runtime (~50MB per platform)"
    echo ""
    exit 0
fi

echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           Auto Code - Production Build                       ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Check prerequisites
echo -e "${CYAN}➤${NC} Checking prerequisites..."

if ! command -v node &> /dev/null; then
    echo -e "${RED}✗${NC} Node.js not found. Run ./scripts/dev-setup.sh first."
    exit 1
fi

NODE_VERSION=$(node --version | sed 's/v//')
NODE_MAJOR=$(echo "$NODE_VERSION" | cut -d. -f1)
if [ "$NODE_MAJOR" -lt 24 ]; then
    echo -e "${RED}✗${NC} Node.js v$NODE_VERSION found, but v24.0.0+ is required"
    exit 1
fi

echo -e "${GREEN}✓${NC} Node.js v$NODE_VERSION"

# Check if dependencies are installed
if [ ! -d "$PROJECT_ROOT/node_modules" ]; then
    echo -e "${RED}✗${NC} Dependencies not installed. Run ./scripts/dev-setup.sh first."
    exit 1
fi

echo -e "${GREEN}✓${NC} Dependencies installed"
echo ""

# Build
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${CYAN}➤${NC} Building production version..."
echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
echo ""

cd "$FRONTEND_DIR"

# Run build
npm run build

if [ $? -ne 0 ]; then
    echo -e "${RED}✗${NC} Build failed"
    exit 1
fi

echo ""
echo -e "${GREEN}✓${NC} Build completed successfully"
echo -e "  Output: ${CYAN}apps/frontend/out/${NC}"

# Package if requested
if [ "$ACTION" = "package" ]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}➤${NC} Creating distributable packages..."
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Determine what to build
    if [ -z "$PLATFORM" ]; then
        # Auto-detect current platform
        case "$(uname -s)" in
            Darwin*)
                PLATFORM="mac"
                ;;
            Linux*)
                PLATFORM="linux"
                ;;
            MINGW*|MSYS*|CYGWIN*)
                PLATFORM="win"
                ;;
            *)
                echo -e "${YELLOW}⚠${NC} Unknown OS, defaulting to current platform..."
                npm run package
                PLATFORM="current"
                ;;
        esac
    fi

    # Build sign argument
    SIGN_ARG=""
    if [ $SIGN -eq 1 ]; then
        SIGN_ARG="-- --sign"
        echo -e "${YELLOW}⚠${NC} Code signing enabled"
    fi

    # Build for selected platform(s)
    case "$PLATFORM" in
        win)
            echo -e "${CYAN}➤${NC} Packaging for Windows..."
            npm run package:win $SIGN_ARG
            ;;
        mac)
            echo -e "${CYAN}➤${NC} Packaging for macOS..."
            npm run package:mac $SIGN_ARG
            ;;
        linux)
            echo -e "${CYAN}➤${NC} Packaging for Linux..."
            npm run package:linux $SIGN_ARG
            ;;
        all)
            echo -e "${CYAN}➤${NC} Packaging for Windows..."
            npm run package:win $SIGN_ARG
            echo ""
            echo -e "${CYAN}➤${NC} Packaging for macOS..."
            npm run package:mac $SIGN_ARG
            echo ""
            echo -e "${CYAN}➤${NC} Packaging for Linux..."
            npm run package:linux $SIGN_ARG
            ;;
    esac

    if [ $? -ne 0 ]; then
        echo -e "${RED}✗${NC} Packaging failed"
        exit 1
    fi

    echo ""
    echo -e "${GREEN}✓${NC} Package(s) created successfully"
    echo -e "  Output: ${CYAN}apps/frontend/dist/${NC}"
    echo ""

    # List created files
    echo -e "${CYAN}Created files:${NC}"
    ls -la "$FRONTEND_DIR/dist/" 2>/dev/null | grep -E '\.(exe|dmg|zip|AppImage|deb|flatpak)$' || echo "  (check dist/ folder)"

    # Show portable folders
    if [ -d "$FRONTEND_DIR/dist/win-unpacked" ]; then
        echo -e "  ${GREEN}win-unpacked/${NC} (Windows portable)"
    fi
    if [ -d "$FRONTEND_DIR/dist/mac" ] || [ -d "$FRONTEND_DIR/dist/mac-arm64" ]; then
        echo -e "  ${GREEN}mac/ or mac-arm64/${NC} (macOS app)"
    fi
    if [ -d "$FRONTEND_DIR/dist/linux-unpacked" ]; then
        echo -e "  ${GREEN}linux-unpacked/${NC} (Linux portable)"
    fi
fi

# Run if requested
if [ "$ACTION" = "run" ]; then
    echo ""
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}➤${NC} Starting production build..."
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════${NC}"
    echo ""

    npm run start
fi

echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  Build completed successfully!${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
