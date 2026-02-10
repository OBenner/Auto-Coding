"""Caching Layer Template"""

from typing import Any

from ..registry import Template


class CachingLayerTemplate(Template):
    """Template for caching implementation."""

    def __init__(self):
        super().__init__(
            name="caching_layer",
            description="Caching layer for performance optimization",
            category="performance",
            parameters={
                "cache_type": {
                    "type": str,
                    "required": True,
                    "description": "Cache type (redis, memcached, in-memory)",
                },
                "cached_data": {
                    "type": list,
                    "required": True,
                    "description": "Data to cache",
                },
                "ttl_seconds": {
                    "type": int,
                    "required": False,
                    "default": 3600,
                    "description": "Cache TTL in seconds",
                },
                "invalidation_strategy": {
                    "type": str,
                    "required": False,
                    "default": "ttl",
                    "description": "Invalidation (ttl, manual, event-based)",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        cache_type = params["cache_type"]
        cached_data = params["cached_data"]
        ttl = params.get("ttl_seconds", 3600)
        invalidation = params.get("invalidation_strategy", "ttl")

        return {
            "title": "Caching Layer",
            "description": f"{cache_type.capitalize()} caching for {', '.join(cached_data)}.",
            "rationale": "Improve application performance by caching frequently accessed data.",
            "user_stories": [
                "As a user, I want faster page load times",
                "As a system, I want to reduce database load",
            ],
            "acceptance_criteria": [
                f"Cache implementation using {cache_type}",
                f"Cache: {', '.join(cached_data)}",
                f"TTL: {ttl} seconds",
                f"Invalidation strategy: {invalidation}",
                "Cache hit/miss monitoring",
            ],
            "technical_details": f"Type: {cache_type}\nTTL: {ttl}s\nInvalidation: {invalidation}",
            "test_coverage": [
                "Cache hit/miss tests",
                "Invalidation tests",
                "Performance benchmarks",
            ],
        }
