# WebSocket Endpoint Testing Guide

## Overview

The WebSocket endpoint provides real-time agent progress updates to connected clients. This guide explains how to test the WebSocket functionality.

## Endpoint

```
ws://localhost:8000/ws/agent-events
```

## Server-Side Implementation

The WebSocket server is implemented using FastAPI's built-in WebSocket support (via the `websockets` package, already in `requirements.txt`). The implementation includes:

- **Connection Manager** - Manages client connections and subscriptions
- **Event Broadcasting** - Broadcasts events to subscribed clients
- **Event Models** - Pydantic models for structured event data

### Files Created

- `api/websocket.py` - WebSocket endpoint and connection manager
- `api/models/agent_event.py` - Event models (ExecutionEvent, LogEvent, ErrorEvent, etc.)
- `main.py` - Updated to include WebSocket router

## Testing the WebSocket Endpoint

### Option 1: Browser Console (Simplest)

1. Start the backend server:
   ```bash
   cd apps/web-backend
   python -m uvicorn main:app --reload
   ```

2. Open browser console (F12) and run:
   ```javascript
   const ws = new WebSocket("ws://localhost:8000/ws/agent-events");

   ws.onopen = () => {
     console.log("Connected!");
     ws.send(JSON.stringify({action: "subscribe", spec_id: "001"}));
   };

   ws.onmessage = (event) => {
     console.log("Received:", JSON.parse(event.data));
   };

   ws.onerror = (error) => {
     console.error("WebSocket error:", error);
   };
   ```

### Option 2: Python websocket-client

If you want to test from Python, install the websocket-client package:

```bash
pip install websocket-client
```

Then create a test script:

```python
import websocket
import json

def on_message(ws, message):
    data = json.loads(message)
    print(f"Received: {data}")

def on_open(ws):
    print("Connected!")
    ws.send(json.dumps({"action": "subscribe", "spec_id": "001"}))

def on_error(ws, error):
    print(f"Error: {error}")

ws = websocket.WebSocketApp(
    "ws://localhost:8000/ws/agent-events",
    on_open=on_open,
    on_message=on_message,
    on_error=on_error
)

ws.run_forever()
```

### Option 3: curl (wscat)

Install wscat:
```bash
npm install -g wscat
```

Connect and test:
```bash
wscat -c ws://localhost:8000/ws/agent-events

# Send subscription:
{"action": "subscribe", "spec_id": "001"}

# Send ping:
{"action": "ping"}
```

## Protocol

### Client → Server Messages

**Subscribe to spec updates:**
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

**Ping (keep-alive):**
```json
{
  "action": "ping"
}
```

### Server → Client Messages

**Subscription confirmation:**
```json
{
  "status": "subscribed",
  "spec_id": "001",
  "timestamp": "2024-01-26T12:00:00Z"
}
```

**Execution progress event:**
```json
{
  "event_type": "execution",
  "spec_id": "001",
  "timestamp": "2024-01-26T12:00:00Z",
  "data": {
    "phase": "coding",
    "phase_progress": 45.5,
    "overall_progress": 30.2,
    "message": "Working on subtask 3/10...",
    "current_subtask": "subtask-1-3"
  }
}
```

**Log event:**
```json
{
  "event_type": "log",
  "spec_id": "001",
  "timestamp": "2024-01-26T12:00:00Z",
  "log_line": "Installing dependencies...",
  "level": "info"
}
```

**Error event:**
```json
{
  "event_type": "error",
  "spec_id": "001",
  "timestamp": "2024-01-26T12:00:00Z",
  "error_message": "Failed to compile code",
  "error_type": "compilation_error",
  "traceback": "..."
}
```

## Event Types

The WebSocket endpoint supports these event types:

- **execution** - Agent execution progress (planning, coding, qa_review, qa_fixing, complete, failed)
- **ideation** - Ideation/spec creation progress (analyzing, discovering, generating, complete)
- **roadmap** - Roadmap generation progress
- **log** - Raw log messages from agent execution
- **error** - Error events with details

## Broadcasting Events from Agent Code

To send events from agent execution code, use the helper functions:

```python
from api.websocket import broadcast_execution_event, broadcast_log_event, broadcast_error_event

# Send execution progress
await broadcast_execution_event(
    spec_id="001",
    phase="coding",
    phase_progress=45.5,
    overall_progress=30.2,
    message="Working on subtask 3/10...",
    current_subtask="subtask-1-3"
)

# Send log message
await broadcast_log_event(
    spec_id="001",
    log_line="Installing dependencies...",
    level="info"
)

# Send error
await broadcast_error_event(
    spec_id="001",
    error_message="Failed to compile code",
    error_type="compilation_error"
)
```

## Integration with Frontend

The frontend `agent-events.ts` parser will receive these WebSocket events and update the UI in real-time. The event structure matches the expectations of the `AgentEvents` class in the Electron app.

## Notes

- The `websockets` package (v14.1) is already in `requirements.txt` - no additional dependencies needed for the server
- The `websocket-client` package is only needed for testing from Python clients
- Browser clients use the native WebSocket API (no additional packages needed)
- The verification command in the implementation plan checks for websocket-client, which is optional for testing
