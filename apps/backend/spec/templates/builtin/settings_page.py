"""Settings Page Template"""

from typing import Any

from ..registry import Template


class SettingsPageTemplate(Template):
    """Template for application settings page."""

    def __init__(self):
        super().__init__(
            name="settings_page",
            description="Application settings page with preferences",
            category="ui",
            parameters={
                "setting_categories": {
                    "type": list,
                    "required": True,
                    "description": "Setting categories",
                },
                "settings": {
                    "type": list,
                    "required": True,
                    "description": "Individual settings",
                },
                "export_import": {
                    "type": bool,
                    "required": False,
                    "default": False,
                    "description": "Export/import settings",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        categories = params["setting_categories"]
        settings = params["settings"]
        export_import = params.get("export_import", False)

        return {
            "title": "Settings Page",
            "description": "Application settings and user preferences management.",
            "rationale": "Provide centralized location for users to configure application behavior.",
            "user_stories": [
                "As a user, I want to customize application settings",
                "As a user, I want settings to persist across sessions",
            ],
            "acceptance_criteria": [
                f"Setting categories: {', '.join(categories)}",
                f"Settings: {', '.join(settings)}",
                "Settings persist to database/local storage",
                "Validation for setting values",
            ]
            + (["Export and import settings"] if export_import else []),
            "technical_details": f"Categories: {', '.join(categories)}\nSettings: {', '.join(settings)}",
            "test_coverage": [
                "Settings save tests",
                "Validation tests",
                "Persistence tests",
            ],
        }
