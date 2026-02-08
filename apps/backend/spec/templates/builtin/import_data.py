"""Import Data Template"""

from typing import Any, Dict
from ..registry import Template


class ImportDataTemplate(Template):
    """Template for data import functionality."""

    def __init__(self):
        super().__init__(
            name="import_data",
            description="Import data from CSV/Excel files with validation",
            category="feature",
            parameters={
                "entity_name": {"type": str, "required": True, "description": "Entity to import"},
                "file_formats": {"type": list, "required": True, "description": "Supported formats (csv, excel)"},
                "validation": {"type": bool, "required": False, "default": True, "description": "Data validation"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entity = params["entity_name"]
        formats = params["file_formats"]
        validation = params.get("validation", True)

        return {
            "title": f"{entity} Data Import",
            "description": f"Import {entity} from {', '.join(formats).upper()} files.",
            "rationale": f"Enable bulk {entity} creation via file import.",
            "user_stories": [
                f"As a user, I want to import {entity} from files",
                "As a user, I want to see import validation errors",
            ],
            "acceptance_criteria": [
                f"Import from: {', '.join(formats)}",
                "Batch processing for large files",
                "Import preview before confirmation",
            ] + (["Row-by-row validation with error reporting"] if validation else []),
            "technical_details": f"Entity: {entity}\nFormats: {', '.join(formats)}",
            "test_coverage": ["Import tests", "Validation tests", "Error handling tests"],
        }
