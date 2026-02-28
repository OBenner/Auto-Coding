# Cloud E2E Integration Test Guide

This guide provides step-by-step instructions for testing the full cloud-hosted Auto Code workflow.

## Test Overview

This end-to-end test validates the complete cloud infrastructure:

1. **User Signup** - New user registration via API
2. **User Login** - Authentication and JWT token retrieval
3. **OAuth Integration** - GitHub OAuth connection flow
4. **Usage Tracking** - Redis-based API usage analytics
5. **Database Operations** - PostgreSQL user data persistence

## Prerequisites

Before running the tests, ensure you have:

- **Docker** and **Docker Compose** installed
- **Python 3.12+** with `requests` library
- **Git** for repository operations
- **Ports available**: 5432 (PostgreSQL), 6379 (Redis), 8000 (Backend API)

## Quick Start

### Step 1: Start the Cloud Stack

```bash
cd apps/web-backend

# Start all services (PostgreSQL, Redis, Backend)
docker-compose -f docker-compose.cloud.yml up -d

# Wait for services to become healthy (30-60 seconds)
docker-compose -f docker-compose.cloud.yml ps

# Expected output:
# autoclaude-postgres   ... Up (healthy)
# autoclaude-redis      ... Up (healthy)
# autoclaude-backend    ... Up (healthy)
```

### Step 2: Initialize Database

```bash
# Run database migrations
docker exec autoclaude-backend alembic upgrade head

# Verify migrations
docker exec autoclaude-backend alembic current

# Expected output: 002_create_repositories (head)
```

### Step 3: Run E2E Tests

```bash
# Option 1: Run Python test script
python tests/test_cloud_e2e.py

# Option 2: Run bash test script
bash tests/run_e2e_tests.sh

# Option 3: Manual API testing (see below)
```

## Manual Testing Steps

### Test 1: Health Check

```bash
curl -X GET http://localhost:8000/health

# Expected: 200 OK
# {"status":"ok","database":"connected","redis":"connected"}
```

### Test 2: User Signup

```bash
curl -X POST http://localhost:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'

# Expected: 201 Created
# {
#   "id": 1,
#   "email": "test@example.com",
#   "is_active": true,
#   "is_verified": false,
#   "created_at": "2024-02-04T12:00:00Z"
# }
```

### Test 3: User Login

```bash
curl -X POST http://localhost:8000/api/users/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "testpass123"
  }'

# Expected: 200 OK
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "user": {
#     "id": 1,
#     "email": "test@example.com"
#   }
# }

# Save the access_token for subsequent requests
export ACCESS_TOKEN="<token-from-response>"
```

### Test 4: OAuth Status

```bash
curl -X GET http://localhost:8000/api/git/status

# Expected: 200 OK
# {
#   "github": {
#     "configured": true,
#     "client_id": "test_client_id"
#   },
#   "gitlab": {
#     "configured": false
#   }
# }
```

### Test 5: GitHub OAuth Redirect

```bash
curl -X GET http://localhost:8000/api/git/github/authorize \
  -H "Cookie: session=..." \
  -L -v

# Expected: 302 Redirect to GitHub
# Location: https://github.com/login/oauth/authorize?client_id=...&redirect_uri=...&scope=...&state=...
```

### Test 6: Usage Tracking Dashboard

```bash
curl -X GET "http://localhost:8000/api/usage/dashboard?user_id=1"

# Expected: 200 OK
# {
#   "user_id": 1,
#   "total_requests_today": 5,
#   "total_requests_this_month": 5,
#   "redis_healthy": true
# }
```

### Test 7: Usage Statistics

```bash
curl -X GET "http://localhost:8000/api/usage/stats?user_id=1&period=daily&days_back=7"

# Expected: 200 OK
# {
#   "user_id": 1,
#   "period": "daily",
#   "days_back": 7,
#   "usage_data": [
#     {
#       "period_start": "2024-02-04T00:00:00Z",
#       "request_count": 5,
#       "unique_endpoints": 3
#     }
#   ],
#   "total_requests": 5,
#   "redis_healthy": true
# }
```

### Test 8: Usage Health (Redis)

```bash
curl -X GET http://localhost:8000/api/usage/health

# Expected: 200 OK
# {
#   "status": "healthy",
#   "redis_healthy": true,
#   "message": "Usage tracking is operational"
# }
```

## Database Verification

### Check Users Table

```bash
docker exec -it autoclaude-postgres psql -U postgres -d autoclaude -c "SELECT id, email, is_active, created_at FROM users;"

# Expected:
#  id |       email        | is_active |         created_at
# ----+--------------------+-----------+----------------------------
#   1 | test@example.com   | t         | 2024-02-04 12:00:00.123456
```

### Check Repositories Table

```bash
docker exec -it autoclaude-postgres psql -U postgres -d autoclaude -c "SELECT * FROM repositories;"

# Expected: Empty table (no OAuth connections yet)
```

### Check Migration Status

```bash
docker exec autoclaude-backend alembic current

# Expected: 002_create_repositories (head)
```

## Redis Verification

### Check Usage Tracking Data

```bash
# Connect to Redis
docker exec -it autoclaude-redis redis-cli

# Inside Redis CLI:
KEYS usage:*

# Expected: Keys like:
# 1) "usage:user:1:daily:2024-02-04"
# 2) "usage:user:1:hourly:2024-02-04:12"
# 3) "usage:user:1:monthly:2024-02"

# Check specific key:
GET "usage:user:1:daily:2024-02-04"

# Expected: Number (request count for the day)
```

## Frontend Testing

### Test Sign-up Page

```bash
# Option 1: Open in browser
open http://localhost:3000/signup

# Option 2: Start frontend dev server
cd apps/web-frontend
npm run dev

# Navigate to http://localhost:3000/signup
```

**Verification Steps:**
1. Fill in email: `test2@example.com`
2. Fill in password: `password123`
3. Confirm password: `password123`
4. Click "Sign Up"
5. Verify success message or redirect

### Test Login Page

```bash
# Navigate to http://localhost:3000/login
open http://localhost:3000/login
```

**Verification Steps:**
1. Fill in email: `test@example.com`
2. Fill in password: `testpass123`
3. Click "Log In"
4. Verify redirect to dashboard or home page

### Test Usage Dashboard

```bash
# Navigate to http://localhost:3000/usage
open http://localhost:3000/usage
```

**Verification Steps:**
1. Verify summary cards display (Today, This Month, Total)
2. Verify usage chart renders
3. Verify usage details table shows data
4. Verify Redis health indicator

### Test GitHub OAuth Connection

```bash
# Navigate to http://localhost:3000/settings/git
open http://localhost:3000/settings/git
```

**Verification Steps:**
1. Click "Connect GitHub Account"
2. Verify redirect to GitHub OAuth
3. Complete OAuth flow (requires real GitHub OAuth app)
4. Verify redirect back to settings page
5. Verify GitHub account shows as connected

## Troubleshooting

### Services Not Starting

```bash
# Check container logs
docker-compose -f docker-compose.cloud.yml logs postgres
docker-compose -f docker-compose.cloud.yml logs redis
docker-compose -f docker-compose.cloud.yml logs web-backend

# Restart services
docker-compose -f docker-compose.cloud.yml restart
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker exec autoclaude-postgres pg_isready -U postgres

# Check database exists
docker exec autoclaude-postgres psql -U postgres -c "\l"

# Recreate database if needed
docker exec autoclaude-postgres psql -U postgres -c "DROP DATABASE IF EXISTS autoclaude; CREATE DATABASE autoclaude;"
```

### Redis Connection Issues

```bash
# Check Redis is running
docker exec autoclaude-redis redis-cli ping

# Expected: PONG

# Flush Redis data (if needed)
docker exec autoclaude-redis redis-cli FLUSHALL
```

### Migration Errors

```bash
# Check current migration status
docker exec autoclaude-backend alembic current

# View migration history
docker exec autoclaude-backend alembic history

# Downgrade and re-apply
docker exec autoclaude-backend alembic downgrade base
docker exec autoclaude-backend alembic upgrade head
```

### API Errors

```bash
# Check backend logs
docker logs autoclaude-backend --tail 100 -f

# Check for common issues:
# - Database not initialized (run migrations)
# - Redis not available (check redis container)
# - Missing environment variables (check .env file)
```

## Clean Up

### Stop Services

```bash
cd apps/web-backend
docker-compose -f docker-compose.cloud.yml down
```

### Remove Data Volumes

```bash
# WARNING: This will delete all data!
docker-compose -f docker-compose.cloud.yml down -v
```

### Complete Reset

```bash
# Stop and remove everything
docker-compose -f docker-compose.cloud.yml down -v --remove-orphans

# Remove test user from database
docker exec autoclaude-postgres psql -U postgres -d autoclaude -c "DELETE FROM users WHERE email = 'test@example.com';"
```

## Test Success Criteria

All tests pass if:

- ✅ Backend API health check returns 200 OK
- ✅ PostgreSQL database is accessible and migrations applied
- ✅ Redis is accessible and tracking usage
- ✅ User signup creates new user in database
- ✅ User login returns valid JWT token
- ✅ OAuth status endpoint shows GitHub configured
- ✅ OAuth authorize redirects to GitHub (302)
- ✅ Usage dashboard returns statistics
- ✅ Usage health shows Redis connected
- ✅ Frontend pages render correctly (signup, login, usage, settings)

## Next Steps

After successful E2E testing:

1. **Create integration test suite** (subtask-6-2)
2. **Run security scan** (verify no secrets in code)
3. **Deploy to staging** (test on real cloud infrastructure)
4. **Performance testing** (load testing with multiple users)
5. **User acceptance testing** (UAT with real users)

## Additional Resources

- [Cloud Deployment Guide](../../guides/CLOUD_DEPLOYMENT.md)
- [Cloud Setup Guide](../../guides/CLOUD_SETUP.md)
- [Backend API Documentation](../API_ENDPOINTS.md)
- [Docker Compose Configuration](../docker-compose.cloud.yml)
