"""
Impact analysis operations for code relationships.

Analyzes the impact of code changes by traversing dependency graphs
and calculating relationship strength scores.
"""

import logging
from pathlib import Path

from core.sentry import capture_exception

logger = logging.getLogger(__name__)


class ImpactAnalyzer:
    """
    Manages impact analysis and dependency traversal operations.

    Provides methods for analyzing the impact of code changes,
    computing relationship strength, and identifying tight coupling.
    """

    def __init__(
        self,
        client,
        group_id: str,
        spec_context_id: str,
        project_dir: Path,
    ):
        """
        Initialize impact analyzer.

        Args:
            client: GraphitiClient instance
            group_id: Group ID for memory namespace
            spec_context_id: Spec-specific context ID
            project_dir: Project root directory
        """
        self.client = client
        self.group_id = group_id
        self.spec_context_id = spec_context_id
        self.project_dir = project_dir
        self.logger = logger

    async def calculate_impact(
        self,
        entity_name: str,
        entity_type: str = "function",
        max_depth: int = 3,
    ) -> dict:
        """
        Calculate the impact of changing a code entity.

        Traverses dependency graph to find all code that would be affected
        by changes to the specified entity. For functions, finds all callers
        recursively. For classes, finds all subclasses and usages.

        Args:
            entity_name: Name of the entity (function, class, etc.)
            entity_type: Type of entity (function, class)
            max_depth: Maximum depth to traverse (default: 3)

        Returns:
            Dictionary with:
                - affected_entities: List of entities that depend on this one
                - impact_score: Numeric score indicating impact magnitude
                - depth_analysis: Breakdown of impact by depth level
        """
        try:
            affected_entities = []
            depth_analysis = {}
            visited = set()  # Prevent circular dependencies

            # Traverse dependencies recursively
            await self._traverse_dependencies(
                entity_name=entity_name,
                entity_type=entity_type,
                current_depth=0,
                max_depth=max_depth,
                visited=visited,
                affected_entities=affected_entities,
                depth_analysis=depth_analysis,
            )

            # Calculate impact score based on number of affected entities
            # and their depth (closer dependencies have higher weight)
            impact_score = self._calculate_impact_score(
                affected_entities,
                depth_analysis,
            )

            logger.debug(
                f"Impact analysis for {entity_name}: "
                f"{len(affected_entities)} affected entities, "
                f"score: {impact_score}"
            )

            return {
                "affected_entities": affected_entities,
                "impact_score": impact_score,
                "depth_analysis": depth_analysis,
            }

        except Exception as e:
            logger.warning(f"Failed to calculate impact for {entity_name}: {e}")
            capture_exception(
                e,
                operation="calculate_impact",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                entity_name=entity_name,
            )
            return {
                "affected_entities": [],
                "impact_score": 0,
                "depth_analysis": {},
            }

    async def _traverse_dependencies(
        self,
        entity_name: str,
        entity_type: str,
        current_depth: int,
        max_depth: int,
        visited: set,
        affected_entities: list,
        depth_analysis: dict,
    ):
        """
        Recursively traverse dependency graph.

        Args:
            entity_name: Current entity to analyze
            entity_type: Type of entity (function, class)
            current_depth: Current traversal depth
            max_depth: Maximum depth to traverse
            visited: Set of already-visited entities
            affected_entities: List to accumulate affected entities
            depth_analysis: Dict to track entities by depth
        """
        # Stop if we've already visited this entity
        if entity_name in visited:
            return

        visited.add(entity_name)

        # Stop if we've reached max depth
        if current_depth >= max_depth:
            return

        try:
            # Find entities that depend on this one
            if entity_type == "function":
                # Find all functions that call this function
                callers = await self.client.code_relationships.find_callers(
                    function_name=entity_name
                )

                for caller in callers:
                    caller_name = caller.get("caller")
                    if not caller_name or caller_name in visited:
                        continue

                    # Add to affected entities
                    affected_entities.append(
                        {
                            "name": caller_name,
                            "type": "function",
                            "file_path": caller.get("file_path", ""),
                            "lineno": caller.get("lineno", 0),
                            "depth": current_depth + 1,
                        }
                    )

                    # Track by depth
                    depth_key = f"depth_{current_depth + 1}"
                    if depth_key not in depth_analysis:
                        depth_analysis[depth_key] = []
                    depth_analysis[depth_key].append(caller_name)

                    # Recursively traverse this caller's dependencies
                    await self._traverse_dependencies(
                        entity_name=caller_name,
                        entity_type="function",
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                        visited=visited,
                        affected_entities=affected_entities,
                        depth_analysis=depth_analysis,
                    )

            elif entity_type == "class":
                # Find all classes that inherit from this class
                children = await self.client.code_relationships.find_child_classes(
                    class_name=entity_name
                )

                for child in children:
                    child_name = child.get("child")
                    if not child_name or child_name in visited:
                        continue

                    # Add to affected entities
                    affected_entities.append(
                        {
                            "name": child_name,
                            "type": "class",
                            "file_path": child.get("file_path", ""),
                            "lineno": child.get("lineno", 0),
                            "depth": current_depth + 1,
                        }
                    )

                    # Track by depth
                    depth_key = f"depth_{current_depth + 1}"
                    if depth_key not in depth_analysis:
                        depth_analysis[depth_key] = []
                    depth_analysis[depth_key].append(child_name)

                    # Recursively traverse child class dependencies
                    await self._traverse_dependencies(
                        entity_name=child_name,
                        entity_type="class",
                        current_depth=current_depth + 1,
                        max_depth=max_depth,
                        visited=visited,
                        affected_entities=affected_entities,
                        depth_analysis=depth_analysis,
                    )

        except Exception as e:
            logger.warning(
                f"Error traversing dependencies for {entity_name} "
                f"at depth {current_depth}: {e}"
            )
            # Continue traversal even if one branch fails

    def _calculate_impact_score(
        self,
        affected_entities: list,
        depth_analysis: dict,
    ) -> float:
        """
        Calculate impact score based on affected entities.

        Entities at shallower depths have higher weight (more direct impact).

        Args:
            affected_entities: List of affected entities
            depth_analysis: Breakdown by depth level

        Returns:
            Impact score (0.0 - 100.0)
        """
        if not affected_entities:
            return 0.0

        total_score = 0.0

        # Weight by depth: depth 1 = 1.0, depth 2 = 0.5, depth 3 = 0.25, etc.
        for entity in affected_entities:
            depth = entity.get("depth", 1)
            weight = 1.0 / (2 ** (depth - 1))
            total_score += weight

        # Normalize to 0-100 scale (cap at 100)
        normalized_score = min(total_score * 10, 100.0)

        return round(normalized_score, 2)
