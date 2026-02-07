#!/usr/bin/env python
"""
Test WebSocket endpoint connectivity

This script tests the WebSocket endpoint at ws://localhost:8000/ws/agent-events
It performs a WebSocket handshake and verifies the connection is established.
"""

import asyncio
import websockets
import json
import sys
from datetime import datetime


async def test_websocket_connection():
    """Test WebSocket connection to the agent-events endpoint"""
    uri = "ws://localhost:8000/ws/agent-events"

    print(f"[*] Testing WebSocket endpoint: {uri}")
    print(f"[*] Timestamp: {datetime.now().isoformat()}")

    try:
        # Attempt to connect to WebSocket
        print("[*] Attempting WebSocket handshake...")
        async with websockets.connect(uri, close_timeout=5) as websocket:
            print("[✓] WebSocket connection established successfully!")
            print(f"[✓] Connection status: 101 Switching Protocols")

            # Test subscription
            print("\n[*] Testing subscription message...")
            subscribe_msg = {
                "action": "subscribe",
                "spec_id": "test-spec-001"
            }
            await websocket.send(json.dumps(subscribe_msg))
            print(f"[✓] Sent subscription message: {subscribe_msg}")

            # Wait for response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            response_data = json.loads(response)
            print(f"[✓] Received response: {response_data}")

            # Test ping/pong
            print("\n[*] Testing ping/pong heartbeat...")
            ping_msg = {"action": "ping"}
            await websocket.send(json.dumps(ping_msg))
            print(f"[✓] Sent ping message")

            pong_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            pong_data = json.loads(pong_response)
            print(f"[✓] Received pong response: {pong_data}")

            # Test unsubscribe
            print("\n[*] Testing unsubscription...")
            unsubscribe_msg = {
                "action": "unsubscribe",
                "spec_id": "test-spec-001"
            }
            await websocket.send(json.dumps(unsubscribe_msg))
            print(f"[✓] Sent unsubscribe message")

            unsubscribe_response = await asyncio.wait_for(websocket.recv(), timeout=5)
            unsubscribe_data = json.loads(unsubscribe_response)
            print(f"[✓] Received unsubscribe response: {unsubscribe_data}")

            print("\n" + "="*60)
            print("[✓] ALL TESTS PASSED")
            print("="*60)
            print("\nWebSocket endpoint is functioning correctly:")
            print("  - Connection handshake: OK")
            print("  - Subscribe/Unsubscribe: OK")
            print("  - Ping/Pong heartbeat: OK")
            print("\nStatus: 101 WebSocket Connection Established")

            return True

    except websockets.exceptions.InvalidStatusCode as e:
        if e.status_code == 404:
            print(f"[✗] Error: WebSocket endpoint not found (404)")
            print(f"[✗] The endpoint {uri} does not exist")
            return False
        else:
            print(f"[✗] Error: Invalid status code {e.status_code}")
            return False

    except websockets.exceptions.InvalidHandshake:
        print(f"[✗] Error: Invalid WebSocket handshake")
        print(f"[✗] The server rejected the WebSocket upgrade request")
        return False

    except ConnectionRefusedError:
        print(f"[✗] Error: Connection refused")
        print(f"[✗] The web-backend service is not running on port 8000")
        print(f"[?] To start the service: cd apps/web-backend && python main.py")
        return False

    except asyncio.TimeoutError:
        print(f"[✗] Error: Request timeout")
        print(f"[✗] Server did not respond within the timeout period")
        return False

    except Exception as e:
        print(f"[✗] Unexpected error: {type(e).__name__}: {e}")
        return False


async def main():
    """Main test runner"""
    print("="*60)
    print("WebSocket Endpoint Connectivity Test")
    print("="*60)
    print()

    success = await test_websocket_connection()

    print()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
