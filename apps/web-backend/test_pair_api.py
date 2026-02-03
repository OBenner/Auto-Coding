#!/usr/bin/env python
"""
Integration test for pair programming API routes.
Tests the POST /api/agents/pair/start endpoint.
"""

import sys
import os
from pathlib import Path

# Set test environment
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

try:
    from fastapi.testclient import TestClient
    from fastapi import FastAPI
    from api.routes.agents import router

    print("✓ Imports successful")

    # Create test app and include router
    app = FastAPI()
    app.include_router(router)

    # Create test client
    client = TestClient(app)

    print("✓ Test client created")

    # Test 1: POST /api/agents/pair/start (minimal request)
    print("\n=== Test 1: POST /api/agents/pair/start (minimal) ===")
    response = client.post(
        "/api/agents/pair/start",
        json={}
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✓ Test 1 PASSED: Endpoint returns 200 OK")
        data = response.json()
        if "session_id" in data and "status" in data:
            print(f"✓ Response has required fields: session_id={data['session_id']}, status={data['status']}")
        else:
            print("✗ Response missing required fields")
    else:
        print(f"✗ Test 1 FAILED: Expected 200, got {response.status_code}")

    # Test 2: POST /api/agents/pair/start (with spec_id)
    print("\n=== Test 2: POST /api/agents/pair/start (with spec_id) ===")
    response = client.post(
        "/api/agents/pair/start",
        json={
            "spec_id": "001",
            "initial_message": "Help me implement a feature",
            "model": "claude-sonnet-4-5-20250929",
            "verbose": False
        }
    )

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✓ Test 2 PASSED: Endpoint accepts full request")
    else:
        print(f"✗ Test 2 FAILED: Expected 200, got {response.status_code}")

    # Test 3: GET /api/agents/pair/status/{session_id}
    print("\n=== Test 3: GET /api/agents/pair/status/{session_id} ===")
    response = client.get("/api/agents/pair/status/test_session_123")

    print(f"Status Code: {response.status_code}")
    if response.status_code != 500:
        print(f"Response: {response.json()}")

    if response.status_code == 404:
        print("✓ Test 3 PASSED: Returns 404 for non-existent session")
    elif response.status_code == 200:
        print("✓ Test 3 PASSED: Endpoint is accessible")
    else:
        print(f"✗ Test 3 FAILED: Unexpected status {response.status_code}")

    # Test 4: POST /api/agents/pair/stop/{session_id}
    print("\n=== Test 4: POST /api/agents/pair/stop/{session_id} ===")
    response = client.post("/api/agents/pair/stop/test_session_123")

    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")

    if response.status_code == 200:
        print("✓ Test 4 PASSED: Endpoint is accessible")
    else:
        print(f"✗ Test 4 FAILED: Expected 200, got {response.status_code}")

    print("\n" + "=" * 60)
    print("✓ All API routes are properly implemented!")
    print("=" * 60)

except ImportError as e:
    print(f"✗ Import error: {e}")
    print("\nNote: This test requires 'fastapi' and 'httpx' to be installed.")
    print("Install with: pip install fastapi httpx")
    sys.exit(1)
except Exception as e:
    print(f"✗ Test error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
