#!/usr/bin/env python
"""List all routes in the FastAPI app (developer debug tool, run directly)"""
import os


def main():
    os.environ.setdefault("SECRET_KEY", "dev-debug-only")
    os.environ.setdefault("DEBUG", "true")

    from main import app  # noqa: PLC0415

    for route in app.routes:
        if hasattr(route, "path") and hasattr(route, "methods"):
            print(f"{route.path} -> {route.methods} -> {route.name}")
            if hasattr(route, "dependencies"):
                print(f"  Dependencies: {route.dependencies}")


if __name__ == "__main__":
    main()
