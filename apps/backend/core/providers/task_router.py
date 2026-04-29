"""
Cost-aware runtime model routing for agent subtasks.

The router uses existing prediction signals to estimate task complexity and
select an appropriate provider/model from configurable routing rules.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from core.providers.cost_calculator import estimate_session_cost
from core.providers.task_router_config import load_model_routing_config
from prediction.patterns import detect_work_type
from prediction.risk_analyzer import RiskAnalyzer

logger = logging.getLogger(__name__)


@dataclass
class TaskRoute:
    """Result of a routing decision."""

    provider: str
    model: str
    complexity: str
    complexity_score: float
    work_types: list[str]
    risk_count: dict[str, int]
    estimated_cost: float
    reasoning: str


class TaskComplexityRouter:
    """Routes subtasks to cost-effective models based on predicted complexity."""

    def __init__(self, config_path: Path | None = None):
        """
        Initialize the task router.

        Args:
            config_path: Optional YAML routing config path. If omitted, the
                default apps/backend/config/model_routing.yaml path is used.

        Raises:
            ValueError: If the routing config is invalid.
        """
        self.config = load_model_routing_config(config_path)
        self.risk_analyzer = RiskAnalyzer()

    def route(self, subtask: dict, agent_type: str | None = None) -> TaskRoute:
        """
        Analyze a subtask and return the selected provider/model route.

        Args:
            subtask: Subtask dictionary with description/files metadata.
            agent_type: Optional agent type for logging context.

        Returns:
            TaskRoute containing the selected model and routing rationale.
        """
        safe_subtask = subtask or {}
        work_types = detect_work_type(safe_subtask)
        risk_issues = self.risk_analyzer.analyze_subtask_risks(safe_subtask)
        complexity_score = self._calculate_complexity_score(
            work_types=work_types,
            risk_issues=risk_issues,
            subtask=safe_subtask,
        )
        complexity = self._complexity_level(complexity_score)
        route_config = self.config["routing"][complexity]
        estimated_tokens = self.config.get("estimated_tokens", {})
        cost_estimate = estimate_session_cost(
            route_config["model"],
            int(estimated_tokens.get("input", 5000)),
            int(estimated_tokens.get("output", 2000)),
        )
        risk_count = self._count_risks(risk_issues)
        reasoning = self._build_reasoning(
            complexity=complexity,
            complexity_score=complexity_score,
            work_types=work_types,
            risk_count=risk_count,
            file_count=self._file_count(safe_subtask),
        )

        route = TaskRoute(
            provider=route_config["provider"],
            model=route_config["model"],
            complexity=complexity,
            complexity_score=complexity_score,
            work_types=work_types,
            risk_count=risk_count,
            estimated_cost=float(cost_estimate["estimated_cost"]),
            reasoning=reasoning,
        )

        logger.info(
            "Task routing decision: agent_type=%s complexity=%s score=%.2f "
            "work_types=%s risks=%s provider=%s model=%s estimated_cost=%.4f "
            "reasoning=%s",
            agent_type or "unknown",
            route.complexity,
            route.complexity_score,
            route.work_types,
            route.risk_count,
            route.provider,
            route.model,
            route.estimated_cost,
            route.reasoning,
        )
        return route

    def _calculate_complexity_score(
        self,
        work_types: list[str],
        risk_issues: list[Any],
        subtask: dict,
    ) -> float:
        """
        Calculate heuristic complexity score in the 0.0-1.0 range.

        Args:
            work_types: Work types returned by detect_work_type().
            risk_issues: Predicted issues from RiskAnalyzer.
            subtask: Subtask dictionary.

        Returns:
            Complexity score clamped to [0.0, 1.0].
        """
        weights = self.config.get("scoring_weights", {})
        score = float(weights.get("base_score", 0.3))

        high_risks = sum(1 for issue in risk_issues if issue.likelihood == "high")
        medium_risks = sum(1 for issue in risk_issues if issue.likelihood == "medium")

        score += min(
            high_risks * float(weights.get("high_risk_issue", 0.1)),
            float(weights.get("high_risk_max", 0.3)),
        )
        score += min(
            medium_risks * float(weights.get("medium_risk_issue", 0.05)),
            float(weights.get("medium_risk_max", 0.15)),
        )

        file_count = self._file_count(subtask)
        if file_count >= int(weights.get("files_threshold_high", 10)):
            score += float(weights.get("files_score_high", 0.25))
        elif file_count >= int(weights.get("files_threshold_medium", 5)):
            score += float(weights.get("files_score_medium", 0.15))

        description = str(subtask.get("description", "")).lower()
        architecture_keywords = weights.get("architecture_keywords", [])
        if any(
            self._matches_keyword(description, str(keyword))
            for keyword in architecture_keywords
        ):
            score += float(weights.get("architecture_keyword_score", 0.2))

        trivial_keywords = weights.get("trivial_keywords", [])
        if any(
            self._matches_keyword(description, str(keyword))
            for keyword in trivial_keywords
        ):
            score += float(weights.get("trivial_keyword_score", -0.2))

        if any(
            work_type in work_types for work_type in ("authentication", "file_upload")
        ):
            score += float(weights.get("security_work_type_bonus", 0.1))

        return max(0.0, min(1.0, score))

    def _complexity_level(self, complexity_score: float) -> str:
        """Map a numeric score to a complexity level."""
        thresholds = self.config.get("complexity_thresholds", {})
        if complexity_score >= float(thresholds.get("high", 0.7)):
            return "high"
        if complexity_score >= float(thresholds.get("medium", 0.4)):
            return "medium"
        return "low"

    def _build_reasoning(
        self,
        complexity: str,
        complexity_score: float,
        work_types: list[str],
        risk_count: dict[str, int],
        file_count: int,
    ) -> str:
        """Build a concise human-readable explanation."""
        work_type_summary = ", ".join(work_types) if work_types else "none detected"
        return (
            f"{complexity} complexity selected from score {complexity_score:.2f}; "
            f"work_types={work_type_summary}; files={file_count}; "
            f"risks high={risk_count['high']}, medium={risk_count['medium']}, "
            f"low={risk_count['low']}"
        )

    def _count_risks(self, risk_issues: list[Any]) -> dict[str, int]:
        """Count predicted issues by likelihood."""
        counts = {"high": 0, "medium": 0, "low": 0}
        for issue in risk_issues:
            likelihood = getattr(issue, "likelihood", "low")
            if likelihood in counts:
                counts[likelihood] += 1
        return counts

    def _file_count(self, subtask: dict) -> int:
        """Count files referenced by a subtask."""
        files_to_modify = subtask.get("files_to_modify", []) or []
        files_to_create = subtask.get("files_to_create", []) or []
        return len({str(path) for path in [*files_to_modify, *files_to_create]})

    def _matches_keyword(self, description: str, keyword: str) -> bool:
        """Return True when keyword appears as a full word or phrase."""
        pattern = r"\b" + re.escape(keyword.lower()) + r"\b"
        return re.search(pattern, description) is not None
