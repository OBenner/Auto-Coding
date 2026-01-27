# WebSocket Real-Time Updates Test

Comprehensive testing guide for WebSocket real-time agent progress updates.

## Overview

This document provides multiple testing approaches for verifying that WebSocket real-time updates work correctly, from automated Python tests to manual browser testing.

## Prerequisites

- Backend server running on `http://localhost:8000`
- WebSocket endpoint available at `ws://localhost:8000/ws/agent-events`

## Test Approaches

### 1. Automated Python Test (Recommended)

**Install dependencies:**
```bash
cd apps/web-backend
pip install websockets  # or: python -m pip install websockets
```

**Run the test:**
```bash
python test_websocket_realtime.py
```

**Expected output:**
```
============================================================
WebSocket Real-Time Updates Test Suite
============================================================

[TEST] Test 1: WebSocket Connection
✓ Connected to WebSocket
✓ Sent ping message
✓ Received pong response

[TEST] Test 2: Spec ID Subscription
✓ Sent subscribe request for spec: test-001
✓ Successfully subscribed

[TEST] Test 3: Execution Progress Events
✓ Received 3 events
✓ Received 2 execution events
✓ First execution event has correct data
✓ Progress tracking works (progress increased)
✓ Received 1 log events

[TEST] Test 4: Unsubscribe Functionality
✓ Successfully unsubscribed
✓ No events received after unsubscribe (correct)

[TEST] Test 5: Multiple Clients
✓ Both clients received the event
✓ Both clients received identical event data

============================================================
Test Results Summary
============================================================

  PASS  WebSocket Connection
  PASS  Spec ID Subscription
  PASS  Execution Progress Events
  PASS  Unsubscribe Functionality
  PASS  Multiple Clients

Total: 5/5 tests passed

✓ All tests passed!
```

### 2. Browser-Based Test (Simple)

**Create test HTML file:**
```html
<!DOCTYPE html>
<html>
<head>
    <title>WebSocket Test</title>
    <style>
        body { font-family: monospace; padding: 20px; }
        #events { border: 1px solid #ccc; height: 400px; overflow-y: auto; padding: 10px; }
        .event { margin: 5px 0; padding: 5px; background: #f0f0f0; }
        .execution { background: #e3f2fd; }
        .log { background: #f3e5f5; }
        .error { background: #ffebee; }
        button { margin: 5px; padding: 10px; }
    </style>
</head>
<body>
    <h1>WebSocket Real-Time Updates Test</h1>
    <p>Status: <span id="status">Disconnected</span></p>

    <div>
        <button onclick="connect()">Connect</button>
        <button onclick="subscribe()">Subscribe to test-001</button>
        <button onclick="ping()">Ping</button>
        <button onclick="disconnect()">Disconnect</button>
        <button onclick="clearEvents()">Clear</button>
    </div>

    <h2>Received Events:</h2>
    <div id="events"></div>

    <script>
        let ws = null;
        const statusEl = document.getElementById('status');
        const eventsEl = document.getElementById('events');

        function connect() {
            ws = new WebSocket('ws://localhost:8000/ws/agent-events');

            ws.onopen = () => {
                statusEl.textContent = 'Connected';
                statusEl.style.color = 'green';
                addEvent('system', 'Connected to WebSocket');
            };

            ws.onclose = () => {
                statusEl.textContent = 'Disconnected';
                statusEl.style.color = 'red';
                addEvent('system', 'Disconnected from WebSocket');
            };

            ws.onerror = (error) => {
                addEvent('error', 'WebSocket error: ' + error);
            };

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const eventType = data.event_type || data.status || 'unknown';
                addEvent(eventType, JSON.stringify(data, null, 2));
            };
        }

        function disconnect() {
            if (ws) {
                ws.close();
                ws = null;
            }
        }

        function subscribe() {
            if (!ws) {
                alert('Connect first!');
                return;
            }
            ws.send(JSON.stringify({
                action: 'subscribe',
                spec_id: 'test-001'
            }));
            addEvent('system', 'Sent subscribe request');
        }

        function ping() {
            if (!ws) {
                alert('Connect first!');
                return;
            }
            ws.send(JSON.stringify({ action: 'ping' }));
            addEvent('system', 'Sent ping');
        }

        function clearEvents() {
            eventsEl.innerHTML = '';
        }

        function addEvent(type, message) {
            const div = document.createElement('div');
            div.className = 'event ' + type;
            div.innerHTML = `<strong>[${new Date().toLocaleTimeString()}] ${type}:</strong><br><pre>${message}</pre>`;
            eventsEl.appendChild(div);
            eventsEl.scrollTop = eventsEl.scrollHeight;
        }
    </script>
</body>
</html>
```

**Steps:**
1. Save the HTML to `websocket-test.html`
2. Open in browser (Chrome, Firefox, etc.)
3. Click "Connect" - should see "Connected to WebSocket"
4. Click "Subscribe to test-001" - should see subscription confirmation
5. Trigger agent events (see section 4 below)
6. Verify events appear in real-time

### 3. Command-Line Test with wscat

**Install wscat:**
```bash
npm install -g wscat
```

**Test connection:**
```bash
wscat -c ws://localhost:8000/ws/agent-events
```

**Send commands:**
```json
{"action": "ping"}
{"action": "subscribe", "spec_id": "test-001"}
{"action": "unsubscribe", "spec_id": "test-001"}
```

**Expected responses:**
```json
{"status": "pong", "timestamp": "2026-01-27T..."}
{"status": "subscribed", "spec_id": "test-001", "timestamp": "..."}
```

### 4. Triggering Test Events

To test that events are actually broadcast, you can:

**Option A: Python script to broadcast events**
```python
import asyncio
from datetime import datetime
from api.websocket import broadcast_execution_event, broadcast_log_event

async def test():
    # Broadcast execution event
    await broadcast_execution_event(
        spec_id="test-001",
        phase="planning",
        phase_progress=50.0,
        overall_progress=25.0,
        message="Creating plan"
    )

    # Broadcast log event
    await broadcast_log_event(
        spec_id="test-001",
        log_line="Test log message",
        level="info"
    )

asyncio.run(test())
```

**Option B: Start an actual agent task**
```bash
# Start backend server if not running
cd apps/web-backend
uvicorn main:app --reload

# In another terminal, trigger an agent task via API
curl -X POST http://localhost:8000/api/agents/run \
  -H "Content-Type: application/json" \
  -d '{"spec_id": "test-001", "agent_type": "planner"}'
```

### 5. Integration Test with Frontend

**Start both servers:**
```bash
# Terminal 1: Backend
cd apps/web-backend
uvicorn main:app --reload

# Terminal 2: Frontend
cd apps/web-frontend
npm run dev
```

**Test in browser:**
1. Open `http://localhost:3001`
2. Navigate to tasks page
3. Create or start a task
4. Watch for real-time updates in the UI
5. Check browser console for WebSocket messages

**Expected behavior:**
- WebSocket connects automatically on page load
- When task starts, progress bar updates in real-time
- Log messages appear as they're generated
- Phase transitions update immediately
- No polling delays - instant updates

## Verification Checklist

### ✓ WebSocket Connection
- [ ] Client can connect to `ws://localhost:8000/ws/agent-events`
- [ ] Connection stays open (no immediate disconnects)
- [ ] Ping/pong works correctly

### ✓ Subscription Management
- [ ] Can subscribe to a spec ID
- [ ] Receives subscription confirmation
- [ ] Can unsubscribe from a spec ID
- [ ] Receives unsubscribe confirmation
- [ ] Events only sent to subscribed clients

### ✓ Event Broadcasting
- [ ] Execution events received with correct structure
- [ ] Log events received with correct structure
- [ ] Error events received with correct structure
- [ ] Events contain proper timestamps
- [ ] Events contain correct spec_id

### ✓ Real-Time Updates
- [ ] Events arrive immediately (< 100ms latency)
- [ ] No polling required
- [ ] Progress updates show incrementally
- [ ] Multiple clients receive same events
- [ ] No missed events

### ✓ Error Handling
- [ ] Invalid JSON rejected gracefully
- [ ] Unknown actions handled with error message
- [ ] Missing spec_id handled properly
- [ ] Disconnected clients cleaned up automatically
- [ ] Server doesn't crash on client disconnect

## Event Schemas

### Execution Event
```json
{
  "event_type": "execution",
  "timestamp": "2026-01-27T12:00:00.000Z",
  "spec_id": "test-001",
  "data": {
    "phase": "planning",
    "phase_progress": 50.0,
    "overall_progress": 25.0,
    "message": "Creating implementation plan",
    "current_subtask": "subtask-1-1"
  }
}
```

### Log Event
```json
{
  "event_type": "log",
  "timestamp": "2026-01-27T12:00:00.000Z",
  "spec_id": "test-001",
  "log_line": "Starting planner agent...",
  "level": "info",
  "data": null
}
```

### Error Event
```json
{
  "event_type": "error",
  "timestamp": "2026-01-27T12:00:00.000Z",
  "spec_id": "test-001",
  "error_message": "Something went wrong",
  "error_type": "RuntimeError",
  "traceback": "Traceback...",
  "data": null
}
```

## Troubleshooting

### WebSocket connection fails
- Check backend server is running on port 8000
- Verify firewall not blocking WebSocket connections
- Check browser console for CORS errors
- Try `ws://` instead of `wss://` for local testing

### No events received
- Verify you subscribed to the correct spec_id
- Check that events are actually being broadcast
- Look for disconnection messages in server logs
- Verify spec_id matches exactly (case-sensitive)

### Events delayed or missing
- Check network tab for WebSocket frame timing
- Verify server not under heavy load
- Check for any buffering in proxy/nginx
- Look for errors in server logs

## Performance Benchmarks

Expected performance characteristics:

- **Connection time:** < 50ms
- **Event latency:** < 100ms (from broadcast to client receive)
- **Concurrent clients:** 100+ supported
- **Events per second:** 1000+ supported
- **Memory per client:** < 1MB

## Conclusion

This test suite verifies that:
1. WebSocket connections work reliably
2. Subscription management functions correctly
3. Events are broadcast in real-time
4. Multiple clients can receive events simultaneously
5. The system handles errors gracefully

All verification steps from the implementation plan are covered.
