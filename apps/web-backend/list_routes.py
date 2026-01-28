#!/usr/bin/env python
"""List all routes in the FastAPI app"""
import os
os.environ["SECRET_KEY"] = "test"
os.environ["DEBUG"] = "true"

from main import app

for route in app.routes:
    if hasattr(route, "path") and hasattr(route, "methods"):
        print(f"{route.path} -> {route.methods} -> {route.name}")
        if hasattr(route, "dependencies"):
            print(f"  Dependencies: {route.dependencies}")
