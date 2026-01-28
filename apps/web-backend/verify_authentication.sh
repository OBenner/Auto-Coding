#!/bin/bash
# Authentication Verification Script for Auto Claude Web Backend
# This script verifies that API authentication is working correctly

set -e

echo "=========================================="
echo "Auto Claude Web Backend Authentication Verification"
echo "=========================================="
echo ""

# Check if server is running
echo "Step 1: Checking if server is running on http://localhost:8000..."
if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo "✓ Server is running"
else
    echo "✗ Server is NOT running"
    echo ""
    echo "Please start the server first:"
    echo "  cd apps/web-backend"
    echo "  python -m uvicorn main:app --host localhost --port 8000"
    exit 1
fi
echo ""

# Test 1: Request without authentication should return 401
echo "Test 1: Request without authentication (should return 401)..."
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/tasks)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "401" ]; then
    echo "✓ Test 1 PASSED: Got 401 Unauthorized as expected"
else
    echo "✗ Test 1 FAILED: Expected 401, got $HTTP_CODE"
    echo "Response: $(echo "$RESPONSE" | head -n-1)"
fi
echo ""

# Test 2: Request with invalid token should return 401
echo "Test 2: Request with invalid token (should return 401)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer invalid" http://localhost:8000/api/tasks)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "401" ]; then
    echo "✓ Test 2 PASSED: Got 401 Unauthorized for invalid token"
else
    echo "✗ Test 2 FAILED: Expected 401, got $HTTP_CODE"
    echo "Response: $(echo "$RESPONSE" | head -n-1)"
fi
echo ""

# Test 3: Get valid token from /api/auth/verify
echo "Test 3: Getting valid token from /api/auth/verify..."
TOKEN_RESPONSE=$(curl -s http://localhost:8000/api/auth/verify)
TOKEN=$(echo "$TOKEN_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])" 2>/dev/null || echo "")

if [ -z "$TOKEN" ]; then
    echo "✗ Test 3 FAILED: Could not extract token from response"
    echo "Response: $TOKEN_RESPONSE"
    exit 1
else
    echo "✓ Test 3 PASSED: Successfully obtained token"
    echo "Token (first 20 chars): ${TOKEN:0:20}..."
fi
echo ""

# Test 4: Request with valid token should return 200
echo "Test 4: Request with valid token (should return 200)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/tasks)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Test 4 PASSED: Got 200 OK with valid token"
    echo "Response preview: $(echo "$RESPONSE" | head -n-1 | head -c 100)..."
else
    echo "✗ Test 4 FAILED: Expected 200, got $HTTP_CODE"
    echo "Response: $(echo "$RESPONSE" | head -n-1)"
fi
echo ""

# Additional Test: Verify /api/specs endpoint also requires auth
echo "Additional Test 5: /api/specs without auth (should return 401)..."
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/api/specs)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "401" ]; then
    echo "✓ Test 5 PASSED: /api/specs requires authentication"
else
    echo "✗ Test 5 FAILED: Expected 401, got $HTTP_CODE"
fi
echo ""

# Additional Test: Verify /api/agents/run endpoint requires auth
echo "Additional Test 6: /api/agents/run without auth (should return 401)..."
RESPONSE=$(curl -s -w "\n%{http_code}" -X POST http://localhost:8000/api/agents/run -H "Content-Type: application/json" -d '{}')
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "401" ]; then
    echo "✓ Test 6 PASSED: /api/agents/run requires authentication"
else
    echo "✗ Test 6 FAILED: Expected 401, got $HTTP_CODE"
fi
echo ""

# Additional Test: Verify /health endpoint does NOT require auth
echo "Additional Test 7: /health without auth (should return 200)..."
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:8000/health)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ Test 7 PASSED: /health endpoint is public"
else
    echo "✗ Test 7 FAILED: Expected 200, got $HTTP_CODE"
fi
echo ""

echo "=========================================="
echo "Authentication Verification Complete"
echo "=========================================="
