"""Logging System Template"""

from typing import Any

from ..registry import Template


class LoggingSystemTemplate(Template):
    """Template for logging system."""

    def __init__(self):
        super().__init__(
            name="logging_system",
            description="Structured logging with log levels and aggregation",
            category="infrastructure",
            parameters={
                "log_destination": {
                    "type": str,
                    "required": True,
                    "description": "Destination (file, cloudwatch, datadog)",
                },
                "log_levels": {
                    "type": list,
                    "required": False,
                    "default": ["debug", "info", "warn", "error"],
                    "description": "Log levels",
                },
                "structured_logs": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Structured JSON logs",
                },
            },
        )

    def generate(self, params: dict[str, Any]) -> dict[str, Any]:
        destination = params["log_destination"]
        levels = params.get("log_levels", ["debug", "info", "warn", "error"])
        structured = params.get("structured_logs", True)

        return {
            "title": "Logging System",
            "description": f"Centralized logging to {destination}.",
            "rationale": "Enable debugging, monitoring, and troubleshooting through comprehensive logging.",
            "user_stories": [
                "As a developer, I want to debug issues using logs",
                "As an operator, I want to monitor application health",
            ],
            "acceptance_criteria": [
                f"Log to {destination}",
                f"Log levels: {', '.join(levels)}",
            ]
            + (["Structured JSON logging"] if structured else []),
            "technical_details": f"Destination: {destination}\nLevels: {', '.join(levels)}",
            "test_coverage": ["Logging tests", "Log level tests", "Format tests"],
        }
