"""
Failure Storage Module
======================

Stores failure analysis results in Graphiti memory for learning and prevention.
Integrates with failure_analyzer.py to persist root cause analyses.

This module provides storage for:
- QA rejection failures
- Build errors
- Test failures
- Recurring issue patterns

All storage operations are async and gracefully degrade if Graphiti is disabled.
"""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.sentry import capture_exception
from integrations.graphiti.config import is_graphiti_enabled
from integrations.graphiti.memory import get_graphiti_memory
from integrations.graphiti.queries_pkg.schema import (
    EPISODE_TYPE_QA_RESULT,
    EPISODE_TYPE_ROOT_CAUSE,
    GroupIdMode,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Shared Helpers
# =============================================================================


@asynccontextmanager
async def _graphiti_session(
    spec_dir: Path,
    project_dir: Path,
    group_id_mode: str = GroupIdMode.PROJECT,
) -> AsyncGenerator[Any, None]:
    """Acquire, initialise and close a Graphiti memory instance.

    Yields the memory object (never ``None``).  Raises ``RuntimeError``
    when memory is unavailable so callers can simply ``async with``.
    """
    memory = get_graphiti_memory(spec_dir, project_dir, group_id_mode)
    if memory is None or not memory.is_enabled:
        raise RuntimeError("Graphiti memory not available")
    try:
        if not memory.is_initialized:
            await memory.initialize()
        yield memory
    finally:
        try:
            await memory.close()
        except Exception:
            pass


async def _add_episode(
    memory: Any,
    *,
    name: str,
    body: str,
    source_description: str,
) -> None:
    """Store an episode via the memory client and bump the counter.

    Raises ``RuntimeError`` when no client is available.
    """
    from graphiti_core.nodes import EpisodeType

    client = memory.client
    if client is None:
        raise RuntimeError("No client available on memory instance")

    await client.graphiti.add_episode(
        name=name,
        episode_body=body,
        source=EpisodeType.text,
        source_description=source_description,
        reference_time=datetime.now(UTC),
        group_id=memory.group_id,
    )

    if memory.state:
        memory.state.episode_count += 1
        try:
            memory.state.save(memory.spec_dir)
        except Exception:
            logger.debug("Failed to persist episode count")


async def store_failure_analysis(
    spec_dir: Path,
    project_dir: Path,
    failure_type: str,
    root_cause: dict[str, Any],
    failure_context: dict[str, Any] | None = None,
    group_id_mode: str = GroupIdMode.PROJECT,
) -> bool:
    """
    Store a failure analysis result in Graphiti memory.

    This function persists failure analysis data to enable learning from
    past failures and prevent recurring issues.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        failure_type: Type of failure ("qa_rejection", "build_error", "test_failure")
        root_cause: Root cause analysis dict from extract_root_cause()
        failure_context: Optional additional context (errors, issues, subtask_id, etc.)
        group_id_mode: "spec" for isolated memory, "project" for shared (default: project)

    Returns:
        True if saved successfully, False otherwise

    Example:
        >>> root_cause = {
        ...     "category": "syntax_error",
        ...     "description": "Missing closing bracket in function",
        ...     "affected_files": ["src/utils.py"],
        ...     "confidence": 0.9,
        ...     "recommendations": ["Add closing bracket on line 42"],
        ...     "is_recurring": False
        ... }
        >>> await store_failure_analysis(
        ...     spec_dir,
        ...     project_dir,
        ...     "build_error",
        ...     root_cause,
        ...     failure_context={"errors": ["SyntaxError: invalid syntax"]}
        ... )
    """
    if not is_graphiti_enabled():
        logger.debug("Graphiti not enabled, skipping failure storage")
        return False

    try:
        async with _graphiti_session(spec_dir, project_dir, group_id_mode) as memory:
            success = await _store_root_cause_episode(
                memory, failure_type, root_cause, failure_context
            )
            if success:
                logger.info(
                    f"Stored {failure_type} failure analysis in Graphiti "
                    f"(category: {root_cause.get('category', 'unknown')})"
                )
            else:
                logger.warning(f"Failed to store {failure_type} failure analysis")
            return success
    except RuntimeError as e:
        logger.debug(f"Skipping failure storage: {e}")
        return False
    except Exception as e:
        logger.warning(f"Error storing failure analysis: {e}")
        capture_exception(
            e,
            operation="store_failure_analysis",
            failure_type=failure_type,
            category=root_cause.get("category", "unknown"),
        )
        return False


async def store_qa_result(
    spec_dir: Path,
    project_dir: Path,
    qa_iteration: int,
    passed: bool,
    issues: list[dict[str, Any]],
    fixes_applied: list[str] | None = None,
    group_id_mode: str = GroupIdMode.PROJECT,
) -> bool:
    """
    Store a QA result (pass or fail) in Graphiti memory.

    This tracks QA iteration history and patterns over time.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        qa_iteration: QA iteration number (1-indexed)
        passed: Whether QA passed
        issues: List of issues found (empty if passed)
        fixes_applied: List of fixes applied in this iteration
        group_id_mode: "spec" for isolated memory, "project" for shared

    Returns:
        True if saved successfully
    """
    if not is_graphiti_enabled():
        logger.debug("Graphiti not enabled, skipping QA result storage")
        return False

    try:
        async with _graphiti_session(spec_dir, project_dir, group_id_mode) as memory:
            success = await _store_qa_result_episode(
                memory, qa_iteration, passed, issues, fixes_applied
            )
            if success:
                status = "passed" if passed else "failed"
                logger.info(f"Stored QA iteration {qa_iteration} result ({status})")
            return success
    except RuntimeError as e:
        logger.debug(f"Skipping QA result storage: {e}")
        return False
    except Exception as e:
        logger.warning(f"Error storing QA result: {e}")
        capture_exception(
            e,
            operation="store_qa_result",
            qa_iteration=qa_iteration,
            passed=passed,
        )
        return False


# =============================================================================
# Internal Episode Storage Helpers
# =============================================================================


async def _store_root_cause_episode(
    memory: Any,
    failure_type: str,
    root_cause: dict[str, Any],
    failure_context: dict[str, Any] | None,
) -> bool:
    """Store a root cause analysis as a Graphiti episode."""
    try:
        category = root_cause.get("category", "unknown")
        episode_content: dict[str, Any] = {
            "type": EPISODE_TYPE_ROOT_CAUSE,
            "spec_id": getattr(memory, "spec_context_id", None),
            "timestamp": datetime.now(UTC).isoformat(),
            "failure_type": failure_type,
            "category": category,
            "description": root_cause.get("description", ""),
            "affected_files": root_cause.get("affected_files", []),
            "confidence": root_cause.get("confidence", 0.0),
            "recommendations": root_cause.get("recommendations", []),
            "is_recurring": root_cause.get("is_recurring", False),
        }

        if failure_context:
            episode_content["context"] = {
                "errors": failure_context.get("errors", []),
                "issues": failure_context.get("issues", []),
                "subtask_id": failure_context.get("subtask_id"),
            }

        await _add_episode(
            memory,
            name=f"root_cause_{failure_type}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
            body=json.dumps(episode_content),
            source_description=f"Root cause analysis: {failure_type} ({category})",
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to store root cause episode: {e}")
        capture_exception(
            e,
            operation="_store_root_cause_episode",
            failure_type=failure_type,
            category=root_cause.get("category", "unknown"),
        )
        return False


async def _store_qa_result_episode(
    memory: Any,
    qa_iteration: int,
    passed: bool,
    issues: list[dict[str, Any]],
    fixes_applied: list[str] | None,
) -> bool:
    """Store a QA result as a Graphiti episode."""
    try:
        spec_id = getattr(memory, "spec_context_id", None)
        episode_content = {
            "type": EPISODE_TYPE_QA_RESULT,
            "spec_id": spec_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "qa_iteration": qa_iteration,
            "passed": passed,
            "issues_found": len(issues),
            "issues": [
                {
                    "severity": issue.get("severity", "unknown"),
                    "message": issue.get("message", ""),
                    "file": issue.get("file"),
                    "line": issue.get("line"),
                }
                for issue in issues[:10]
            ],
            "fixes_applied": fixes_applied or [],
        }

        status_str = "passed" if passed else "failed"
        await _add_episode(
            memory,
            name=f"qa_result_{spec_id}_iter{qa_iteration:02d}",
            body=json.dumps(episode_content),
            source_description=f"QA iteration {qa_iteration} {status_str} with {len(issues)} issues",
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to store QA result episode: {e}")
        capture_exception(
            e,
            operation="_store_qa_result_episode",
            qa_iteration=qa_iteration,
            passed=passed,
        )
        return False


# =============================================================================
# Public API
# =============================================================================

__all__ = [
    "store_failure_analysis",
    "store_qa_result",
]
