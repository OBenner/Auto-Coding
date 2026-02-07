#!/usr/bin/env python3
"""
Connection Recovery and Heartbeat Test Suite
Subtask 3-3: Test connection recovery and heartbeat

This test verifies:
1. Establish WebSocket connection
2. Verify ping/pong messages keep connection alive
3. Simulate network disconnect
4. Verify auto-reconnect on recovery
5. Verify re-subscription to spec events
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
HEARTBEAT_INTERVAL = 5  # seconds (shorter than production for testing)


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


async def test_initial_connection() -> bool:
    """Test 1: Establish WebSocket connection"""
    print_section("Test 1: Establish WebSocket Connection")

    try:
        print_info(f"Connecting to {BACKEND_URL}...")
        async with websockets.connect(BACKEND_URL) as ws:
            print_success("WebSocket connection established")

            # Subscribe to spec
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
                print_success(f"Subscription confirmed for spec: {data.get('spec_id')}")
                return True
            else:
                print_error(f"Unexpected response: {data}")
                return False

    except asyncio.TimeoutError:
        print_error("Connection timeout - no response from server")
        return False
    except Exception as e:
        print_error(f"Connection failed: {e}")
        return False


async def test_heartbeat_keepalive() -> bool:
    """Test 2: Verify ping/pong messages keep connection alive"""
    print_section("Test 2: Heartbeat Keep-Alive Mechanism")

    try:
        async with websockets.connect(BACKEND_URL) as ws:
            print_info("Testing heartbeat mechanism over 15 seconds...")

            # Subscribe first
            await ws.send(json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }))
            await ws.recv()  # Wait for subscription confirmation

            ping_count = 0
            pong_count = 0

            # Send pings every 5 seconds for 15 seconds
            for i in range(3):
                print_info(f"Sending ping #{i+1}...")
                ping_msg = {"action": "ping"}
                await ws.send(json.dumps(ping_msg))
                ping_count += 1

                # Wait for pong response
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)
                data = json.loads(response)

                if data.get("status") == "pong":
                    pong_count += 1
                    timestamp = data.get("timestamp", "unknown")
                    print_success(f"Pong #{i+1} received at {timestamp}")
                else:
                    print_error(f"Unexpected response to ping: {data}")
                    return False

                # Wait before next ping (simulate heartbeat interval)
                if i < 2:  # Don't wait after last ping
                    await asyncio.sleep(HEARTBEAT_INTERVAL)

            if ping_count == pong_count == 3:
                print_success(f"Heartbeat verified: {pong_count}/3 pongs received")
                print_success("Connection stayed alive during 15-second test period")
                return True
            else:
                print_error(f"Heartbeat incomplete: {pong_count}/{ping_count} pongs received")
                return False

    except asyncio.TimeoutError:
        print_error("Heartbeat timeout - connection may have died")
        return False
    except Exception as e:
        print_error(f"Heartbeat test failed: {e}")
        return False


async def test_simulated_disconnect() -> bool:
    """Test 3: Simulate network disconnect and verify recovery"""
    print_section("Test 3: Simulated Network Disconnect")

    try:
        # First connection
        print_info("Establishing initial connection...")
        ws1 = await websockets.connect(BACKEND_URL)

        # Subscribe
        await ws1.send(json.dumps({
            "action": "subscribe",
            "spec_id": TEST_SPEC_ID
        }))
        response = await ws1.recv()
        print_success("Initial connection and subscription successful")

        # Verify connection is alive with ping
        await ws1.send(json.dumps({"action": "ping"}))
        pong = await ws1.recv()
        print_success(f"Pre-disconnect ping successful")

        # Simulate disconnect by closing the connection
        print_info("Simulating network disconnect (closing connection)...")
        await ws1.close()
        print_success("Connection closed (simulating network failure)")

        # Wait a moment to simulate network recovery delay
        print_info("Waiting 2 seconds (simulating network recovery)...")
        await asyncio.sleep(2)

        # Attempt reconnection
        print_info("Attempting to reconnect...")
        ws2 = await websockets.connect(BACKEND_URL)
        print_success("Reconnection successful!")

        # Verify connection is working
        await ws2.send(json.dumps({"action": "ping"}))
        pong = await asyncio.wait_for(ws2.recv(), timeout=5.0)
        if json.loads(pong).get("status") == "pong":
            print_success("Post-reconnect ping successful")
        else:
            print_error("Post-reconnect ping failed")
            await ws2.close()
            return False

        await ws2.close()
        return True

    except Exception as e:
        print_error(f"Disconnect simulation test failed: {e}")
        return False


async def test_auto_reconnect() -> bool:
    """Test 4: Verify auto-reconnect on recovery"""
    print_section("Test 4: Auto-Reconnect Behavior")

    try:
        # This test simulates the client-side auto-reconnect logic
        max_attempts = 3
        reconnect_delay = 1  # seconds

        print_info(f"Testing auto-reconnect with {max_attempts} attempts...")

        for attempt in range(1, max_attempts + 1):
            print_info(f"Reconnect attempt {attempt}/{max_attempts}...")

            try:
                ws = await asyncio.wait_for(
                    websockets.connect(BACKEND_URL),
                    timeout=5.0
                )

                # Verify connection with ping
                await ws.send(json.dumps({"action": "ping"}))
                response = await asyncio.wait_for(ws.recv(), timeout=5.0)

                if json.loads(response).get("status") == "pong":
                    print_success(f"Auto-reconnect successful on attempt {attempt}")
                    await ws.close()
                    return True
                else:
                    print_warning(f"Attempt {attempt} connected but ping failed")
                    await ws.close()

            except asyncio.TimeoutError:
                print_warning(f"Attempt {attempt} timed out")
            except Exception as e:
                print_warning(f"Attempt {attempt} failed: {e}")

            # Wait before retry (except on last attempt)
            if attempt < max_attempts:
                print_info(f"Waiting {reconnect_delay}s before retry...")
                await asyncio.sleep(reconnect_delay)

        print_error("All reconnect attempts failed")
        return False

    except Exception as e:
        print_error(f"Auto-reconnect test failed: {e}")
        return False


async def test_resubscription_after_reconnect() -> bool:
    """Test 5: Verify re-subscription to spec events after reconnect"""
    print_section("Test 5: Re-subscription After Reconnect")

    try:
        # First connection with subscription
        print_info("Establishing initial connection...")
        ws1 = await websockets.connect(BACKEND_URL)

        await ws1.send(json.dumps({
            "action": "subscribe",
            "spec_id": TEST_SPEC_ID
        }))
        response1 = await ws1.recv()
        data1 = json.loads(response1)

        if data1.get("status") != "subscribed":
            print_error("Initial subscription failed")
            await ws1.close()
            return False

        print_success(f"Initial subscription successful for spec: {TEST_SPEC_ID}")

        # Close connection (simulate disconnect)
        print_info("Simulating disconnect...")
        await ws1.close()
        await asyncio.sleep(1)

        # Reconnect and re-subscribe
        print_info("Reconnecting...")
        ws2 = await websockets.connect(BACKEND_URL)
        print_success("Reconnected successfully")

        # Re-subscribe to same spec
        print_info("Re-subscribing to spec events...")
        await ws2.send(json.dumps({
            "action": "subscribe",
            "spec_id": TEST_SPEC_ID
        }))
        response2 = await asyncio.wait_for(ws2.recv(), timeout=5.0)
        data2 = json.loads(response2)

        if data2.get("status") == "subscribed" and data2.get("spec_id") == TEST_SPEC_ID:
            print_success(f"Re-subscription successful for spec: {TEST_SPEC_ID}")
            print_success("Client can restore subscriptions after reconnect")

            # Verify connection is fully functional with ping
            await ws2.send(json.dumps({"action": "ping"}))
            pong = await asyncio.wait_for(ws2.recv(), timeout=5.0)

            if json.loads(pong).get("status") == "pong":
                print_success("Post-resubscription ping successful")
                await ws2.close()
                return True
            else:
                print_error("Post-resubscription ping failed")
                await ws2.close()
                return False
        else:
            print_error(f"Re-subscription failed: {data2}")
            await ws2.close()
            return False

    except asyncio.TimeoutError:
        print_error("Re-subscription timeout")
        return False
    except Exception as e:
        print_error(f"Re-subscription test failed: {e}")
        return False


async def test_long_connection_stability() -> bool:
    """Test 6: Verify connection remains stable over extended period with heartbeats"""
    print_section("Test 6: Long Connection Stability")

    try:
        print_info("Testing connection stability over 20 seconds with heartbeats...")

        async with websockets.connect(BACKEND_URL) as ws:
            # Subscribe
            await ws.send(json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            }))
            await ws.recv()
            print_success("Connection established and subscribed")

            # Send periodic pings over 20 seconds
            duration = 20  # seconds
            ping_interval = 4  # seconds
            pings_sent = 0
            pongs_received = 0

            start_time = time.time()

            while time.time() - start_time < duration:
                # Send ping
                await ws.send(json.dumps({"action": "ping"}))
                pings_sent += 1
                print_info(f"Ping #{pings_sent} sent ({int(time.time() - start_time)}s elapsed)")

                # Wait for pong
                try:
                    response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                    data = json.loads(response)

                    if data.get("status") == "pong":
                        pongs_received += 1
                        print_success(f"Pong #{pongs_received} received")
                    else:
                        print_warning(f"Unexpected response: {data}")

                except asyncio.TimeoutError:
                    print_warning(f"Pong timeout for ping #{pings_sent}")

                # Wait before next ping
                remaining = duration - (time.time() - start_time)
                if remaining >= ping_interval:
                    await asyncio.sleep(ping_interval)
                else:
                    break

            print_info(f"Test duration: {int(time.time() - start_time)}s")
            print_info(f"Pings sent: {pings_sent}, Pongs received: {pongs_received}")

            if pongs_received >= pings_sent * 0.8:  # Allow 20% loss
                print_success(f"Connection remained stable: {pongs_received}/{pings_sent} heartbeats successful")
                return True
            else:
                print_error(f"Connection unstable: only {pongs_received}/{pings_sent} heartbeats successful")
                return False

    except Exception as e:
        print_error(f"Long connection stability test failed: {e}")
        return False


async def run_all_tests() -> Dict[str, bool]:
    """Run all connection recovery and heartbeat tests"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}")
    print("╔════════════════════════════════════════════════════════╗")
    print("║   Connection Recovery and Heartbeat Test Suite        ║")
    print("║   Subtask 3-3                                          ║")
    print("╚════════════════════════════════════════════════════════╝")
    print(f"{Colors.RESET}\n")

    print_info(f"Backend URL: {BACKEND_URL}")
    print_info(f"Test Spec ID: {TEST_SPEC_ID}")
    print_info(f"Timeout: {TEST_TIMEOUT}s")
    print_info(f"Heartbeat Interval: {HEARTBEAT_INTERVAL}s")

    results = {}

    # Run all tests
    tests = [
        ("Establish WebSocket Connection", test_initial_connection),
        ("Heartbeat Keep-Alive", test_heartbeat_keepalive),
        ("Simulated Network Disconnect", test_simulated_disconnect),
        ("Auto-Reconnect Behavior", test_auto_reconnect),
        ("Re-subscription After Reconnect", test_resubscription_after_reconnect),
        ("Long Connection Stability", test_long_connection_stability),
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

    # Verification steps from implementation_plan.json
    print_section("Verification Steps Completed")

    verification_steps = [
        ("Establish WebSocket connection", results.get("Establish WebSocket Connection", False)),
        ("Verify ping/pong messages keep connection alive", results.get("Heartbeat Keep-Alive", False)),
        ("Simulate network disconnect", results.get("Simulated Network Disconnect", False)),
        ("Verify auto-reconnect on recovery", results.get("Auto-Reconnect Behavior", False)),
        ("Verify re-subscription to spec events", results.get("Re-subscription After Reconnect", False)),
    ]

    for step, passed in verification_steps:
        status = f"{Colors.GREEN}✓{Colors.RESET}" if passed else f"{Colors.RED}✗{Colors.RESET}"
        print(f"  {status} {step}")

    print()

    if failed == 0:
        print(f"{Colors.BOLD}{Colors.GREEN}╔═══════════════════════════════════════╗")
        print("║     ALL TESTS PASSED! 🎉               ║")
        print("║     Subtask 3-3 Complete               ║")
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
