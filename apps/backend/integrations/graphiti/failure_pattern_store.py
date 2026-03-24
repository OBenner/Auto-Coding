"""
Failure Pattern Store
=====================

Stores and retrieves failure patterns from auto-recovery attempts in Graphiti memory.
Provides pattern querying, confidence tracking, and recovery strategy recommendations.
"""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.sentry import capture_exception

from .queries_pkg.schema import (
    EPISODE_TYPE_FAILURE_PATTERN,
    GroupIdMode,
)

logger = logging.getLogger(__name__)


class FailurePatternStore:
    """
    Manages failure pattern storage and retrieval for auto-recovery.

    This class provides high-level methods for:
    - Storing failure patterns with metadata (type, confidence, frequency, affected subtasks)
    - Retrieving patterns by type, category, or similarity
    - Querying for historical patterns to aid recovery strategy selection
    - Tracking pattern occurrences across specs and subtasks
    - Providing pattern-based recovery recommendations
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
        Initialize failure pattern store.

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

    async def store_failure_pattern(
        self,
        pattern_type: str,
        description: str,
        frequency: int = 1,
        confidence: float = 0.7,
        first_seen: str | None = None,
        last_seen: str | None = None,
        affected_subtasks: list[str] | None = None,
        recovery_recommendations: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Store a failure pattern with recovery metadata.

        Args:
            pattern_type: Type of failure pattern (e.g., "recurring_error", "escalating_complexity")
            description: Human-readable description of the pattern
            frequency: Number of times this pattern occurred
            confidence: Confidence score (0.0 to 1.0)
            first_seen: ISO timestamp of first occurrence
            last_seen: ISO timestamp of most recent occurrence
            affected_subtasks: List of subtask IDs where pattern appears
            recovery_recommendations: List of recovery strategy recommendations
            metadata: Optional additional metadata (error_examples, error_category, etc.)

        Returns:
            True if stored successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            # Normalize confidence to 0.0-1.0 range
            confidence = max(0.0, min(1.0, confidence))

            # Use current timestamp if not provided
            now = datetime.now(UTC).isoformat()
            first_seen = first_seen or now
            last_seen = last_seen or now

            episode_content = {
                "type": EPISODE_TYPE_FAILURE_PATTERN,
                "spec_id": self.spec_context_id,
                "timestamp": now,
                "pattern_type": pattern_type,
                "description": description,
                "frequency": frequency,
                "confidence": confidence,
                "first_seen": first_seen,
                "last_seen": last_seen,
                "affected_subtasks": affected_subtasks or [],
                "recovery_recommendations": recovery_recommendations or [],
            }

            # Add optional metadata
            if metadata:
                episode_content.update(metadata)

            # Generate unique episode name using hash of pattern type + description
            pattern_hash = hashlib.md5(
                f"{pattern_type}:{description}".encode(), usedforsecurity=False
            ).hexdigest()[:8]
            episode_name = (
                f"failure_pattern_{pattern_type}_{pattern_hash}_"
                f"{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
            )

            await self.client.graphiti.add_episode(
                name=episode_name,
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Failure pattern ({pattern_type}): {description[:50]}...",
                reference_time=datetime.now(UTC),
                group_id=self.group_id,
            )

            logger.info(
                f"Stored failure pattern in Graphiti: [{pattern_type}] {description[:50]}... "
                f"(confidence: {confidence:.2f}, frequency: {frequency})"
            )
            return True

        except Exception as e:
            logger.warning(f"Failed to store failure pattern: {e}")
            capture_exception(
                e,
                operation="store_failure_pattern",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                pattern_type=pattern_type,
                confidence=confidence,
                content_summary=description[:100] if description else "",
            )
            return False

    async def store_failure_patterns_batch(
        self,
        patterns: list[dict[str, Any]],
    ) -> int:
        """
        Store multiple failure patterns at once.

        Args:
            patterns: List of pattern dictionaries with keys:
                - pattern_type (str): Type of failure pattern
                - description (str): Pattern description
                - frequency (int, optional): Occurrence count
                - confidence (float, optional): Confidence score
                - first_seen (str, optional): First occurrence timestamp
                - last_seen (str, optional): Last occurrence timestamp
                - affected_subtasks (list, optional): Affected subtask IDs
                - recovery_recommendations (list, optional): Recovery recommendations
                - metadata (dict, optional): Additional metadata

        Returns:
            Number of patterns successfully stored
        """
        stored_count = 0

        for pattern_data in patterns:
            pattern_type = pattern_data.get("pattern_type", "unknown")
            description = pattern_data.get("description", "")
            frequency = pattern_data.get("frequency", 1)
            confidence = pattern_data.get("confidence", 0.7)
            first_seen = pattern_data.get("first_seen")
            last_seen = pattern_data.get("last_seen")
            affected_subtasks = pattern_data.get("affected_subtasks", [])
            recovery_recommendations = pattern_data.get("recovery_recommendations", [])
            metadata = pattern_data.get("metadata", {})

            success = await self.store_failure_pattern(
                pattern_type=pattern_type,
                description=description,
                frequency=frequency,
                confidence=confidence,
                first_seen=first_seen,
                last_seen=last_seen,
                affected_subtasks=affected_subtasks,
                recovery_recommendations=recovery_recommendations,
                metadata=metadata,
            )

            if success:
                stored_count += 1

        logger.info(
            f"Batch stored {stored_count}/{len(patterns)} failure patterns in Graphiti"
        )
        return stored_count

    async def query_failure_patterns(
        self,
        query: str,
        pattern_type: str | None = None,
        min_confidence: float = 0.0,
        min_frequency: int = 1,
        num_results: int = 10,
        include_project_patterns: bool = True,
    ) -> list[dict[str, Any]]:
        """
        Query for failure patterns matching a query string.

        Args:
            query: Search query for finding relevant patterns
            pattern_type: Optional pattern type filter (e.g., "recurring_error", "circular_fix")
            min_confidence: Minimum confidence score to include (0.0 to 1.0)
            min_frequency: Minimum frequency count to include
            num_results: Maximum number of results to return
            include_project_patterns: If True and in SPEC mode, include project-wide patterns

        Returns:
            List of matching failure patterns with metadata:
            [
                {
                    "pattern_type": "recurring_error",
                    "description": "Pattern description",
                    "frequency": 5,
                    "confidence": 0.85,
                    "first_seen": "2024-01-01T00:00:00Z",
                    "last_seen": "2024-01-05T12:00:00Z",
                    "affected_subtasks": ["subtask-1", "subtask-2"],
                    "recovery_recommendations": ["Try different approach"],
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

                # Filter to failure pattern episodes only
                if episode_data.get("type") != EPISODE_TYPE_FAILURE_PATTERN:
                    continue

                # Apply pattern type filter
                if pattern_type and episode_data.get("pattern_type") != pattern_type:
                    continue

                # Apply confidence filter
                pattern_confidence = episode_data.get("confidence", 0.0)
                if pattern_confidence < min_confidence:
                    continue

                # Apply frequency filter
                pattern_frequency = episode_data.get("frequency", 1)
                if pattern_frequency < min_frequency:
                    continue

                # Extract relevance score
                relevance_score = getattr(result, "score", 0.0)

                # Build pattern result
                pattern_result = {
                    "pattern_type": episode_data.get("pattern_type", "unknown"),
                    "description": episode_data.get("description", ""),
                    "frequency": pattern_frequency,
                    "confidence": pattern_confidence,
                    "first_seen": episode_data.get("first_seen", ""),
                    "last_seen": episode_data.get("last_seen", ""),
                    "affected_subtasks": episode_data.get("affected_subtasks", []),
                    "recovery_recommendations": episode_data.get(
                        "recovery_recommendations", []
                    ),
                    "relevance_score": relevance_score,
                    "timestamp": episode_data.get("timestamp", ""),
                    "metadata": {
                        k: v
                        for k, v in episode_data.items()
                        if k
                        not in [
                            "type",
                            "pattern_type",
                            "description",
                            "frequency",
                            "confidence",
                            "first_seen",
                            "last_seen",
                            "affected_subtasks",
                            "recovery_recommendations",
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
                f"Found {len(patterns)} failure patterns matching query: {query[:50]}..."
                + (f" (type: {pattern_type})" if pattern_type else "")
            )
            return patterns

        except Exception as e:
            logger.warning(f"Failed to query failure patterns: {e}")
            capture_exception(
                e,
                operation="query_failure_patterns",
                group_id=self.group_id,
                query=query[:100] if query else "",
                pattern_type=pattern_type or "all",
                min_confidence=min_confidence,
            )
            return []

    async def get_patterns_by_type(
        self,
        pattern_type: str,
        min_confidence: float = 0.0,
        min_frequency: int = 1,
        num_results: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get all failure patterns of a specific type.

        Args:
            pattern_type: Pattern type (e.g., "recurring_error", "circular_fix")
            min_confidence: Minimum confidence score to include
            min_frequency: Minimum frequency count to include
            num_results: Maximum number of results to return

        Returns:
            List of patterns of the specified type
        """
        return await self.query_failure_patterns(
            query=f"{pattern_type} failure patterns",
            pattern_type=pattern_type,
            min_confidence=min_confidence,
            min_frequency=min_frequency,
            num_results=num_results,
            include_project_patterns=True,
        )

    async def get_patterns_for_subtask(
        self,
        subtask_id: str,
        min_confidence: float = 0.0,
        num_results: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get failure patterns that affected a specific subtask.

        Args:
            subtask_id: Subtask identifier
            min_confidence: Minimum confidence score to include
            num_results: Maximum number of results to return

        Returns:
            List of patterns affecting the subtask
        """
        try:
            # Search for patterns mentioning the subtask
            query = f"failure patterns for subtask {subtask_id}"
            patterns = await self.query_failure_patterns(
                query=query,
                min_confidence=min_confidence,
                num_results=num_results * 2,  # Get more to filter
                include_project_patterns=True,
            )

            # Filter to patterns that include this subtask
            filtered_patterns = [
                p for p in patterns if subtask_id in p.get("affected_subtasks", [])
            ]

            return filtered_patterns[:num_results]

        except Exception as e:
            logger.warning(f"Failed to get patterns for subtask {subtask_id}: {e}")
            return []

    async def get_high_frequency_patterns(
        self,
        min_frequency: int = 3,
        min_confidence: float = 0.7,
        num_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Get failure patterns that occur frequently (common issues).

        Args:
            min_frequency: Minimum frequency threshold (default: 3)
            min_confidence: Minimum confidence threshold
            num_results: Maximum number of results

        Returns:
            List of high-frequency failure patterns
        """
        return await self.query_failure_patterns(
            query="frequent recurring failure patterns",
            min_confidence=min_confidence,
            min_frequency=min_frequency,
            num_results=num_results,
            include_project_patterns=True,
        )

    async def get_recovery_recommendations(
        self,
        failure_context: str,
        pattern_type: str | None = None,
        num_recommendations: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get recovery recommendations based on similar failure patterns.

        Args:
            failure_context: Description of the current failure
            pattern_type: Optional pattern type to filter by
            num_recommendations: Maximum number of recommendations to return

        Returns:
            List of recommendations with context:
            [
                {
                    "recommendation": "Try a different approach",
                    "pattern_type": "recurring_error",
                    "confidence": 0.85,
                    "frequency": 5,
                    "similar_patterns": ["pattern1", "pattern2"]
                },
                ...
            ]
        """
        try:
            # Query for similar patterns
            patterns = await self.query_failure_patterns(
                query=failure_context,
                pattern_type=pattern_type,
                min_confidence=0.5,
                num_results=num_recommendations * 2,
                include_project_patterns=True,
            )

            # Extract unique recommendations
            recommendations_map: dict[str, dict[str, Any]] = {}

            for pattern in patterns:
                for rec in pattern.get("recovery_recommendations", []):
                    if rec not in recommendations_map:
                        recommendations_map[rec] = {
                            "recommendation": rec,
                            "pattern_type": pattern.get("pattern_type"),
                            "confidence": pattern.get("confidence", 0.0),
                            "frequency": pattern.get("frequency", 1),
                            "similar_patterns": [],
                        }
                        recommendations_map[rec]["similar_patterns"].append(
                            pattern.get("description", "")
                        )

            # Convert to list and sort by confidence and frequency
            recommendations = list(recommendations_map.values())
            recommendations.sort(
                key=lambda x: (x["confidence"], x["frequency"]), reverse=True
            )

            return recommendations[:num_recommendations]

        except Exception as e:
            logger.warning(f"Failed to get recovery recommendations: {e}")
            return []

    async def update_pattern_frequency(
        self,
        pattern_type: str,
        description: str,
        increment: int = 1,
        new_confidence: float | None = None,
        additional_subtasks: list[str] | None = None,
    ) -> bool:
        """
        Update the frequency and optionally confidence for a failure pattern.

        Note: This creates a new episode with updated metadata. Graphiti's
        deduplication will merge with existing pattern knowledge over time.

        Args:
            pattern_type: Pattern type
            description: Pattern description
            increment: Amount to increment frequency (default: 1)
            new_confidence: Optional new confidence score
            additional_subtasks: Optional list of additional affected subtasks

        Returns:
            True if updated successfully
        """
        try:
            # Query for the existing pattern
            existing_patterns = await self.query_failure_patterns(
                query=description,
                pattern_type=pattern_type,
                num_results=1,
            )

            if not existing_patterns:
                # Pattern doesn't exist yet, create it
                return await self.store_failure_pattern(
                    pattern_type=pattern_type,
                    description=description,
                    frequency=increment,
                    confidence=new_confidence or 0.7,
                    affected_subtasks=additional_subtasks,
                )

            # Get existing pattern data
            existing = existing_patterns[0]
            new_frequency = existing.get("frequency", 1) + increment
            updated_confidence = new_confidence or existing.get("confidence", 0.7)
            updated_subtasks = existing.get("affected_subtasks", [])
            if additional_subtasks:
                updated_subtasks.extend(additional_subtasks)
                updated_subtasks = list(set(updated_subtasks))  # Remove duplicates

            # Store updated pattern
            return await self.store_failure_pattern(
                pattern_type=pattern_type,
                description=description,
                frequency=new_frequency,
                confidence=updated_confidence,
                first_seen=existing.get("first_seen"),
                last_seen=datetime.now(UTC).isoformat(),
                affected_subtasks=updated_subtasks,
                recovery_recommendations=existing.get("recovery_recommendations", []),
                metadata={
                    "updated": True,
                    "frequency_increment": increment,
                    "previous_frequency": existing.get("frequency", 1),
                },
            )

        except Exception as e:
            logger.warning(f"Failed to update pattern frequency: {e}")
            capture_exception(
                e,
                operation="update_pattern_frequency",
                group_id=self.group_id,
                pattern_type=pattern_type,
                content_summary=description[:100] if description else "",
            )
            return False

    async def get_pattern_statistics(self) -> dict[str, Any]:
        """
        Get statistics about stored failure patterns.

        Returns:
            Dict with pattern statistics:
            {
                "total_patterns": int,
                "patterns_by_type": {...},
                "most_common_patterns": [...],
                "high_frequency_patterns": int,
                "average_confidence": float
            }
        """
        try:
            # Query for all patterns
            all_patterns = await self.query_failure_patterns(
                query="failure patterns",
                num_results=100,
                include_project_patterns=True,
            )

            if not all_patterns:
                return {
                    "total_patterns": 0,
                    "patterns_by_type": {},
                    "most_common_patterns": [],
                    "high_frequency_patterns": 0,
                    "average_confidence": 0.0,
                }

            # Count patterns by type
            patterns_by_type: dict[str, int] = {}
            total_confidence = 0.0
            high_frequency_count = 0

            for pattern in all_patterns:
                pattern_type = pattern.get("pattern_type", "unknown")
                patterns_by_type[pattern_type] = (
                    patterns_by_type.get(pattern_type, 0) + 1
                )
                total_confidence += pattern.get("confidence", 0.0)
                if pattern.get("frequency", 1) >= 3:
                    high_frequency_count += 1

            # Get most common patterns (by frequency)
            most_common = sorted(
                all_patterns, key=lambda x: x.get("frequency", 0), reverse=True
            )[:5]

            return {
                "total_patterns": len(all_patterns),
                "patterns_by_type": patterns_by_type,
                "most_common_patterns": [
                    {
                        "pattern_type": p.get("pattern_type"),
                        "description": p.get("description"),
                        "frequency": p.get("frequency"),
                    }
                    for p in most_common
                ],
                "high_frequency_patterns": high_frequency_count,
                "average_confidence": total_confidence / len(all_patterns)
                if all_patterns
                else 0.0,
            }

        except Exception as e:
            logger.warning(f"Failed to get pattern statistics: {e}")
            return {
                "total_patterns": 0,
                "patterns_by_type": {},
                "most_common_patterns": [],
                "high_frequency_patterns": 0,
                "average_confidence": 0.0,
            }
