#!/usr/bin/env python
"""
Direct WebSocket connection test using websockets library
"""

import asyncio
import websockets
import sys


async def test_websocket():
    """Test WebSocket connection using websockets library"""
    uri = "ws://localhost:8000/ws/agent-events"

    print(f"[*] Connecting to: {uri}")

    try:
        async with websockets.connect(uri, close_timeout=10) as websocket:
            print("[✓] Connected successfully!")
            print("[✓] Connection status: 101 Switching Protocols")

            # Send subscription message
            message = {"action": "subscribe", "spec_id": "test-001"}
            await websocket.send_json(message)
            print(f"[✓] Sent: {message}")

            # Receive response
            response = await asyncio.wait_for(websocket.recv(), timeout=5)
            print(f"[✓] Received: {response}")

            return True

    except websockets.exceptions.InvalidStatusCode as e:
        print(f"\n[✗] Status Code: {e.status_code}")
        if e.headers:
            print(f"[✗] Response Headers:")
            for k, v in e.headers.items():
                print(f"    {k}: {v}")

        if e.status_code == 403:
            print("\n[✗] FORBIDDEN - Possible causes:")
            print("    1. CORS policy rejecting the connection")
            print("    2. Middleware blocking WebSocket upgrade")
            print("    3. Authentication required")
        elif e.status_code == 404:
            print("\n[✗] NOT FOUND - WebSocket endpoint doesn't exist")
        else:
            print(f"\n[✗] Unexpected status code: {e.status_code}")

        return False

    except ConnectionRefusedError:
        print(f"\n[✗] Connection refused - server not running")
        return False

    except Exception as e:
        print(f"\n[✗] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    print("="*60)
    print("WebSocket Connection Test (websockets library)")
    print("="*60)
    print()

    success = await test_websocket()

    print()
    print("="*60)
    if success:
        print("[✓] WebSocket endpoint is working")
    else:
        print("[✗] WebSocket connection failed")
    print("="*60)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
