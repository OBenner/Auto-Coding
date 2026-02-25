"""
Failure Analyzer
================

Analyzes failed builds, QA rejections, and recurring issues to extract root causes.
Provides structured failure analysis for learning from mistakes.

Uses the Claude Agent SDK (same as the rest of the system) for analysis.
Falls back to basic analysis if extraction fails (never blocks the build).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    ClaudeAgentOptions = None
    ClaudeSDKClient = None

from core.auth import get_auth_token

# Default model for failure analysis (fast and cheap)
DEFAULT_ANALYSIS_MODEL = "claude-haiku-4-5-20251001"

# Maximum error message length to analyze
MAX_ERROR_CHARS = 10000

# Maximum diff size to send to the LLM
MAX_DIFF_CHARS = 15000


def is_analysis_enabled() -> bool:
    """Check if failure analysis is enabled."""
    # Analysis requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("FAILURE_ANALYSIS_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_analysis_model() -> str:
    """Get the model to use for failure analysis."""
    return os.environ.get("FAILURE_ANALYZER_MODEL", DEFAULT_ANALYSIS_MODEL)


# =============================================================================
# Data Gathering Helpers
# =============================================================================


def get_recent_logs(project_dir: Path, lines: int = 100) -> str:
    """
    Get recent git commit logs.

    Args:
        project_dir: Project root directory
        lines: Number of recent commits to fetch

    Returns:
        Formatted log text
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-{lines}", "--oneline"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.stdout.strip() else "(No commits)"

    except Exception as e:
        logger.warning(f"Failed to get recent logs: {e}")
        return f"(Failed to get logs: {e})"


def get_recent_diff(project_dir: Path, commit_range: str = "HEAD~5..HEAD") -> str:
    """
    Get recent git diff.

    Args:
        project_dir: Project root directory
        commit_range: Git commit range to diff

    Returns:
        Diff text (truncated if too large)
    """
    try:
        result = subprocess.run(
            ["git", "diff", commit_range],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        diff = result.stdout

        if len(diff) > MAX_DIFF_CHARS:
            diff = (
                diff[:MAX_DIFF_CHARS] + f"\n\n... (truncated, {len(diff)} chars total)"
            )

        return diff if diff else "(Empty diff)"

    except Exception as e:
        logger.warning(f"Failed to get recent diff: {e}")
        return f"(Failed to get diff: {e})"


def load_qa_iteration_history(spec_dir: Path) -> list[dict[str, Any]]:
    """
    Load QA iteration history from implementation plan.

    Args:
        spec_dir: Spec directory

    Returns:
        List of QA iteration records
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return []

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
        return plan.get("qa_iteration_history", [])

    except Exception as e:
        logger.warning(f"Failed to load QA iteration history: {e}")
        return []


def load_subtask_history(spec_dir: Path, subtask_id: str) -> dict[str, Any]:
    """
    Load subtask information from implementation plan.

    Args:
        spec_dir: Spec directory
        subtask_id: Subtask identifier

    Returns:
        Subtask data or empty dict
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return {}

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        # Search through phases for the subtask
        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                if subtask.get("id") == subtask_id:
                    return subtask

        return {}

    except Exception as e:
        logger.warning(f"Failed to load subtask history: {e}")
        return {}


# =============================================================================
# Failure Analysis - Core Logic
# =============================================================================


def extract_root_cause(
    failure_data: dict[str, Any],
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Extract root cause from failure data.

    Args:
        failure_data: Dict with failure information (errors, issues, context)
        use_llm: Whether to use LLM for deeper analysis

    Returns:
        Dict with root cause analysis:
        {
            "category": str,  # e.g., "syntax_error", "logic_error", "missing_dependency"
            "description": str,  # Human-readable description
            "affected_files": list[str],
            "confidence": float,  # 0.0 - 1.0
            "recommendations": list[str],
            "is_recurring": bool,
        }
    """
    # Basic heuristic analysis (always runs)
    root_cause = _analyze_failure_heuristics(failure_data)

    # Enhanced LLM analysis (optional)
    if use_llm and is_analysis_enabled():
        try:
            llm_analysis = _analyze_failure_with_llm(failure_data)
            if llm_analysis:
                # Merge LLM insights with heuristic base
                root_cause.update(llm_analysis)
        except Exception as e:
            logger.warning(f"LLM analysis failed, using heuristics only: {e}")

    return root_cause


def _analyze_failure_heuristics(failure_data: dict[str, Any]) -> dict[str, Any]:
    """
    Perform heuristic-based failure analysis.

    Args:
        failure_data: Failure information

    Returns:
        Basic root cause dict
    """
    errors = failure_data.get("errors", [])
    issues = failure_data.get("issues", [])
    is_recurring = failure_data.get("is_recurring", False)

    # Default root cause
    root_cause = {
        "category": "unknown",
        "description": "Unable to determine root cause",
        "affected_files": [],
        "confidence": 0.3,
        "recommendations": [],
        "is_recurring": is_recurring,
    }

    # Extract affected files from issues
    affected_files = set()
    for issue in issues:
        if file := issue.get("file"):
            affected_files.add(file)

    root_cause["affected_files"] = list(affected_files)

    # Categorize based on error patterns
    error_text = " ".join(str(e) for e in errors).lower()

    if any(
        pattern in error_text
        for pattern in ["syntaxerror", "unexpected token", "invalid syntax"]
    ):
        root_cause["category"] = "syntax_error"
        root_cause["description"] = "Syntax error in code"
        root_cause["confidence"] = 0.9
        root_cause["recommendations"] = [
            "Check for missing brackets, quotes, or semicolons",
            "Verify code follows language syntax rules",
        ]

    elif any(
        pattern in error_text
        for pattern in ["modulenotfounderror", "importerror", "cannot find module"]
    ):
        root_cause["category"] = "missing_dependency"
        root_cause["description"] = "Missing or misconfigured dependency"
        root_cause["confidence"] = 0.85
        root_cause["recommendations"] = [
            "Check if all dependencies are installed",
            "Verify import paths are correct",
            "Update package.json or requirements.txt",
        ]

    elif any(
        pattern in error_text
        for pattern in [
            "typeerror",
            "attributeerror",
            "referenceerror",
            "undefined is not",
        ]
    ):
        root_cause["category"] = "logic_error"
        root_cause["description"] = "Logic or type error in code"
        root_cause["confidence"] = 0.8
        root_cause["recommendations"] = [
            "Check variable types and null checks",
            "Verify object properties exist before access",
            "Review function signatures and return values",
        ]

    elif any(
        pattern in error_text
        for pattern in ["test failed", "assertion", "expected", "actual"]
    ):
        root_cause["category"] = "test_failure"
        root_cause["description"] = "Test assertion failed"
        root_cause["confidence"] = 0.9
        root_cause["recommendations"] = [
            "Review test expectations vs actual behavior",
            "Check if implementation matches test requirements",
            "Verify test setup and mocks are correct",
        ]

    elif any(pattern in error_text for pattern in ["timeout", "timed out", "deadline"]):
        root_cause["category"] = "timeout"
        root_cause["description"] = "Operation timed out"
        root_cause["confidence"] = 0.85
        root_cause["recommendations"] = [
            "Optimize slow operations",
            "Increase timeout limits if appropriate",
            "Check for infinite loops or blocking operations",
        ]

    # Adjust confidence based on recurring status
    if is_recurring:
        root_cause["recommendations"].insert(
            0, "⚠️ RECURRING ISSUE - This problem has occurred multiple times"
        )

    return root_cause


def _analyze_failure_with_llm(failure_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Perform LLM-based failure analysis.

    Args:
        failure_data: Failure information

    Returns:
        Enhanced root cause dict or None if analysis fails
    """
    # TODO: Implement LLM-based analysis using Claude SDK
    # This would build a prompt similar to insight_extractor.py
    # and use ClaudeSDKClient to analyze the failure deeply
    #
    # For now, return None to use heuristics only
    return None


def analyze_failure(
    spec_dir: Path,
    project_dir: Path,
    failure_type: str,
    failure_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze a failure and extract actionable insights.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        failure_type: Type of failure ("qa_rejection", "build_error", "test_failure")
        failure_context: Context about the failure (errors, issues, subtask_id, etc.)

    Returns:
        Dict with failure analysis:
        {
            "failure_type": str,
            "timestamp": str,
            "root_cause": dict,
            "qa_history": list,
            "recommendations": list[str],
        }
    """
    logger.info(f"Analyzing {failure_type} in {spec_dir.name}")

    # Gather failure data
    failure_data = {
        "failure_type": failure_type,
        "errors": failure_context.get("errors", []),
        "issues": failure_context.get("issues", []),
        "is_recurring": failure_context.get("is_recurring", False),
    }

    # Load QA history if available
    qa_history = load_qa_iteration_history(spec_dir)

    # Load subtask info if provided
    if subtask_id := failure_context.get("subtask_id"):
        subtask_info = load_subtask_history(spec_dir, subtask_id)
        failure_data["subtask"] = subtask_info

    # Extract root cause
    root_cause = extract_root_cause(failure_data, use_llm=True)

    # Build analysis result
    analysis = {
        "failure_type": failure_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "root_cause": root_cause,
        "qa_history_length": len(qa_history),
        "recommendations": root_cause.get("recommendations", []),
    }

    # Add recurring issue warning if applicable
    if root_cause.get("is_recurring"):
        analysis["recurring_warning"] = (
            f"This issue has occurred {failure_context.get('occurrence_count', 'multiple')} times"
        )

    logger.info(
        f"Analysis complete: {root_cause['category']} (confidence: {root_cause['confidence']})"
    )

    return analysis


# =============================================================================
# Failure Storage (for Graphiti integration)
# =============================================================================


def format_for_graphiti(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Format failure analysis for storage in Graphiti memory.

    Args:
        analysis: Failure analysis result from analyze_failure()

    Returns:
        Dict formatted for Graphiti episode storage
    """
    root_cause = analysis.get("root_cause", {})

    return {
        "episode_type": "root_cause",
        "name": f"{analysis['failure_type']}: {root_cause.get('category', 'unknown')}",
        "content": root_cause.get("description", "Unknown failure"),
        "metadata": {
            "failure_type": analysis["failure_type"],
            "category": root_cause.get("category", "unknown"),
            "confidence": root_cause.get("confidence", 0.0),
            "affected_files": root_cause.get("affected_files", []),
            "is_recurring": root_cause.get("is_recurring", False),
            "recommendations": root_cause.get("recommendations", []),
            "timestamp": analysis["timestamp"],
        },
    }
