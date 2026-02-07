#!/usr/bin/env python
"""
Test WebSocket connection with proper headers including Origin
"""

import http.client
import sys

def test_websocket_upgrade():
    """Test WebSocket upgrade handshake with proper headers"""
    host = "localhost"
    port = 8000
    path = "/ws/agent-events"

    print(f"[*] Testing WebSocket upgrade to {host}:{port}{path}")

    try:
        # Create HTTP connection
        conn = http.client.HTTPConnection(host, port, timeout=5)

        # Send WebSocket upgrade request with all required headers
        headers = {
            "Upgrade": "websocket",
            "Connection": "Upgrade",
            "Sec-WebSocket-Key": "dGhlIHNhbXBsZSBub25jZQ==",  # Sample key
            "Sec-WebSocket-Version": "13",
            "Origin": "http://localhost:3000",  # Include Origin header for CORS
        }

        print(f"[*] Sending WebSocket upgrade request with headers:")
        for k, v in headers.items():
            print(f"    {k}: {v}")

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
            print("\n[*] Verifying required headers:")
            headers_dict = dict(response.getheaders())
            required_headers = {
                "Upgrade": "websocket",
                "Connection": "Upgrade"
            }
            for header, expected in required_headers.items():
                actual = headers_dict.get(header, "")
                if header.lower() in actual.lower():
                    print(f"    [✓] {header}: {actual}")
                else:
                    print(f"    [✗] {header}: Expected '{expected}', got '{actual}'")
                    return False
            return True

        elif response.status == 403:
            print("\n[✗] FAILED: Forbidden (403)")
            print("\n[?] Possible causes:")
            print("    - CORS policy blocking the request")
            print("    - Middleware rejecting WebSocket upgrade")
            print("    - Missing or invalid authentication")
            return False

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
        import traceback
        traceback.print_exc()
        return False
    finally:
        conn.close()


if __name__ == "__main__":
    print("="*60)
    print("WebSocket Upgrade Handshake Test (with CORS)")
    print("="*60)
    print()

    success = test_websocket_upgrade()

    print()
    print("="*60)
    if success:
        print("[✓] WebSocket endpoint is reachable and working")
        print("[✓] Status: 101 Switching Protocols")
    else:
        print("[✗] WebSocket endpoint test failed")
    print("="*60)

    sys.exit(0 if success else 1)
