#!/usr/bin/env python
"""Inspect router dependencies"""
import os
os.environ["SECRET_KEY"] = "test"
os.environ["DEBUG"] = "true"

from api.routes import tasks, specs

print("Tasks router:")
print(f"  prefix: {tasks.router.prefix}")
print(f"  dependencies: {tasks.router.dependencies}")
print(f"  routes: {len(tasks.router.routes)}")

print("\nSpecs router:")
print(f"  prefix: {specs.router.prefix}")
print(f"  dependencies: {specs.router.dependencies}")
print(f"  routes: {len(specs.router.routes)}")

# Check each route in tasks router
print("\nTasks routes:")
for route in tasks.router.routes:
    if hasattr(route, "path"):
        print(f"  {route.path}: dependencies={route.dependencies if hasattr(route, 'dependencies') else 'N/A'}")
