#!/usr/bin/env python
"""Inspect endpoint signatures (developer debug tool, run directly)"""
import inspect
import os


def main():
    os.environ.setdefault("SECRET_KEY", "dev-debug-only")
    os.environ.setdefault("DEBUG", "true")

    from main import app  # noqa: PLC0415

    for route in app.routes:
        if hasattr(route, "path") and route.path == "/api/tasks/health":
            print(f"Route: {route.path}")
            print(f"Endpoint: {route.endpoint}")
            print(f"Signature: {inspect.signature(route.endpoint)}")
            print(f"Dependencies: {route.dependencies}")
            print(f"Dependant: {route.dependant}")
            if hasattr(route.dependant, "dependencies"):
                print(f"Dependant dependencies: {route.dependant.dependencies}")


if __name__ == "__main__":
    main()
