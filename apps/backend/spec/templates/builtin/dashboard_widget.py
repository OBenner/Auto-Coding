"""Dashboard Widget Template"""

from typing import Any, Dict
from ..registry import Template


class DashboardWidgetTemplate(Template):
    """Template for dashboard widget."""

    def __init__(self):
        super().__init__(
            name="dashboard_widget",
            description="Dashboard widget with data visualization",
            category="ui",
            parameters={
                "widget_name": {"type": str, "required": True, "description": "Widget name"},
                "data_source": {"type": str, "required": True, "description": "Data source API"},
                "visualization_type": {"type": str, "required": True, "description": "Chart type (bar, line, pie, table)"},
                "refresh_interval": {"type": int, "required": False, "default": 60, "description": "Refresh interval (seconds)"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        name = params["widget_name"]
        source = params["data_source"]
        viz = params["visualization_type"]
        interval = params.get("refresh_interval", 60)

        return {
            "title": f"{name} Dashboard Widget",
            "description": f"Dashboard widget displaying {viz} visualization.",
            "rationale": f"Provide at-a-glance {name} metrics on dashboard.",
            "user_stories": [
                f"As a user, I want to see {name} metrics",
                "As a user, I want the widget to auto-refresh",
            ],
            "acceptance_criteria": [
                f"Display {viz} visualization",
                f"Fetch data from {source}",
                f"Auto-refresh every {interval} seconds",
                "Loading and error states",
                "Responsive design",
            ],
            "technical_details": f"Type: {viz}\nSource: {source}\nRefresh: {interval}s",
            "test_coverage": ["Data fetching tests", "Rendering tests", "Refresh tests"],
        }
