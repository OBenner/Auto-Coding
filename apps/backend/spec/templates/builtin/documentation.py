"""Documentation Template"""

from typing import Any

from ..registry import Template


class DocumentationTemplate(Template):
    """Template for documentation."""

    def __init__(self):
        super().__init__(
            name="documentation",
            description="Technical documentation for API/component/feature",
            category="documentation",
            parameters={
                "doc_type": {
                    "type": str,
                    "required": True,
                    "description": "Type (api, user-guide, technical, readme)",
                },
                "target_audience": {
                    "type": str,
                    "required": True,
                    "description": "Audience (developers, users, admins)",
                },
                "include_examples": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Include code examples",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        doc_type = params["doc_type"]
        audience = params["target_audience"]
        examples = params.get("include_examples", True)

        return {
            "title": f"{doc_type.replace('-', ' ').title()} Documentation",
            "description": f"{doc_type.capitalize()} documentation for {audience}.",
            "rationale": f"Provide clear documentation to help {audience} understand and use the system effectively.",
            "user_stories": [
                f"As a {audience}, I want comprehensive documentation",
                f"As a {audience}, I want to find information quickly",
            ],
            "acceptance_criteria": [
                f"{doc_type.capitalize()} documentation written",
                "Clear, concise writing style",
                "Proper formatting and structure",
                "Search functionality",
            ]
            + (["Code examples for all features"] if examples else []),
            "technical_details": f"Type: {doc_type}\nAudience: {audience}",
            "test_coverage": [
                "Documentation review",
                "Example validation",
                "Link checking",
            ],
        }
