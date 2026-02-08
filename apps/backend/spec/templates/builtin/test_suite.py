"""Test Suite Template"""

from typing import Any, Dict
from ..registry import Template


class TestSuiteTemplate(Template):
    """Template for test suite creation."""

    def __init__(self):
        super().__init__(
            name="test_suite",
            description="Comprehensive test suite for component/feature",
            category="testing",
            parameters={
                "test_target": {"type": str, "required": True, "description": "What to test"},
                "test_types": {"type": list, "required": True, "description": "Test types (unit, integration, e2e)"},
                "coverage_goal": {"type": int, "required": False, "default": 80, "description": "Code coverage % goal"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        target = params["test_target"]
        test_types = params["test_types"]
        coverage = params.get("coverage_goal", 80)

        return {
            "title": f"Test Suite: {target}",
            "description": f"Comprehensive test suite for {target}.",
            "rationale": f"Ensure {target} reliability and prevent regressions through automated testing.",
            "user_stories": [
                "As a developer, I want automated tests to catch bugs",
                "As a team, I want to prevent regressions",
            ],
            "acceptance_criteria": [
                f"Test types: {', '.join(test_types)}",
                f"Achieve {coverage}% code coverage",
                "All tests pass in CI/CD pipeline",
                "Tests run in under 5 minutes",
            ],
            "technical_details": f"Target: {target}\nTypes: {', '.join(test_types)}\nCoverage: {coverage}%",
            "test_coverage": [f"{t.capitalize()} tests implemented" for t in test_types],
        }
