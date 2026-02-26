# Auto Code Web Backend API Endpoints

## Specs Management

The specs endpoints provide access to spec (task) management functionality.

### List All Specs

**Endpoint:** `GET /api/specs`

**Description:** Returns a list of all specs in the project with their current status and progress.

**Response:**
```json
{
  "specs": [
    {
      "number": "001",
      "name": "feature-name",
      "folder": "001-feature-name",
      "status": "in_progress",
      "progress": "3/10",
      "has_build": true
    }
  ],
  "total": 1
}
```

**Example:**
```bash
curl -X GET http://localhost:8000/api/specs \
     -H "Content-Type: application/json"
```

### Get Spec Details

**Endpoint:** `GET /api/specs/{spec_id}`

**Description:** Returns detailed information about a specific spec, including its content and subtask progress.

**Parameters:**
- `spec_id`: Spec number (e.g., "001") or full folder name (e.g., "001-feature-name")

**Response:**
```json
{
  "number": "001",
  "name": "feature-name",
  "folder": "001-feature-name",
  "status": "in_progress",
  "progress": {
    "completed": 3,
    "in_progress": 1,
    "pending": 6,
    "failed": 0,
    "total": 10,
    "percentage": 30.0
  },
  "has_build": true,
  "spec_content": "# Feature Specification\n\n..."
}
```

**Example:**
```bash
curl -X GET http://localhost:8000/api/specs/001 \
     -H "Content-Type: application/json"
```

### Health Check

**Endpoint:** `GET /api/specs/health`

**Description:** Returns health status of the specs API endpoint.

**Response:**
```json
{
  "status": "ok",
  "endpoint": "specs",
  "project_dir": "/path/to/project",
  "specs_dir_exists": true
}
```

## Tasks Management

The tasks endpoints are synonymous with specs endpoints (tasks and specs are the same concept).

See `/api/tasks` for equivalent functionality with task-oriented naming.

## Authentication

See `/api/auth` for authentication endpoints.
