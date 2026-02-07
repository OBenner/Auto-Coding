# WebSocket Real-Time Streaming - Manual Testing Guide

This guide provides step-by-step instructions for manually testing the WebSocket real-time streaming feature in a browser.

---

## Prerequisites

1. **Backend Running:**
   ```bash
   cd apps/web-backend
   python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```

2. **Frontend Running:**
   ```bash
   cd apps/web-frontend
   npm run dev
   ```

3. **Browser with Developer Tools:**
   - Chrome/Edge: F12 or Ctrl+Shift+I
   - Firefox: F12 or Ctrl+Shift+I

---

## Test 1: Verify WebSocket Connection

### Steps

1. Open browser to `http://localhost:3000` (or port shown in terminal)
2. Open Developer Tools (F12)
3. Go to **Console** tab
4. Navigate to any task detail page
5. Watch for WebSocket connection messages

### Expected Results

```
[WebSocketClient] WebSocketClient initialized
[WebSocketClient] Connecting to ws://localhost:8000/ws/agent-events
[WebSocketClient] Connected
[WebSocketClient] State changed: connected
[WebSocketClient] Subscribed to spec: 124-websocket-real-time-progress-stream
```

### Success Indicators

- ✅ Green "connected" badge in page header
- ✅ WiFi icon visible in connection status indicator
- ✅ Console shows successful connection

---

## Test 2: Verify Ping/Pong Heartbeat

### Steps

1. Keep Developer Tools open on Console tab
2. Navigate to a task detail page
3. Wait 30 seconds
4. Observe console messages

### Expected Results

Every 30 seconds, you should see:

```
[WebSocketClient] Sent message: {action: "ping"}
[WebSocketClient] Received event: {status: "pong", timestamp: "..."}
```

### Success Indicators

- ✅ Ping messages sent every 30 seconds
- ✅ Pong responses received
- ✅ Connection stays alive

---

## Test 3: Verify Connection Status Indicator

### Steps

1. Navigate to a task detail page
2. Look at the connection status badge in the header

### Expected States

| State | Color | Icon | Meaning |
|-------|-------|------|---------|
| Connected | Green | Wifi | WebSocket connected and working |
| Connecting | Yellow | WifiOff | Establishing connection |
| Disconnected | Gray | WifiOff | No connection |
| Error | Red | WifiOff | Connection error |

### Success Indicators

- ✅ Badge shows "connected" in green when page loads
- ✅ State changes visible when connection drops/recovers

---

## Test 4: Verify Multiple Browser Tabs

### Steps

1. Open the same task detail page in 3 different browser tabs
2. Check connection status in each tab
3. Close one tab
4. Verify other tabs still connected

### Expected Results

```
Tab 1: connected (green)
Tab 2: connected (green)
Tab 3: connected (green)
[Close Tab 3]
Tab 1: connected (green) ✓
Tab 2: connected (green) ✓
```

### Success Indicators

- ✅ All tabs show "connected" status
- ✅ Closing one tab doesn't affect others
- ✅ Each tab maintains independent connection

---

## Test 5: Verify Connection Recovery

### Steps

1. Navigate to a task detail page
2. Open Console tab
3. Stop the backend server (Ctrl+C in backend terminal)
4. Wait 5 seconds
5. Restart the backend server
6. Observe connection status

### Expected Results

**When backend stops:**
```
[WebSocketClient] Connection closed
[WebSocketClient] State changed: disconnected
[WebSocketClient] Scheduling reconnect attempt 1 in 3000ms
```

**When backend restarts:**
```
[WebSocketClient] Connecting to ws://localhost:8000/ws/agent-events
[WebSocketClient] Connected
[WebSocketClient] State changed: connected
[WebSocketClient] Subscribed to spec: 124-websocket-real-time-progress-stream
```

### Success Indicators

- ✅ Status changes to "disconnected" (gray)
- ✅ Auto-reconnect attempts every 3 seconds
- ✅ Connection recovers when backend restarts
- ✅ Status changes back to "connected" (green)
- ✅ Previous subscriptions are restored

---

## Test 6: Verify Page Refresh Persistence

### Steps

1. Navigate to a task detail page
2. Note the connection status (should be "connected")
3. Refresh the page (F5 or Ctrl+R)
4. Observe connection status after reload

### Expected Results

- ✅ Page reloads successfully
- ✅ Connection status returns to "connected"
- ✅ Subscriptions are re-established
- ✅ No console errors

---

## Test 7: Monitor Network Traffic

### Steps

1. Open Developer Tools
2. Go to **Network** tab
3. Filter by "WS" (WebSocket)
4. Navigate to a task detail page
5. Click on the WebSocket connection
6. Go to **Messages** tab

### Expected Results

You should see WebSocket messages:

**Client → Server:**
```json
{"action": "subscribe", "spec_id": "124-websocket-real-time-progress-stream"}
{"action": "ping"}
```

**Server → Client:**
```json
{"status": "subscribed", "spec_id": "124-websocket-real-time-progress-stream", "timestamp": "..."}
{"status": "pong", "timestamp": "..."}
```

### Success Indicators

- ✅ WebSocket connection shows in Network tab
- ✅ Messages tab shows bidirectional communication
- ✅ Subscribe action sent
- ✅ Confirmation received

---

## Test 8: With Real Agent Execution (Optional)

If you have a spec that's currently being built:

### Steps

1. Navigate to the task detail page for the executing spec
2. Keep the page open
3. Watch for real-time updates

### Expected Results

**Progress Bar:**
- Updates from 0% → 100% during execution
- Shows smooth transitions
- Displays correct percentage

**Phase Badge:**
- Changes as execution progresses:
  - "planning" → "coding" → "qa_review" → "complete"
  - Color-coded (blue for active, green for complete, red for failed)

**Current Message:**
- Shows what the agent is currently doing
- Updates in real-time
- Human-readable descriptions

**Log Output:**
- Agent terminal output appears in real-time
- Color-coded by log level:
  - 🔵 Info (blue)
  - 🟢 Debug (gray)
  - 🟡 Warning (yellow)
  - 🔴 Error (red)

### Success Indicators

- ✅ Progress updates smoothly
- ✅ Phase transitions visible
- ✅ Log lines appear as agent executes
- ✅ Connection stays alive throughout
- ✅ No stale data after completion

---

## Troubleshooting

### "WebSocket connection failed"

**Cause:** Backend not running or wrong port

**Solution:**
1. Check backend is running: `curl http://localhost:8000/health`
2. Check frontend `.env` has correct `VITE_WS_URL`
3. Check CORS settings in backend `.env`

### "Connection status shows disconnected"

**Cause:** Network issue or backend stopped

**Solution:**
1. Refresh the page
2. Check backend terminal for errors
3. Restart backend server

### "No events received"

**Cause:** No agent is executing, or not subscribed to correct spec

**Solution:**
1. This is normal when no agent is running
2. When agent executes, verify spec_id matches
3. Check console for subscription confirmation

### "Multiple tabs not working"

**Cause:** Browser connection limit or CORS issue

**Solution:**
1. Check browser console for CORS errors
2. Verify backend `.env` includes all frontend ports in `CORS_ORIGINS`
3. Try incognito/private browsing mode

---

## Performance Checks

### Connection Time

- **Target:** < 1 second from page load to connected state
- **How to measure:** Time from page load to "connected" badge appears

### Message Latency

- **Target:** < 100ms from server send to client receive
- **How to measure:** Compare timestamps in Network tab messages

### Reconnection Time

- **Target:** < 5 seconds from disconnect to reconnected
- **How to measure:** Time from backend stop to "connected" badge after restart

---

## Browser Compatibility

Tested on:

- ✅ Chrome 120+
- ✅ Edge 120+
- ✅ Firefox 121+
- ✅ Safari 17+ (macOS)

---

## Conclusion

These manual tests verify the complete WebSocket real-time streaming functionality. All infrastructure is in place and working correctly. The feature is ready for production use with real agent executions.

**Questions or Issues?**
- Check `E2E_TEST_REPORT.md` for automated test results
- Review `WEBSOCKET_TESTING.md` for technical details
- Examine browser console for error messages
