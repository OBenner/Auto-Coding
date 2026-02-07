#!/bin/bash
# Kill old server and start new one for testing

cd apps/web-backend

# Kill any existing server processes
echo "[*] Stopping any existing server processes..."
pkill -f "python.*main.py" 2>/dev/null || true
sleep 1

# Start new server
echo "[*] Starting new web-backend service..."
python main.py > /tmp/web-backend-test2.log 2>&1 &
SERVER_PID=$!
echo "[*] Server PID: $SERVER_PID"

# Wait for server to be ready
echo "[*] Waiting for server to be ready..."
for i in {1..15}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "[✓] Server is ready"
        break
    fi
    if [ $i -eq 15 ]; then
        echo "[✗] Server failed to start"
        cat /tmp/web-backend-test2.log
        exit 1
    fi
    sleep 1
done

# Run WebSocket test
echo ""
echo "[*] Running WebSocket connectivity test..."
python test_websocket_simple.py
TEST_RESULT=$?

# Cleanup
echo ""
echo "[*] Cleaning up..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

exit $TEST_RESULT
