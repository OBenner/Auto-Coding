"""
Conflict Analysis
=================

Core logic for detecting and analyzing conflicts between task changes.

This module contains:
- Conflict detection algorithms
- Severity assessment logic
- Implicit conflict detection
- Range overlap checking
"""

from __future__ import annotations

import logging
from collections import defaultdict

from .compatibility_rules import CompatibilityRule
from .rename_detector import detect_rename, extract_renamed_identifiers
from .types import (
    ChangeType,
    ConflictRegion,
    ConflictSeverity,
    FileAnalysis,
    MergeStrategy,
    SemanticChange,
)

# Import debug utilities
try:
    from debug import debug, debug_detailed, debug_verbose
except ImportError:

    def debug(*args, **kwargs):
        """No-op fallback when debug module is unavailable."""

    def debug_detailed(*args, **kwargs):
        """No-op fallback when debug module is unavailable."""

    def debug_verbose(*args, **kwargs):
        """No-op fallback when debug module is unavailable."""


logger = logging.getLogger(__name__)
MODULE = "merge.conflict_analysis"


def detect_conflicts(
    task_analyses: dict[str, FileAnalysis],
    rule_index: dict[tuple[ChangeType, ChangeType], CompatibilityRule],
) -> list[ConflictRegion]:
    """
    Detect conflicts between multiple task changes to the same file.

    Args:
        task_analyses: Map of task_id -> FileAnalysis
        rule_index: Indexed compatibility rules for fast lookup

    Returns:
        List of detected conflict regions
    """
    task_ids = list(task_analyses.keys())
    debug(
        MODULE,
        f"Detecting conflicts between {len(task_analyses)} tasks",
        tasks=task_ids,
    )

    if len(task_analyses) <= 1:
        debug(MODULE, "No conflicts possible with 0-1 tasks")
        return []  # No conflicts possible with 0-1 tasks

    conflicts: list[ConflictRegion] = []

    # Group changes by location
    location_changes: dict[str, list[tuple[str, SemanticChange]]] = defaultdict(list)

    for task_id, analysis in task_analyses.items():
        debug_detailed(
            MODULE,
            f"Processing task {task_id}",
            changes_count=len(analysis.changes),
            file=analysis.file_path,
        )
        for change in analysis.changes:
            location_changes[change.location].append((task_id, change))

    debug_detailed(MODULE, f"Grouped changes into {len(location_changes)} locations")

    # Analyze each location for conflicts
    for location, task_changes in location_changes.items():
        if len(task_changes) <= 1:
            continue  # No conflict at this location

        debug_verbose(
            MODULE,
            f"Checking location {location}",
            task_changes_count=len(task_changes),
        )

        file_path = next(iter(task_analyses.values())).file_path
        conflict = analyze_location_conflict(
            file_path, location, task_changes, rule_index
        )
        if conflict:
            debug_detailed(
                MODULE,
                f"Conflict detected at {location}",
                severity=conflict.severity.value,
                can_auto_merge=conflict.can_auto_merge,
                tasks=conflict.tasks_involved,
            )
            conflicts.append(conflict)

    # Also check for implicit conflicts (e.g., changes to related code)
    implicit_conflicts = detect_implicit_conflicts(task_analyses)
    if implicit_conflicts:
        debug_detailed(MODULE, f"Found {len(implicit_conflicts)} implicit conflicts")
    conflicts.extend(implicit_conflicts)

    return conflicts


def analyze_location_conflict(
    file_path: str,
    location: str,
    task_changes: list[tuple[str, SemanticChange]],
    rule_index: dict[tuple[ChangeType, ChangeType], CompatibilityRule],
) -> ConflictRegion | None:
    """
    Analyze changes at a specific location for conflicts.

    Args:
        file_path: Path to the file being analyzed
        location: Location identifier (e.g., "function:main")
        task_changes: List of (task_id, change) tuples for this location
        rule_index: Indexed compatibility rules

    Returns:
        ConflictRegion if conflicts exist, None otherwise
    """
    tasks = [tc[0] for tc in task_changes]
    changes = [tc[1] for tc in task_changes]
    change_types = [c.change_type for c in changes]

    # Check if all changes target the same thing
    targets = {c.target for c in changes}
    if len(targets) > 1:
        # Different targets at same location - likely compatible
        # (e.g., adding two different functions)
        return None

    # Check pairwise compatibility
    all_compatible = True
    final_strategy: MergeStrategy | None = None
    reasons = []

    for i, (type_a, change_a) in enumerate(zip(change_types, changes)):
        for type_b, change_b in zip(change_types[i + 1 :], changes[i + 1 :]):
            rule = rule_index.get((type_a, type_b))

            if rule:
                if not rule.compatible:
                    all_compatible = False
                    reasons.append(rule.reason)
                elif rule.strategy:
                    final_strategy = rule.strategy
            else:
                # No rule - conservative default
                all_compatible = False
                reasons.append(f"No rule for {type_a.value} + {type_b.value}")

    # Determine severity
    if all_compatible:
        severity = ConflictSeverity.NONE
    else:
        severity = assess_severity(change_types, changes)

    return ConflictRegion(
        file_path=file_path,
        location=location,
        tasks_involved=tasks,
        change_types=change_types,
        severity=severity,
        can_auto_merge=all_compatible,
        merge_strategy=final_strategy if all_compatible else MergeStrategy.AI_REQUIRED,
        reason=" | ".join(reasons) if reasons else "Changes are compatible",
    )


def assess_severity(
    change_types: list[ChangeType],
    changes: list[SemanticChange],
) -> ConflictSeverity:
    """
    Assess the severity of a conflict.

    Args:
        change_types: List of change types involved
        changes: List of semantic changes

    Returns:
        Assessed conflict severity level
    """
    # Critical: Both tasks modify core logic
    modify_types = {
        ChangeType.MODIFY_FUNCTION,
        ChangeType.MODIFY_METHOD,
        ChangeType.MODIFY_CLASS,
    }
    modify_count = sum(1 for ct in change_types if ct in modify_types)

    if modify_count >= 2:
        # Check if they modify the exact same lines
        line_ranges = [(c.line_start, c.line_end) for c in changes]
        if ranges_overlap(line_ranges):
            return ConflictSeverity.CRITICAL

    # High: Structural changes that could break compilation
    structural_types = {
        ChangeType.WRAP_JSX,
        ChangeType.UNWRAP_JSX,
        ChangeType.REMOVE_FUNCTION,
        ChangeType.REMOVE_CLASS,
    }
    if any(ct in structural_types for ct in change_types):
        return ConflictSeverity.HIGH

    # Medium: Modifications to same function/method
    if modify_count >= 1:
        return ConflictSeverity.MEDIUM

    # Low: Likely resolvable with AI
    return ConflictSeverity.LOW


def ranges_overlap(ranges: list[tuple[int, int]]) -> bool:
    """
    Check if any line ranges overlap.

    Args:
        ranges: List of (start_line, end_line) tuples

    Returns:
        True if any ranges overlap, False otherwise
    """
    sorted_ranges = sorted(ranges)
    for i in range(len(sorted_ranges) - 1):
        if sorted_ranges[i][1] >= sorted_ranges[i + 1][0]:
            return True
    return False


def detect_implicit_conflicts(
    task_analyses: dict[str, FileAnalysis],
) -> list[ConflictRegion]:
    """
    Detect implicit conflicts not caught by location analysis.

    This includes conflicts like:
    - Function rename + function call changes
    - Import removal + usage
    - Variable rename + references

    Args:
        task_analyses: Map of task_id -> FileAnalysis

    Returns:
        List of implicit conflict regions
    """
    conflicts = []

    # Check for function rename + function call conflicts
    # If task A renames a function and task B modifies/uses the old name
    rename_conflicts = _detect_rename_conflicts(task_analyses)
    if rename_conflicts:
        debug_detailed(
            MODULE,
            f"Found {len(rename_conflicts)} rename-related conflicts",
        )
        conflicts.extend(rename_conflicts)

    # Check for import removal + usage
    # (If task A removes an import and task B uses it)
    # TODO: Implement import conflict detection

    # Check for variable rename + references
    # TODO: Implement variable rename conflict detection

    return conflicts


def _detect_rename_conflicts(
    task_analyses: dict[str, FileAnalysis],
) -> list[ConflictRegion]:
    """
    Detect conflicts related to renames.

    This catches cases where:
    - Task A renames a function/variable
    - Task B modifies or uses the old name

    Args:
        task_analyses: Map of task_id -> FileAnalysis

    Returns:
        List of rename-related conflict regions
    """
    conflicts = []

    # Group analyses by file path
    by_file: dict[str, dict[str, FileAnalysis]] = defaultdict(dict)
    for task_id, analysis in task_analyses.items():
        by_file[analysis.file_path][task_id] = analysis

    # Check each file for rename conflicts
    for file_path, file_analyses in by_file.items():
        # Find all rename changes across tasks
        renames_by_task: dict[str, dict[str, str]] = defaultdict(dict)

        for task_id, analysis in file_analyses.items():
            for change in analysis.changes:
                if change.change_type in (
                    ChangeType.RENAME_FUNCTION,
                    ChangeType.RENAME_VARIABLE,
                ):
                    # Extract old_name -> new_name mapping from metadata
                    if change.metadata:
                        old_name = change.metadata.get("old_name")
                        new_name = change.metadata.get("new_name")
                        if old_name and new_name:
                            renames_by_task[task_id][old_name] = new_name

        # If no renames found, no conflicts to check
        if not renames_by_task:
            continue

        # Check if any other task modifies/uses the old names
        for rename_task, renames in renames_by_task.items():
            for other_task, other_analysis in file_analyses.items():
                if other_task == rename_task:
                    continue

                # Check if other task modifies the old name
                for change in other_analysis.changes:
                    # Check if this change references a renamed entity
                    for old_name, new_name in renames.items():
                        if _references_entity(change, old_name):
                            # Found implicit conflict: rename + modify/call old name
                            conflicts.append(
                                ConflictRegion(
                                    file_path=file_path,
                                    location=change.location,
                                    tasks_involved=[rename_task, other_task],
                                    change_types=[
                                        ChangeType.RENAME_FUNCTION
                                        if "function" in change.location
                                        else ChangeType.RENAME_VARIABLE,
                                        change.change_type,
                                    ],
                                    severity=ConflictSeverity.HIGH,
                                    can_auto_merge=False,
                                    merge_strategy=MergeStrategy.AI_REQUIRED,
                                    reason=f"Task {rename_task} renamed '{old_name}' to '{new_name}', but task {other_task} modifies the old name",
                                )
                            )
                            debug_verbose(
                                MODULE,
                                f"Rename conflict detected",
                                file=file_path,
                                rename_task=rename_task,
                                other_task=other_task,
                                old_name=old_name,
                                new_name=new_name,
                                location=change.location,
                            )

    return conflicts


def _references_entity(change: SemanticChange, entity_name: str) -> bool:
    """
    Check if a semantic change references an entity by name.

    Args:
        change: Semantic change to check
        entity_name: Name of entity to look for

    Returns:
        True if the change references the entity
    """
    # Check if target matches
    if change.target == entity_name:
        return True

    # Check if target contains entity_name (e.g., "calling foo")
    if entity_name in change.target.lower():
        return True

    # Check content_before/content_after for references
    if change.content_before and entity_name in change.content_before:
        return True

    if change.content_after and entity_name in change.content_after:
        return True

    # For MODIFY_FUNCTION, check if it's modifying the entity
    if change.change_type == ChangeType.MODIFY_FUNCTION:
        if change.target == entity_name:
            return True

    return False


def analyze_compatibility(
    change_a: SemanticChange,
    change_b: SemanticChange,
    rule_index: dict[tuple[ChangeType, ChangeType], CompatibilityRule],
) -> tuple[bool, MergeStrategy | None, str]:
    """
    Analyze compatibility between two specific changes.

    Args:
        change_a: First semantic change
        change_b: Second semantic change
        rule_index: Indexed compatibility rules

    Returns:
        Tuple of (compatible, strategy, reason)
    """
    rule = rule_index.get((change_a.change_type, change_b.change_type))

    if rule:
        return (rule.compatible, rule.strategy, rule.reason)
    else:
        return (False, MergeStrategy.AI_REQUIRED, "No compatibility rule defined")
