"""Search Feature Template"""

from typing import Any

from ..registry import Template


class SearchFeatureTemplate(Template):
    """Template for search functionality."""

    def __init__(self):
        super().__init__(
            name="search_feature",
            description="Full-text search with filters and autocomplete",
            category="feature",
            parameters={
                "search_entities": {
                    "type": list,
                    "required": True,
                    "description": "Entities to search",
                },
                "search_fields": {
                    "type": list,
                    "required": True,
                    "description": "Fields to search in",
                },
                "filters": {
                    "type": list,
                    "required": False,
                    "default": [],
                    "description": "Available filters",
                },
                "autocomplete": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Autocomplete",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        entities = params["search_entities"]
        fields = params["search_fields"]
        filters = params.get("filters", [])
        autocomplete = params.get("autocomplete", True)

        return {
            "title": "Search Feature",
            "description": f"Full-text search across {', '.join(entities)} with filters.",
            "rationale": "Enable users to quickly find content through search.",
            "user_stories": [
                "As a user, I want to search for content",
                "As a user, I want to filter search results",
            ],
            "acceptance_criteria": [
                f"Search across: {', '.join(entities)}",
                f"Search in fields: {', '.join(fields)}",
                "Real-time search results",
            ]
            + ([f"Filters: {', '.join(filters)}"] if filters else [])
            + (["Autocomplete suggestions"] if autocomplete else []),
            "technical_details": f"Entities: {', '.join(entities)}\nFields: {', '.join(fields)}",
            "test_coverage": [
                "Search accuracy tests",
                "Filter tests",
                "Performance tests",
            ],
        }
