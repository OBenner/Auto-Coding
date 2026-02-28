# API Endpoint: Create Spec

## Overview

**Base URL**: `/api/v1/specs`
**HTTP Method**: `POST`
**Authentication**: Required (Bearer token)
**Rate Limiting**: 10 requests per minute per user

**Purpose**: Create a new feature specification from a task description.

## Request

### URL Structure

```
POST /api/v1/specs
```

### Path Parameters

None (collection endpoint)

### Query Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `complexity` | string | No | Force complexity level: `simple`, `standard`, `complex` |
| `interactive` | boolean | No | Enable interactive mode (default: false) |

### Headers

| Header | Type | Required | Description |
|--------|------|----------|-------------|
| `Authorization` | string | Yes | Bearer token: `Bearer <token>` |
| `Content-Type` | string | Yes | Must be `application/json` |
| `X-Request-ID` | string | No | Client-generated request ID for tracing |

### Request Body

**Content-Type**: `application/json`

**Schema**:
```json
{
  "task_description": "string (required, 10-5000 chars)",
  "project_dir": "string (required, absolute path)",
  "spec_type": "string (optional, enum: feature|bugfix|enhancement)",
  "metadata": {
    "labels": ["string"],
    "priority": "string (enum: low|medium|high)"
  }
}
```

**Example**:
```json
{
  "task_description": "Add dark mode support to the desktop application",
  "project_dir": "/home/user/projects/my-app",
  "spec_type": "feature",
  "metadata": {
    "labels": ["ui", "accessibility"],
    "priority": "medium"
  }
}
```

## Response

### Success Response (201 Created)

**Content-Type**: `application/json`

**Schema**:
```json
{
  "spec_id": "string (format: XXX-kebab-case-name)",
  "status": "string (enum: created|in_progress|completed)",
  "spec_dir": "string (absolute path)",
  "created_at": "string (ISO 8601 timestamp)",
  "estimated_completion": "string (ISO 8601 timestamp)",
  "spec_url": "string (URL to spec file)"
}
```

**Example**:
```json
{
  "spec_id": "042-dark-mode-support",
  "status": "created",
  "spec_dir": "/home/user/projects/my-app/.auto-claude/specs/042-dark-mode-support",
  "created_at": "2026-02-05T18:30:00Z",
  "estimated_completion": "2026-02-05T18:35:00Z",
  "spec_url": "/api/v1/specs/042-dark-mode-support"
}
```

### Error Responses

#### 400 Bad Request

**Cause**: Invalid request body or parameters

**Schema**:
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "string",
    "details": {
      "field": "string",
      "reason": "string"
    }
  }
}
```

**Example**:
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Task description is required",
    "details": {
      "field": "task_description",
      "reason": "Field is missing or empty"
    }
  }
}
```

#### 401 Unauthorized

**Cause**: Missing or invalid authentication token

**Example**:
```json
{
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Invalid or expired authentication token"
  }
}
```

#### 429 Too Many Requests

**Cause**: Rate limit exceeded

**Example**:
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again in 45 seconds.",
    "retry_after": 45
  }
}
```

#### 500 Internal Server Error

**Cause**: Server-side error during spec creation

**Example**:
```json
{
  "error": {
    "code": "INTERNAL_ERROR",
    "message": "Failed to create spec",
    "request_id": "req_abc123"
  }
}
```

## Authentication

### Token Management

**Obtaining Token**:
```bash
POST /api/v1/auth/login
{
  "username": "user@example.com",
  "password": "password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGc...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Using Token**:
```bash
curl -X POST /api/v1/specs \
  -H "Authorization: Bearer eyJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"task_description": "..."}'
```

## Examples

### cURL

```bash
curl -X POST http://localhost:8000/api/v1/specs \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "task_description": "Add dark mode support to the application",
    "project_dir": "/home/user/my-project",
    "spec_type": "feature"
  }'
```

### Python

```python
import requests

url = "http://localhost:8000/api/v1/specs"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}
payload = {
    "task_description": "Add dark mode support",
    "project_dir": "/home/user/my-project",
    "spec_type": "feature"
}

response = requests.post(url, json=payload, headers=headers)
print(response.json())
```

### JavaScript (fetch)

```javascript
const response = await fetch('http://localhost:8000/api/v1/specs', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    task_description: 'Add dark mode support',
    project_dir: '/home/user/my-project',
    spec_type: 'feature'
  })
});

const data = await response.json();
console.log(data);
```

## Rate Limiting

### Limits

| User Type | Rate Limit | Burst Limit |
|-----------|-----------|-------------|
| **Free** | 10 req/min | 20 req/hour |
| **Pro** | 60 req/min | 200 req/hour |
| **Enterprise** | Unlimited | Unlimited |

### Retry Handling

```python
import time
import requests

def create_spec_with_retry(payload, max_retries=3):
    for attempt in range(max_retries):
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            time.sleep(retry_after)
            continue

        return response

    raise Exception("Max retries exceeded")
```

## Performance Considerations

### Pagination

For listing specs, use pagination:
```
GET /api/v1/specs?page=1&limit=20
```

### Response Times

- Simple specs: 2-3 seconds
- Standard specs: 3-5 seconds
- Complex specs: 5-8 seconds

## Testing

### Unit Tests

```python
def test_create_spec_success(client, auth_token):
    response = client.post(
        '/api/v1/specs',
        headers={'Authorization': f'Bearer {auth_token}'},
        json={
            'task_description': 'Test feature',
            'project_dir': '/tmp/test-project'
        }
    )
    assert response.status_code == 201
    assert 'spec_id' in response.json()
```

### Integration Tests

```bash
pytest tests/api/test_specs_endpoint.py -v
```

## Security Considerations

### Common Vulnerabilities

| Vulnerability | Mitigation |
|--------------|------------|
| **Path Traversal** | Validate project_dir is absolute path within allowed directories |
| **SQL Injection** | Use parameterized queries (not applicable here) |
| **XSS** | Sanitize task_description input |
| **CSRF** | Require CSRF token for web clients |

## Troubleshooting

### Common Issues

**Issue**: 401 Unauthorized despite valid token
**Solution**: Check token expiration, refresh if needed

**Issue**: Spec creation hangs indefinitely
**Solution**: Check background job queue, may be stuck

**Issue**: Invalid project_dir error
**Solution**: Ensure path is absolute and directory exists

## Related Documentation

- [Spec Creation Guide](../../guides/SPEC-CREATION-PIPELINE.md)
- [Authentication API](./auth-endpoint.md)
- [Spec Management API](./specs-list-endpoint.md)

## Changelog

- **2026-02-05**: Added `metadata` field to request
- **2026-01-15**: Initial API release
