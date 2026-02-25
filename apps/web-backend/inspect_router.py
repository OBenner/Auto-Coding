#!/usr/bin/env python
"""Inspect router dependencies (developer debug tool, run directly)"""
import os


def main():
    os.environ.setdefault("SECRET_KEY", "dev-debug-only")
    os.environ.setdefault("DEBUG", "true")

    from api.routes import specs, tasks  # noqa: PLC0415

    print("Tasks router:")
    print(f"  prefix: {tasks.router.prefix}")
    print(f"  dependencies: {tasks.router.dependencies}")
    print(f"  routes: {len(tasks.router.routes)}")

    print("\nSpecs router:")
    print(f"  prefix: {specs.router.prefix}")
    print(f"  dependencies: {specs.router.dependencies}")
    print(f"  routes: {len(specs.router.routes)}")

    print("\nTasks routes:")
    for route in tasks.router.routes:
        if hasattr(route, "path"):
            deps = getattr(route, "dependencies", "N/A")
            print(f"  {route.path}: dependencies={deps}")


if __name__ == "__main__":
    main()
