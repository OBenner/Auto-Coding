# Auth API Integration Tests

## Test File
`test_api_auth.py` - Comprehensive integration tests for `/api/auth` endpoints

## Test Coverage

### Token Verification Tests
- ✓ Verify token without authentication (401)
- ✓ Verify token with invalid token (401)
- ✓ Verify token with expired token (401)
- ✓ Verify token with valid authentication (200)
- ✓ Verify token with missing Bearer prefix (403)
- ✓ Verify token with empty Authorization header (403)
- ✓ Verify token with malformed JWT (401)
- ✓ Verify token response model structure
- ✓ Verify token with multiple requests (reusability)
- ✓ Verify token with tampered token (401)

### Auth Status Tests
- ✓ Auth status without authentication (200)
- ✓ Auth status with authentication (200)

## Running Tests

### Prerequisites
```bash
cd apps/web-backend
pip install -r requirements.txt
```

### Run All Auth Tests
```bash
cd apps/web-backend
pytest tests/test_api_auth.py -v
```

### Run Specific Test
```bash
pytest tests/test_api_auth.py::test_verify_token_success -v
```

### Run with Coverage
```bash
pytest tests/test_api_auth.py --cov=api.routes.auth --cov=core.security -v
```

## Test Fixtures Used

From `conftest.py`:
- `async_client` - AsyncClient for making requests
- `auth_token` - Valid JWT token
- `expired_token` - Expired JWT token for testing rejection
- `auth_headers` - Headers dict with Authorization bearer token

## Expected Behavior

All tests should **PASS** with the current implementation:
- Authentication endpoints properly validate tokens
- Invalid/expired/malformed tokens are rejected with 401
- Valid tokens return correct claims
- Auth status endpoint works without authentication
- Response models match expected structure
