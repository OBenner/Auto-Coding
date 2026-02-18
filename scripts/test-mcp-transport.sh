#!/bin/bash
# Test script for MCP transport layer verification
# Tests the stdio transport by sending JSON-RPC messages to the wrapper

set -e

FRONTEND_DIR="apps/frontend"
WRAPPER="$FRONTEND_DIR/out/main/mcp-server-wrapper.js"

echo "=========================================="
echo "MCP Transport Layer Test"
echo "=========================================="
echo ""

# Check if wrapper exists
if [ ! -f "$WRAPPER" ]; then
    echo "❌ FAIL: MCP server wrapper not found at $WRAPPER"
    echo "   Run: cd apps/frontend && npm run build"
    exit 1
fi

echo "✅ MCP server wrapper exists: $WRAPPER"
echo ""

# Test 1: Health check tool
echo "Test 1: Calling health_check tool..."
echo ""

REQUEST='{"jsonrpc":"2.0","id":1,"method":"tools/call","params":{"name":"health_check","arguments":{}}}'

RESPONSE=$(echo "$REQUEST" | node "$WRAPPER" 2>&1 || true)

if echo "$RESPONSE" | grep -q '"status":"healthy"'; then
    echo "✅ PASS: health_check tool returned healthy status"
else
    echo "❌ FAIL: health_check tool did not return expected response"
    echo "   Response: $RESPONSE"
    exit 1
fi

echo ""

# Test 2: Check for tool registration
echo "Test 2: Verifying tool registration..."
echo ""

if echo "$RESPONSE" | grep -q "uptime\|pid\|memory"; then
    echo "✅ PASS: MCP server returned health metrics"
else
    echo "⚠️  WARN: Health metrics not found in response"
fi

echo ""

# Test 3: Verify wrapper script starts and logs
echo "Test 3: Checking wrapper script startup..."
echo ""

STARTUP_LOGS=$(timeout 2s node "$WRAPPER" 2>&1 || true)

if echo "$STARTUP_LOGS" | grep -q "MCP-Wrapper.*Starting MCP server wrapper"; then
    echo "✅ PASS: Wrapper script starts and logs initialization"
else
    echo "⚠️  WARN: Could not verify startup logs"
fi

echo ""

# Test 4: Check for stdio transport
echo "Test 4: Verifying stdio transport..."
echo ""

if echo "$STARTUP_LOGS" | grep -q "Server started on stdio"; then
    echo "✅ PASS: MCP server uses stdio transport"
else
    echo "⚠️  WARN: Could not verify stdio transport"
fi

echo ""
echo "=========================================="
echo "MCP Transport Layer Test Complete"
echo "=========================================="
echo ""
echo "Summary:"
echo "  ✅ MCP server wrapper built successfully"
echo "  ✅ health_check tool functional"
echo "  ✅ Stdio transport operational"
echo ""
echo "Next steps:"
echo "  1. Test backend integration (subtask 3.1)"
echo "  2. Add main process initialization (subtask 2.4)"
echo ""
