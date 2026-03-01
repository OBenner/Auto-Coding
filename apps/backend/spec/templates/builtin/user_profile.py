"""User Profile Template"""

from typing import Any

from ..registry import Template


class UserProfileTemplate(Template):
    """Template for user profile functionality."""

    def __init__(self):
        super().__init__(
            name="user_profile",
            description="User profile with editable fields and avatar",
            category="feature",
            parameters={
                "profile_fields": {
                    "type": list,
                    "required": True,
                    "description": "Profile fields",
                },
                "avatar_upload": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Avatar upload",
                },
                "privacy_settings": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Privacy controls",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        fields = params["profile_fields"]
        avatar = params.get("avatar_upload", True)
        privacy = params.get("privacy_settings", True)

        return {
            "title": "User Profile",
            "description": "User profile management with customizable fields.",
            "rationale": "Allow users to manage their profile information and preferences.",
            "user_stories": [
                "As a user, I want to view my profile",
                "As a user, I want to update my profile information",
            ],
            "acceptance_criteria": [
                f"Profile fields: {', '.join(fields)}",
                "View and edit profile",
            ]
            + (["Upload and crop avatar image"] if avatar else [])
            + (["Privacy settings for profile visibility"] if privacy else []),
            "technical_details": f"Fields: {', '.join(fields)}",
            "test_coverage": [
                "Profile update tests",
                "Validation tests",
                "Avatar upload tests" if avatar else "",
            ],
        }
