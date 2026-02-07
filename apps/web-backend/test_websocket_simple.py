#!/usr/bin/env python
"""
Simple WebSocket connection test using Python's http.client
"""

import http.client
import sys

def test_websocket_upgrade():
    """Test WebSocket upgrade handshake"""
    host = "localhost"
    port = 8000
    path = "/ws/agent-events"

    print(f"[*] Testing WebSocket upgrade to {host}:{port}{path}")

    try:
        # Create HTTP connection
        conn = http.client.HTTPConnection(host, port, timeout=5)

        # Send WebSocket upgrade request
        headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",  # Sample key
            "Sec-WebSocket-Version": "13",
        }

        print(f"[*] Sending WebSocket upgrade request...")
        conn.request("GET", path, headers=headers)

        # Get response
        response = conn.getresponse()

        print(f"\n[*] Response Status: {response.status} {response.reason}")
        print(f"[*] Response Headers:")
        for header, value in response.getheaders():
            print(f"    {header}: {value}")

        # Check if upgrade was successful
        if response.status == 101:
            print("\n[✓] SUCCESS: WebSocket upgrade accepted (101 Switching Protocols)")
            return True
        elif response.status == 404:
            print("\n[✗] FAILED: Endpoint not found (404)")
            return False
        else:
            print(f"\n[✗] FAILED: Unexpected status code {response.status}")
            return False

    except ConnectionRefusedError:
        print(f"\n[✗] FAILED: Connection refused - server not running")
        return False
    except Exception as e:
        print(f"\n[✗] FAILED: {type(e).__name__}: {e}")
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("="*60)
    print("WebSocket Upgrade Handshake Test")
    print("="*60)
    print()

    success = test_websocket_upgrade()

    print()
    print("="*60)
    if success:
        print("[✓] WebSocket endpoint is reachable")
    else:
        print("[✗] WebSocket endpoint test failed")
    print("="*60)

    sys.exit(0 if success else 1)
