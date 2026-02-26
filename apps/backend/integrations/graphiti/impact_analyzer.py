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

    async def calculate_coupling_score(
        self,
        entity_name: str,
        entity_type: str = "function",
    ) -> dict:
        """
        Calculate relationship strength score to identify tight vs loose coupling.

        Analyzes various coupling indicators:
        - Same-file relationships (tight coupling)
        - Number of references/calls (frequency)
        - Bidirectional dependencies (circular coupling)
        - Cross-module boundaries (loose coupling)

        Args:
            entity_name: Name of the entity to analyze
            entity_type: Type of entity (function, class)

        Returns:
            Dictionary with:
                - coupling_score: Numeric score (0-100, higher = tighter coupling)
                - relationship_strength: Classification (tight, moderate, loose)
                - tight_coupling_indicators: Dict of specific coupling patterns
                - relationships: List of all relationships analyzed
        """
        try:
            relationships = []
            indicators = {
                "same_file_callers": 0,
                "cross_file_callers": 0,
                "bidirectional_dependencies": 0,
                "total_references": 0,
            }

            # Get the entity's file path from first caller/callee
            entity_file_path = None

            # Find all entities that call this one
            if entity_type == "function":
                callers = await self.client.code_relationships.find_callers(
                    function_name=entity_name
                )

                # Also find what this entity calls
                callees = await self.client.code_relationships.find_callees(
                    function_name=entity_name
                )

                # Extract entity's own file from callees
                # (callees have caller=entity_name, so file_path is where entity lives)
                for callee in callees:
                    if callee.get("caller") == entity_name:
                        entity_file_path = callee.get("file_path")
                        break

                # Build relationships list from callers
                for caller in callers:
                    caller_name = caller.get("caller")
                    file_path = caller.get("file_path", "")

                    relationships.append(
                        {
                            "type": "incoming_call",
                            "entity": caller_name,
                            "file_path": file_path,
                            "lineno": caller.get("lineno", 0),
                        }
                    )

                    indicators["total_references"] += 1

                # Analyze coupling indicators
                for rel in relationships:
                    rel_file = rel.get("file_path", "")

                    # Check for same-file relationships
                    if entity_file_path and rel_file:
                        if rel_file == entity_file_path:
                            indicators["same_file_callers"] += 1
                        else:
                            indicators["cross_file_callers"] += 1
                    elif rel_file:
                        indicators["cross_file_callers"] += 1

                # If no entity_file_path was found, use heuristic from relationships
                if not entity_file_path and relationships:
                    # Count relationships by file to detect same-file clustering
                    file_counts = {}
                    for rel in relationships:
                        f = rel.get("file_path", "unknown")
                        file_counts[f] = file_counts.get(f, 0) + 1

                    # If multiple callers are in the same file, that indicates same-file coupling
                    for file_path, count in file_counts.items():
                        if count >= 2:
                            indicators["same_file_callers"] += count

                # Detect bidirectional dependencies
                # Check if any callers are also callees
                caller_names = {caller.get("caller") for caller in callers}
                callee_names = {callee.get("callee") for callee in callees}
                bidirectional = caller_names.intersection(callee_names)
                indicators["bidirectional_dependencies"] = len(bidirectional)

            elif entity_type == "class":
                # For classes, check parent/child relationships
                parents = await self.client.code_relationships.find_parent_classes(
                    class_name=entity_name
                )
                children = await self.client.code_relationships.find_child_classes(
                    class_name=entity_name
                )

                for parent in parents:
                    relationships.append(
                        {
                            "type": "inherits_from",
                            "entity": parent.get("parent"),
                            "file_path": parent.get("file_path", ""),
                        }
                    )

                for child in children:
                    relationships.append(
                        {
                            "type": "inherited_by",
                            "entity": child.get("child"),
                            "file_path": child.get("file_path", ""),
                        }
                    )

                indicators["total_references"] = len(parents) + len(children)

            # Calculate coupling score based on indicators
            coupling_score = self._calculate_coupling_score_from_indicators(indicators)

            # Classify relationship strength
            if coupling_score >= 60:
                strength = "tight"
            elif coupling_score >= 30:
                strength = "moderate"
            else:
                strength = "loose"

            logger.debug(
                f"Coupling analysis for {entity_name}: "
                f"score={coupling_score}, strength={strength}, "
                f"indicators={indicators}"
            )

            return {
                "coupling_score": coupling_score,
                "relationship_strength": strength,
                "tight_coupling_indicators": indicators,
                "relationships": relationships,
            }

        except Exception as e:
            logger.warning(f"Failed to calculate coupling score for {entity_name}: {e}")
            capture_exception(
                e,
                operation="calculate_coupling_score",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                entity_name=entity_name,
            )
            return {
                "coupling_score": 0,
                "relationship_strength": "unknown",
                "tight_coupling_indicators": {},
                "relationships": [],
            }

    def _calculate_coupling_score_from_indicators(
        self,
        indicators: dict,
    ) -> float:
        """
        Calculate coupling score from relationship indicators.

        Args:
            indicators: Dict with coupling indicators

        Returns:
            Coupling score (0-100, higher = tighter coupling)
        """
        score = 0.0

        # Same-file relationships indicate tight coupling
        # Weight: 20 points per same-file caller (capped at 60)
        same_file = indicators.get("same_file_callers", 0)
        score += min(same_file * 20, 60)

        # Bidirectional dependencies are a strong indicator of tight coupling
        # Weight: 35 points per bidirectional dependency (capped at 70)
        bidirectional = indicators.get("bidirectional_dependencies", 0)
        score += min(bidirectional * 35, 70)

        # Combination bonus: same-file + bidirectional = very tight coupling
        # Add extra 20 points if both indicators present
        if same_file > 0 and bidirectional > 0:
            score += 20

        # Total number of references (frequency of use)
        # Weight: 5 points per reference (capped at 25)
        total_refs = indicators.get("total_references", 0)
        score += min(total_refs * 5, 25)

        # Cross-file callers reduce coupling (loose coupling)
        # But we don't subtract, we just don't add as much
        # Already handled by not counting them heavily

        # Cap at 100
        return min(score, 100.0)
