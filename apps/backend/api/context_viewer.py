"""
Context Window Viewer API
==========================

API endpoints for viewing and analyzing context window usage, token statistics,
and optimization metrics. Provides data for the frontend ContextViewer component.

Usage:
    from api.context_viewer import get_context_stats

    # Get comprehensive context statistics
    stats = get_context_stats(spec_dir)
    print(f"Token usage: {stats['token_stats']['total_usage']}")
"""

from __future__ import annotations

import logging
from datetime import UTC
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _ensure_backend_on_path() -> None:
    """Add the backend directory to sys.path if not already present."""
    import sys

    parent_dir = str(Path(__file__).parent.parent)
    if parent_dir not in sys.path:
        sys.path.insert(0, parent_dir)


def get_context_stats(
    spec_dir: Path | None = None,
    project_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Get comprehensive context window statistics.

    Provides detailed information about token usage, session history,
    file prioritization, and optimization metrics.

    Args:
        spec_dir: Spec directory path (optional, for history tracking)
        project_dir: Project directory path (defaults to cwd if not provided)

    Returns:
        Dictionary containing:
        - token_stats: Token usage and budget information
        - session_stats: Session history and coherence metrics
        - optimization_stats: Deduplication and prioritization metrics
        - files_stats: File-level context information
    """
    _ensure_backend_on_path()
    from context.builder import ContextBuilder
    from context.history_tracker import get_history_tracker

    stats = {
        "token_stats": {},
        "session_stats": {},
        "optimization_stats": {},
        "files_stats": {},
    }

    try:
        # Get token budget statistics
        # Create a temporary builder to access token counting capabilities
        effective_project_dir = project_dir or Path.cwd()
        builder = ContextBuilder(effective_project_dir)

        stats["token_stats"] = builder.get_budget_stats()

        # Get session history if spec_dir provided
        if spec_dir and spec_dir.exists():
            tracker = get_history_tracker(spec_dir)
            session_summary = tracker.get_session_summary()

            stats["session_stats"] = {
                "current_turn": session_summary.get("current_turn", 0),
                "total_tokens_sent": session_summary.get("total_tokens_sent", 0),
                "unique_files_sent": session_summary.get("unique_files_sent", 0),
                "recent_files": session_summary.get("recent_files", []),
                "most_frequent_files": session_summary.get("most_frequent", []),
            }
        else:
            stats["session_stats"] = {
                "current_turn": 0,
                "total_tokens_sent": 0,
                "unique_files_sent": 0,
                "recent_files": [],
                "most_frequent_files": [],
            }

        # Optimization statistics (placeholder for now - will be populated by actual context building)
        stats["optimization_stats"] = {
            "deduplication_enabled": True,
            "semantic_search_enabled": False,
            "prioritization_enabled": True,
            "tokens_saved": 0,
            "files_deduplicated": 0,
        }

        # File statistics
        stats["files_stats"] = {
            "total_files_in_context": 0,
            "files_to_modify": 0,
            "files_to_reference": 0,
            "top_priority_files": [],
        }

    except Exception as e:
        logger.error(f"Error getting context stats: {e}", exc_info=True)

    return stats


def get_token_breakdown(spec_dir: Path | None = None) -> dict[str, Any]:
    """
    Get detailed token usage breakdown by file and category.

    Args:
        spec_dir: Spec directory path (optional)

    Returns:
        Dictionary with token breakdown:
        - by_file: Token count per file
        - by_category: Token count by category (to_modify, to_reference, etc.)
        - total: Total token count
    """
    _ensure_backend_on_path()
    from context.history_tracker import get_history_tracker

    breakdown = {
        "by_file": {},
        "by_category": {
            "to_modify": 0,
            "to_reference": 0,
            "patterns": 0,
            "summaries": 0,
        },
        "total": 0,
    }

    try:
        if spec_dir and spec_dir.exists():
            tracker = get_history_tracker(spec_dir)

            # Get token counts by file from history
            for file_path, entry in tracker.history.items():
                breakdown["by_file"][file_path] = entry.token_count
                breakdown["total"] += entry.token_count

    except Exception as e:
        logger.error(f"Error getting token breakdown: {e}", exc_info=True)

    return breakdown


def get_prioritization_scores(
    project_dir: Path,
    task: str | None = None,
) -> dict[str, Any]:
    """
    Get file prioritization scores for the current context.

    Args:
        project_dir: Project directory path
        task: Optional task description for relevance scoring

    Returns:
        Dictionary with prioritization data:
        - scored_files: List of files with their priority scores
        - algorithm: Prioritization algorithm used
        - factors: Weighting factors applied
    """
    _ensure_backend_on_path()
    from context.prioritizer import FilePrioritizer

    result = {
        "scored_files": [],
        "algorithm": "recency + relevance",
        "factors": {
            "relevance_weight": 0.7,
            "recency_weight": 0.3,
            "dependency_boost": 0.2,
        },
    }

    try:
        prioritizer = FilePrioritizer(project_dir)
        result["algorithm"] = "exponential_decay_recency"

        # Get scored files for recently modified Python files
        python_files = [
            str(p.relative_to(project_dir))
            for p in project_dir.rglob("*.py")
            if not any(
                part.startswith(".")
                or part in ("venv", "env", ".venv", "__pycache__", "node_modules")
                for part in p.parts
            )
        ][:50]  # Limit to 50 files

        if python_files:
            scored = prioritizer.get_most_recent_files(python_files, max_results=20)
            result["scored_files"] = [
                {"file": f, "recency_score": s} for f, s in scored
            ]

    except Exception as e:
        logger.error(f"Error getting prioritization scores: {e}", exc_info=True)

    return result


def get_optimization_report(_spec_dir: Path) -> dict[str, Any]:
    """
    Get optimization effectiveness report.

    Shows how well context optimization is working:
    - Token savings from deduplication
    - Effectiveness of prioritization
    - Semantic search hit rate
    - Overall optimization impact

    Args:
        spec_dir: Spec directory path

    Returns:
        Dictionary with optimization metrics
    """
    report = {
        "deduplication": {
            "files_processed": 0,
            "duplicates_found": 0,
            "tokens_saved": 0,
            "savings_percent": 0.0,
        },
        "prioritization": {
            "files_ranked": 0,
            "top_files_selected": 0,
            "relevance_score_avg": 0.0,
        },
        "semantic_search": {
            "queries_made": 0,
            "results_found": 0,
            "avg_similarity": 0.0,
        },
        "overall": {
            "total_tokens_saved": 0,
            "optimization_percent": 0.0,
            "target_percent": 30.0,  # From acceptance criteria
        },
    }

    return report


def export_context_snapshot(spec_dir: Path) -> dict[str, Any]:
    """
    Export a complete snapshot of current context state.

    Useful for debugging and analysis.

    Args:
        spec_dir: Spec directory path

    Returns:
        Complete context snapshot with all metadata
    """
    _ensure_backend_on_path()
    from context.history_tracker import get_history_tracker

    snapshot = {
        "timestamp": "",
        "spec": str(spec_dir.name) if spec_dir else "",
        "context_entries": [],
        "session_summary": {},
        "token_stats": {},
    }

    try:
        # Get current stats
        stats = get_context_stats(spec_dir)
        snapshot["token_stats"] = stats["token_stats"]
        snapshot["session_summary"] = stats["session_stats"]

        # Get detailed context entries
        if spec_dir and spec_dir.exists():
            tracker = get_history_tracker(spec_dir)

            snapshot["context_entries"] = [
                {
                    "file_path": entry.file_path,
                    "token_count": entry.token_count,
                    "sent_count": entry.sent_count,
                    "turn_number": entry.turn_number,
                    "timestamp": entry.timestamp,
                }
                for entry in tracker.history.values()
            ]

        # Add timestamp
        from datetime import datetime

        snapshot["timestamp"] = datetime.now(UTC).isoformat()

    except Exception as e:
        logger.error(f"Error exporting context snapshot: {e}", exc_info=True)

    return snapshot
