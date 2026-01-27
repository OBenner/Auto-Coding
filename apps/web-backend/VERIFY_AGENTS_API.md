# Agent Execution API Verification

This document describes how to verify the agent execution API endpoints.

## Prerequisites

1. Install dependencies:
```bash
cd apps/web-backend
pip install -r requirements.txt
```

2. Create `.env` file (or set environment variables):
```bash
DEBUG=true
SECRET_KEY=dev-secret-key-for-testing-only
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
```

3. Start the server:
```bash
python main.py
```

## Test Endpoints

### 1. Health Check
```bash
curl http://localhost:8000/api/agents/health
```

Expected response:
```json
{
  "status": "ok",
  "endpoint": "agents",
  "project_dir": "/path/to/project"
}
```

### 2. Start Agent (Planner)
```bash
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{
    "spec_id": "001",
    "agent_type": "planner",
    "model": "claude-sonnet-4-5-20250929",
    "verbose": false
  }'
```

Expected response (202 Accepted):
```json
{
  "task_id": "001:planner",
  "spec_id": "001",
  "agent_type": "planner",
  "status": "started",
  "message": "Agent task started: planner for spec 001"
}
```

### 3. Check Agent Status
```bash
curl http://localhost:8000/api/agents/status/001:planner
```

Expected response (while running):
```json
{
  "task_id": "001:planner",
  "status": "running",
  "result": null,
  "error": null
}
```

Expected response (completed):
```json
{
  "task_id": "001:planner",
  "status": "completed",
  "result": {
    "success": true,
    "agent_type": "planner",
    "spec_id": "001",
    "message": "Planner execution completed"
  },
  "error": null
}
```

### 4. Cancel Agent
```bash
curl -X POST http://localhost:8000/api/agents/cancel/001:planner
```

Expected response:
```json
{
  "task_id": "001:planner",
  "cancelled": true,
  "message": "Task cancelled: 001:planner"
}
```

## API Endpoints Summary

| Method | Endpoint | Description | Status Code |
|--------|----------|-------------|-------------|
| POST | `/api/agents/run` | Start an agent task | 202 |
| GET | `/api/agents/status/{task_id}` | Get task status | 200 |
| POST | `/api/agents/cancel/{task_id}` | Cancel a task | 200 |
| GET | `/api/agents/health` | Health check | 200 |

## Agent Types

Supported agent types:
- `planner` - Creates implementation plan
- `coder` - Implements subtasks
- `qa_reviewer` - Reviews and validates work
- `qa_fixer` - Fixes QA-reported issues

## Error Responses

### 400 Bad Request
Invalid request parameters (e.g., invalid agent_type)

### 404 Not Found
Spec not found or task not found

### 409 Conflict
Task already running for the spec

### 500 Internal Server Error
Server error during agent execution
