#!/usr/bin/env python
"""Inspect endpoint signatures"""
import os
import inspect
os.environ["SECRET_KEY"] = "test"
os.environ["DEBUG"] = "true"

from main import app

# Find the tasks_health endpoint
for route in app.routes:
    if hasattr(route, "path") and route.path == "/api/tasks/health":
        print(f"Route: {route.path}")
        print(f"Endpoint: {route.endpoint}")
        print(f"Signature: {inspect.signature(route.endpoint)}")
        print(f"Dependencies: {route.dependencies}")
        print(f"Dependant: {route.dependant}")
        if hasattr(route.dependant, "dependencies"):
            print(f"Dependant dependencies: {route.dependant.dependencies}")
