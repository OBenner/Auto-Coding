# Web-Based IDE Interface

**Documentation Date:** 2026-03-23

## Overview

The Web-Based IDE Interface provides browser-based access to Auto Code's project management, file editing, agent execution, and real-time progress monitoring. It enables users to interact with Auto Code from any device with a web browser, removing the dependency on the Electron desktop app or CLI.

**Key Characteristics:**
- REST API backend built with FastAPI (Python)
- React + TypeScript frontend with Vite
- Real-time agent progress via WebSocket
- Sandboxed file system operations with path traversal protection
- JWT-based authentication with user registration and login
- Git OAuth integration (GitHub and GitLab)
- Integrated web terminal (PTY sessions)
- API usage tracking and rate limiting

---

## Architecture

The Web IDE is split into two applications that communicate over HTTP and WebSocket:

```
Browser (web-frontend)
    |
    |  HTTP REST / WebSocket
    v
FastAPI Server (web-backend)
    |
    |  Python imports
    v
Auto Code Backend (apps/backend)
    |
    v
Claude Agent SDK
```

### Web Backend (`apps/web-backend/`)

A FastAPI application providing REST API endpoints and WebSocket handlers.

```
apps/web-backend/
+-- main.py                  # FastAPI app entry point, middleware, router registration
+-- core/
|   +-- config.py            # Centralized settings from environment variables
|   +-- security.py          # JWT token creation, verification, auth dependencies
|   +-- database.py          # SQLAlchemy database setup
|   +-- middleware.py         # Usage tracking middleware
|   +-- oauth.py             # GitHub/GitLab OAuth client setup
+-- api/
|   +-- routes/
|   |   +-- agents.py        # Agent execution endpoints (run, status, cancel)
|   |   +-- auth.py          # Token verification
|   |   +-- files.py         # File browsing and editing (sandboxed)
|   |   +-- git.py           # GitHub/GitLab OAuth flows
|   |   +-- specs.py         # Spec listing and detail
|   |   +-- tasks.py         # Task listing and detail (alias for specs)
|   |   +-- usage.py         # Usage statistics and dashboard
|   |   +-- users.py         # User registration and login
|   |   +-- shared.py        # Shared utilities (path helpers, spec parsing)
|   +-- websocket.py         # WebSocket connection manager and event broadcasting
|   +-- models/              # Pydantic models for API request/response
|   +-- utils/               # Shared utilities
+-- services/
|   +-- agent_runner.py      # Async agent task management
|   +-- filesystem_service.py # Sandboxed file system operations
|   +-- git_service.py       # Git provider API client
|   +-- terminal_manager.py  # PTY terminal session management
|   +-- usage_tracker.py     # Redis-based usage tracking
+-- tests/                   # Test suite
```

### Web Frontend (`apps/web-frontend/`)

A React + TypeScript single-page application built with Vite.

- Task/spec management dashboard
- File browser and code editor
- Real-time agent progress monitoring via WebSocket
- Web terminal
- Usage statistics dashboard

---

## Key Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/users/register` | Register a new user account |
| POST | `/api/users/login` | Login and receive JWT token |
| POST | `/api/auth/verify` | Verify an existing JWT token |

### File System (Sandboxed)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/files/list?path=` | List files and directories |
| GET | `/api/files/content?path=` | Read file content (text only) |
| PUT | `/api/files/content` | Write/create a file |
| POST | `/api/files/mkdir` | Create a directory |
| DELETE | `/api/files?path=` | Delete a file or directory |

### Specs and Tasks

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/specs` | List all specs with status |
| GET | `/api/specs/{id}` | Get spec detail with progress |
| GET | `/api/specs/{id}/progress` | Get subtask progress breakdown |
| GET | `/api/tasks` | List all tasks (alias for specs) |
| GET | `/api/tasks/{id}` | Get task detail |

### Agent Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agents/run` | Start an agent (planner, coder, qa_reviewer, qa_fixer) |
| GET | `/api/agents/status/{task_id}` | Check agent task status |
| POST | `/api/agents/cancel/{task_id}` | Cancel a running agent |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://.../ws/agent-events?token=` | Real-time agent progress events |
| `ws://.../ws/terminal/{session_id}?token=` | Web terminal I/O |

### Git OAuth

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/git/github/authorize` | Start GitHub OAuth flow |
| GET | `/api/git/github/callback` | GitHub OAuth callback |
| GET | `/api/git/gitlab/authorize` | Start GitLab OAuth flow |
| GET | `/api/git/gitlab/callback` | GitLab OAuth callback |

---

## Starting the Web Backend

### Prerequisites

- Python 3.10+
- Node.js 18+ (for the frontend)

### Backend

```bash
cd apps/web-backend

# Create virtual environment and install dependencies
uv venv && uv pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings (SECRET_KEY, CORS_ORIGINS, etc.)

# Start the server
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

The API is then available at `http://localhost:8000` with interactive docs at `http://localhost:8000/docs`.

### Frontend

```bash
cd apps/web-frontend
npm install
npm run dev
```

The frontend is available at `http://localhost:3000` (or the next available port).

See `apps/START_SERVERS.md` for detailed startup instructions and troubleshooting.

---

## Security Model

### Authentication

- **JWT tokens** issued on login/register, verified on every protected endpoint
- Tokens expire after a configurable period (`ACCESS_TOKEN_EXPIRE_MINUTES`)
- WebSocket connections authenticated via query parameter token
- OAuth state tokens for CSRF protection on GitHub/GitLab flows

### File System Sandboxing

All file operations are restricted to the configured project directory:

1. **Path validation**: Every file endpoint calls `_validate_and_resolve_path()` which:
   - Strips leading separators to treat all paths as relative
   - Resolves the full path (expanding `..`, symlinks)
   - Checks `Path.is_relative_to(project_root)` to block traversal
   - Also validates the parent directory to catch symlink-based escapes
2. **Error messages**: Use validated relative paths (never raw user input) in responses
3. **Size limits**: File reads capped at 1 MB; binary files rejected
4. **Project root protection**: Deletion of the project root is explicitly blocked

### CORS

- Configurable allowed origins via `CORS_ORIGINS` environment variable
- Defaults to localhost development ports in development mode

### Rate Limiting

- Optional Redis-based rate limiting via `UsageTrackingMiddleware`
- Configurable per-user request limits and time periods

---

## Configuration

Key environment variables for `apps/web-backend/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `false` |
| `HOST` | Server bind address | `""` (all interfaces) |
| `PORT` | Server port | `8000` |
| `SECRET_KEY` | JWT signing key (required in production) | auto-generated |
| `CORS_ORIGINS` | Comma-separated allowed origins | localhost dev ports |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token lifetime | `60` |
| `DATABASE_URL` | SQLAlchemy database URL | `""` |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | GitHub OAuth credentials | `""` |
| `GITLAB_CLIENT_ID` / `GITLAB_CLIENT_SECRET` | GitLab OAuth credentials | `""` |
| `REDIS_HOST` / `REDIS_PORT` | Redis for usage tracking | `""` / `6379` |

---

## Related Documentation

- [START_SERVERS.md](../../apps/START_SERVERS.md) -- Detailed server startup and troubleshooting
- [CLI-USAGE.md](../../guides/CLI-USAGE.md) -- Terminal-based usage (alternative to web IDE)
- [CLOUD_DEPLOYMENT.md](../../guides/CLOUD_DEPLOYMENT.md) -- Cloud deployment guide
