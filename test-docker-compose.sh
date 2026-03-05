#!/bin/bash
# Docker Compose Health Check Test Script
# This script tests the docker-compose startup and verifies health checks

set -e

echo "======================================"
echo "Docker Compose Health Check Test"
echo "======================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker and docker-compose are available
if ! command -v docker &> /dev/null; then
    echo -e "${RED}ERROR: Docker is not installed or not in PATH${NC}"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}ERROR: docker-compose is not installed or not in PATH${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}WARNING: .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please configure .env with your API keys before running services${NC}"
    else
        echo -e "${RED}ERROR: .env.example not found${NC}"
        exit 1
    fi
fi

# Validate docker-compose configuration
echo "Step 1: Validating docker-compose configuration..."
if docker-compose config > /dev/null 2>&1; then
    echo -e "${GREEN}✓ docker-compose.yml is valid${NC}"
else
    echo -e "${RED}✗ docker-compose.yml has errors${NC}"
    docker-compose config
    exit 1
fi
echo ""

# Start services
echo "Step 2: Starting Docker Compose services..."
docker-compose up -d
echo ""

# Wait for services to initialize
echo "Step 3: Waiting for services to initialize (30 seconds)..."
sleep 30
echo ""

# Check service status
echo "Step 4: Checking service health status..."
docker-compose ps
echo ""

# Verify each service individually
echo "Step 5: Verifying individual services..."

# Check postgres
if docker-compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is healthy${NC}"
else
    echo -e "${RED}✗ PostgreSQL is not healthy${NC}"
fi

# Check redis
if docker-compose exec -T redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✓ Redis is healthy${NC}"
else
    echo -e "${RED}✗ Redis is not healthy${NC}"
fi

# Check web-backend
if curl -s -f http://localhost:8000/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Web Backend is healthy${NC}"
else
    echo -e "${RED}✗ Web Backend is not healthy${NC}"
fi

# Check web-frontend
if curl -s -f http://localhost:3000/ > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Web Frontend is healthy${NC}"
else
    echo -e "${RED}✗ Web Frontend is not healthy${NC}"
fi

echo ""

# Check for unhealthy services
UNHEALTHY=$(docker-compose ps | grep -c "unhealthy" || true)
if [ "$UNHEALTHY" -gt 0 ]; then
    echo -e "${RED}WARNING: $UNHEALTHY service(s) are unhealthy${NC}"
    echo ""
    echo "Logs from unhealthy services:"
    docker-compose logs --tail=50
    exit 1
fi

# Check all services are running
RUNNING=$(docker-compose ps | grep -c "Up" || true)
EXPECTED=5  # postgres, redis, backend, web-backend, web-frontend

if [ "$RUNNING" -ge "$EXPECTED" ]; then
    echo -e "${GREEN}✓ All services are running and healthy${NC}"
else
    echo -e "${RED}✗ Expected $EXPECTED services running, found $RUNNING${NC}"
    exit 1
fi

echo ""
echo "======================================"
echo -e "${GREEN}SUCCESS: All health checks passed!${NC}"
echo "======================================"
echo ""
echo "Service URLs:"
echo "  - Web Backend API: http://localhost:8000"
echo "  - Web Frontend: http://localhost:3000"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"
echo ""
echo "To view logs: docker-compose logs -f"
echo "To stop services: docker-compose down"
echo ""
