#!/usr/bin/env python
"""
Test script to verify pair programming API routes are properly defined.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

# Mock settings to avoid config validation
import os
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-secret-key-for-testing-only"

try:
    from api.routes.agents import router

    # Get all routes from the router
    routes = []
    for route in router.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            routes.append({
                "path": route.path,
                "methods": list(route.methods) if route.methods else [],
                "name": getattr(route, "name", "unnamed")
            })

    print("✓ Module imports successfully")
    print(f"✓ Router has {len(routes)} routes")
    print("\nPair Programming Routes:")

    pair_routes = [r for r in routes if "/pair" in r["path"]]

    if not pair_routes:
        print("✗ No pair programming routes found!")
        sys.exit(1)

    for route in pair_routes:
        methods_str = ", ".join(route["methods"])
        print(f"  {methods_str:12} {route['path']}")

    # Check for required route
    start_route = [r for r in pair_routes if r["path"] == "/api/agents/pair/start" and "POST" in r["methods"]]

    if start_route:
        print("\n✓ POST /api/agents/pair/start route found")
        print("✓ Implementation complete!")
    else:
        print("\n✗ POST /api/agents/pair/start route not found!")
        sys.exit(1)

except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
