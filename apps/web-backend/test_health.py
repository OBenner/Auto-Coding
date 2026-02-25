#!/usr/bin/env python
"""Quick test script to check health endpoint (developer debug tool, run directly)"""
import asyncio
import os

os.environ.setdefault("SECRET_KEY", "dev-debug-only")
os.environ.setdefault("DEBUG", "true")

from httpx import AsyncClient, ASGITransport
from main import app


async def test_health():
    # ASGITransport bypasses the network — 'http://test' is a placeholder base URL,
    # not a real HTTP connection, so HTTP vs HTTPS is not a security concern here.
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")
        assert response.status_code == 200, f"Expected 200, got {response.status_code}"
        data = response.json()
        assert "status" in data, "Response missing 'status' key"
        print("✓ /health check passed")

        response = await client.get("/api/tasks/health")
        print(f"\nTasks health status: {response.status_code}")
        assert response.status_code in (200, 401), f"Unexpected status: {response.status_code}"
        print("✓ /api/tasks/health check passed")


if __name__ == "__main__":
    asyncio.run(test_health())
