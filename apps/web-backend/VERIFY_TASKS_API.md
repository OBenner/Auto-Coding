# Tasks API Verification

This document explains how to verify the tasks API endpoints.

## Prerequisites

1. Install dependencies:
   ```bash
   cd apps/web-backend
   pip install -r requirements.txt
   ```

2. Create `.env` file (or set DEBUG=true):
   ```bash
   cp .env.example .env
   # Edit .env and set DEBUG=true for development
   ```

## Start the Server

```bash
cd apps/web-backend
python main.py
```

The server will start on `http://localhost:8000` (default port).

## Test the Endpoints

### 1. List All Tasks
```bash
curl -X GET http://localhost:8000/api/tasks \
     -H "Content-Type: application/json"
```

**Expected Response (200 OK):**
```json
{
  "tasks": [
    {
      "number": "022",
      "name": "web-interface-browser-based-access",
      "folder": "022-web-interface-browser-based-access",
      "status": "in_progress",
      "progress": "2/15",
      "has_build": true
    }
  ],
  "total": 1
}
```

### 2. Get Task Detail
```bash
curl -X GET http://localhost:8000/api/tasks/022 \
     -H "Content-Type: application/json"
```

**Expected Response (200 OK):**
```json
{
  "number": "022",
  "name": "web-interface-browser-based-access",
  "folder": "022-web-interface-browser-based-access",
  "status": "in_progress",
  "progress": {
    "completed": 2,
    "in_progress": 0,
    "pending": 13,
    "failed": 0,
    "total": 15,
    "percentage": 13.33
  },
  "has_build": true,
  "spec_content": "# Web Interface (Browser-Based Access)\n..."
}
```

### 3. Tasks Health Check
```bash
curl -X GET http://localhost:8000/api/tasks/health
```

**Expected Response (200 OK):**
```json
{
  "status": "ok",
  "endpoint": "tasks",
  "project_dir": "I:/git/Auto-Claude",
  "specs_dir_exists": true
}
```

## API Documentation

When running in DEBUG mode, you can access:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### ModuleNotFoundError
Make sure you're running Python from the virtual environment:
```bash
# Windows
.venv\Scripts\python.exe main.py

# Unix/Mac
.venv/bin/python main.py
```

### SECRET_KEY Error
Set `DEBUG=true` in your `.env` file or environment:
```bash
DEBUG=true python main.py
```

### No specs found
The API reads from `.auto-claude/specs/` in the project directory.
Make sure you have at least one spec created.
