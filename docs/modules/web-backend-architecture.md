# Web Backend Architecture

The Web Backend is a FastAPI-based REST API service that provides HTTP endpoints and WebSocket connections for the Auto Claude web interface. It acts as a bridge between the frontend UI and the Python backend agent system, enabling remote agent execution and real-time progress monitoring.

## Architecture Overview

```
apps/web-backend/
├── api/                    # API layer (routes, models, WebSocket)
│   ├── models/            # Pydantic data models
│   ├── routes/            # HTTP endpoint handlers
│   └── websocket.py       # WebSocket connection management
├── core/                   # Core infrastructure
│   ├── config.py          # Configuration management
│   └── security.py        # Authentication and JWT utilities
├── services/              # Business logic services
│   └── agent_runner.py    # Agent execution service
└── main.py                # Application entry point
```

## Core Infrastructure

### `main.py` (124 lines)
**FastAPI Application Entry Point** - Main application setup with CORS, lifecycle management, and basic endpoints.

**Key Features:**
- FastAPI app initialization with lifespan handler
- CORS middleware configuration for cross-origin requests
- Environment-based configuration (DEBUG, HOST, PORT)
- Root and health check endpoints
- WebSocket placeholder endpoint

**Configuration:**
- `HOST` (default: `0.0.0.0`) - Server host
- `PORT` (default: `8000`) - Server port
- `DEBUG` (default: `false`) - Debug mode
- `CORS_ORIGINS` (default: `http://localhost:3000`) - Allowed origins
- `SECRET_KEY` - JWT signing secret (required in production)

**Usage:**
```bash
# Start server
python main.py

# Or with uvicorn
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### `core/config.py` (69 lines)
**Configuration Management** - Centralized settings from environment variables.

**Settings:**
- Server: `HOST`, `PORT`, `DEBUG`
- CORS: `CORS_ORIGINS` (comma-separated list)
- Auth: `SECRET_KEY`, `ACCESS_TOKEN_EXPIRE_MINUTES`
- Integration: `AUTO_CLAUDE_BACKEND_DIR` (path to Python backend)
- WebSocket: `WS_HEARTBEAT_INTERVAL`

**Validation:**
- Ensures `SECRET_KEY` is set in production (`DEBUG=false`)
- Uses `lru_cache()` for singleton settings instance

### `core/security.py` (127 lines)
**Authentication and Security** - JWT token validation and FastAPI security dependencies.

**Key Functions:**
- `create_access_token(data, expires_delta)` - Create JWT tokens
- `verify_token(token)` - Verify and decode JWT tokens
- `get_current_token(credentials)` - FastAPI dependency for token extraction
- `require_auth(token)` - FastAPI dependency for protected routes

**Token Format:**
- Algorithm: HS256
- Default expiry: 60 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Claims: User-defined data + `exp` (expiration timestamp)

**Usage:**
```python
from fastapi import Depends
from core.security import require_auth

@router.post("/protected")
async def protected_route(auth: dict = Depends(require_auth)):
    return {"authenticated": True, "user": auth.get("sub")}
```

## API Endpoints

### Specs API (`api/routes/specs.py`, 388 lines)

Manages specs (feature specifications). Specs and tasks are synonymous in Auto Claude.

**Endpoints:**
- `GET /api/specs` - List all specs with status and progress
- `GET /api/specs/{spec_id}` - Get detailed spec information
- `GET /api/specs/health` - Health check

**Key Features:**
- Reads specs from `.auto-claude/specs/` directory
- Parses `implementation_plan.json` for progress tracking
- Status calculation: `pending`, `initialized`, `in_progress`, `complete`
- Progress tracking: completed/total subtasks with percentage

**Example:**
```bash
# List all specs
curl http://localhost:8000/api/specs

# Get spec detail
curl http://localhost:8000/api/specs/001
```

### Tasks API (`api/routes/tasks.py`, 389 lines)

Alias endpoint for specs API. Tasks and specs are synonymous - this provides an alternative naming for consistency with different UX patterns.

**Endpoints:**
- `GET /api/tasks` - List all tasks (specs)
- `GET /api/tasks/{task_id}` - Get detailed task information
- `GET /api/tasks/health` - Health check

**Note:** Internally uses the same logic as specs API - both endpoints access the same data.

### Agents API (`api/routes/agents.py`, 271 lines)

Manages agent execution for planning, coding, and QA tasks.

**Endpoints:**
- `POST /api/agents/run` - Start agent execution (returns task_id)
- `GET /api/agents/status/{task_id}` - Check agent task status
- `POST /api/agents/cancel/{task_id}` - Cancel running agent
- `GET /api/agents/health` - Health check

**Supported Agent Types:**
- `planner` - Creates implementation plan with subtasks
- `coder` - Implements subtasks
- `qa_reviewer` - Validates acceptance criteria
- `qa_fixer` - Fixes QA-reported issues

**Request Model:**
```python
{
    "spec_id": "001",                               # Spec ID or folder name
    "agent_type": "planner",                        # Agent type
    "model": "claude-sonnet-4-5-20250929",         # Claude model
    "verbose": false                                # Verbose output
}
```

**Response:**
```python
{
    "task_id": "001:planner",        # Task ID for status tracking
    "spec_id": "001",
    "agent_type": "planner",
    "status": "started",
    "message": "Agent task started: planner for spec 001"
}
```

**Example:**
```bash
# Start planner agent
curl -X POST http://localhost:8000/api/agents/run \
     -H "Content-Type: application/json" \
     -d '{"spec_id": "001", "agent_type": "planner"}'

# Check status
curl http://localhost:8000/api/agents/status/001:planner

# Cancel task
curl -X POST http://localhost:8000/api/agents/cancel/001:planner
```

### Authentication API (`api/routes/auth.py`, 81 lines)

Handles token verification and authentication status.

**Endpoints:**
- `POST /api/auth/verify` - Verify JWT token (requires auth)
- `GET /api/auth/status` - Get auth system status (no auth required)

**Token Verification:**
```bash
# Verify token
curl -X POST http://localhost:8000/api/auth/verify \
     -H "Authorization: Bearer <your-token>"

# Response
{
    "valid": true,
    "message": "Token is valid",
    "claims": {
        "sub": "user@example.com",
        "exp": 1234567890
    }
}
```

## WebSocket API

### `api/websocket.py` (352 lines)

**Real-Time Agent Progress Updates** - WebSocket endpoint for streaming agent events to connected clients.

**Key Components:**
- `ConnectionManager` - Manages WebSocket connections and subscriptions
- `manager` - Global connection manager instance
- Event broadcasting helpers

**WebSocket Endpoint:**
- `WS /ws/agent-events` - Real-time agent event stream

**Protocol:**

**Client → Server:**
```json
{"action": "subscribe", "spec_id": "001"}
{"action": "unsubscribe", "spec_id": "001"}
{"action": "ping"}
```

**Server → Client:**
```json
{
    "event_type": "execution",
    "spec_id": "001",
    "timestamp": "2024-02-04T10:30:00Z",
    "data": {
        "phase": "coding",
        "phase_progress": 50.0,
        "overall_progress": 25.0,
        "message": "Implementing subtask-1-1",
        "current_subtask": "subtask-1-1"
    }
}
```

**Event Types:**
- `execution` - Execution progress updates
- `ideation` - Ideation/planning events
- `roadmap` - Roadmap generation events
- `log` - Log messages from agent
- `error` - Error events
- `phase` - Phase transition events

**Connection Manager API:**
- `connect(websocket)` - Accept new WebSocket connection
- `disconnect(websocket)` - Remove connection and cleanup
- `subscribe(websocket, spec_id)` - Subscribe to spec events
- `unsubscribe(websocket, spec_id)` - Unsubscribe from spec
- `broadcast_to_spec(spec_id, event)` - Broadcast to spec subscribers
- `broadcast_to_all(event)` - Broadcast to all clients

**Helper Functions:**
```python
# Broadcast execution progress
await broadcast_execution_event(
    spec_id="001",
    phase="coding",
    phase_progress=50.0,
    overall_progress=25.0,
    message="Implementing feature X",
    current_subtask="subtask-1-1"
)

# Broadcast log message
await broadcast_log_event(
    spec_id="001",
    log_line="Running tests...",
    level="info"
)

# Broadcast error
await broadcast_error_event(
    spec_id="001",
    error_message="Test failed",
    error_type="TestError",
    traceback="..."
)
```

**Example Usage:**
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

// Handle events
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log(`Event: ${data.event_type}`, data);
};
```

## Data Models

### `api/models/spec.py`

Pydantic models for spec-related data:
- `SpecSummary` - Brief spec info for list view
- `SpecProgressDetail` - Detailed progress breakdown
- `SpecDetail` - Complete spec information
- `SpecListResponse` - List response wrapper

### `api/models/task.py`

Pydantic models for task-related data (mirrors spec models):
- `TaskSummary` - Brief task info
- `TaskProgressDetail` - Progress breakdown
- `TaskDetail` - Complete task info
- `TaskListResponse` - List response wrapper

### `api/models/agent_event.py`

Pydantic models for WebSocket events:
- `AgentEvent` - Base event class
- `ExecutionEvent` - Execution progress events
- `IdeationEvent` - Ideation/planning events
- `RoadmapEvent` - Roadmap generation events
- `LogEvent` - Log messages
- `ErrorEvent` - Error events
- `PhaseEvent` - Phase transition events
- `WebSocketMessage` - WebSocket message wrapper

## Services Layer

### `services/agent_runner.py` (281 lines)

**Agent Execution Service** - Wraps backend agent logic for async execution in FastAPI context.

**Key Features:**
- Async agent execution with `asyncio`
- Task tracking and management
- Backend integration via dynamic imports
- Task status monitoring

**Key Functions:**
- `run_agent_async(spec_id, agent_type, ...)` - Execute agent asynchronously
- `start_agent_task(spec_id, agent_type, ...)` - Start background task
- `get_task_status(task_id)` - Check task status
- `cancel_task(task_id)` - Cancel running task
- `cleanup_completed_tasks()` - Remove completed tasks

**Task Tracking:**
- Task ID format: `{spec_id}:{agent_type}` (e.g., `001:planner`)
- Status: `running`, `completed`, `failed`, `not_found`
- Global `_running_tasks` dict tracks active tasks

**Backend Integration:**
```python
# Lazy import from backend
_ensure_backend_in_path()
from agents import run_autonomous_agent, run_followup_planner

# Execute agent
if agent_type == "planner":
    success = await run_followup_planner(...)
else:
    await run_autonomous_agent(...)
```

**Error Handling:**
- `ValueError` - Invalid agent type
- `FileNotFoundError` - Spec not found
- `RuntimeError` - Task already running
- Generic `Exception` - Execution failure

## API Documentation

FastAPI automatically generates interactive API documentation:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`
- **OpenAPI Schema:** `http://localhost:8000/openapi.json`

## Security Model

### Authentication
- JWT-based authentication using HS256 algorithm
- Bearer token in `Authorization` header
- Token expiration (default: 60 minutes)

### CORS
- Configurable allowed origins via `CORS_ORIGINS`
- Supports credentials and all methods/headers

### Production Checklist
- [ ] Set strong `SECRET_KEY` (not default)
- [ ] Set `DEBUG=false`
- [ ] Configure `CORS_ORIGINS` to allowed domains only
- [ ] Use HTTPS in production
- [ ] Enable rate limiting (not implemented)
- [ ] Set up proper logging and monitoring

## Development Workflow

### Local Development
```bash
# 1. Set up environment
cd apps/web-backend
cp .env.example .env
# Edit .env with your settings

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run in development mode
python main.py
# Or with auto-reload:
uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 4. Test WebSocket
# Open http://localhost:8000/docs
# Try /ws/agent-events endpoint
```

### Testing
```bash
# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8000/api/specs
curl http://localhost:8000/api/tasks

# Test authentication
curl -X POST http://localhost:8000/api/auth/verify \
     -H "Authorization: Bearer test-token"
```

## Integration with Frontend

The web backend integrates with the Electron/React frontend:

1. **Frontend** sends HTTP requests to REST API
2. **WebSocket** connection for real-time updates
3. **Agent execution** triggered via `/api/agents/run`
4. **Progress updates** streamed via WebSocket
5. **Status polling** via `/api/agents/status/{task_id}`

**Example Flow:**
```
Frontend                  Web Backend              Python Backend
   |                          |                          |
   |--POST /api/agents/run--->|                          |
   |                          |--start_agent_task------->|
   |<--202 {task_id}----------|                          |
   |                          |                          |
   |--WS subscribe(spec_id)-->|                          |
   |                          |                          |
   |                          |<--progress events--------|
   |<--WS events--------------|                          |
   |                          |                          |
   |--GET /status/{task_id}-->|                          |
   |<--200 {status}-----------|                          |
```

## Module Dependencies

```
main.py
  ├── core.config (Settings)
  ├── api.routes.specs (Router)
  ├── api.routes.tasks (Router)
  ├── api.routes.agents (Router)
  ├── api.routes.auth (Router)
  └── api.websocket (Router)

api/routes/agents.py
  └── services.agent_runner (run, status, cancel)

services/agent_runner.py
  └── apps.backend.agents (run_autonomous_agent, run_followup_planner)

api/routes/auth.py
  └── core.security (require_auth, get_current_token)

api/websocket.py
  └── api.models.agent_event (Event models)
```

## Environment Variables

Required:
- `SECRET_KEY` - JWT signing secret (must be set in production)

Optional:
- `HOST` - Server host (default: `127.0.0.1`)
- `PORT` - Server port (default: `8000`)
- `DEBUG` - Debug mode (default: `false`)
- `CORS_ORIGINS` - Allowed origins (default: `http://localhost:3000,http://localhost:5173`)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiry (default: `60`)
- `AUTO_CLAUDE_BACKEND_DIR` - Path to Python backend (auto-detected)
- `WS_HEARTBEAT_INTERVAL` - WebSocket heartbeat interval (default: `30`)
- `LOG_LEVEL` - Logging level (default: `INFO`)

## Performance Considerations

### Async Task Management
- Agents run in background `asyncio` tasks
- Non-blocking API responses (202 Accepted)
- Task status polling for completion

### WebSocket Connection Management
- Connection pooling with subscription tracking
- Automatic cleanup of disconnected clients
- Efficient broadcast to spec subscribers only

### Caching
- Settings cached with `lru_cache()`
- No file system caching (reads on-demand)

## Future Enhancements

Planned features:
- [ ] Rate limiting per client IP
- [ ] Agent execution queuing system
- [ ] Persistent task history
- [ ] Enhanced error reporting with stack traces
- [ ] Metrics and monitoring endpoints
- [ ] Health check for backend integration
- [ ] WebSocket authentication
- [ ] Multi-tenancy support

## Troubleshooting

### Agent Execution Fails
- Check backend directory path in `AUTO_CLAUDE_BACKEND_DIR`
- Ensure backend dependencies are installed
- Verify spec directory exists in `.auto-claude/specs/`

### WebSocket Connection Drops
- Check `WS_HEARTBEAT_INTERVAL` setting
- Verify CORS origins include WebSocket client origin
- Check for network proxy issues

### Authentication Errors
- Verify `SECRET_KEY` is set and consistent
- Check token expiration time
- Ensure `Authorization: Bearer <token>` header format

### CORS Issues
- Add frontend origin to `CORS_ORIGINS`
- Verify credentials are enabled in frontend requests
- Check for trailing slashes in origin URLs
