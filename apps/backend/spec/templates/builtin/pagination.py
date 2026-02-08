"""Pagination Template"""

from typing import Any, Dict
from ..registry import Template


class PaginationTemplate(Template):
    """Template for pagination implementation."""

    def __init__(self):
        super().__init__(
            name="pagination",
            description="Pagination for large data sets",
            category="feature",
            parameters={
                "entity_name": {"type": str, "required": True, "description": "Entity to paginate"},
                "default_page_size": {"type": int, "required": False, "default": 20, "description": "Items per page"},
                "pagination_type": {"type": str, "required": False, "default": "offset", "description": "Type (offset, cursor)"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity = params["entity_name"]
        page_size = params.get("default_page_size", 20)
        pagination_type = params.get("pagination_type", "offset")

        return {
            "title": f"{entity} Pagination",
            "description": f"{pagination_type.capitalize()}-based pagination for {entity} lists.",
            "rationale": f"Improve performance and UX for large {entity} lists.",
            "user_stories": [
                f"As a user, I want to navigate through {entity} pages",
                "As a user, I want to see total count of items",
            ],
            "acceptance_criteria": [
                f"Paginate {entity} lists",
                f"Default page size: {page_size} items",
                f"{pagination_type.capitalize()}-based pagination",
                "Page controls (next, previous, jump to page)",
                "Display total count and current page",
            ],
            "technical_details": f"Type: {pagination_type}\nPage size: {page_size}\nEntity: {entity}",
            "test_coverage": ["Pagination logic tests", "Edge case tests (empty, single page)", "Performance tests"],
        }
