# Auto Claude Web Backend

FastAPI-based REST API and WebSocket server that exposes Auto Claude functionality for browser-based access.

## Overview

The Auto Claude Web Backend provides a web API layer on top of the Auto Claude autonomous coding framework. It enables:

- **REST API endpoints** for task and spec management
- **WebSocket connections** for real-time agent progress updates
- **Authentication and security** for secure remote access
- **CORS support** for browser-based frontend applications

## Architecture

```
┌─────────────────┐      HTTP/WS      ┌──────────────────┐
│  Web Frontend   │ ◄───────────────► │  Web Backend     │
│  (React/Vite)   │                    │  (FastAPI)       │
└─────────────────┘                    └────────┬─────────┘
                                                 │
                                                 │ Python API
                                                 │
                                       ┌─────────▼─────────┐
                                       │  Auto Claude      │
                                       │  Backend Core     │
                                       │  (agents, specs)  │
                                       └───────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.12 or higher
- Auto Claude backend (located at `../backend`)

### Installation

1. **Create virtual environment:**
   ```bash
   cd apps/web-backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set your configuration
   ```

4. **Run the server:**
   ```bash
   # Development mode (with auto-reload)
   python main.py

   # Or using uvicorn directly
   uvicorn main:app --reload --host 127.0.0.1 --port 8000
   ```

5. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## Configuration

All configuration is managed via environment variables. See `.env.example` for available options.

### Key Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `HOST` | Server host address | `127.0.0.1` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `true` |
| `CORS_ORIGINS` | Allowed CORS origins | `http://localhost:3000,...` |
| `SECRET_KEY` | JWT signing key | (must set in production) |

## API Endpoints

### Health & Status

- `GET /` - Basic health check
- `GET /health` - Detailed health information

### Authentication (Coming Soon)

- `POST /api/auth/login` - Authenticate and get access token
- `POST /api/auth/verify` - Verify access token
- `POST /api/auth/refresh` - Refresh access token

### Tasks (Coming Soon)

- `GET /api/tasks` - List all tasks
- `POST /api/tasks` - Create a new task
- `GET /api/tasks/{task_id}` - Get task details
- `PUT /api/tasks/{task_id}` - Update task
- `DELETE /api/tasks/{task_id}` - Delete task

### Specs (Coming Soon)

- `GET /api/specs` - List all specs
- `POST /api/specs` - Create a new spec
- `GET /api/specs/{spec_id}` - Get spec details

### Agents (Coming Soon)

- `POST /api/agents/run` - Start agent execution
- `GET /api/agents/status/{session_id}` - Get agent status

### WebSocket (Coming Soon)

- `WS /ws/agent/{session_id}` - Real-time agent progress updates

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/test_main.py
```

### Code Quality

```bash
# Format code
black .

# Lint code
ruff check .

# Type checking
mypy .
```

### Project Structure

```
apps/web-backend/
├── main.py                 # FastAPI application entry point
├── core/
│   ├── config.py          # Configuration management
│   └── security.py        # Authentication & security (coming soon)
├── api/
│   ├── routes/            # API route handlers
│   │   ├── auth.py        # Authentication endpoints
│   │   ├── tasks.py       # Task management endpoints
│   │   ├── specs.py       # Spec management endpoints
│   │   └── agents.py      # Agent execution endpoints
│   ├── models/            # Pydantic models
│   └── websocket.py       # WebSocket handlers
├── services/              # Business logic
│   └── agent_runner.py    # Agent execution service
├── tests/                 # Test suite
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variable template
└── README.md             # This file
```

## Security Considerations

### Production Deployment

1. **Set a strong SECRET_KEY:**
   ```bash
   openssl rand -hex 32
   ```

2. **Disable DEBUG mode:**
   ```bash
   DEBUG=false
   ```

3. **Restrict CORS origins:**
   ```bash
   CORS_ORIGINS=https://your-frontend-domain.com
   ```

4. **Use HTTPS:**
   - Deploy behind a reverse proxy (nginx, Caddy)
   - Configure SSL/TLS certificates

5. **Implement rate limiting:**
   - Consider using middleware like slowapi
   - Protect against brute force and DoS attacks

6. **Authentication:**
   - Validate all JWT tokens
   - Implement proper token refresh logic
   - Consider session management

## Troubleshooting

### Port already in use

```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill the process or use a different port
PORT=8001 python main.py
```

### CORS errors in browser

- Ensure frontend origin is in `CORS_ORIGINS` environment variable
- Check that credentials are allowed if sending cookies
- Verify preflight OPTIONS requests are handled correctly

### Cannot connect to Auto Claude backend

- Verify `AUTO_CLAUDE_BACKEND_DIR` points to correct location
- Ensure Auto Claude backend is properly installed
- Check that backend dependencies are available

## Contributing

When contributing to the web backend:

1. Follow FastAPI best practices
2. Write tests for new endpoints
3. Update API documentation
4. Follow the existing code style (black, ruff)
5. Test CORS behavior with actual frontend

## License

Part of the Auto Claude project. See root LICENSE file for details.
