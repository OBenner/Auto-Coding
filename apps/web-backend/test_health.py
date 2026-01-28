#!/usr/bin/env python
"""Quick test script to check health endpoint"""
import asyncio
from httpx import AsyncClient, ASGITransport
from main import app

async def test_health():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/tasks/health")
        print(f"Status: {response.status_code}")
        print(f"Body: {response.text}")

if __name__ == "__main__":
    asyncio.run(test_health())
