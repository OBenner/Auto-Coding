"""
Pattern Suggestion Engine
=========================

Semantic search and filtering for code patterns in the Graphiti knowledge graph.
Suggests relevant patterns based on task context with optional category filtering.
"""

import hashlib
import json
import logging
from pathlib import Path

from core.sentry import capture_exception

from .queries_pkg.schema import (
    EPISODE_TYPE_PATTERN,
    GroupIdMode,
)

logger = logging.getLogger(__name__)


async def suggest_patterns(
    client,
    group_id: str,
    spec_context_id: str,
    query: str,
    categories: list[str] | None = None,
    num_results: int = 5,
    min_score: float = 0.5,
    include_project_context: bool = True,
    group_id_mode: str = GroupIdMode.SPEC,
    project_dir: Path | None = None,
) -> list[dict]:
    """
    Suggest relevant code patterns based on task context.

    Uses semantic search to find patterns relevant to the current task,
    with optional category filtering to narrow results.

    Args:
        client: GraphitiClient instance
        group_id: Group ID for memory namespace
        spec_context_id: Spec-specific context ID
        query: Task description or search query
        categories: Optional list of pattern categories to filter by
        num_results: Maximum number of patterns to return (default: 5)
        min_score: Minimum relevance score 0.0-1.0 (default: 0.5)
        include_project_context: If True and in SPEC mode, search project-wide
        group_id_mode: "spec" or "project" mode (default: SPEC)
        project_dir: Project root directory (required for project context)

    Returns:
        List of pattern suggestions with metadata:
        [
            {
                "pattern": "Use React hooks for state management",
                "category": "state-management",
                "confidence": 0.95,
                "reasoning": "Pattern describes state flow",
                "score": 0.87,
                "spec_id": "032-feature-name",
                "timestamp": "2024-01-01T12:00:00Z"
            },
            ...
        ]
    """
    try:
        # Determine which group IDs to search
        group_ids = [group_id]

        # In spec mode, optionally include project context too
        if (
            group_id_mode == GroupIdMode.SPEC
            and include_project_context
            and project_dir
        ):
            project_name = project_dir.name
            path_hash = hashlib.md5(
                str(project_dir.resolve()).encode(), usedforsecurity=False
            ).hexdigest()[:8]
            project_group_id = f"project_{project_name}_{path_hash}"
            if project_group_id != group_id:
                group_ids.append(project_group_id)

        # Search with query focused on patterns
        pattern_results = await client.graphiti.search(
            query=f"pattern: {query}",
            group_ids=group_ids,
            num_results=num_results * 3,  # Get more to filter by category
        )

        patterns = []
        for result in pattern_results:
            content = getattr(result, "content", None) or getattr(
                result, "fact", None
            )
            score = getattr(result, "score", 0.0)

            # Filter by minimum score
            if score < min_score:
                continue

            # Only process pattern episodes
            if content and EPISODE_TYPE_PATTERN in str(content):
                try:
                    data = (
                        json.loads(content) if isinstance(content, str) else content
                    )

                    # Ensure data is a dict before processing
                    if not isinstance(data, dict):
                        continue

                    if data.get("type") == EPISODE_TYPE_PATTERN:
                        # Extract pattern metadata
                        pattern_entry = {
                            "pattern": data.get("pattern", ""),
                            "category": data.get("category", "uncategorized"),
                            "confidence": data.get("confidence", 0.0),
                            "reasoning": data.get("reasoning", ""),
                            "score": score,
                            "spec_id": data.get("spec_id", ""),
                            "timestamp": data.get("timestamp", ""),
                        }

                        # Filter by category if specified
                        if categories is None or pattern_entry["category"] in categories:
                            patterns.append(pattern_entry)

                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue

        # Sort by relevance score (highest first)
        patterns.sort(key=lambda x: x.get("score", 0), reverse=True)

        # Limit to requested number of results
        patterns = patterns[:num_results]

        category_filter_str = f" (filtered by: {', '.join(categories)})" if categories else ""
        logger.info(
            f"Found {len(patterns)} pattern suggestions for: {query[:50]}...{category_filter_str}"
        )
        return patterns

    except Exception as e:
        logger.warning(f"Failed to suggest patterns: {e}")
        capture_exception(
            e,
            query_summary=query[:100] if query else "",
            group_id=group_id,
            categories=categories,
            operation="suggest_patterns",
        )
        return []


async def get_patterns_by_category(
    client,
    group_id: str,
    category: str,
    num_results: int = 10,
    min_score: float = 0.0,
) -> list[dict]:
    """
    Retrieve all patterns for a specific category.

    Useful for browsing patterns by category or showing category-specific
    suggestions without a specific task query.

    Args:
        client: GraphitiClient instance
        group_id: Group ID for memory namespace
        category: Pattern category to retrieve
        num_results: Maximum number of patterns to return (default: 10)
        min_score: Minimum relevance score 0.0-1.0 (default: 0.0)

    Returns:
        List of patterns in the specified category
    """
    try:
        # Search with category-focused query
        results = await client.graphiti.search(
            query=f"pattern category: {category}",
            group_ids=[group_id],
            num_results=num_results * 2,
        )

        patterns = []
        for result in results:
            content = getattr(result, "content", None) or getattr(
                result, "fact", None
            )
            score = getattr(result, "score", 0.0)

            # Filter by minimum score
            if score < min_score:
                continue

            # Only process pattern episodes
            if content and EPISODE_TYPE_PATTERN in str(content):
                try:
                    data = (
                        json.loads(content) if isinstance(content, str) else content
                    )

                    # Ensure data is a dict before processing
                    if not isinstance(data, dict):
                        continue

                    if (
                        data.get("type") == EPISODE_TYPE_PATTERN
                        and data.get("category") == category
                    ):
                        patterns.append(
                            {
                                "pattern": data.get("pattern", ""),
                                "category": data.get("category", "uncategorized"),
                                "confidence": data.get("confidence", 0.0),
                                "reasoning": data.get("reasoning", ""),
                                "score": score,
                                "spec_id": data.get("spec_id", ""),
                                "timestamp": data.get("timestamp", ""),
                            }
                        )

                except (json.JSONDecodeError, TypeError, AttributeError):
                    continue

        # Sort by score and limit results
        patterns.sort(key=lambda x: x.get("score", 0), reverse=True)
        patterns = patterns[:num_results]

        logger.info(
            f"Found {len(patterns)} patterns in category '{category}' (group: {group_id})"
        )
        return patterns

    except Exception as e:
        logger.warning(f"Failed to get patterns by category: {e}")
        capture_exception(
            e,
            group_id=group_id,
            category=category,
            operation="get_patterns_by_category",
        )
        return []
