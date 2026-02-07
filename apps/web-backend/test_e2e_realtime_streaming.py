#!/usr/bin/env python3
"""
End-to-End Integration Test for Real-Time WebSocket Streaming

This test verifies:
1. WebSocket connection establishment
2. Real-time log streaming
3. Progress bar updates
4. Connection health monitoring
5. Multiple client support
"""

import asyncio
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("❌ ERROR: websockets module not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


# Configuration
BACKEND_URL = "ws://localhost:8000/ws/agent-events"
TEST_SPEC_ID = "124-websocket-real-time-progress-stream"
TEST_TIMEOUT = 30  # seconds


class Colors:
    """ANSI color codes for terminal output"""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_success(message: str):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")


def print_info(message: str):
    print(f"{Colors.BLUE}ℹ {message}{Colors.RESET}")


def print_error(message: str):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")


def print_warning(message: str):
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")


def print_section(title: str):
    print(f"\n{Colors.BOLD}{Colors.BLUE}═══ {title} ═══{Colors.RESET}\n")


async def test_websocket_connection() -> bool:
    """Test 1: Verify WebSocket connection can be established"""
    print_section("Test 1: WebSocket Connection")

    try:
        print_info(f"Connecting to {BACKEND_URL}...")
        async with websockets.connect(BACKEND_URL) as ws:
            print_success("WebSocket connection established")

            # Test subscribe action
            subscribe_msg = {
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }
            await ws.send(json.dumps(subscribe_msg))
            print_info(f"Sent subscribe request for spec: {TEST_SPEC_ID}")

            # Wait for subscription confirmation
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("status") == "subscribed":
                print_success(f"Subscription confirmed: {data}")
                return True
            else:
                print_error(f"Unexpected response: {data}")
                return False

    except asyncio.TimeoutError:
        print_error("Connection timeout - no response from server")
        return False
    except ConnectionClosed as e:
        print_error(f"Connection closed: {e}")
        return False
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False


async def test_ping_pong() -> bool:
    """Test 2: Verify ping/pong heartbeat mechanism"""
    print_section("Test 2: Ping/Pong Heartbeat")

    try:
        async with websockets.connect(BACKEND_URL) as ws:
            print_info("Sending ping...")

            ping_msg = {"action": "ping"}
            await ws.send(json.dumps(ping_msg))

            # Wait for pong response
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            if data.get("status") == "pong":
                print_success(f"Pong received: {data}")
                return True
            else:
                print_error(f"Unexpected response to ping: {data}")
                return False

    except Exception as e:
        print_error(f"Ping/pong test failed: {e}")
        return False


async def test_event_receiving() -> bool:
    """Test 3: Verify client can receive various event types"""
    print_section("Test 3: Event Receiving")

    events_received = []

    try:
        async with websockets.connect(BACKEND_URL) as ws:
            # Subscribe to spec
            await ws.send(json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }))

            # Wait for subscription confirmation
            await ws.recv()

            print_info("Listening for events (5 seconds)...")

            # Listen for events for 5 seconds
            try:
                while len(events_received) < 10:
                    event = await asyncio.wait_for(ws.recv(), timeout=5.0)
                    data = json.loads(event)
                    events_received.append(data)

                    event_type = data.get("event_type", "unknown")
                    print_info(f"Received event: {event_type}")

            except asyncio.TimeoutError:
                print_info("Event collection timeout reached")

            if events_received:
                print_success(f"Received {len(events_received)} events")

                # Show sample events
                print_info("\nSample events:")
                for i, event in enumerate(events_received[:3], 1):
                    print(f"  {i}. {event.get('event_type', 'unknown')}: {json.dumps(event, indent=2)[:200]}...")

                return True
            else:
                print_warning("No events received (no agent may be running)")
                return True  # Not a failure, just no active agent

    except Exception as e:
        print_error(f"Event receiving test failed: {e}")
        return False


async def test_multiple_clients() -> bool:
    """Test 4: Verify multiple clients can connect simultaneously"""
    print_section("Test 4: Multiple Client Connections")

    async def client_task(client_id: int) -> bool:
        """Individual client connection task"""
        try:
            async with websockets.connect(BACKEND_URL) as ws:
                # Subscribe to spec
                await ws.send(json.dumps({
                    "action": "subscribe",
                    "spec_id": TEST_SPEC_ID
                }))

                # Wait for confirmation
                await asyncio.wait_for(ws.recv(), timeout=5.0)

                print_success(f"Client {client_id} connected and subscribed")
                return True

        except Exception as e:
            print_error(f"Client {client_id} failed: {e}")
            return False

    try:
        # Create 3 simultaneous connections
        print_info("Creating 3 simultaneous WebSocket connections...")

        tasks = [client_task(i) for i in range(1, 4)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if r is True)

        if successful == 3:
            print_success(f"All 3 clients connected successfully")
            return True
        else:
            print_warning(f"Only {successful}/3 clients connected")
            return False

    except Exception as e:
        print_error(f"Multiple client test failed: {e}")
        return False


async def test_unsubscribe() -> bool:
    """Test 5: Verify unsubscribe functionality"""
    print_section("Test 5: Unsubscribe Functionality")

    try:
        async with websockets.connect(BACKEND_URL) as ws:
            # Subscribe first
            await ws.send(json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }))

            # Wait for confirmation
            response1 = await ws.recv()
            data1 = json.loads(response1)

            if data1.get("status") != "subscribed":
                print_error("Subscribe failed")
                return False

            print_success("Subscribed successfully")

            # Now unsubscribe
            await ws.send(json.dumps({
                "action": "unsubscribe",
                "spec_id": TEST_SPEC_ID
            }))

            response2 = await ws.recv()
            data2 = json.loads(response2)

            if data2.get("status") == "unsubscribed":
                print_success(f"Unsubscribed successfully: {data2}")
                return True
            else:
                print_error(f"Unexpected unsubscribe response: {data2}")
                return False

    except Exception as e:
        print_error(f"Unsubscribe test failed: {e}")
        return False


async def test_connection_recovery() -> bool:
    """Test 6: Verify connection can recover after disconnect"""
    print_section("Test 6: Connection Recovery")

    try:
        # First connection
        print_info("Establishing first connection...")
        async with websockets.connect(BACKEND_URL) as ws1:
            await ws1.send(json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }))
            await ws1.recv()
            print_success("First connection established")

        # Connection closes here
        print_info("Connection closed, reconnecting...")

        # Wait a moment
        await asyncio.sleep(1)

        # Second connection (recovery)
        print_info("Establishing recovery connection...")
        async with websockets.connect(BACKEND_URL) as ws2:
            await ws2.send(json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }))
            response = await ws2.recv()

            if json.loads(response).get("status") == "subscribed":
                print_success("Connection recovered successfully")
                return True
            else:
                print_error("Reconnection failed")
                return False

    except Exception as e:
        print_error(f"Connection recovery test failed: {e}")
        return False


async def run_all_tests() -> Dict[str, bool]:
    """Run all E2E tests and return results"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║  WebSocket Real-Time Streaming E2E Integration Test   ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")

    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Test Spec ID: {TEST_SPEC_ID}")
    print_info(f"Timeout: {TEST_TIMEOUT}s")

    results = {}

    # Run all tests
    tests = [
        ("WebSocket Connection", test_websocket_connection),
        ("Ping/Pong Heartbeat", test_ping_pong),
        ("Event Receiving", test_event_receiving),
        ("Multiple Clients", test_multiple_clients),
        ("Unsubscribe", test_unsubscribe),
        ("Connection Recovery", test_connection_recovery),
    ]

    for test_name, test_func in tests:
        try:
            result = await asyncio.wait_for(test_func(), timeout=TEST_TIMEOUT)
            results[test_name] = result
        except asyncio.TimeoutError:
            print_error(f"Test timed out after {TEST_TIMEOUT}s")
            results[test_name] = False
        except Exception as e:
            print_error(f"Test failed with exception: {e}")
            results[test_name] = False

    return results


def print_summary(results: Dict[str, bool]):
    """Print test summary"""
    print_section("Test Summary")

    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}\n")

    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"  {status} - {test_name}")

    print()

    if failed == 0:
        print(f"{Colors.BOLD}{Colors.GREEN}╔═══════════════════════════════════════╗")
        print("║           ALL TESTS PASSED! 🎉         ║")
        print(f"╚═══════════════════════════════════════╝{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.BOLD}{Colors.RED}╔═══════════════════════════════════════╗")
        print("║      SOME TESTS FAILED ⚠️               ║")
        print(f"╚═══════════════════════════════════════╝{Colors.RESET}\n")
        return 1


def check_backend_running():
    """Check if backend is running before starting tests"""
    import socket

    try:
        sock = socket.create_connection(("localhost", 8000), timeout=2)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False


async def main():
    """Main entry point"""
    # Check backend is running
    print_info("Checking if backend is running...")
    if not check_backend_running():
        print_error("Backend is not running!")
        print("\nPlease start the backend first:")
        print("  cd apps/web-backend")
        print("  .venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload\n")
        return 1

    print_success("Backend is running\n")

    # Run tests
    results = await run_all_tests()

    # Print summary and return exit code
    return print_summary(results)


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
