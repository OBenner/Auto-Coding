"""Performance Optimization Template"""

from typing import Any, Dict
from ..registry import Template


class PerformanceOptimizationTemplate(Template):
    """Template for performance optimization."""

    def __init__(self):
        super().__init__(
            name="performance_optimization",
            description="Performance optimization for specific component/feature",
            category="performance",
            parameters={
                "target_component": {"type": str, "required": True, "description": "Component to optimize"},
                "optimization_type": {"type": str, "required": True, "description": "Type (database, frontend, api, algorithm)"},
                "performance_goal": {"type": str, "required": True, "description": "Goal (e.g., '50% faster', 'reduce memory by 30%')"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        component = params["target_component"]
        opt_type = params["optimization_type"]
        goal = params["performance_goal"]

        return {
            "title": f"Performance Optimization: {component}",
            "description": f"Optimize {component} {opt_type} performance to achieve {goal}.",
            "rationale": f"Improve user experience and system efficiency by optimizing {component}.",
            "user_stories": [
                "As a user, I want faster response times",
                "As a developer, I want efficient resource usage",
            ],
            "acceptance_criteria": [
                f"Achieve performance goal: {goal}",
                "Benchmark before and after optimization",
                "No regression in functionality",
                "Monitor performance metrics in production",
            ],
            "technical_details": f"Component: {component}\nType: {opt_type}\nGoal: {goal}",
            "test_coverage": ["Performance benchmarks", "Load tests", "Regression tests"],
        }
