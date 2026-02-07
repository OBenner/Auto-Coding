"""
Pattern Store
=============

Stores and retrieves code patterns with confidence scores in Graphiti memory.
Provides pattern querying, confidence tracking, and usage frequency management.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.sentry import capture_exception

from .queries_pkg.schema import EPISODE_TYPE_PATTERN, GroupIdMode

logger = logging.getLogger(__name__)


class PatternStore:
    """
    Manages pattern storage and retrieval with confidence tracking.

    This class provides high-level methods for:
    - Storing patterns with metadata (category, confidence, usage count)
    - Retrieving patterns by category or similarity
    - Updating pattern confidence scores based on usage
    - Querying for similar patterns to aid code generation
    """

    def __init__(
        self,
        client,
        group_id: str,
        spec_context_id: str,
        group_id_mode: str = GroupIdMode.SPEC,
        project_dir: Path | None = None,
    ):
        """
        Initialize pattern store.

        Args:
            client: GraphitiClient instance
            group_id: Group ID for memory namespace
            spec_context_id: Spec-specific context ID
            group_id_mode: "spec" or "project" mode (default: "spec")
            project_dir: Project root directory (required for project-wide queries)
        """
        self.client = client
        self.group_id = group_id
        self.spec_context_id = spec_context_id
        self.group_id_mode = group_id_mode
        self.project_dir = project_dir

    async def store_pattern(
        self,
        pattern: str,
        category: str = "uncategorized",
        confidence: float = 0.7,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store a code pattern with confidence metadata.

        Args:
            pattern: Description of the code pattern
            category: Pattern category (e.g., "api-design", "error-handling", "state-management")
            confidence: Initial confidence score (0.0 to 1.0)
            metadata: Optional additional metadata (file_path, line_number, code_snippet, etc.)

        Returns:
            True if stored successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            # Normalize confidence to 0.0-1.0 range
            confidence = max(0.0, min(1.0, confidence))

            episode_content = {
                "type": EPISODE_TYPE_PATTERN,
                "spec_id": self.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "pattern": pattern,
                "category": category,
                "confidence": confidence,
                "usage_count": 1,  # Initial usage count
            }

            # Add optional metadata
            if metadata:
                episode_content.update(metadata)

            # Generate unique episode name using hash of pattern + category
            pattern_hash = hashlib.md5(
                f"{pattern}:{category}".encode(), usedforsecurity=False
            ).hexdigest()[:8]
            episode_name = f"pattern_{category}_{pattern_hash}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"

            await self.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Code pattern ({category}): {pattern[:50]}...",
                reference_time=datetime.now(UTC),
                group_id=self.group_id,
            )

            logger.info(
                f"Stored pattern in Graphiti: [{category}] {pattern[:50]}... "
                f"(confidence: {confidence:.2f})"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to store pattern: {e}")
            capture_exception(
                e,
                operation="store_pattern",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                category=category,
                confidence=confidence,
                content_summary=pattern[:100] if pattern else "",
            )
            return False

    async def store_patterns_batch(
        self,
        patterns: list[dict[str, Any]],
    ) -> int:
        """
        Store multiple patterns at once.

        Args:
            patterns: List of pattern dictionaries with keys:
                - pattern (str): Pattern description
                - category (str, optional): Pattern category
                - confidence (float, optional): Confidence score
                - metadata (dict, optional): Additional metadata

        Returns:
            Number of patterns successfully stored
        """
        stored_count = 0

        for pattern_data in patterns:
            pattern = pattern_data.get("pattern", "")
            category = pattern_data.get("category", "uncategorized")
            confidence = pattern_data.get("confidence", 0.7)
            metadata = pattern_data.get("metadata", {})

            success = await self.store_pattern(
                pattern=pattern,
                category=category,
                confidence=confidence,
                metadata=metadata,
            )

            if success:
                stored_count += 1

        logger.info(
            f"Batch stored {stored_count}/{len(patterns)} patterns in Graphiti"
        )
        return stored_count

    async def query_patterns(
        self,
        query: str,
        category: str | None = None,
        min_confidence: float = 0.0,
        num_results: int = 10,
        include_project_patterns: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Query for patterns matching a query string.

        Args:
            query: Search query for finding relevant patterns
            category: Optional category filter (e.g., "api-design", "error-handling")
            min_confidence: Minimum confidence score to include (0.0 to 1.0)
            num_results: Maximum number of results to return
            include_project_patterns: If True and in SPEC mode, include project-wide patterns

        Returns:
            List of matching patterns with metadata:
            [
                {
                    "pattern": "Pattern description",
                    "category": "api-design",
                    "confidence": 0.85,
                    "usage_count": 5,
                    "relevance_score": 0.92,
                    "metadata": {...}
                },
                ...
            ]
        """
        try:
            # Determine which group IDs to search
            group_ids = [self.group_id]

            # In spec mode, optionally include project patterns
            if (
                self.group_id_mode == GroupIdMode.SPEC
                and include_project_patterns
                and self.project_dir
            ):
                project_name = self.project_dir.name
                path_hash = hashlib.md5(
                    str(self.project_dir.resolve()).encode(), usedforsecurity=False
                ).hexdigest()[:8]
                project_group_id = f"project_{project_name}_{path_hash}"
                if project_group_id != self.group_id:
                    group_ids.append(project_group_id)

            # Search for patterns
            results = await self.client.graphiti.search(
                query=query,
                group_ids=group_ids,
                num_results=num_results * 2,  # Get more to filter
            )

            patterns = []
            for result in results:
                # Extract content from result
                content = (
                    getattr(result, "content", None)
                    or getattr(result, "fact", None)
                    or ""
                )

                if not content:
                    continue

                # Try to parse episode content as JSON
                try:
                    episode_data = json.loads(content)
                except (json.JSONDecodeError, TypeError):
                    # If not JSON, skip this result
                    continue

                # Filter to pattern episodes only
                if episode_data.get("type") != EPISODE_TYPE_PATTERN:
                    continue

                # Apply category filter
                if category and episode_data.get("category") != category:
                    continue

                # Apply confidence filter
                pattern_confidence = episode_data.get("confidence", 0.0)
                if pattern_confidence < min_confidence:
                    continue

                # Extract relevance score
                relevance_score = getattr(result, "score", 0.0)

                # Build pattern result
                pattern_result = {
                    "pattern": episode_data.get("pattern", ""),
                    "category": episode_data.get("category", "uncategorized"),
                    "confidence": pattern_confidence,
                    "usage_count": episode_data.get("usage_count", 1),
                    "relevance_score": relevance_score,
                    "timestamp": episode_data.get("timestamp", ""),
                    "metadata": {
                        k: v
                        for k, v in episode_data.items()
                        if k
                        not in [
                            "type",
                            "pattern",
                            "category",
                            "confidence",
                            "usage_count",
                            "timestamp",
                            "spec_id",
                        ]
                    },
                }

                patterns.append(pattern_result)

                # Stop if we have enough results
                if len(patterns) >= num_results:
                    break

            logger.info(
                f"Found {len(patterns)} patterns matching query: {query[:50]}..."
                + (f" (category: {category})" if category else "")
            )
            return patterns

        except Exception as e:
            logger.warning(f"Failed to query patterns: {e}")
            capture_exception(
                e,
                operation="query_patterns",
                group_id=self.group_id,
                query=query[:100] if query else "",
                category=category or "all",
                min_confidence=min_confidence,
            )
            return []

    async def get_patterns_by_category(
        self,
        category: str,
        min_confidence: float = 0.0,
        num_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get all patterns in a specific category.

        Args:
            category: Pattern category (e.g., "api-design", "error-handling")
            min_confidence: Minimum confidence score to include
            num_results: Maximum number of results to return

        Returns:
            List of patterns in the category
        """
        return await self.query_patterns(
            query=f"{category} patterns",
            category=category,
            min_confidence=min_confidence,
            num_results=num_results,
            include_project_patterns=True,
        )

    async def update_pattern_confidence(
        self,
        pattern: str,
        category: str,
        new_confidence: float,
        increment_usage: bool = True,
    ) -> bool:
        """
        Update the confidence score for a pattern.

        Note: This creates a new episode with updated metadata. Graphiti's
        deduplication will merge with existing pattern knowledge over time.

        Args:
            pattern: Pattern description
            category: Pattern category
            new_confidence: New confidence score (0.0 to 1.0)
            increment_usage: If True, increment usage count

        Returns:
            True if updated successfully
        """
        try:
            # Store updated pattern (Graphiti will handle deduplication)
            metadata = {
                "updated": True,
                "previous_update": datetime.now(UTC).isoformat(),
            }

            if increment_usage:
                metadata["usage_increment"] = 1

            return await self.store_pattern(
                pattern=pattern,
                category=category,
                confidence=new_confidence,
                metadata=metadata,
            )

        except Exception as e:
            logger.warning(f"Failed to update pattern confidence: {e}")
            capture_exception(
                e,
                operation="update_pattern_confidence",
                group_id=self.group_id,
                category=category,
                new_confidence=new_confidence,
                content_summary=pattern[:100] if pattern else "",
            )
            return False

    async def get_high_confidence_patterns(
        self,
        min_confidence: float = 0.8,
        num_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get patterns with high confidence scores (team standards).

        Args:
            min_confidence: Minimum confidence threshold (default: 0.8)
            num_results: Maximum number of results

        Returns:
            List of high-confidence patterns
        """
        return await self.query_patterns(
            query="established coding patterns and conventions",
            min_confidence=min_confidence,
            num_results=num_results,
            include_project_patterns=True,
        )

    async def mark_as_team_standard(
        self,
        pattern: str,
        category: str,
    ) -> bool:
        """
        Mark a pattern as a team standard (sets confidence to 1.0).

        Args:
            pattern: Pattern description
            category: Pattern category

        Returns:
            True if marked successfully
        """
        return await self.update_pattern_confidence(
            pattern=pattern,
            category=category,
            new_confidence=1.0,
            increment_usage=True,
        )

    async def mark_as_deprecated(
        self,
        pattern: str,
        category: str,
    ) -> bool:
        """
        Mark a pattern as deprecated (sets confidence to 0.0).

        Args:
            pattern: Pattern description
            category: Pattern category

        Returns:
            True if marked successfully
        """
        metadata = {
            "deprecated": True,
            "deprecated_at": datetime.now(UTC).isoformat(),
        }

        return await self.store_pattern(
            pattern=pattern,
            category=category,
            confidence=0.0,
            metadata=metadata,
        )
