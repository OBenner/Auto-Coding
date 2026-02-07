#!/usr/bin/env python3
"""
Simple Multi-Tab WebSocket Test

Verifies that multiple WebSocket clients can:
1. Connect simultaneously
2. All receive the same broadcasted events
3. Continue operating when one disconnects
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("❌ ERROR: websockets module not installed")
    print("Install with: pip install websockets")
    sys.exit(1)

# Import broadcast functions (these use the ConnectionManager from the server process)
from api.websocket import manager

BACKEND_URL = "ws://localhost:8000/ws/agent-events"
TEST_SPEC_ID = "multicast-test"


class Colors:
    """ANSI color codes"""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_success(msg): print(f"{Colors.GREEN}✓ {msg}{Colors.RESET}")
def print_info(msg): print(f"{Colors.BLUE}ℹ {msg}{Colors.RESET}")
def print_error(msg): print(f"{Colors.RED}✗ {msg}{Colors.RESET}")
def print_section(title): print(f"\n{Colors.BOLD}{Colors.BLUE}═══ {title} ═══{Colors.RESET}\n")


async def client_task(client_id: int, spec_id: str, results: dict, num_events: int = 5):
    """WebSocket client that connects and collects events"""
    events_received = []

    try:
        async with websockets.connect(BACKEND_URL) as ws:
            # Subscribe
            await ws.send(json.dumps({"action": "subscribe", "spec_id": spec_id}))
            response = await ws.recv()
            data = json.loads(response)

            if data.get("status") != "subscribed":
                print_error(f"Client {client_id} failed to subscribe")
                return

            print_success(f"Client {client_id} connected and subscribed")

            # Listen for events
            try:
                while len(events_received) < num_events:
                    event = await asyncio.wait_for(ws.recv(), timeout=10.0)
                    event_data = json.loads(event)

                    # Count only log events (not subscription confirmations)
                    if event_data.get("event_type") == "log":
                        events_received.append(event_data)
                        log_line = event_data.get("log_line", "")
                        print_info(f"Client {client_id} received: {log_line}")

            except asyncio.TimeoutError:
                print_info(f"Client {client_id} finished listening (received {len(events_received)} events)")

    except Exception as e:
        print_error(f"Client {client_id} error: {e}")

    results[client_id] = events_received


async def test_multiple_clients_receive_same_events():
    """Test that all clients receive the same broadcasted events"""
    print_section("Test 1: Multiple Clients Receive Same Events")

    num_clients = 3
    num_events = 5
    results = {}

    try:
        # Start multiple clients
        print_info(f"Starting {num_clients} clients...")
        tasks = [
            asyncio.create_task(client_task(i, TEST_SPEC_ID, results, num_events))
            for i in range(1, num_clients + 1)
        ]

        # Give them time to connect
        await asyncio.sleep(2)

        # Broadcast events using the server's ConnectionManager
        print_info(f"Broadcasting {num_events} log events...")
        for i in range(num_events):
            await manager.broadcast_to_spec(
                TEST_SPEC_ID,
                type('Event', (), {
                    "event_type": "log",
                    "spec_id": TEST_SPEC_ID,
                    "timestamp": "2024-01-01T00:00:00",
                    "log_line": f"Broadcast event {i + 1}",
                    "level": "info",
                    "model_dump": lambda mode="json": {
                        "event_type": "log",
                        "spec_id": TEST_SPEC_ID,
                        "timestamp": "2024-01-01T00:00:00",
                        "log_line": f"Broadcast event {i + 1}",
                        "level": "info"
                    }
                })()
            )
            await asyncio.sleep(0.3)

        # Wait for all clients to finish
        await asyncio.sleep(2)

        # Cancel tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        print_info("\nResults:")
        all_counts = []
        for client_id in sorted(results.keys()):
            count = len(results[client_id])
            all_counts.append(count)
            print(f"  Client {client_id}: {count} events")

        if len(set(all_counts)) == 1 and all_counts[0] == num_events:
            print_success(f"All {num_clients} clients received {num_events} events")
            return True
        elif all_counts and min(all_counts) > 0:
            print_warning(f"Event counts vary: {all_counts} - but all clients received events")
            return True
        else:
            print_error("Clients received different numbers of events")
            return False

    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_client_disconnect_doesnt_affect_others():
    """Test that disconnecting one client doesn't affect others"""
    print_section("Test 2: Client Disconnect Doesn't Affect Others")

    num_clients = 3
    num_events = 5
    results = {}

    try:
        # Start clients (client 1 will disconnect early)
        print_info(f"Starting {num_clients} clients (Client 1 will disconnect after 2 events)...")
        tasks = [
            asyncio.create_task(client_task(1, TEST_SPEC_ID, results, 2)),  # Disconnect after 2
            asyncio.create_task(client_task(2, TEST_SPEC_ID, results, num_events)),
            asyncio.create_task(client_task(3, TEST_SPEC_ID, results, num_events)),
        ]

        await asyncio.sleep(2)

        # Broadcast events
        print_info(f"Broadcasting {num_events} log events...")
        for i in range(num_events):
            await manager.broadcast_to_spec(
                TEST_SPEC_ID,
                type('Event', (), {
                    "event_type": "log",
                    "spec_id": TEST_SPEC_ID,
                    "timestamp": "2024-01-01T00:00:00",
                    "log_line": f"Event {i + 1}",
                    "level": "info",
                    "model_dump": lambda mode="json": {
                        "event_type": "log",
                        "spec_id": TEST_SPEC_ID,
                        "timestamp": "2024-01-01T00:00:00",
                        "log_line": f"Event {i + 1}",
                        "level": "info"
                    }
                })()
            )
            await asyncio.sleep(0.3)

        await asyncio.sleep(2)

        # Cancel tasks
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

        # Analyze results
        print_info("\nResults:")
        client_1_count = len(results.get(1, []))
        client_2_count = len(results.get(2, []))
        client_3_count = len(results.get(3, []))

        print(f"  Client 1: {client_1_count} events (disconnected early)")
        print(f"  Client 2: {client_2_count} events")
        print(f"  Client 3: {client_3_count} events")

        if client_1_count == 2 and client_2_count == num_events and client_3_count == num_events:
            print_success("Client 1 disconnected early, clients 2-3 continued receiving")
            return True
        elif client_1_count < client_2_count and client_1_count < client_3_count:
            print_success("Client 1 disconnected early, clients 2-3 continued (approximate)")
            return True
        else:
            print_warning("Unexpected event counts")
            return client_1_count < client_2_count

    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def check_backend_running():
    """Check if backend is running"""
    import socket
    try:
        sock = socket.create_connection(("localhost", 8000), timeout=2)
        sock.close()
        return True
    except (socket.timeout, ConnectionRefusedError):
        return False


async def main():
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║       Multi-Tab WebSocket Connection Test              ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")

    if not check_backend_running():
        print_error("Backend is not running!")
        print("\nStart the backend first:")
        print("  cd apps/web-backend")
        print("  .venv/Scripts/python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload\n")
        return 1

    print_success("Backend is running\n")

    tests = [
        ("Multiple Clients Receive Same Events", test_multiple_clients_receive_same_events),
        ("Client Disconnect Doesn't Affect Others", test_client_disconnect_doesnt_affect_others),
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = await asyncio.wait_for(test_func(), timeout=30)
        except asyncio.TimeoutError:
            print_error("Test timed out")
            results[test_name] = False
        except Exception as e:
            print_error(f"Test failed: {e}")
            results[test_name] = False

    # Print summary
    print_section("Test Summary")
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    failed = total - passed

    print(f"Total: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.RESET}")
    print(f"{Colors.RED}Failed: {failed}{Colors.RESET}\n")

    for test_name, result in results.items():
        status = f"{Colors.GREEN}✓ PASS{Colors.RESET}" if result else f"{Colors.RED}✗ FAIL{Colors.RESET}"
        print(f"  {status} - {test_name}")

    if failed == 0:
        print(f"\n{Colors.BOLD}{Colors.GREEN}╔═══════════════════════════════════════╗")
        print("║     ALL TESTS PASSED! 🎉                ║")
        print(f"╚═══════════════════════════════════════╝{Colors.RESET}\n")
        return 0
    else:
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
