# Web Backend API Reference

Complete reference for Auto Code's FastAPI web backend REST API and WebSocket endpoints.

## Overview

The web backend is a FastAPI service that provides HTTP REST APIs and WebSocket connections for the Auto Code web interface. It enables task management, agent execution, and real-time progress updates.

**Tech Stack:**
- Framework: FastAPI
- Language: Python
- Port: 8000 (default)
- Entry Point: `apps/web-backend/main.py`

**Key Features:**
- RESTful API for specs/tasks management
- Agent execution with background processing
- WebSocket for real-time agent events
- JWT-based authentication
- CORS support for web frontend integration

---

## Getting Started

### Starting the Server

```bash
cd apps/web-backend
python main.py
```

The server will start on `http://localhost:8000` by default.

### Interactive API Documentation

FastAPI provides automatic interactive documentation:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Environment Variables

Required configuration in `apps/web-backend/.env`:

```bash
# Server configuration
HOST=0.0.0.0
PORT=8000
DEBUG=true
LOG_LEVEL=INFO

# CORS configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Authentication
SECRET_KEY=<generate-secure-secret-key>
ACCESS_TOKEN_EXPIRE_MINUTES=30

# WebSocket configuration
WS_HEARTBEAT_INTERVAL=30

# Auto Code backend integration (optional)
AUTO_CLAUDE_BACKEND_DIR=/path/to/apps/backend
```

---

## Endpoints

### Root & Health

#### `GET /`

Root endpoint providing API information.

**Response: 200 OK**
```json
{
  "name": "Web Backend API",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

**Example:**
```bash
curl http://localhost:8000/
```

---

#### `GET /health`

Health check endpoint for monitoring.

**Response: 200 OK**
```json
{
  "status": "healthy",
  "service": "web-backend",
  "debug": true
}
```

**Example:**
```bash
curl http://localhost:8000/health
```

---

### Specs API

Endpoints for managing specifications (specs). Specs and tasks are synonymous in Auto Code.

**Base Path:** `/api/specs`

---

#### `GET /api/specs`

List all specs in the project.

**Response: 200 OK**
```json
{
  "specs": [
    {
      "number": "001",
      "name": "feature-name",
      "folder": "001-feature-name",
      "status": "in_progress",
      "progress": "5/10",
      "has_build": true
    }
  ],
  "total": 1
}
```

**Status Values:**
- `pending` - Spec created, no implementation plan
- `initialized` - Implementation plan created, no progress
- `in_progress` - Some subtasks completed
- `complete` - All subtasks completed

**Example:**
```bash
curl -X GET http://localhost:8000/api/specs \
     -H "Content-Type: application/json"
```

---

#### `GET /api/specs/{spec_id}`

Get detailed information for a specific spec.

**Path Parameters:**
- `spec_id` (string) - Spec number (e.g., "001") or full folder name (e.g., "001-feature")

**Response: 200 OK**
```json
{
  "number": "001",
  "name": "feature-name",
  "folder": "001-feature-name",
  "status": "in_progress",
  "progress": {
    "completed": 5,
    "in_progress": 1,
    "pending": 4,
    "failed": 0,
    "total": 10,
    "percentage": 50.0
  },
  "has_build": true,
  "spec_content": "# Specification: ...\n\n..."
}
```

**Errors:**
- `404 Not Found` - Spec does not exist
- `500 Internal Server Error` - Failed to read spec

**Example:**
```bash
curl -X GET http://localhost:8000/api/specs/001 \
     -H "Content-Type: application/json"
```

---

#### `GET /api/specs/health`

Health check for specs API.

**Response: 200 OK**
```json
{
  "status": "ok",
  "endpoint": "specs",
  "project_dir": "/path/to/project",
  "specs_dir_exists": true
}
```

---

### Tasks API

Endpoints for managing tasks. Tasks and specs are synonymous - this is an alias endpoint for specs.

**Base Path:** `/api/tasks`

---

#### `GET /api/tasks`

List all tasks (specs) in the project.

**Response:** Same format as `GET /api/specs`

**Example:**
```bash
curl -X GET http://localhost:8000/api/tasks \
     -H "Content-Type: application/json"
```

---

#### `GET /api/tasks/{task_id}`

Get detailed information for a specific task.

**Response:** Same format as `GET /api/specs/{spec_id}`

**Example:**
```bash
curl -X GET http://localhost:8000/api/tasks/001 \
     -H "Content-Type: application/json"
```

---

#### `GET /api/tasks/health`

Health check for tasks API.

**Response:** Same format as `GET /api/specs/health`

---

### Agents API

Endpoints for starting and managing agent execution.

**Base Path:** `/api/agents`

---

#### `POST /api/agents/run`

Start an agent execution task in the background.

**Request Body:**
```json
{
  "spec_id": "001",
  "agent_type": "planner",
  "model": "claude-sonnet-4-5-20250929",
  "verbose": false
}
```

**Request Schema:**
- `spec_id` (string, required) - Spec ID (e.g., "001" or "001-feature-name")
- `agent_type` (string, required) - Type of agent: `planner`, `coder`, `qa_reviewer`, `qa_fixer`
- `model` (string, optional) - Claude model to use (default: "claude-sonnet-4-5-20250929")
- `verbose` (boolean, optional) - Enable verbose output (default: false)

**Response: 202 Accepted**
```json
{
  "task_id": "001:planner",
  "spec_id": "001",
  "agent_type": "planner",
  "status": "started",
  "message": "Agent task started: planner for spec 001"
}
```

**Errors:**
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Spec does not exist
- `409 Conflict` - Task already running
- `500 Internal Server Error` - Failed to start agent

**Example:**
```bash
curl -X POST http://localhost:8000/api/agents/run \
     -H "Content-Type: application/json" \
     -d '{
       "spec_id": "001",
       "agent_type": "planner"
     }'
```

**Notes:**
- The agent runs asynchronously in the background
- Use the returned `task_id` to check status via `GET /api/agents/status/{task_id}`
- Progress events are emitted via WebSocket (`/ws/agent-events`)

---

#### `GET /api/agents/status/{task_id}`

Get the status of a running agent task.

**Path Parameters:**
- `task_id` (string) - Task ID returned by POST /api/agents/run

**Response: 200 OK**
```json
{
  "task_id": "001:planner",
  "status": "running",
  "result": null,
  "error": null
}
```

**Status Values:**
- `running` - Task is currently executing
- `completed` - Task finished successfully
- `failed` - Task encountered an error
- `not_found` - Task does not exist

**Errors:**
- `404 Not Found` - Task does not exist
- `500 Internal Server Error` - Failed to get status

**Example:**
```bash
curl -X GET http://localhost:8000/api/agents/status/001:planner \
     -H "Content-Type: application/json"
```

---

#### `POST /api/agents/cancel/{task_id}`

Cancel a running agent task.

**Path Parameters:**
- `task_id` (string) - Task ID to cancel

**Response: 200 OK**
```json
{
  "task_id": "001:planner",
  "cancelled": true,
  "message": "Task cancelled: 001:planner"
}
```

**Response (task not found):**
```json
{
  "task_id": "001:planner",
  "cancelled": false,
  "message": "Task not found or already completed: 001:planner"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/agents/cancel/001:planner \
     -H "Content-Type: application/json"
```

---

#### `GET /api/agents/health`

Health check for agents API.

**Response: 200 OK**
```json
{
  "status": "ok",
  "endpoint": "agents",
  "project_dir": "/path/to/project"
}
```

---

### Authentication API

Endpoints for token verification and authentication management.

**Base Path:** `/api/auth`

---

#### `POST /api/auth/verify`

Verify the authentication token provided in the Authorization header.

**Headers:**
```
Authorization: Bearer <jwt-token>
```

**Response: 200 OK**
```json
{
  "valid": true,
  "message": "Token is valid",
  "claims": {
    "sub": "user_id",
    "exp": 1234567890
  }
}
```

**Errors:**
- `401 Unauthorized` - Token is missing, invalid, or expired

**Example:**
```bash
# Valid token
curl -X POST http://localhost:8000/api/auth/verify \
     -H "Authorization: Bearer <valid-token>"

# Invalid/missing token
curl -X POST http://localhost:8000/api/auth/verify
# Returns: 401 Unauthorized
```

---

#### `GET /api/auth/status`

Get authentication system status (no authentication required).

**Response: 200 OK**
```json
{
  "status": "ok",
  "auth_enabled": true,
  "message": "Authentication system is operational"
}
```

**Example:**
```bash
curl http://localhost:8000/api/auth/status
```

---

## WebSocket

### Real-Time Agent Events

The web backend provides a WebSocket endpoint for real-time agent progress updates.

**Endpoint:** `ws://localhost:8000/ws/agent-events`

---

#### Connection Protocol

**Client → Server Messages:**

**Subscribe to spec:**
```json
{
  "action": "subscribe",
  "spec_id": "001"
}
```

**Unsubscribe from spec:**
```json
{
  "action": "unsubscribe",
  "spec_id": "001"
}
```

**Ping (heartbeat):**
```json
{
  "action": "ping"
}
```

**Server → Client Responses:**

**Subscription confirmed:**
```json
{
  "status": "subscribed",
  "spec_id": "001",
  "timestamp": "2026-02-04T12:00:00"
}
```

**Unsubscription confirmed:**
```json
{
  "status": "unsubscribed",
  "spec_id": "001",
  "timestamp": "2026-02-04T12:00:00"
}
```

**Pong (heartbeat response):**
```json
{
  "status": "pong",
  "timestamp": "2026-02-04T12:00:00"
}
```

**Error:**
```json
{
  "status": "error",
  "message": "Error description"
}
```

---

#### Event Types

**Execution Progress Event:**
```json
{
  "event_type": "execution",
  "timestamp": "2026-02-04T12:00:00",
  "spec_id": "001",
  "data": {
    "phase": "implementation",
    "phase_progress": 50.0,
    "overall_progress": 25.0,
    "message": "Implementing subtask-1",
    "current_subtask": "subtask-1"
  }
}
```

**Log Event:**
```json
{
  "event_type": "log",
  "timestamp": "2026-02-04T12:00:00",
  "spec_id": "001",
  "log_line": "Starting implementation...",
  "level": "info"
}
```

**Error Event:**
```json
{
  "event_type": "error",
  "timestamp": "2026-02-04T12:00:00",
  "spec_id": "001",
  "error_message": "Failed to execute command",
  "error_type": "RuntimeError",
  "traceback": "Traceback (most recent call last):\n..."
}
```

**Phase Event:**
```json
{
  "event_type": "phase",
  "timestamp": "2026-02-04T12:00:00",
  "spec_id": "001",
  "phase_name": "planning",
  "status": "started"
}
```

---

#### JavaScript Client Example

```javascript
// Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/ws/agent-events");

// Subscribe to spec
ws.onopen = () => {
  ws.send(JSON.stringify({
    action: "subscribe",
    spec_id: "001"
  }));
};

// Handle incoming events
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.event_type === "execution") {
    console.log(`Progress: ${data.data.overall_progress}%`);
  } else if (data.event_type === "log") {
    console.log(`[${data.level}] ${data.log_line}`);
  } else if (data.event_type === "error") {
    console.error(`Error: ${data.error_message}`);
  }
};

// Handle connection close
ws.onclose = () => {
  console.log("WebSocket disconnected");
};

// Heartbeat (ping every 30 seconds)
setInterval(() => {
  if (ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ action: "ping" }));
  }
}, 30000);
```

---

#### Python Client Example

```python
import asyncio
import json
import websockets

async def agent_events_client():
    uri = "ws://localhost:8000/ws/agent-events"

    async with websockets.connect(uri) as websocket:
        # Subscribe to spec
        await websocket.send(json.dumps({
            "action": "subscribe",
            "spec_id": "001"
        }))

        # Receive events
        async for message in websocket:
            data = json.loads(message)

            if data.get("event_type") == "execution":
                print(f"Progress: {data['data']['overall_progress']}%")
            elif data.get("event_type") == "log":
                print(f"[{data['level']}] {data['log_line']}")
            elif data.get("event_type") == "error":
                print(f"Error: {data['error_message']}")

# Run client
asyncio.run(agent_events_client())
```

---

## Data Models

### Spec/Task Models

**SpecSummary / TaskSummary:**
```python
{
  "number": str,           # Spec number (e.g., "001")
  "name": str,             # Spec name (e.g., "feature-name")
  "folder": str,           # Full folder name (e.g., "001-feature-name")
  "status": str,           # Status: pending, initialized, in_progress, complete
  "progress": str,         # Progress string (e.g., "5/10")
  "has_build": bool        # Whether implementation plan exists
}
```

**SpecDetail / TaskDetail:**
```python
{
  "number": str,
  "name": str,
  "folder": str,
  "status": str,
  "progress": {
    "completed": int,
    "in_progress": int,
    "pending": int,
    "failed": int,
    "total": int,
    "percentage": float   # 0-100
  },
  "has_build": bool,
  "spec_content": str     # Full spec.md content
}
```

---

### Agent Models

**AgentRunRequest:**
```python
{
  "spec_id": str,          # Required
  "agent_type": str,       # Required: planner, coder, qa_reviewer, qa_fixer
  "model": str,            # Optional: default "claude-sonnet-4-5-20250929"
  "verbose": bool          # Optional: default false
}
```

**AgentRunResponse:**
```python
{
  "task_id": str,
  "spec_id": str,
  "agent_type": str,
  "status": str,           # "started" or "error"
  "message": str
}
```

**AgentStatusResponse:**
```python
{
  "task_id": str,
  "status": str,           # running, completed, failed, not_found
  "result": dict | None,
  "error": str | None
}
```

---

## Configuration

### Settings Module

Location: `apps/web-backend/core/config.py`

**Available Settings:**

```python
from core.config import settings

# Server
settings.HOST                          # "127.0.0.1"
settings.PORT                          # 8000
settings.DEBUG                         # False

# CORS
settings.CORS_ORIGINS                  # ["http://localhost:3000"]

# Authentication
settings.SECRET_KEY                    # JWT secret key
settings.ACCESS_TOKEN_EXPIRE_MINUTES   # 60

# Backend Integration
settings.AUTO_CLAUDE_BACKEND_DIR       # Path to backend directory

# WebSocket
settings.WS_HEARTBEAT_INTERVAL         # 30 seconds
```

---

## Error Handling

### Standard Error Responses

All endpoints return standard HTTP error responses:

**400 Bad Request:**
```json
{
  "detail": "Invalid request parameters"
}
```

**401 Unauthorized:**
```json
{
  "detail": "Could not validate credentials"
}
```

**404 Not Found:**
```json
{
  "detail": "Spec 001 not found"
}
```

**409 Conflict:**
```json
{
  "detail": "Task already running"
}
```

**500 Internal Server Error:**
```json
{
  "detail": "Failed to list specs: Internal error"
}
```

---

## Security

### CORS Configuration

The API supports Cross-Origin Resource Sharing (CORS) for web frontend integration.

**Default Allowed Origins:**
- `http://localhost:3000` (React dev server)
- `http://localhost:5173` (Vite dev server)

Configure via `CORS_ORIGINS` environment variable:
```bash
CORS_ORIGINS=http://localhost:3000,http://localhost:5173,https://app.example.com
```

---

### Authentication

JWT-based authentication is implemented but not enforced on all endpoints.

**Protected Endpoints:**
- `POST /api/auth/verify` - Requires valid JWT token

**Public Endpoints:**
- All other endpoints (authentication can be added as needed)

**Token Format:**
```
Authorization: Bearer <jwt-token>
```

---

## Development

### Running Tests

```bash
cd apps/web-backend

# Test imports
python test_imports.py

# Test specs endpoint
python test_specs_endpoint.py

# Test WebSocket
python test_websocket_realtime.py
```

---

### Adding New Endpoints

**1. Create route module in `api/routes/`:**

```python
# api/routes/my_endpoint.py
from fastapi import APIRouter, HTTPException, status

router = APIRouter(prefix="/api/my-endpoint", tags=["my-endpoint"])

@router.get("")
async def my_endpoint():
    return {"status": "ok"}
```

**2. Register route in main.py:**

```python
from api.routes import my_endpoint

app.include_router(my_endpoint.router)
```

---

### Broadcasting WebSocket Events

Use helper functions from `api.websocket`:

```python
from api.websocket import broadcast_execution_event, broadcast_log_event

# Broadcast execution progress
await broadcast_execution_event(
    spec_id="001",
    phase="implementation",
    phase_progress=50.0,
    overall_progress=25.0,
    message="Implementing subtask-1"
)

# Broadcast log message
await broadcast_log_event(
    spec_id="001",
    log_line="Starting implementation...",
    level="info"
)
```

---

## Integration with Backend CLI

The web backend integrates with the Python backend CLI (`apps/backend/run.py`) for agent execution.

**Agent Execution Flow:**

1. Web frontend calls `POST /api/agents/run`
2. Web backend spawns background task
3. Background task executes Python backend CLI
4. Progress updates broadcast via WebSocket
5. Task completion updates task status

**Configuration:**

Set `AUTO_CLAUDE_BACKEND_DIR` to point to `apps/backend/` directory:

```bash
AUTO_CLAUDE_BACKEND_DIR=/path/to/Auto-Claude/apps/backend
```

---

## See Also

- [Backend CLI API](./backend-api.md) - Python backend API reference
- [Frontend Architecture](../modules/frontend-architecture.md) - Electron desktop app
- [Web Frontend Architecture](../modules/web-frontend-architecture.md) - React web interface
- [Agent Pipeline Diagram](../diagrams/agent-pipeline.mermaid) - Agent workflow visualization

---

**Version:** 1.0.0
**Last Updated:** 2026-02-04
**Maintained By:** Auto Code Team
