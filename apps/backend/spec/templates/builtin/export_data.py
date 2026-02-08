"""Export Data Template"""

from typing import Any, Dict
from ..registry import Template


class ExportDataTemplate(Template):
    """Template for data export functionality."""

    def __init__(self):
        super().__init__(
            name="export_data",
            description="Export data to various formats (CSV, Excel, JSON)",
            category="feature",
            parameters={
                "entity_name": {"type": str, "required": True, "description": "Entity to export"},
                "formats": {"type": list, "required": True, "description": "Export formats (csv, excel, json, pdf)"},
                "filters": {"type": bool, "required": False, "default": True, "description": "Support filtering"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity = params["entity_name"]
        formats = params["formats"]
        filters = params.get("filters", True)

        return {
            "title": f"{entity} Data Export",
            "description": f"Export {entity} data to {', '.join(formats).upper()}.",
            "rationale": f"Allow users to export {entity} data for external use.",
            "user_stories": [
                f"As a user, I want to export {entity} data",
                "As a user, I want to choose export format",
            ],
            "acceptance_criteria": [
                f"Export {entity} to: {', '.join(formats)}",
                "Large dataset support (streaming)",
            ] + (["Filter data before export"] if filters else []),
            "technical_details": f"Entity: {entity}\nFormats: {', '.join(formats)}",
            "test_coverage": ["Export tests for each format", "Large dataset tests", "Filter tests"],
        }
