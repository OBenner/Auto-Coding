# Authentication Verification

This document describes how to verify the authentication implementation.

## Prerequisites

Ensure all dependencies are installed:

```bash
cd apps/web-backend
pip install -r requirements.txt
```

## Start the Server

```bash
cd apps/web-backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

## Test Authentication Endpoints

### 1. Test /api/auth/verify without token (should return 401)

```bash
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Content-Type: application/json"
```

**Expected Response:**
```json
{
  "detail": "Not authenticated"
}
```
**Expected Status:** 401 Unauthorized

### 2. Test /api/auth/verify with invalid token (should return 401)

```bash
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer invalid-token"
```

**Expected Response:**
```json
{
  "detail": "Could not validate credentials"
}
```
**Expected Status:** 401 Unauthorized

### 3. Test /api/auth/status (no auth required)

```bash
curl -X GET http://localhost:8000/api/auth/status
```

**Expected Response:**
```json
{
  "status": "ok",
  "auth_enabled": true,
  "message": "Authentication system is operational"
}
```
**Expected Status:** 200 OK

### 4. Test with valid token

To test with a valid token, you need to create one first using the security module:

```python
from core.security import create_access_token

# Create a test token
token = create_access_token({"sub": "test-user"})
print(f"Bearer {token}")
```

Then use the generated token:

```bash
curl -X POST http://localhost:8000/api/auth/verify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <TOKEN_FROM_ABOVE>"
```

**Expected Response:**
```json
{
  "valid": true,
  "message": "Token is valid",
  "claims": {
    "sub": "test-user",
    "exp": 1234567890
  }
}
```
**Expected Status:** 200 OK

## Implementation Details

### Files Created

1. **core/security.py** - Authentication utilities
   - `create_access_token()` - Creates JWT tokens
   - `verify_token()` - Validates JWT tokens
   - `get_current_token()` - FastAPI dependency for token extraction
   - `require_auth()` - FastAPI dependency for route protection

2. **api/routes/auth.py** - Authentication endpoints
   - `POST /api/auth/verify` - Token verification (requires auth)
   - `GET /api/auth/status` - Auth system status (public)

### Security Features

- JWT-based authentication using HS256 algorithm
- Configurable token expiration (default: 60 minutes)
- Proper HTTP 401 Unauthorized responses for invalid tokens
- Bearer token scheme following OAuth 2.0 standards
- Secret key validation (prevents production use with default key)

### Configuration

Authentication settings are configured in `.env`:

```bash
SECRET_KEY=your-secret-key-here  # MUST be set in production
ACCESS_TOKEN_EXPIRE_MINUTES=60   # Token expiration time
DEBUG=false                      # Set to false in production
```

**CRITICAL:** Never use the default SECRET_KEY in production!
