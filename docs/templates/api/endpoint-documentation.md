# Endpoint: [HTTP Method] [Endpoint Path]

<!--
INSTRUCTIONS: Replace [HTTP Method] with GET, POST, PUT, PATCH, DELETE, etc.
Replace [Endpoint Path] with the full path (e.g., /api/v1/specs/{spec_id}/status)
This template helps document REST API endpoints following Auto Code's documentation patterns.
Fill in each section below, removing placeholder comments when done.
-->

[One-sentence description of what this endpoint does]

## Overview

<!--
INSTRUCTIONS: Provide a brief overview of the endpoint's purpose and use cases.
-->

**Base URL:** `[http://localhost:8000 or production URL]`
**Full Path:** `[Base URL][Endpoint Path]`
**Method:** `[HTTP Method]`
**Authentication:** [Required/Optional/None]
**Rate Limiting:** [Yes/No - specify limits if applicable]

### Purpose

[Explain what this endpoint accomplishes and when it should be used]

### Use Cases

- **Use Case 1:** [Description]
- **Use Case 2:** [Description]
- **Use Case 3:** [Description]

---

## Request

<!--
INSTRUCTIONS: Document all request parameters, headers, and body structure.
-->

### HTTP Method

**`[GET/POST/PUT/PATCH/DELETE]`**

[Explain why this HTTP method was chosen for this operation]

### URL Structure

```
[BASE_URL]/[path]/[{param1}]/[{param2}]
```

**Example:**
```
http://localhost:8000/api/v1/resources/123/actions
```

### Path Parameters

<!--
INSTRUCTIONS: Document parameters that appear in the URL path (e.g., {spec_id})
-->

| Parameter | Type | Required | Description | Example |
|-----------|------|----------|-------------|---------|
| `{param_name}` | string | Yes | [What this parameter identifies] | `001-feature-name` |
| `{param_name}` | integer | Yes | [What this parameter identifies] | `42` |

### Query Parameters

<!--
INSTRUCTIONS: Document parameters passed in the query string (?key=value)
Remove this section if not applicable.
-->

| Parameter | Type | Required | Default | Description | Example |
|-----------|------|----------|---------|-------------|---------|
| `param_name` | string | No | `default_value` | [What this parameter controls] | `?param_name=value` |
| `param_name` | integer | No | `10` | [What this parameter controls] | `?param_name=20` |
| `param_name` | boolean | No | `false` | [What this parameter controls] | `?param_name=true` |

**Valid Query String Examples:**
```
?param1=value1&param2=value2
?filter=active&sort=desc&limit=50
```

### Request Headers

<!--
INSTRUCTIONS: Document required and optional HTTP headers.
-->

| Header | Required | Description | Example |
|--------|----------|-------------|---------|
| `Authorization` | Yes | Bearer token for authentication | `Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...` |
| `Content-Type` | Yes | Request body format | `application/json` |
| `Accept` | No | Response format preference | `application/json` |
| `X-Request-ID` | No | Request tracking identifier | `uuid-v4-string` |

### Request Body

<!--
INSTRUCTIONS: Document the request body structure for POST/PUT/PATCH requests.
Remove this section for GET/DELETE requests without a body.
-->

**Content-Type:** `application/json`

**Schema:**

```json
{
  "field_name": "string",
  "field_name": 123,
  "nested_object": {
    "property": "value",
    "property": true
  },
  "array_field": ["item1", "item2"]
}
```

**Field Descriptions:**

| Field | Type | Required | Description | Constraints |
|-------|------|----------|-------------|-------------|
| `field_name` | string | Yes | [What this field represents] | Max 255 chars |
| `field_name` | integer | Yes | [What this field represents] | Min: 0, Max: 100 |
| `nested_object` | object | No | [What this object contains] | - |
| `nested_object.property` | string | Yes | [Description] | Must be unique |
| `array_field` | array[string] | No | [What this array contains] | Max 50 items |

**Example Request Body:**

```json
{
  "name": "Example Feature",
  "description": "This is an example feature specification",
  "complexity": "standard",
  "priority": 1,
  "tags": ["backend", "api", "new-feature"]
}
```

**Validation Rules:**
- [Rule 1: e.g., `name` must be unique within project]
- [Rule 2: e.g., `priority` must be between 1 and 5]
- [Rule 3: e.g., `tags` cannot contain duplicates]

---

## Response

<!--
INSTRUCTIONS: Document all possible response formats and status codes.
-->

### Success Response

#### HTTP `200 OK` (or `201 Created`, `204 No Content`, etc.)

**Description:** [When this response is returned]

**Response Body:**

```json
{
  "status": "success",
  "data": {
    "id": "string",
    "field_name": "value",
    "field_name": 123,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

**Field Descriptions:**

| Field | Type | Description |
|-------|------|-------------|
| `status` | string | Operation status: `success` or `error` |
| `data` | object | Response payload containing requested data |
| `data.id` | string | Unique identifier for the resource |
| `data.field_name` | string | [Description of this field] |
| `data.created_at` | string (ISO 8601) | Creation timestamp |
| `meta` | object | Response metadata |
| `meta.timestamp` | string (ISO 8601) | Response generation timestamp |
| `meta.request_id` | string | Request tracking identifier |

**Example Success Response:**

```json
{
  "status": "success",
  "data": {
    "spec_id": "001-authentication-feature",
    "name": "Authentication Feature",
    "status": "completed",
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T14:22:00Z",
    "subtasks_completed": 8,
    "subtasks_total": 8
  },
  "meta": {
    "timestamp": "2024-01-15T14:23:00Z",
    "request_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

### Error Responses

<!--
INSTRUCTIONS: Document all possible error responses with their status codes.
-->

#### HTTP `400 Bad Request`

**Description:** Invalid request parameters or body

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "field_name",
        "issue": "Field is required",
        "provided": null
      }
    ]
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

**Common Validation Errors:**
- `MISSING_REQUIRED_FIELD` - Required field not provided
- `INVALID_FIELD_TYPE` - Field has wrong data type
- `INVALID_FIELD_VALUE` - Field value doesn't meet constraints
- `DUPLICATE_VALUE` - Unique field value already exists

#### HTTP `401 Unauthorized`

**Description:** Missing or invalid authentication credentials

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required",
    "details": "Missing or invalid Authorization header"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

#### HTTP `403 Forbidden`

**Description:** Authenticated but lacking necessary permissions

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "FORBIDDEN",
    "message": "Insufficient permissions",
    "details": "User lacks permission to perform this operation"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

#### HTTP `404 Not Found`

**Description:** Requested resource does not exist

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "NOT_FOUND",
    "message": "Resource not found",
    "details": "Spec with ID '001-nonexistent' does not exist"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

#### HTTP `409 Conflict`

**Description:** Request conflicts with current state

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "CONFLICT",
    "message": "Resource conflict",
    "details": "Spec with this name already exists"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

#### HTTP `422 Unprocessable Entity`

**Description:** Valid request format but semantically incorrect

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "UNPROCESSABLE_ENTITY",
    "message": "Cannot process request",
    "details": "Cannot delete spec while build is in progress"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

#### HTTP `429 Too Many Requests`

**Description:** Rate limit exceeded

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Too many requests",
    "details": "Rate limit of 100 requests/minute exceeded"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string",
    "retry_after": 45
  }
}
```

**Response Headers:**
- `Retry-After: 45` (seconds until rate limit resets)
- `X-RateLimit-Limit: 100`
- `X-RateLimit-Remaining: 0`
- `X-RateLimit-Reset: 1705320000` (Unix timestamp)

#### HTTP `500 Internal Server Error`

**Description:** Unexpected server error

**Response Body:**

```json
{
  "status": "error",
  "error": {
    "code": "INTERNAL_SERVER_ERROR",
    "message": "An unexpected error occurred",
    "details": "Please contact support with request ID"
  },
  "meta": {
    "timestamp": "2024-01-15T10:30:00Z",
    "request_id": "uuid-v4-string"
  }
}
```

---

## Authentication

<!--
INSTRUCTIONS: Document authentication requirements and methods.
Remove this section if endpoint does not require authentication.
-->

### Authentication Method

**Type:** [Bearer Token / API Key / OAuth 2.0 / None]

### Required Credentials

[Describe what credentials are needed and how to obtain them]

**Example:**

```bash
# Authentication header format
Authorization: Bearer YOUR_API_TOKEN_HERE
```

### Obtaining Credentials

1. [Step 1 to get credentials]
2. [Step 2 to get credentials]
3. [Step 3 to get credentials]

### Token Expiration

- **Access Token Lifetime:** [Duration, e.g., 1 hour]
- **Refresh Token Lifetime:** [Duration, e.g., 30 days]
- **Refresh Process:** [How to refresh expired tokens]

---

## Examples

<!--
INSTRUCTIONS: Provide practical examples using different tools/languages.
-->

### cURL Example

```bash
# Basic request
curl -X [METHOD] \
  [BASE_URL][ENDPOINT_PATH] \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "field_name": "value",
    "field_name": 123
  }'

# With query parameters
curl -X GET \
  "[BASE_URL][ENDPOINT_PATH]?param1=value1&param2=value2" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Python Example

```python
import requests

# Configuration
BASE_URL = "http://localhost:8000"
API_TOKEN = "your_token_here"
ENDPOINT = "/api/v1/endpoint/path"

# Headers
headers = {
    "Authorization": f"Bearer {API_TOKEN}",
    "Content-Type": "application/json"
}

# Request body
payload = {
    "field_name": "value",
    "field_name": 123
}

# Make request
response = requests.[method](
    f"{BASE_URL}{ENDPOINT}",
    headers=headers,
    json=payload
)

# Handle response
if response.status_code == 200:
    data = response.json()
    print(f"Success: {data}")
else:
    print(f"Error {response.status_code}: {response.json()}")
```

### JavaScript Example

```javascript
// Using fetch API
const BASE_URL = 'http://localhost:8000';
const API_TOKEN = 'your_token_here';
const ENDPOINT = '/api/v1/endpoint/path';

async function makeRequest() {
  try {
    const response = await fetch(`${BASE_URL}${ENDPOINT}`, {
      method: '[METHOD]',
      headers: {
        'Authorization': `Bearer ${API_TOKEN}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        field_name: 'value',
        field_name: 123
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    console.log('Success:', data);
    return data;
  } catch (error) {
    console.error('Error:', error);
    throw error;
  }
}

makeRequest();
```

### Auto Code Backend Example

```python
from fastapi import APIRouter, HTTPException, Depends
from typing import Optional
from pydantic import BaseModel

router = APIRouter()

class RequestModel(BaseModel):
    """Request body model"""
    field_name: str
    field_name: int
    optional_field: Optional[str] = None

class ResponseModel(BaseModel):
    """Response body model"""
    status: str
    data: dict
    meta: dict

@router.[method]("[endpoint_path]")
async def endpoint_handler(
    path_param: str,
    request_body: RequestModel,
    # Add authentication dependency
    # current_user: User = Depends(get_current_user)
) -> ResponseModel:
    """
    [Endpoint description]

    Args:
        path_param: [Description]
        request_body: [Description]

    Returns:
        ResponseModel with operation result

    Raises:
        HTTPException: Various error conditions
    """
    try:
        # Validation
        if not path_param:
            raise HTTPException(
                status_code=400,
                detail="Path parameter is required"
            )

        # Business logic
        result = perform_operation(path_param, request_body)

        # Success response
        return ResponseModel(
            status="success",
            data=result,
            meta={"timestamp": datetime.utcnow().isoformat()}
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Rate Limiting

<!--
INSTRUCTIONS: Document rate limiting policies.
Remove this section if no rate limiting applies.
-->

### Limits

| Tier | Requests/Minute | Requests/Hour | Requests/Day |
|------|-----------------|---------------|--------------|
| Free | [number] | [number] | [number] |
| Pro | [number] | [number] | [number] |
| Enterprise | [number] | [number] | Unlimited |

### Rate Limit Headers

Every response includes rate limit information:

```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1705320000
```

### Handling Rate Limits

```python
import time
import requests

def make_request_with_retry(url, headers, payload, max_retries=3):
    """Make request with automatic retry on rate limit"""
    for attempt in range(max_retries):
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 429:
            # Rate limited - check retry-after
            retry_after = int(response.headers.get('Retry-After', 60))
            print(f"Rate limited. Retrying after {retry_after} seconds...")
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

---

## Versioning

<!--
INSTRUCTIONS: Document API versioning strategy.
-->

**Current Version:** `v1`

**Version Format:** `/api/v{version}/[endpoint]`

### Version History

| Version | Status | Deprecated | Sunset Date |
|---------|--------|------------|-------------|
| v1 | Active | No | - |

### Version Migration

[If applicable, document how to migrate from older versions]

---

## Performance

<!--
INSTRUCTIONS: Document performance characteristics.
OPTIONAL: Remove if not applicable.
-->

### Expected Response Times

| Percentile | Response Time |
|------------|---------------|
| p50 (median) | [X]ms |
| p95 | [Y]ms |
| p99 | [Z]ms |

### Optimization Tips

1. **[Tip 1]** - [Description]
2. **[Tip 2]** - [Description]
3. **[Tip 3]** - [Description]

### Pagination

<!--
For endpoints returning large datasets
-->

**Query Parameters:**
- `limit` - Number of items per page (default: 20, max: 100)
- `offset` - Number of items to skip (default: 0)
- `cursor` - Cursor-based pagination token (alternative to offset)

**Example Paginated Response:**

```json
{
  "status": "success",
  "data": {
    "items": [...],
    "pagination": {
      "total": 150,
      "limit": 20,
      "offset": 40,
      "has_more": true,
      "next_cursor": "eyJpZCI6MTIzfQ=="
    }
  }
}
```

---

## Testing

<!--
INSTRUCTIONS: Provide testing guidance.
-->

### Unit Tests

**Location:** `tests/api/test_[endpoint_name].py`

**Example Test:**

```python
import pytest
from fastapi.testclient import TestClient
from apps.backend.main import app

client = TestClient(app)

def test_endpoint_success():
    """Test successful endpoint call"""
    response = client.[method](
        "/api/v1/endpoint/path",
        json={"field_name": "value"},
        headers={"Authorization": "Bearer test_token"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

def test_endpoint_validation_error():
    """Test validation error handling"""
    response = client.[method](
        "/api/v1/endpoint/path",
        json={"invalid_field": "value"},
        headers={"Authorization": "Bearer test_token"}
    )

    assert response.status_code == 400
    assert "error" in response.json()
```

### Integration Tests

```bash
# Run endpoint integration tests
pytest tests/integration/test_[endpoint_name].py -v

# Run with coverage
pytest tests/integration/test_[endpoint_name].py --cov=apps/backend
```

### Manual Testing

**Test Checklist:**
- [ ] Successful request with valid data
- [ ] Validation error with invalid data
- [ ] Authentication error without token
- [ ] Authorization error with insufficient permissions
- [ ] Rate limiting behavior
- [ ] Error handling for edge cases

---

## Monitoring & Observability

<!--
INSTRUCTIONS: Document monitoring and logging.
OPTIONAL: Remove if not applicable.
-->

### Metrics

Key metrics tracked for this endpoint:

- **Request Count:** Total requests received
- **Success Rate:** Percentage of 2xx responses
- **Error Rate:** Percentage of 4xx/5xx responses
- **Response Time:** Average/p95/p99 latency
- **Throughput:** Requests per second

### Logging

**Log Level:** INFO (configurable to DEBUG)

**Logged Information:**
- Request method and path
- Request ID for tracing
- Response status code
- Response time
- Error messages (excluding sensitive data)

**Example Log Entry:**

```
[2024-01-15 10:30:00] INFO - Request: POST /api/v1/specs/create | Request-ID: a1b2c3d4 | Status: 201 | Duration: 125ms
```

### Tracing

Each request includes a `X-Request-ID` header for distributed tracing.

---

## Security Considerations

<!--
INSTRUCTIONS: Document security aspects specific to this endpoint.
-->

### Security Model

[Describe the security approach for this endpoint]

### Input Validation

- **Sanitization:** All input is sanitized to prevent injection attacks
- **Type Checking:** Pydantic models enforce type safety
- **Length Limits:** String fields have maximum length constraints
- **Allowed Values:** Enums restrict values to predefined sets

### Sensitive Data

**Fields containing sensitive data:**
- `[field_name]` - [How it's protected: hashed, encrypted, etc.]

**Data handling:**
- Sensitive data is never logged
- PII is encrypted at rest
- Secure transmission via HTTPS only

### Common Vulnerabilities

| Vulnerability | Mitigation |
|---------------|------------|
| SQL Injection | Parameterized queries via ORM |
| XSS | Input sanitization, output encoding |
| CSRF | CSRF tokens for state-changing operations |
| Mass Assignment | Explicit field whitelisting |

---

## Troubleshooting

<!--
INSTRUCTIONS: Document common issues and solutions.
-->

### Common Issues

#### Issue: "Invalid request body"

**Cause:** Request body doesn't match expected schema

**Solution:**
1. Verify Content-Type header is `application/json`
2. Check JSON is valid (use JSON validator)
3. Ensure all required fields are present
4. Verify field types match schema

#### Issue: "Authentication failed"

**Cause:** Missing or invalid authentication token

**Solution:**
1. Verify Authorization header is present
2. Check token format: `Bearer YOUR_TOKEN`
3. Ensure token has not expired
4. Regenerate token if necessary

### Debug Mode

Enable debug logging for detailed request/response information:

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("apps.backend.api")
logger.setLevel(logging.DEBUG)
```

---

## Related Documentation

<!--
INSTRUCTIONS: Link to related documentation.
-->

- [API Overview](../../README.md#api-documentation)
- [Authentication Guide](../architecture/authentication-system.md)
- [Error Handling Guide](../guides/error-handling.md)
- [API Versioning Policy](../guides/api-versioning.md)
- [Rate Limiting Guide](../guides/rate-limiting.md)

---

## Changelog

<!--
INSTRUCTIONS: Document changes to this endpoint.
-->

### Version [X.Y.Z] - [YYYY-MM-DD]

**Added:**
- [New feature or capability]

**Changed:**
- [Modified behavior]

**Deprecated:**
- [Feature being phased out]

**Removed:**
- [Feature removed]

**Fixed:**
- [Bug fix]

**Security:**
- [Security improvement]

---

**Document Information:**
- **Endpoint Version:** [X.Y.Z]
- **API Version:** v1
- **Last Updated:** [YYYY-MM-DD]
- **Maintainer:** [Team/Person responsible]
- **Status:** [Active/Deprecated/Experimental]
