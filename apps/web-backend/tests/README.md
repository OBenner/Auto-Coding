# Cloud Integration Tests

This directory contains end-to-end integration tests for the cloud-hosted Auto Claude infrastructure.

## Test Files

### E2E Test Suite

- **`test_cloud_e2e.py`** - Python-based E2E test suite
  - Automated testing of signup → login → OAuth → usage tracking
  - Uses `requests` library for API testing
  - Includes service health checks and wait logic
  - Returns detailed test results and summary

- **`run_e2e_tests.sh`** - Bash script for automated E2E testing
  - Manages Docker stack lifecycle
  - Runs database migrations
  - Executes all API tests
  - Provides colored output and detailed logging
  - Supports `--skip-start`, `--skip-cleanup`, `--verbose` flags

- **`E2E_TEST_GUIDE.md`** - Comprehensive testing documentation
  - Step-by-step manual testing instructions
  - curl examples for all API endpoints
  - Database and Redis verification steps
  - Frontend testing procedures
  - Troubleshooting guide

## Quick Start

### Automated Testing (Recommended)

```bash
# Run the automated bash script
cd apps/web-backend
bash tests/run_e2e_tests.sh
```

This will:
1. Check prerequisites (Docker, Python, curl)
2. Start the cloud stack (PostgreSQL, Redis, Backend)
3. Run database migrations
4. Execute all E2E tests
5. Display results summary

### Manual Testing

```bash
# 1. Start cloud stack
cd apps/web-backend
docker-compose -f docker-compose.cloud.yml up -d

# 2. Run migrations
docker exec autoclaude-backend alembic upgrade head

# 3. Run Python tests
python tests/test_cloud_e2e.py

# 4. Or follow manual steps in E2E_TEST_GUIDE.md
```

## Test Coverage

The E2E test suite validates:

✅ **Backend API**
- Health check endpoint
- User registration (signup)
- User authentication (login)
- JWT token generation

✅ **Database (PostgreSQL)**
- Connection and schema
- User data persistence
- Migration execution

✅ **OAuth Integration**
- GitHub OAuth configuration
- OAuth authorization flow
- Redirect handling

✅ **Usage Tracking (Redis)**
- API request tracking
- Usage statistics
- Dashboard analytics
- Health monitoring

✅ **Frontend (Manual)**
- Sign-up page rendering
- Login page rendering
- Usage dashboard display
- GitHub OAuth connection UI

## Prerequisites

### Required Software

- **Docker** and **Docker Compose** - For running cloud stack
- **Python 3.12+** - For running test scripts
- **curl** - For API testing (bash script)
- **jq** (optional) - For JSON formatting in bash script

### Required Services

The tests require these services to be running:

- **PostgreSQL** (port 5432) - User database
- **Redis** (port 6379) - Usage tracking cache
- **Backend API** (port 8000) - FastAPI application

These are automatically started by `docker-compose.cloud.yml`.

## Test Workflow

```
┌─────────────────────────────────────────────┐
│ 1. Start Docker Stack                       │
│    • PostgreSQL                             │
│    • Redis                                  │
│    • Backend API                            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 2. Initialize Database                      │
│    • Run Alembic migrations                 │
│    • Create users table                     │
│    • Create repositories table              │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 3. Run API Tests                            │
│    • Health check                           │
│    • User signup                            │
│    • User login                             │
│    • OAuth status                           │
│    • OAuth redirect                         │
│    • Usage tracking                         │
│    • Usage statistics                       │
│    • Redis health                           │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 4. Verify Results                           │
│    • Check database records                 │
│    • Verify Redis data                      │
│    • Review logs                            │
└──────────────────┬──────────────────────────┘
                   │
┌──────────────────▼──────────────────────────┐
│ 5. Cleanup (Optional)                       │
│    • Stop Docker stack                      │
│    • Remove test data                       │
└─────────────────────────────────────────────┘
```

## Test Scenarios

### Scenario 1: Fresh Installation

Tests cloud setup from scratch:

```bash
# Clean environment
docker-compose -f docker-compose.cloud.yml down -v

# Run full test suite
bash tests/run_e2e_tests.sh
```

### Scenario 2: Existing Stack

Tests with already-running services:

```bash
# Stack already running
docker-compose -f docker-compose.cloud.yml up -d

# Skip stack startup
bash tests/run_e2e_tests.sh --skip-start --skip-cleanup
```

### Scenario 3: Manual Verification

Follow step-by-step guide:

```bash
# Read the guide
cat tests/E2E_TEST_GUIDE.md

# Run manual curl commands
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"testpass123"}'
```

## Expected Results

### Success Criteria

All tests should pass with:

- ✅ **8/8 tests passing**
- ✅ Database tables created (users, repositories)
- ✅ User can signup and login
- ✅ JWT token is generated and valid
- ✅ OAuth endpoints respond correctly
- ✅ Usage tracking records API calls
- ✅ Redis connection is healthy

### Example Output

```
================================================================================
Cloud E2E Integration Test Runner
================================================================================
ℹ️  Checking prerequisites...
✅ Docker is installed: Docker version 24.0.0
✅ Docker Compose is installed: v2.20.0
✅ curl is installed
✅ Python is installed: Python 3.12.0

================================================================================
Starting Cloud Stack
================================================================================
ℹ️  Starting services (PostgreSQL, Redis, Backend)...
✅ Cloud stack is running!

================================================================================
Running Database Migrations
================================================================================
ℹ️  Applying migrations...
✅ Migrations applied successfully

================================================================================
Running E2E Tests
================================================================================
ℹ️  Test 1: Health Check
✅ Health check passed

ℹ️  Test 2: User Signup
✅ User signup succeeded

ℹ️  Test 3: User Login
✅ User login succeeded
✅ Access token received

ℹ️  Test 4: OAuth Status
✅ OAuth status check passed

ℹ️  Test 5: GitHub OAuth Redirect
✅ GitHub OAuth redirect working (HTTP 302)

ℹ️  Test 6: Usage Tracking Dashboard
✅ Usage dashboard working

ℹ️  Test 7: Usage Statistics
✅ Usage statistics working

ℹ️  Test 8: Usage Health (Redis)
✅ Redis connection healthy

================================================================================
Test Results Summary
================================================================================
Total Tests: 8
Passed: 8
Failed: 0

✅ All tests passed! 🎉
```

## Troubleshooting

### Tests Fail to Start

**Problem:** Docker stack doesn't start

**Solution:**
```bash
# Check Docker is running
docker ps

# Check ports are available
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :8000  # Backend

# View logs
docker-compose -f docker-compose.cloud.yml logs
```

### Database Connection Errors

**Problem:** Backend can't connect to PostgreSQL

**Solution:**
```bash
# Check PostgreSQL is healthy
docker exec autoclaude-postgres pg_isready -U postgres

# Restart PostgreSQL
docker-compose -f docker-compose.cloud.yml restart postgres

# Check DATABASE_URL in docker-compose.cloud.yml
```

### Redis Connection Errors

**Problem:** Usage tracking shows Redis unhealthy

**Solution:**
```bash
# Check Redis is running
docker exec autoclaude-redis redis-cli ping

# Restart Redis
docker-compose -f docker-compose.cloud.yml restart redis

# Check REDIS_HOST in docker-compose.cloud.yml
```

### Migration Errors

**Problem:** Alembic migrations fail

**Solution:**
```bash
# Check migration status
docker exec autoclaude-backend alembic current

# Downgrade and retry
docker exec autoclaude-backend alembic downgrade -1
docker exec autoclaude-backend alembic upgrade head

# Reset database (WARNING: deletes data)
docker exec autoclaude-postgres psql -U postgres -c \
  "DROP DATABASE autoclaude; CREATE DATABASE autoclaude;"
docker exec autoclaude-backend alembic upgrade head
```

## Next Steps

After successful E2E testing:

1. **Create integration test suite** (subtask-6-2)
   - Add pytest-based integration tests
   - Test database operations
   - Test OAuth flow with mocks

2. **Security scanning**
   - Run secret detection: `python apps/backend/scan_secrets.py`
   - Check for vulnerabilities: `pip-audit`

3. **Deploy to staging**
   - Test on real cloud infrastructure (AWS/GCP/Azure)
   - Verify with production-like environment

4. **Performance testing**
   - Load testing with multiple concurrent users
   - Stress testing usage tracking

## References

- [Cloud Deployment Guide](../../guides/CLOUD_DEPLOYMENT.md)
- [Cloud Setup Guide](../../guides/CLOUD_SETUP.md)
- [Backend API Documentation](../API_ENDPOINTS.md)
- [Docker Compose Configuration](../docker-compose.cloud.yml)
