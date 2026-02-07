#!/usr/bin/env python3
"""
Simple Multi-Tab WebSocket Connection Test

Tests the verification steps for subtask-3-2:
1. Open TaskDetail in multiple browser tabs (3 WebSocket connections)
2. Start agent execution (broadcast test events)
3. Verify all tabs receive same events
4. Close one tab
5. Verify other tabs continue receiving events
"""

import asyncio
import json
import sys
from datetime import datetime

try:
    import websockets
except ImportError:
    print("❌ ERROR: websockets module not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_test(message: str):
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {message}")


def print_success(message: str):
    print(f"{Colors.GREEN}✓{Colors.RESET} {message}")


def print_error(message: str):
    print(f"{Colors.RED}✗{Colors.RESET} {message}")


def print_info(message: str):
    print(f"{Colors.YELLOW}ℹ{Colors.RESET} {message}")


WEBSOCKET_URL = "ws://localhost:8000/ws/agent-events"
TEST_SPEC_ID = "124-websocket-real-time-progress-stream"


async def broadcast_test_event(spec_id: str, log_line: str):
    """Helper to broadcast a test event"""
    from api.websocket import manager
    from api.models.agent_event import LogEvent

    event = LogEvent(
        event_type="log",
        timestamp=datetime.now().isoformat(),
        spec_id=spec_id,
        log_line=log_line,
        level="info",
        data=None
    )
    await manager.broadcast_to_spec(spec_id, event)


async def test_multi_tab_scenario():
    """
    Test multi-tab WebSocket connections matching the verification steps
    """
    print_test("Multi-Tab WebSocket Connection Test")
    print_info("Simulating 3 browser tabs (WebSocket connections)\n")

    tab1_events = []
    tab2_events = []
    tab3_events = []
    all_connected = asyncio.Event()

    try:
        # Step 1: Open TaskDetail in multiple browser tabs
        print_test("Step 1: Connecting 3 browser tabs")

        async with websockets.connect(WEBSOCKET_URL) as tab1, \
                   websockets.connect(WEBSOCKET_URL) as tab2, \
                   websockets.connect(WEBSOCKET_URL) as tab3:

            print_success("Tab 1 connected")
            print_success("Tab 2 connected")
            print_success("Tab 3 connected")

            # Subscribe all tabs to the same spec
            subscribe_msg = json.dumps({
                "action": "subscribe",
                "spec_id": TEST_SPEC_ID
            })

            await tab1.send(subscribe_msg)
            await tab2.send(subscribe_msg)
            await tab3.send(subscribe_msg)

            # Wait for subscription confirmations
            await tab1.recv()
            await tab2.recv()
            await tab3.recv()

            print_success(f"All 3 tabs subscribed to spec: {TEST_SPEC_ID}\n")

            # Step 2 & 3: Start agent execution and verify all tabs receive events
            print_test("Step 2-3: Broadcasting events and verifying all tabs receive them")

            async def listen_tab1():
                """Listen on tab 1 until closed"""
                try:
                    while True:
                        msg = await tab1.recv()
                        event = json.loads(msg)
                        if event.get("event_type") == "log":
                            tab1_events.append(event)
                            print_info(f"Tab 1 received: {event['log_line']}")
                except:
                    pass

            async def listen_tab2():
                """Listen on tab 2"""
                try:
                    while True:
                        msg = await tab2.recv()
                        event = json.loads(msg)
                        if event.get("event_type") == "log":
                            tab2_events.append(event)
                            print_info(f"Tab 2 received: {event['log_line']}")
                except:
                    pass

            async def listen_tab3():
                """Listen on tab 3"""
                try:
                    while True:
                        msg = await tab3.recv()
                        event = json.loads(msg)
                        if event.get("event_type") == "log":
                            tab3_events.append(event)
                            print_info(f"Tab 3 received: {event['log_line']}")
                except:
                    pass

            async def broadcast_and_close():
                """Broadcast events, close tab 1, broadcast more"""
                await asyncio.sleep(0.5)

                # Broadcast first 2 events (all tabs should receive)
                print_info("\n[Broadcasting] Event 1...")
                await broadcast_test_event(TEST_SPEC_ID, "Event 1: Agent starting")
                await asyncio.sleep(0.3)

                print_info("[Broadcasting] Event 2...")
                await broadcast_test_event(TEST_SPEC_ID, "Event 2: Planning phase")
                await asyncio.sleep(0.3)

                # Step 4: Close tab 1
                print_test("\nStep 4: Closing Tab 1")
                await tab1.close()
                print_success("Tab 1 closed")
                await asyncio.sleep(0.3)

                # Step 5: Broadcast more events (only tabs 2 & 3 should receive)
                print_test("\nStep 5: Broadcasting more events to verify tabs 2 & 3 still receive")

                print_info("[Broadcasting] Event 3...")
                await broadcast_test_event(TEST_SPEC_ID, "Event 3: Coder phase")
                await asyncio.sleep(0.3)

                print_info("[Broadcasting] Event 4...")
                await broadcast_test_event(TEST_SPEC_ID, "Event 4: Writing code")
                await asyncio.sleep(0.3)

                print_info("[Broadcasting] Event 5...")
                await broadcast_test_event(TEST_SPEC_ID, "Event 5: Completed")
                await asyncio.sleep(0.5)

            # Run all listeners and broadcaster concurrently
            listener_tasks = [
                asyncio.create_task(listen_tab1()),
                asyncio.create_task(listen_tab2()),
                asyncio.create_task(listen_tab3()),
            ]

            broadcaster_task = asyncio.create_task(broadcast_and_close())

            # Wait for broadcaster to finish
            await broadcaster_task

            # Cancel listeners
            for task in listener_tasks:
                task.cancel()

            try:
                await asyncio.gather(*listener_tasks, return_exceptions=True)
            except:
                pass

    except Exception as e:
        print_error(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

    # Verify results
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Test Results{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

    success = True

    # Check tab 1 received first 2 events (before closing)
    print_test("Verifying Tab 1 (closed after 2 events)")
    if len(tab1_events) >= 2:
        print_success(f"Tab 1 received {len(tab1_events)} events before closing")
    else:
        print_error(f"Tab 1 only received {len(tab1_events)} events (expected at least 2)")
        success = False

    # Check tab 1 did NOT receive events after closing
    if len(tab1_events) <= 2:
        print_success("Tab 1 correctly stopped receiving events after closing")
    else:
        print_error(f"Tab 1 received {len(tab1_events)} events (should have stopped at 2)")
        success = False

    # Check tab 2 received all 5 events
    print_test("\nVerifying Tab 2 (remained open)")
    if len(tab2_events) >= 5:
        print_success(f"Tab 2 received all {len(tab2_events)} events")
    else:
        print_error(f"Tab 2 only received {len(tab2_events)} events (expected 5)")
        success = False

    # Check tab 3 received all 5 events
    print_test("\nVerifying Tab 3 (remained open)")
    if len(tab3_events) >= 5:
        print_success(f"Tab 3 received all {len(tab3_events)} events")
    else:
        print_error(f"Tab 3 only received {len(tab3_events)} events (expected 5)")
        success = False

    # Verify tabs 2 and 3 received identical events
    print_test("\nVerifying Tab 2 and Tab 3 received identical events")
    if len(tab2_events) >= 5 and len(tab3_events) >= 5:
        if all(tab2_events[i]["log_line"] == tab3_events[i]["log_line"] for i in range(5)):
            print_success("Tabs 2 and 3 received identical events")
        else:
            print_error("Tabs 2 and 3 received different events")
            success = False
    else:
        print_error("Cannot verify - not enough events received")
        success = False

    if success:
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.GREEN}{Colors.BOLD}✓ All Multi-Tab Tests Passed!{Colors.RESET}\n")

        print_success("Verification Summary:")
        print(f"  • 3 tabs connected simultaneously")
        print(f"  • All tabs received initial events (Event 1-2)")
        print(f"  • Tab 1 closed after receiving 2 events")
        print(f"  • Tabs 2 & 3 continued receiving events (Event 3-5)")
        print(f"  • Tabs 2 & 3 received identical events")
        print(f"  • No events lost during tab closure\n")
        return True
    else:
        print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
        print(f"{Colors.RED}{Colors.BOLD}✗ Some Tests Failed{Colors.RESET}\n")
        return False


async def main():
    """Main test runner"""
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}Multi-Tab WebSocket Connection Test Suite{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}\n")

    print_info(f"WebSocket URL: {WEBSOCKET_URL}")
    print_info(f"Test Spec ID: {TEST_SPEC_ID}")
    print_info("Make sure the backend server is running on http://localhost:8000\n")

    try:
        result = await test_multi_tab_scenario()
        return 0 if result else 1
    except KeyboardInterrupt:
        print_info("\nTest interrupted by user")
        return 1
    except Exception as e:
        print_error(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
