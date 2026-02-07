#!/usr/bin/env python3
"""
Debug test to verify WebSocket broadcasting works
"""

import asyncio
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    import websockets
except ImportError:
    print("❌ ERROR: websockets module not installed")
    sys.exit(1)

from api.websocket import manager, broadcast_log_event

BACKEND_URL = "ws://localhost:8000/ws/agent-events"
TEST_SPEC_ID = "debug-spec"


async def test_client_receives_broadcast():
    """Test that a client receives a broadcasted event"""
    print("Starting test client...")

    async with websockets.connect(BACKEND_URL) as ws:
        # Subscribe
        await ws.send(json.dumps({
            "action": "subscribe",
            "spec_id": TEST_SPEC_ID
        }))

        # Wait for confirmation
        response = await ws.recv()
        print(f"Subscription response: {response}")

        # Broadcast an event
        print(f"\nBroadcasting log event to spec '{TEST_SPEC_ID}'...")
        await broadcast_log_event(
            spec_id=TEST_SPEC_ID,
            log_line="Debug test log line",
            level="info"
        )

        # Try to receive it
        print("Waiting for event...")
        try:
            event = await asyncio.wait_for(ws.recv(), timeout=3.0)
            event_data = json.loads(event)
            print(f"\n✓ Received event:")
            print(json.dumps(event_data, indent=2))

            if event_data.get("event_type") == "log":
                return True
            else:
                print(f"✗ Unexpected event type: {event_data.get('event_type')}")
                return False

        except asyncio.TimeoutError:
            print("✗ Timeout - no event received")
            print(f"\nDebug info:")
            print(f"  Active connections: {len(manager.active_connections)}")
            print(f"  Spec subscriptions: {list(manager.spec_subscriptions.keys())}")
            return False


async def main():
    print("=" * 60)
    print("WebSocket Broadcast Debug Test")
    print("=" * 60)

    result = await test_client_receives_broadcast()

    if result:
        print("\n✓ Test PASSED")
        return 0
    else:
        print("\n✗ Test FAILED")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
