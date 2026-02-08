"""Admin Panel Template"""

from typing import Any, Dict
from ..registry import Template


class AdminPanelTemplate(Template):
    """Template for admin panel."""

    def __init__(self):
        super().__init__(
            name="admin_panel",
            description="Admin panel for managing application data",
            category="feature",
            parameters={
                "managed_entities": {"type": list, "required": True, "description": "Entities to manage"},
                "permissions": {"type": bool, "required": False, "default": True, "description": "Role-based permissions"},
                "audit_log": {"type": bool, "required": False, "default": True, "description": "Audit logging"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        entities = params["managed_entities"]
        permissions = params.get("permissions", True)
        audit = params.get("audit_log", True)

        return {
            "title": "Admin Panel",
            "description": "Administrative interface for managing application data.",
            "rationale": "Provide administrators with tools to manage application data and users.",
            "user_stories": [
                "As an admin, I want to manage application data",
                "As an admin, I want to view activity logs",
            ],
            "acceptance_criteria": [
                f"Manage: {', '.join(entities)}",
                "CRUD operations for all entities",
                "Search and filter capabilities",
            ] + (["Role-based access control"] if permissions else [])
            + (["Audit log for all admin actions"] if audit else []),
            "technical_details": f"Entities: {', '.join(entities)}",
            "test_coverage": ["CRUD tests", "Permission tests" if permissions else "", "Audit tests" if audit else ""],
        }
