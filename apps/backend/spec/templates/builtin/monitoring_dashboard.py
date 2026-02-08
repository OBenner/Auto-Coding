"""Monitoring Dashboard Template"""

from typing import Any, Dict
from ..registry import Template


class MonitoringDashboardTemplate(Template):
    """Template for monitoring dashboard."""

    def __init__(self):
        super().__init__(
            name="monitoring_dashboard",
            description="Application monitoring dashboard with metrics and alerts",
            category="infrastructure",
            parameters={
                "monitoring_service": {"type": str, "required": True, "description": "Service (datadog, newrelic, grafana)"},
                "metrics": {"type": list, "required": True, "description": "Metrics to monitor"},
                "alerts": {"type": bool, "required": False, "default": True, "description": "Configure alerts"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        service = params["monitoring_service"]
        metrics = params["metrics"]
        alerts = params.get("alerts", True)

        return {
            "title": "Monitoring Dashboard",
            "description": f"Application monitoring using {service}.",
            "rationale": "Monitor application health, performance, and availability in real-time.",
            "user_stories": [
                "As an operator, I want to monitor application health",
                "As a developer, I want to be alerted to issues",
            ],
            "acceptance_criteria": [
                f"Monitor metrics: {', '.join(metrics)}",
                f"Dashboard in {service}",
                "Real-time metric updates",
            ] + (["Alert configuration for critical metrics"] if alerts else []),
            "technical_details": f"Service: {service}\nMetrics: {', '.join(metrics)}",
            "test_coverage": ["Metrics collection tests", "Dashboard rendering tests", "Alert tests" if alerts else ""],
        }
