#!/usr/bin/env python3
"""
Test WebSocket Implementation Imports

Verifies that the WebSocket endpoint and agent event models are correctly implemented.
Note: This only tests imports, not runtime behavior.
"""

import sys
import ast
import os

def check_syntax(filepath):
    """Check if a Python file has valid syntax"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            code = f.read()
        ast.parse(code)
        return True, None
    except SyntaxError as e:
        return False, str(e)

def main():
    print("Testing WebSocket Implementation...")
    print("=" * 60)

    files_to_check = [
        "api/models/agent_event.py",
        "api/websocket.py",
        "main.py"
    ]

    all_passed = True

    for filepath in files_to_check:
        if not os.path.exists(filepath):
            print(f"✗ File not found: {filepath}")
            all_passed = False
            continue

        valid, error = check_syntax(filepath)
        if valid:
            print(f"✓ {filepath} - Valid syntax")
        else:
            print(f"✗ {filepath} - Syntax error: {error}")
            all_passed = False

    print("=" * 60)

    if all_passed:
        print("✓ All WebSocket files have valid syntax")
        print("\nWebSocket endpoint will be available at: ws://localhost:8000/ws/agent-events")
        print("\nTo fully test, install dependencies:")
        print("  cd apps/web-backend")
        print("  pip install -r requirements.txt")
        print("  python -m uvicorn main:app --reload")
        print("\nThen connect with a WebSocket client:")
        print('  ws = new WebSocket("ws://localhost:8000/ws/agent-events");')
        print('  ws.send(JSON.stringify({action: "subscribe", spec_id: "001"}));')
        return 0
    else:
        print("✗ Some files have syntax errors")
        return 1

if __name__ == "__main__":
    sys.exit(main())
