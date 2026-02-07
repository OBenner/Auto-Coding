#!/bin/bash
# Start web-backend service and test WebSocket connectivity

cd apps/web-backend

# Start server in background
echo "[*] Starting web-backend service..."
python main.py > /tmp/web-backend-test.log 2>&1 &
SERVER_PID=$!
echo "[*] Server PID: $SERVER_PID"

# Wait for server to start
echo "[*] Waiting for server to be ready..."
for i in {1..10}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "[✓] Server is ready"
        break
    fi
    if [ $i -eq 10 ]; then
        echo "[✗] Server failed to start"
        cat /tmp/web-backend-test.log
        exit 1
    fi
    sleep 1
done

# Run WebSocket test
echo ""
echo "[*] Running WebSocket connectivity test..."
python test_websocket_connection.py
TEST_RESULT=$?

# Cleanup
echo ""
echo "[*] Cleaning up..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

exit $TEST_RESULT
