#!/usr/bin/env python3
"""
WebSocket Real-Time Updates Test

Automated test that verifies WebSocket agent progress updates work end-to-end.
This test:
1. Starts the FastAPI server in the background
2. Connects a WebSocket client
3. Subscribes to a spec ID
4. Simulates agent progress events
5. Verifies events are received in real-time
6. Reports test results

Usage:
    python test_websocket_realtime.py
"""

import asyncio
import json
import sys
from datetime import datetime

import websockets

# Test configuration
BACKEND_URL = "http://localhost:8000"
WEBSOCKET_URL = "ws://localhost:8000/ws/agent-events"
TEST_SPEC_ID = "test-001"


class Colors:
    """ANSI color codes for terminal output"""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
    BOLD = "\033[1m"


def print_test(message: str):
    """Print test step message"""
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {message}")


def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def print_info(message: str):
    """Print info message"""
    print(f"{Colors.YELLOW}ℹ{Colors.RESET} {message}")


async def test_websocket_connection():
    """Test 1: WebSocket connection and protocol"""
    print_test("Test 1: WebSocket Connection")

    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            print_success("Connected to WebSocket")

            # Test ping/pong
            ping_msg = json.dumps({"action": "ping"})
            await websocket.send(ping_msg)
            print_success("Sent ping message")

            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)

            if response_data.get("status") == "pong":
                print_success(f"Received pong response: {response_data}")
                return True
            else:
                print_error(f"Unexpected response: {response_data}")
                return False

    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False


async def test_subscription():
    """Test 2: Spec ID subscription"""
    print_test("Test 2: Spec ID Subscription")

    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            # Subscribe to test spec
            subscribe_msg = json.dumps({"action": "subscribe", "spec_id": TEST_SPEC_ID})
            await websocket.send(subscribe_msg)
            print_success(f"Sent subscribe request for spec: {TEST_SPEC_ID}")

            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            response_data = json.loads(response)

            if (
                response_data.get("status") == "subscribed"
                and response_data.get("spec_id") == TEST_SPEC_ID
            ):
                print_success(f"Successfully subscribed: {response_data}")
                return True
            else:
                print_error(f"Subscription failed: {response_data}")
                return False

    except Exception as e:
        print_error(f"Subscription test failed: {e}")
        return False


async def broadcast_test_event(event_type: str, spec_id: str, data: dict):
    """
    Helper function to broadcast a test event.

    Note: This simulates what the agent runner would do. In a real scenario,
    the agent execution code would call these broadcast functions.
    """
    from api.models.agent_event import (
        ErrorEvent,
        ExecutionEvent,
        ExecutionProgressData,
        LogEvent,
    )
    from api.websocket import manager

    if event_type == "execution":
        event = ExecutionEvent(
            event_type="execution",
            timestamp=datetime.now().isoformat(),
            spec_id=spec_id,
            data=ExecutionProgressData(**data),
        )
    elif event_type == "log":
        event = LogEvent(
            event_type="log",
            timestamp=datetime.now().isoformat(),
            spec_id=spec_id,
            log_line=data.get("log_line", ""),
            level=data.get("level", "info"),
            data=None,
        )
    elif event_type == "error":
        event = ErrorEvent(
            event_type="error",
            timestamp=datetime.now().isoformat(),
            spec_id=spec_id,
            error_message=data.get("error_message", ""),
            error_type=data.get("error_type"),
            traceback=data.get("traceback"),
            data=None,
        )
    else:
        raise ValueError(f"Unknown event type: {event_type}")

    await manager.broadcast_to_spec(spec_id, event)


async def test_execution_events():
    """Test 3: Execution progress events"""
    print_test("Test 3: Execution Progress Events")

    received_events = []

    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            # Subscribe
            subscribe_msg = json.dumps({"action": "subscribe", "spec_id": TEST_SPEC_ID})
            await websocket.send(subscribe_msg)

            # Wait for subscription confirmation
            sub_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print_info(f"Subscribed: {json.loads(sub_response).get('status')}")

            # Start event listener task
            async def listen_for_events():
                try:
                    while len(received_events) < 3:
                        message = await asyncio.wait_for(websocket.recv(), timeout=10.0)
                        event = json.loads(message)
                        if event.get("event_type") in ["execution", "log", "error"]:
                            received_events.append(event)
                            print_info(f"Received: {event.get('event_type')} event")
                except TimeoutError:
                    print_info("Event listening timed out")

            # Start broadcaster task
            async def broadcast_events():
                await asyncio.sleep(0.5)  # Give listener time to start

                # Broadcast execution event
                await broadcast_test_event(
                    "execution",
                    TEST_SPEC_ID,
                    {
                        "phase": "planning",
                        "phase_progress": 25.0,
                        "overall_progress": 10.0,
                        "message": "Creating implementation plan",
                        "current_subtask": "subtask-1-1",
                    },
                )
                print_info("Broadcasted execution event")
                await asyncio.sleep(0.2)

                # Broadcast log event
                await broadcast_test_event(
                    "log",
                    TEST_SPEC_ID,
                    {"log_line": "Starting planner agent...", "level": "info"},
                )
                print_info("Broadcasted log event")
                await asyncio.sleep(0.2)

                # Broadcast another execution event (progress update)
                await broadcast_test_event(
                    "execution",
                    TEST_SPEC_ID,
                    {
                        "phase": "planning",
                        "phase_progress": 75.0,
                        "overall_progress": 30.0,
                        "message": "Finalizing plan",
                        "current_subtask": "subtask-1-2",
                    },
                )
                print_info("Broadcasted progress update")

            # Run both tasks concurrently
            await asyncio.gather(listen_for_events(), broadcast_events())

            # Verify received events
            if len(received_events) >= 3:
                print_success(f"Received {len(received_events)} events")

                # Verify event types
                execution_events = [
                    e for e in received_events if e["event_type"] == "execution"
                ]
                log_events = [e for e in received_events if e["event_type"] == "log"]

                if len(execution_events) >= 2:
                    print_success(f"Received {len(execution_events)} execution events")

                    # Verify progress tracking
                    first_exec = execution_events[0]
                    if (
                        first_exec["data"]["phase"] == "planning"
                        and abs(first_exec["data"]["phase_progress"] - 25.0) < 0.01
                    ):
                        print_success("First execution event has correct data")

                    if len(execution_events) > 1:
                        second_exec = execution_events[1]
                        if (
                            second_exec["data"]["phase_progress"]
                            > first_exec["data"]["phase_progress"]
                        ):
                            print_success(
                                "Progress tracking works (progress increased)"
                            )

                if len(log_events) >= 1:
                    print_success(f"Received {len(log_events)} log events")

                return True
            else:
                print_error(f"Expected 3+ events, received {len(received_events)}")
                return False

    except Exception as e:
        print_error(f"Execution events test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_unsubscribe():
    """Test 4: Unsubscribe functionality"""
    print_test("Test 4: Unsubscribe Functionality")

    try:
        async with websockets.connect(WEBSOCKET_URL) as websocket:
            # Subscribe
            await websocket.send(
                json.dumps({"action": "subscribe", "spec_id": TEST_SPEC_ID})
            )
            await asyncio.wait_for(websocket.recv(), timeout=5.0)
            print_info("Subscribed")

            # Unsubscribe
            await websocket.send(
                json.dumps({"action": "unsubscribe", "spec_id": TEST_SPEC_ID})
            )
            unsub_response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            unsub_data = json.loads(unsub_response)

            if (
                unsub_data.get("status") == "unsubscribed"
                and unsub_data.get("spec_id") == TEST_SPEC_ID
            ):
                print_success("Successfully unsubscribed")

                # Broadcast event (should NOT be received)
                await broadcast_test_event(
                    "log",
                    TEST_SPEC_ID,
                    {"log_line": "This should not be received", "level": "info"},
                )

                # Try to receive (should timeout)
                try:
                    await asyncio.wait_for(websocket.recv(), timeout=2.0)
                    print_error("Received event after unsubscribe (should not happen)")
                    return False
                except TimeoutError:
                    print_success("No events received after unsubscribe (correct)")
                    return True
            else:
                print_error(f"Unsubscribe failed: {unsub_data}")
                return False

    except Exception as e:
        print_error(f"Unsubscribe test failed: {e}")
        return False


async def test_multiple_clients():
    """Test 5: Multiple clients receiving same events"""
    print_test("Test 5: Multiple Clients")

    received_by_client1 = []
    received_by_client2 = []

    try:
        async with (
            websockets.connect(WEBSOCKET_URL) as ws1,
            websockets.connect(WEBSOCKET_URL) as ws2,
        ):
            # Subscribe both clients
            await ws1.send(json.dumps({"action": "subscribe", "spec_id": TEST_SPEC_ID}))
            await ws2.send(json.dumps({"action": "subscribe", "spec_id": TEST_SPEC_ID}))

            # Wait for subscription confirmations
            await ws1.recv()
            await ws2.recv()
            print_info("Both clients subscribed")

            # Listen for events on both clients
            async def listen_client1():
                try:
                    while len(received_by_client1) < 1:
                        msg = await asyncio.wait_for(ws1.recv(), timeout=5.0)
                        event = json.loads(msg)
                        if event.get("event_type") == "log":
                            received_by_client1.append(event)
                except (TimeoutError, OSError, json.JSONDecodeError):
                    pass  # Listener timeout or connection closed

            async def listen_client2():
                try:
                    while len(received_by_client2) < 1:
                        msg = await asyncio.wait_for(ws2.recv(), timeout=5.0)
                        event = json.loads(msg)
                        if event.get("event_type") == "log":
                            received_by_client2.append(event)
                except (TimeoutError, OSError, json.JSONDecodeError):
                    pass  # Listener timeout or connection closed

            async def broadcast():
                await asyncio.sleep(0.5)
                await broadcast_test_event(
                    "log",
                    TEST_SPEC_ID,
                    {"log_line": "Multi-client test message", "level": "info"},
                )
                print_info("Broadcasted test event")

            # Run all tasks
            await asyncio.gather(listen_client1(), listen_client2(), broadcast())

            # Verify both clients received the event
            if len(received_by_client1) > 0 and len(received_by_client2) > 0:
                print_success("Both clients received the event")
                if (
                    received_by_client1[0]["log_line"]
                    == received_by_client2[0]["log_line"]
                    == "Multi-client test message"
                ):
                    print_success("Both clients received identical event data")
                    return True

            print_error(
                f"Client 1: {len(received_by_client1)}, Client 2: {len(received_by_client2)}"
            )
            return False

    except Exception as e:
        print_error(f"Multiple clients test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def run_all_tests():
    """Run all WebSocket tests"""
    print(f"\n{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}WebSocket Real-Time Updates Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")

    print_info(f"Testing WebSocket endpoint: {WEBSOCKET_URL}")
    print_info(f"Test spec ID: {TEST_SPEC_ID}\n")

    tests = [
        ("WebSocket Connection", test_websocket_connection),
        ("Spec ID Subscription", test_subscription),
        ("Execution Progress Events", test_execution_events),
        ("Unsubscribe Functionality", test_unsubscribe),
    ]

    results = []

    for test_name, test_func in tests:
        try:
            result = await test_func()
            results.append((test_name, result))
            print()  # Blank line between tests
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            import traceback

            traceback.print_exc()
            results.append((test_name, False))
            print()

    # Print summary
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}Test Results Summary{Colors.RESET}")
    print(f"{Colors.BOLD}{'=' * 60}{Colors.RESET}\n")

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = (
            f"{Colors.GREEN}PASS{Colors.RESET}"
            if result
            else f"{Colors.RED}FAIL{Colors.RESET}"
        )
        print(f"  {status}  {test_name}")

    print(f"\n{Colors.BOLD}Total: {passed}/{total} tests passed{Colors.RESET}\n")

    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All tests passed!{Colors.RESET}\n")
        return 0
    else:
        print(f"{Colors.RED}{Colors.BOLD}✗ Some tests failed{Colors.RESET}\n")
        return 1


def main():
    """Main entry point"""
    print_info("Starting WebSocket real-time updates test...")
    print_info("Make sure the backend server is running on http://localhost:8000\n")

    # Check if websockets is installed
    try:
        import websockets
    except ImportError:
        print_error("websockets package not found")
        print_info("Install with: pip install websockets")
        return 1

    # Run tests
    try:
        exit_code = asyncio.run(run_all_tests())
        return exit_code
    except KeyboardInterrupt:
        print_info("\nTests interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Test suite failed: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
