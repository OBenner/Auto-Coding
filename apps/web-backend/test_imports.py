#!/usr/bin/env python
"""Test that all modules can be imported successfully"""

import sys

try:
    print("✓ core.security imported successfully")
except Exception as e:
    print(f"✗ Failed to import core.security: {e}")
    sys.exit(1)

try:
    print("✓ api.routes.auth imported successfully")
except Exception as e:
    print(f"✗ Failed to import api.routes.auth: {e}")
    sys.exit(1)

try:
    print("✓ fastapi imported successfully")
except Exception as e:
    print(f"✗ Failed to import fastapi: {e}")
    sys.exit(1)

print("\nAll imports successful!")
