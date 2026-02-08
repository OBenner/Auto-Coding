"""Error Handling Template"""

from typing import Any, Dict
from ..registry import Template


class ErrorHandlingTemplate(Template):
    """Template for error handling."""

    def __init__(self):
        super().__init__(
            name="error_handling",
            description="Centralized error handling and user-friendly error messages",
            category="infrastructure",
            parameters={
                "error_tracking": {"type": str, "required": True, "description": "Error tracking service (sentry, bugsnag)"},
                "custom_error_pages": {"type": bool, "required": False, "default": True, "description": "Custom error pages"},
                "error_reporting": {"type": bool, "required": False, "default": True, "description": "User error reporting"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        tracking = params["error_tracking"]
        custom_pages = params.get("custom_error_pages", True)
        reporting = params.get("error_reporting", True)

        return {
            "title": "Error Handling System",
            "description": f"Centralized error handling with {tracking} integration.",
            "rationale": "Improve user experience and debugging through proper error handling.",
            "user_stories": [
                "As a user, I want clear error messages",
                "As a developer, I want to track production errors",
            ],
            "acceptance_criteria": [
                f"Integrate {tracking} for error tracking",
                "Graceful error handling",
                "User-friendly error messages",
            ] + (["Custom 404/500 error pages"] if custom_pages else [])
            + (["Allow users to report errors"] if reporting else []),
            "technical_details": f"Tracking: {tracking}",
            "test_coverage": ["Error handling tests", "Integration tests", "UI tests"],
        }
