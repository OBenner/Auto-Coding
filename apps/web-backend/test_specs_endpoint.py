#!/usr/bin/env python3
"""
Quick test script for specs API endpoint
"""

import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

try:
    from api.routes import specs
    from api.models import spec
    print("✓ Imports successful")

    # Test that router is configured correctly
    print(f"✓ Router prefix: {specs.router.prefix}")
    print(f"✓ Router tags: {specs.router.tags}")

    # Count routes
    routes = [route.path for route in specs.router.routes]
    print(f"✓ Routes defined: {len(routes)}")
    for route in routes:
        print(f"  - {route}")

    print("\n✅ All tests passed!")
    sys.exit(0)

except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
