"""API Integration Template"""

from typing import Any, Dict
from ..registry import Template


class ApiIntegrationTemplate(Template):
    """Template for third-party API integration."""

    def __init__(self):
        super().__init__(
            name="api_integration",
            description="Integrate with external third-party API",
            category="integration",
            parameters={
                "api_name": {"type": str, "required": True, "description": "Name of the API service"},
                "endpoints": {"type": list, "required": True, "description": "API endpoints to integrate"},
                "auth_type": {"type": str, "required": True, "description": "Authentication type (api_key, oauth, basic)"},
                "rate_limiting": {"type": bool, "required": False, "default": True, "description": "Handle rate limiting"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        api_name = params["api_name"]
        endpoints = params["endpoints"]
        auth_type = params["auth_type"]
        rate_limiting = params.get("rate_limiting", True)

        return {
            "title": f"{api_name} API Integration",
            "description": f"Integration with {api_name} API for {', '.join(endpoints[:3])}.",
            "rationale": f"Enable the application to leverage {api_name} functionality through API integration.",
            "user_stories": [
                f"As a developer, I want to call {api_name} API endpoints",
                "As a system, I want to handle API errors gracefully",
            ],
            "acceptance_criteria": [
                f"Integration with {api_name} API endpoints: {', '.join(endpoints)}",
                f"{auth_type.upper()} authentication implemented",
                "Error handling for API failures",
                "Response data parsing and validation",
            ] + (["Rate limiting with exponential backoff"] if rate_limiting else []),
            "technical_details": f"API: {api_name}\nAuth: {auth_type}\nEndpoints: {', '.join(endpoints)}",
            "test_coverage": ["API integration tests", "Error handling tests", "Authentication tests"],
        }
