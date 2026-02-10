"""Email Notifications Template"""

from typing import Any

from ..registry import Template


class EmailNotificationsTemplate(Template):
    """Template for email notification system."""

    def __init__(self):
        super().__init__(
            name="email_notifications",
            description="Email notification system with templates",
            category="feature",
            parameters={
                "email_types": {
                    "type": list,
                    "required": True,
                    "description": "Types of emails to send",
                },
                "email_provider": {
                    "type": str,
                    "required": True,
                    "description": "Email provider (sendgrid, ses, smtp)",
                },
                "templates": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Use email templates",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        email_types = params["email_types"]
        provider = params["email_provider"]
        templates = params.get("templates", True)

        return {
            "title": "Email Notification System",
            "description": f"Email notifications using {provider.upper()}.",
            "rationale": "Send automated email notifications to users for important events.",
            "user_stories": [
                "As a user, I want to receive email notifications",
                "As an admin, I want to customize email templates",
            ],
            "acceptance_criteria": [
                f"Send emails via {provider}",
                f"Email types: {', '.join(email_types)}",
            ]
            + (["HTML email templates with variables"] if templates else []),
            "technical_details": f"Provider: {provider}\nTypes: {', '.join(email_types)}",
            "test_coverage": [
                "Email sending tests",
                "Template rendering tests",
                "Delivery tests",
            ],
        }
