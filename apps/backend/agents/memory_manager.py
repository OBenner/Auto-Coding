"""
Memory Management for Agent System
===================================

Handles session memory storage using dual-layer approach:
- PRIMARY: Graphiti (when enabled) - semantic search, cross-session context
- FALLBACK: File-based memory - zero dependencies, always available
"""

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from core.sentry import capture_exception

if TYPE_CHECKING:
    from agents.session_context import SessionContext

from debug import (
    debug,
    debug_detailed,
    debug_error,
    debug_section,
    debug_success,
    debug_warning,
    is_debug_enabled,
)
from integrations.graphiti.config import get_graphiti_status, is_graphiti_enabled

# Import from parent memory package
# Now safe since this module is named memory_manager (not memory)
from memory import save_session_insights as save_file_based_memory
from memory.graphiti_helpers import get_graphiti_memory
from memory.patterns import (
    save_detected_patterns_from_errors,
    save_detected_patterns_from_naming,
    save_detected_patterns_from_organization,
)

logger = logging.getLogger(__name__)


async def get_session_context(
    spec_dir: Path,
    project_dir: Path,
) -> "SessionContext | None":
    """
    Get SessionContext instance for managing conversation history in Graphiti.

    This provides access to session context storage and retrieval for:
    - Persisting conversation history across restarts
    - Tracking code references
    - Optimizing context window

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory

    Returns:
        SessionContext instance or None if initialization fails
    """
    try:
        from agents.session_context import SessionContext

        # Create SessionContext instance
        session_context = SessionContext(
            spec_dir=spec_dir,
            project_dir=project_dir,
        )

        # Initialize Graphiti connection
        if await session_context.initialize():
            debug_success(
                "memory",
                "SessionContext initialized",
                spec_dir=str(spec_dir),
            )
            return session_context
        else:
            debug_warning(
                "memory",
                "SessionContext initialization failed - Graphiti not available",
            )
            return None

    except Exception as e:
        debug_error(
            "memory",
            f"Failed to create SessionContext: {e}",
        )
        logger.warning(f"Failed to create SessionContext: {e}")
        capture_exception(
            e,
            operation="get_session_context",
            spec_dir=str(spec_dir),
        )
        return None


def debug_memory_system_status() -> None:
    """
    Print memory system status for debugging.

    Called at startup when DEBUG=true to show memory configuration.
    """
    if not is_debug_enabled():
        return

    debug_section("memory", "Memory System Status")

    # Get Graphiti status
    graphiti_status = get_graphiti_status()

    debug(
        "memory",
        "Memory system configuration",
        primary_system="Graphiti"
        if graphiti_status.get("available")
        else "File-based (fallback)",
        graphiti_enabled=graphiti_status.get("enabled"),
        graphiti_available=graphiti_status.get("available"),
    )

    if graphiti_status.get("enabled"):
        debug_detailed(
            "memory",
            "Graphiti configuration",
            host=graphiti_status.get("host"),
            port=graphiti_status.get("port"),
            database=graphiti_status.get("database"),
            llm_provider=graphiti_status.get("llm_provider"),
            embedder_provider=graphiti_status.get("embedder_provider"),
        )

        if not graphiti_status.get("available"):
            debug_warning(
                "memory",
                "Graphiti not available",
                reason=graphiti_status.get("reason"),
                errors=graphiti_status.get("errors"),
            )
            debug("memory", "Will use file-based memory as fallback")
        else:
            debug_success("memory", "Graphiti ready as PRIMARY memory system")
    else:
        debug(
            "memory",
            "Graphiti disabled, using file-based memory only",
            note="Set GRAPHITI_ENABLED=true to enable Graphiti",
        )


async def get_pattern_suggestions(
    spec_dir: Path,
    project_dir: Path,
    query: str,
    categories: list[str] | None = None,
    num_results: int = 5,
    min_score: float = 0.5,
) -> str | None:
    """
    Retrieve pattern suggestions from Graphiti for the current task.

    This searches the knowledge graph for relevant code patterns that match
    the task query, returning categorized patterns with confidence scores.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        query: Task description or search query
        categories: Optional list of pattern categories to filter by
        num_results: Maximum number of patterns to return (default: 5)
        min_score: Minimum relevance score 0.0-1.0 (default: 0.5)

    Returns:
        Formatted pattern suggestions string or None if unavailable
    """
    if is_debug_enabled():
        debug(
            "memory",
            "Retrieving pattern suggestions",
            query=query[:100],
            categories=categories,
            num_results=num_results,
        )

    if not is_graphiti_enabled():
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping pattern suggestions")
        return None

    memory = None
    try:
        # Get GraphitiMemory instance
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            if is_debug_enabled():
                debug_warning(
                    "memory", "GraphitiMemory not available for pattern suggestions"
                )
            return None

        # Import pattern suggester
        from integrations.graphiti.pattern_suggester import suggest_patterns

        # Get group_id and spec_context_id from memory
        group_id = memory.group_id
        spec_context_id = memory.spec_context_id

        if is_debug_enabled():
            debug_detailed(
                "memory",
                "Searching for pattern suggestions",
                query=query[:200],
                group_id=group_id,
                categories=categories,
            )

        # Get pattern suggestions
        patterns = await suggest_patterns(
            client=memory.client,
            group_id=group_id,
            spec_context_id=spec_context_id,
            query=query,
            categories=categories,
            num_results=num_results,
            min_score=min_score,
            include_project_context=True,
            project_dir=project_dir,
        )

        if is_debug_enabled():
            debug(
                "memory",
                "Pattern suggestion retrieval complete",
                patterns_found=len(patterns) if patterns else 0,
            )

        if not patterns:
            if is_debug_enabled():
                debug("memory", "No pattern suggestions found")
            return None

        # Format the patterns
        sections = ["## Pattern Suggestions\n"]
        sections.append("_Relevant code patterns from previous implementations:_\n")

        # Group patterns by category
        by_category: dict[str, list[dict]] = {}
        for pattern in patterns:
            category = pattern.get("category", "uncategorized")
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(pattern)

        # Format each category
        for category, category_patterns in by_category.items():
            sections.append(f"### {category.replace('-', ' ').title()}\n")
            for p in category_patterns:
                pattern_text = p.get("pattern", "")
                reasoning = p.get("reasoning", "")
                confidence = p.get("confidence", 0.0)
                score = p.get("score", 0.0)
                spec_id = p.get("spec_id", "")

                sections.append(f"- **Pattern**: {pattern_text}\n")
                if reasoning:
                    sections.append(f"  _Reasoning_: {reasoning}\n")
                sections.append(
                    f"  _Confidence_: {confidence:.2f} | _Relevance_: {score:.2f}"
                )
                if spec_id:
                    sections.append(f" | _From_: {spec_id}")
                sections.append("\n")

        formatted = "".join(sections)

        if is_debug_enabled():
            debug_success(
                "memory",
                "Pattern suggestions formatted",
                categories=len(by_category),
                total_patterns=len(patterns),
            )

        return formatted

    except Exception as e:
        if is_debug_enabled():
            debug_error("memory", "Failed to get pattern suggestions", error=str(e))
        logger.warning(f"Failed to get pattern suggestions: {e}")
        capture_exception(
            e,
            query_summary=query[:100] if query else "",
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
            operation="get_pattern_suggestions",
        )
        return None
    finally:
        # Close memory connection if we opened it
        if memory is not None:
            try:
                await memory.close()
            except Exception:
                pass


async def get_failure_patterns(
    spec_dir: Path,
    project_dir: Path,
    query: str,
    failure_types: list[str] | None = None,
    num_results: int = 5,
    min_score: float = 0.5,
) -> str | None:
    """
    Retrieve failure patterns from Graphiti for the current task.

    This searches the knowledge graph for relevant root cause analyses
    from past failures, returning categorized patterns with recommendations.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        query: Task description or error message to search for
        failure_types: Optional list of failure types to filter by
                       ("qa_rejection", "build_error", "test_failure")
        num_results: Maximum number of patterns to return (default: 5)
        min_score: Minimum relevance score 0.0-1.0 (default: 0.5)

    Returns:
        Formatted failure pattern suggestions string or None if unavailable
    """
    if is_debug_enabled():
        debug(
            "memory",
            "Retrieving failure patterns",
            query=query[:100],
            failure_types=failure_types,
            num_results=num_results,
        )

    if not is_graphiti_enabled():
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping failure pattern retrieval")
        return None

    memory = None
    try:
        # Get GraphitiMemory instance
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            if is_debug_enabled():
                debug_warning(
                    "memory", "GraphitiMemory not available for failure patterns"
                )
            return None

        # Import schema constants
        from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_ROOT_CAUSE

        if is_debug_enabled():
            debug_detailed(
                "memory",
                "Searching for failure patterns",
                query=query[:200],
                group_id=memory.group_id,
                failure_types=failure_types,
            )

        # Search for root cause episodes
        search_query = f"root cause failure {query}"
        client = getattr(memory, "client", None) or getattr(memory, "_client", None)
        if client is None:
            if is_debug_enabled():
                debug_warning("memory", "No client available on memory instance")
            return None
        results = await client.graphiti.search(
            query=search_query,
            group_ids=[memory.group_id],
            num_results=num_results * 2,  # Get extra results for filtering
        )

        if is_debug_enabled():
            debug(
                "memory",
                "Failure pattern search complete",
                raw_results=len(results) if results else 0,
            )

        if not results:
            if is_debug_enabled():
                debug("memory", "No failure patterns found")
            return None

        # Parse and filter results
        failure_patterns = []
        for result in results:
            content = (
                getattr(result, "content", None)
                or getattr(result, "fact", None)
                or (result.get("content") if isinstance(result, dict) else None)
            )
            score = getattr(result, "score", 0.0)

            if score < min_score:
                continue

            if content:
                try:
                    data = json.loads(content) if isinstance(content, str) else content

                    # Ensure data is a dict
                    if not isinstance(data, dict):
                        continue

                    # Verify it's a root cause episode
                    if data.get("type") != EPISODE_TYPE_ROOT_CAUSE:
                        continue

                    # Filter by failure type if specified
                    if failure_types and data.get("failure_type") not in failure_types:
                        continue

                    # Extract failure pattern data
                    pattern = {
                        "failure_type": data.get("failure_type", "unknown"),
                        "category": data.get("category", "unknown"),
                        "description": data.get("description", ""),
                        "affected_files": data.get("affected_files", []),
                        "confidence": data.get("confidence", 0.0),
                        "recommendations": data.get("recommendations", []),
                        "is_recurring": data.get("is_recurring", False),
                        "score": score,
                        "spec_id": data.get("spec_id", ""),
                    }

                    failure_patterns.append(pattern)

                    if len(failure_patterns) >= num_results:
                        break

                except (json.JSONDecodeError, AttributeError, KeyError) as e:
                    if is_debug_enabled():
                        debug_warning(
                            "memory",
                            "Failed to parse failure pattern result",
                            error=str(e),
                        )
                    continue

        if is_debug_enabled():
            debug(
                "memory",
                "Failure pattern parsing complete",
                patterns_found=len(failure_patterns),
            )

        if not failure_patterns:
            if is_debug_enabled():
                debug("memory", "No relevant failure patterns after filtering")
            return None

        # Format the failure patterns
        sections = ["## Failure Pattern Analysis\n"]
        sections.append("_Similar failures from past builds (learn from history):_\n")

        # Group patterns by failure type and category
        by_type: dict[str, list[dict]] = {}
        for pattern in failure_patterns:
            failure_type = pattern.get("failure_type", "unknown")
            if failure_type not in by_type:
                by_type[failure_type] = []
            by_type[failure_type].append(pattern)

        # Format each failure type
        for failure_type, type_patterns in by_type.items():
            sections.append(f"### {failure_type.replace('_', ' ').title()}\n")

            # Group by category within type
            by_category: dict[str, list[dict]] = {}
            for p in type_patterns:
                category = p.get("category", "uncategorized")
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(p)

            for category, category_patterns in by_category.items():
                sections.append(f"#### {category.replace('_', ' ').title()}\n")
                for p in category_patterns:
                    description = p.get("description", "")
                    confidence = p.get("confidence", 0.0)
                    score = p.get("score", 0.0)
                    recommendations = p.get("recommendations", [])
                    is_recurring = p.get("is_recurring", False)
                    affected_files = p.get("affected_files", [])
                    spec_id = p.get("spec_id", "")

                    sections.append(f"- **Root Cause**: {description}\n")

                    if affected_files:
                        files_str = ", ".join(affected_files[:3])
                        if len(affected_files) > 3:
                            files_str += f" (+{len(affected_files) - 3} more)"
                        sections.append(f"  _Affected Files_: {files_str}\n")

                    if recommendations:
                        sections.append("  _Recommendations_:\n")
                        for rec in recommendations[:3]:  # Limit to top 3
                            sections.append(f"    • {rec}\n")

                    sections.append(
                        f"  _Confidence_: {confidence:.2f} | _Relevance_: {score:.2f}"
                    )
                    if is_recurring:
                        sections.append(" | ⚠️ _RECURRING ISSUE_")
                    if spec_id:
                        sections.append(f" | _From_: {spec_id}")
                    sections.append("\n")

        formatted = "".join(sections)

        if is_debug_enabled():
            debug_success(
                "memory",
                "Failure patterns formatted",
                types=len(by_type),
                total_patterns=len(failure_patterns),
            )

        return formatted

    except Exception as e:
        if is_debug_enabled():
            debug_error("memory", "Failed to get failure patterns", error=str(e))
        logger.warning(f"Failed to get failure patterns: {e}")
        capture_exception(
            e,
            query_summary=query[:100] if query else "",
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
            operation="get_failure_patterns",
        )
        return None
    finally:
        # Close memory connection if we opened it
        if memory is not None:
            try:
                await memory.close()
            except Exception:
                pass


async def get_graphiti_context(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
) -> str | None:
    """
    Retrieve relevant context from Graphiti for the current subtask.

    This searches the knowledge graph for context relevant to the subtask's
    task description, returning past insights, patterns, and gotchas.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        subtask: The current subtask being worked on

    Returns:
        Formatted context string or None if unavailable
    """
    if is_debug_enabled():
        debug(
            "memory",
            "Retrieving Graphiti context for subtask",
            subtask_id=subtask.get("id", "unknown"),
            subtask_desc=subtask.get("description", "")[:100],
        )

    if not is_graphiti_enabled():
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping context retrieval")
        return None

    memory = None
    try:
        # Use centralized helper for GraphitiMemory instantiation (async)
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            if is_debug_enabled():
                debug_warning(
                    "memory", "GraphitiMemory not available for context retrieval"
                )
            return None

        # Build search query from subtask description
        subtask_desc = subtask.get("description", "")
        subtask_id = subtask.get("id", "")
        query = f"{subtask_desc} {subtask_id}".strip()

        if not query:
            if is_debug_enabled():
                debug_warning("memory", "Empty query, skipping context retrieval")
            return None

        if is_debug_enabled():
            debug_detailed(
                "memory",
                "Searching Graphiti knowledge graph",
                query=query[:200],
                num_results=5,
            )

        # Get relevant context
        context_items = await memory.get_relevant_context(query, num_results=5)

        # Get patterns and gotchas specifically (THE FIX for learning loop!)
        # This retrieves PATTERN and GOTCHA episode types for cross-session learning
        patterns, gotchas = await memory.get_patterns_and_gotchas(
            query, num_results=3, min_score=0.5
        )

        # Also get recent session history
        session_history = await memory.get_session_history(limit=3)

        if is_debug_enabled():
            debug(
                "memory",
                "Graphiti context retrieval complete",
                context_items_found=len(context_items) if context_items else 0,
                patterns_found=len(patterns) if patterns else 0,
                gotchas_found=len(gotchas) if gotchas else 0,
                session_history_found=len(session_history) if session_history else 0,
            )

        if not context_items and not session_history and not patterns and not gotchas:
            if is_debug_enabled():
                debug("memory", "No relevant context found in Graphiti")
            return None

        # Format the context
        sections = ["## Graphiti Memory Context\n"]
        sections.append("_Retrieved from knowledge graph for this subtask:_\n")

        if context_items:
            sections.append("### Relevant Knowledge\n")
            for item in context_items:
                content = item.get("content", "")[:500]  # Truncate
                item_type = item.get("type", "unknown")
                sections.append(f"- **[{item_type}]** {content}\n")

        # Add patterns section (cross-session learning)
        if patterns:
            sections.append("### Learned Patterns\n")
            sections.append("_Patterns discovered in previous sessions:_\n")
            for p in patterns:
                pattern_text = p.get("pattern", "")
                applies_to = p.get("applies_to", "")
                if applies_to:
                    sections.append(
                        f"- **Pattern**: {pattern_text}\n  _Applies to:_ {applies_to}\n"
                    )
                else:
                    sections.append(f"- **Pattern**: {pattern_text}\n")

        # Add gotchas section (cross-session learning)
        if gotchas:
            sections.append("### Known Gotchas\n")
            sections.append("_Pitfalls to avoid:_\n")
            for g in gotchas:
                gotcha_text = g.get("gotcha", "")
                solution = g.get("solution", "")
                if solution:
                    sections.append(
                        f"- **Gotcha**: {gotcha_text}\n  _Solution:_ {solution}\n"
                    )
                else:
                    sections.append(f"- **Gotcha**: {gotcha_text}\n")

        if session_history:
            sections.append("### Recent Session Insights\n")
            for session in session_history[:2]:  # Only show last 2
                session_num = session.get("session_number", "?")
                recommendations = session.get("recommendations_for_next_session", [])
                if recommendations:
                    sections.append(f"**Session {session_num} recommendations:**")
                    for rec in recommendations[:3]:  # Limit to 3
                        sections.append(f"- {rec}")
                    sections.append("")

        if is_debug_enabled():
            debug_success(
                "memory", "Graphiti context formatted", total_sections=len(sections)
            )

        return "\n".join(sections)

    except Exception as e:
        logger.warning(f"Failed to get Graphiti context: {e}")
        if is_debug_enabled():
            debug_error("memory", "Graphiti context retrieval failed", error=str(e))
        # Capture exception to Sentry with full context
        capture_exception(
            e,
            operation="get_graphiti_context",
            subtask_id=subtask.get("id", "unknown"),
            subtask_desc=subtask.get("description", "")[:200],
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
        )
        return None
    finally:
        # Always close the memory connection (swallow exceptions to avoid overriding)
        if memory is not None:
            try:
                await memory.close()
            except Exception:
                logger.debug(
                    "Failed to close Graphiti memory connection", exc_info=True
                )


async def save_session_memory(
    spec_dir: Path,
    project_dir: Path,
    subtask_id: str,
    session_num: int,
    success: bool,
    subtasks_completed: list[str],
    discoveries: dict | None = None,
) -> tuple[bool, str]:
    """
    Save session insights to memory.

    Memory Strategy:
    - PRIMARY: Graphiti (when enabled) - provides semantic search, cross-session context
    - FALLBACK: File-based (when Graphiti is disabled) - zero dependencies, always works

    This is called after each session to persist learnings.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        subtask_id: The subtask that was worked on
        session_num: Current session number
        success: Whether the subtask was completed successfully
        subtasks_completed: List of subtask IDs completed this session
        discoveries: Optional dict with file discoveries, patterns, gotchas

    Returns:
        Tuple of (success, storage_type) where storage_type is "graphiti" or "file"
    """
    # Debug: Log memory save start
    if is_debug_enabled():
        debug_section("memory", f"Saving Session {session_num} Memory")
        debug(
            "memory",
            "Memory save initiated",
            subtask_id=subtask_id,
            session_num=session_num,
            success=success,
            subtasks_completed=subtasks_completed,
            spec_dir=str(spec_dir),
        )

    # Build insights structure (same format for both storage systems)
    insights = {
        "subtasks_completed": subtasks_completed,
        "discoveries": discoveries
        or {
            "files_understood": {},
            "patterns_found": [],
            "gotchas_encountered": [],
        },
        "what_worked": [f"Implemented subtask: {subtask_id}"] if success else [],
        "what_failed": [] if success else [f"Failed to complete subtask: {subtask_id}"],
        "recommendations_for_next_session": [],
    }

    if is_debug_enabled():
        debug_detailed("memory", "Insights structure built", insights=insights)

    # Check Graphiti status for debugging
    graphiti_enabled = is_graphiti_enabled()
    if is_debug_enabled():
        graphiti_status = get_graphiti_status()
        debug(
            "memory",
            "Graphiti status check",
            enabled=graphiti_status.get("enabled"),
            available=graphiti_status.get("available"),
            host=graphiti_status.get("host"),
            port=graphiti_status.get("port"),
            database=graphiti_status.get("database"),
            llm_provider=graphiti_status.get("llm_provider"),
            embedder_provider=graphiti_status.get("embedder_provider"),
            reason=graphiti_status.get("reason") or "OK",
        )

    # PRIMARY: Try Graphiti if enabled
    if graphiti_enabled:
        if is_debug_enabled():
            debug("memory", "Attempting PRIMARY storage: Graphiti")

        memory = None
        try:
            # Use centralized helper for GraphitiMemory instantiation (async)
            memory = await get_graphiti_memory(spec_dir, project_dir)
            if memory is None:
                if is_debug_enabled():
                    debug_warning("memory", "GraphitiMemory not available")
                    debug(
                        "memory",
                        "get_graphiti_memory() returned None - this usually means Graphiti is disabled or provider config is invalid",
                    )
                # Continue to file-based fallback
            if memory is not None and memory.is_enabled:
                if is_debug_enabled():
                    debug("memory", "Saving to Graphiti...")

                # Use structured insights if we have rich extracted data
                if discoveries and discoveries.get("file_insights"):
                    # Rich insights from insight_extractor
                    if is_debug_enabled():
                        debug(
                            "memory",
                            "Using save_structured_insights (rich data available)",
                        )
                    result = await memory.save_structured_insights(discoveries)
                else:
                    # Fallback to basic session insights
                    result = await memory.save_session_insights(session_num, insights)

                if result:
                    logger.info(
                        f"Session {session_num} insights saved to Graphiti (primary)"
                    )
                    if is_debug_enabled():
                        debug_success(
                            "memory",
                            f"Session {session_num} saved to Graphiti (PRIMARY)",
                            storage_type="graphiti",
                            subtasks_saved=len(subtasks_completed),
                        )
                    return True, "graphiti"
                else:
                    logger.warning(
                        "Graphiti save returned False, falling back to file-based"
                    )
                    if is_debug_enabled():
                        debug_warning(
                            "memory", "Graphiti save returned False, using FALLBACK"
                        )
            elif memory is None:
                if is_debug_enabled():
                    debug_warning(
                        "memory", "GraphitiMemory not available, using FALLBACK"
                    )
            else:
                # memory is not None but memory.is_enabled is False
                logger.warning(
                    "GraphitiMemory.is_enabled=False, falling back to file-based"
                )
                if is_debug_enabled():
                    debug_warning("memory", "GraphitiMemory disabled, using FALLBACK")

        except Exception as e:
            logger.warning(f"Graphiti save failed: {e}, falling back to file-based")
            if is_debug_enabled():
                debug_error("memory", "Graphiti save failed", error=str(e))
            # Capture exception to Sentry with full context
            capture_exception(
                e,
                operation="save_session_memory_graphiti",
                subtask_id=subtask_id,
                session_num=session_num,
                success=success,
                subtasks_completed=subtasks_completed,
                spec_dir=str(spec_dir),
                project_dir=str(project_dir),
            )
        finally:
            # Always close the memory connection (swallow exceptions to avoid overriding)
            if memory is not None:
                try:
                    await memory.close()
                except Exception as e:
                    logger.debug(
                        "Failed to close Graphiti memory connection", exc_info=e
                    )
    else:
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping to FALLBACK")

    # FALLBACK: File-based memory (when Graphiti is disabled or fails)
    if is_debug_enabled():
        debug("memory", "Attempting FALLBACK storage: File-based")

    try:
        memory_dir = spec_dir / "memory" / "session_insights"
        if is_debug_enabled():
            debug_detailed(
                "memory",
                "File-based memory path",
                memory_dir=str(memory_dir),
                session_file=f"session_{session_num:03d}.json",
            )

        save_file_based_memory(spec_dir, session_num, insights)
        logger.info(
            f"Session {session_num} insights saved to file-based memory (fallback)"
        )

        if is_debug_enabled():
            debug_success(
                "memory",
                f"Session {session_num} saved to file-based (FALLBACK)",
                storage_type="file",
                file_path=str(memory_dir / f"session_{session_num:03d}.json"),
                subtasks_saved=len(subtasks_completed),
            )
        return True, "file"
    except Exception as e:
        logger.error(f"File-based memory save also failed: {e}")
        if is_debug_enabled():
            debug_error("memory", "File-based memory save FAILED", error=str(e))
        # Capture exception to Sentry with full context
        capture_exception(
            e,
            operation="save_session_memory_file",
            subtask_id=subtask_id,
            session_num=session_num,
            success=success,
            subtasks_completed=subtasks_completed,
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
        )
        return False, "none"


async def save_feedback(
    spec_dir: Path,
    project_dir: Path,
    feedback_type: str,
    task_description: str,
    agent_type: str,
    context: dict | None = None,
    rating: int | None = None,
) -> bool:
    """
    Save user feedback (accept/reject/modify) to memory and update preferences.

    This is the primary feedback collection function that tracks all user
    interactions with agent outputs and updates the preference profile to
    enable adaptive behavior.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        feedback_type: Type of feedback ("accepted", "rejected", "modified")
        task_description: Description of the task that was evaluated
        agent_type: Type of agent that produced the output (planner, coder, qa_reviewer, etc.)
        context: Optional additional context about the feedback
                 For "modified": should include what was changed
                 For "rejected": should include why it was rejected
        rating: Optional rating (1-5 for stars, or 0/1 for thumbs down/up)

    Returns:
        True if saved successfully, False otherwise
    """
    if not is_graphiti_enabled():
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping feedback save")
        return False

    memory = None
    try:
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            if is_debug_enabled():
                debug_warning("memory", "GraphitiMemory not available for feedback")
            return False

        if is_debug_enabled():
            debug_data = {
                "feedback_type": feedback_type,
                "agent_type": agent_type,
                "task": task_description[:100],
            }
            if rating is not None:
                debug_data["rating"] = rating
            debug(
                "memory",
                "Saving user feedback",
                **debug_data,
            )

        # Save feedback to preference profile via Graphiti
        from agents.preferences import FeedbackType

        # Validate feedback type
        try:
            feedback_enum = FeedbackType(feedback_type)
        except ValueError:
            logger.warning(f"Invalid feedback type: {feedback_type}")
            if is_debug_enabled():
                debug_error(
                    "memory", "Invalid feedback type", feedback_type=feedback_type
                )
            return False

        # Store feedback in Graphiti as an episode
        episode_data = {
            "episode_type": "user_feedback",
            "feedback_type": feedback_type,
            "task_description": task_description,
            "agent_type": agent_type,
            "context": context or {},
        }
        if rating is not None:
            episode_data["rating"] = rating

        # Build insights based on feedback type
        insights = {
            "what_failed": [],
            "what_worked": [],
            "discoveries": {},
            "recommendations_for_next_session": [],
            "subtasks_completed": [],
            "_user_feedback": episode_data,
        }

        if feedback_enum == FeedbackType.ACCEPTED:
            insights["what_worked"].append(
                f"{agent_type} output accepted for: {task_description[:200]}"
            )
            insights["recommendations_for_next_session"].append(
                f"Continue current approach for {agent_type} tasks"
            )
        elif feedback_enum == FeedbackType.REJECTED:
            reason = (
                context.get("reason", "No reason provided")
                if context
                else "No reason provided"
            )
            insights["what_failed"].append(
                f"{agent_type} output rejected: {task_description[:200]}"
            )
            insights["discoveries"]["gotchas_encountered"] = [
                {
                    "gotcha": f"User rejected {agent_type} approach",
                    "solution": reason[:500],
                    "source": "user_feedback",
                }
            ]
            insights["recommendations_for_next_session"].append(
                f"Adjust {agent_type} approach: {reason[:300]}"
            )
        elif feedback_enum == FeedbackType.MODIFIED:
            modifications = (
                context.get("modifications", "User made changes")
                if context
                else "User made changes"
            )
            reason = context.get("reason", "") if context else ""
            insights["what_worked"].append(
                f"{agent_type} output partially accepted (with modifications)"
            )
            insights["what_failed"].append(
                f"Required modification: {modifications[:200]}"
            )
            if reason:
                insights["discoveries"]["patterns"] = [
                    {
                        "pattern": f"User prefers different approach for {task_description[:100]}",
                        "reason": reason[:300],
                        "source": "user_feedback",
                    }
                ]
            insights["recommendations_for_next_session"].append(
                f"Apply learned modifications: {modifications[:300]}"
            )

        # Save to Graphiti
        result = await memory.save_session_insights(
            session_num=0,  # Feedback is session-independent
            insights=insights,
        )

        # Also update preference profile directly
        profile_kwargs = {
            "feedback_type": feedback_enum,
            "task_description": task_description,
            "agent_type": agent_type,
            "context": context or {},
        }
        if rating is not None:
            profile_kwargs["rating"] = rating
        profile_result = await memory.add_feedback_to_profile(**profile_kwargs)

        if result and profile_result:
            logger.info(f"User feedback saved: {feedback_type} for {agent_type} task")
            if is_debug_enabled():
                debug_success(
                    "memory",
                    "Feedback saved successfully",
                    feedback_type=feedback_type,
                    profile_updated=profile_result,
                )
        return bool(result and profile_result)

    except Exception as e:
        logger.warning(f"Failed to save user feedback: {e}")
        if is_debug_enabled():
            debug_error("memory", "Feedback save failed", error=str(e))
        capture_exception(
            e,
            operation="save_feedback",
            feedback_type=feedback_type,
            agent_type=agent_type,
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
        )
        return False
    finally:
        if memory is not None:
            try:
                await memory.close()
            except Exception:
                pass


async def track_improvement(
    spec_dir: Path,
    project_dir: Path,
    improvement_description: str,
    feedback_ids: list[str] | None = None,
    before_metrics: dict | None = None,
    after_metrics: dict | None = None,
    agent_type: str | None = None,
    context: dict | None = None,
) -> bool:
    """
    Track an improvement made in response to user feedback.

    This function records when user feedback has led to a measurable improvement
    in agent behavior, code quality, or user satisfaction. This creates a feedback
    loop showing how user input directly influences the system.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        improvement_description: Description of what was improved
        feedback_ids: Optional list of feedback IDs that triggered this improvement
        before_metrics: Optional metrics before the improvement
                       (e.g., {"success_rate": 0.6, "avg_rating": 3.2})
        after_metrics: Optional metrics after the improvement
                      (e.g., {"success_rate": 0.85, "avg_rating": 4.1})
        agent_type: Optional agent type that was improved (planner, coder, etc.)
        context: Optional additional context about the improvement

    Returns:
        True if tracked successfully, False otherwise

    Example:
        >>> await track_improvement(
        ...     spec_dir=Path(".auto-claude/specs/001"),
        ...     project_dir=Path("."),
        ...     improvement_description="Improved error handling based on user feedback",
        ...     feedback_ids=["feedback_123", "feedback_456"],
        ...     before_metrics={"error_rate": 0.15},
        ...     after_metrics={"error_rate": 0.03},
        ...     agent_type="coder"
        ... )
    """
    if not is_graphiti_enabled():
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping improvement tracking")
        return False

    memory = None
    try:
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            if is_debug_enabled():
                debug_warning(
                    "memory", "GraphitiMemory not available for improvement tracking"
                )
            return False

        if is_debug_enabled():
            debug_data = {
                "improvement": improvement_description[:100],
            }
            if feedback_ids:
                debug_data["feedback_count"] = len(feedback_ids)
            if agent_type:
                debug_data["agent_type"] = agent_type
            debug(
                "memory",
                "Tracking improvement",
                **debug_data,
            )

        # Import episode type
        from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_IMPROVEMENT

        # Calculate improvement delta if metrics provided
        improvement_delta = {}
        if before_metrics and after_metrics:
            for key in set(before_metrics.keys()) | set(after_metrics.keys()):
                before_val = before_metrics.get(key)
                after_val = after_metrics.get(key)
                if before_val is not None and after_val is not None:
                    if isinstance(before_val, (int, float)) and isinstance(
                        after_val, (int, float)
                    ):
                        delta = after_val - before_val
                        percent_change = (
                            round(((delta / before_val) * 100), 2)
                            if before_val != 0
                            else None
                        )
                        improvement_delta[key] = {
                            "before": before_val,
                            "after": after_val,
                            "delta": delta,
                            "percent_change": percent_change,
                        }

        # Store improvement in Graphiti as an episode
        episode_data = {
            "episode_type": EPISODE_TYPE_IMPROVEMENT,
            "improvement_description": improvement_description,
            "feedback_ids": feedback_ids or [],
            "before_metrics": before_metrics or {},
            "after_metrics": after_metrics or {},
            "improvement_delta": improvement_delta,
            "context": context or {},
        }
        if agent_type:
            episode_data["agent_type"] = agent_type

        # Build insights that show how feedback led to improvement
        insights = {
            "what_worked": [
                f"User feedback led to improvement: {improvement_description[:200]}"
            ],
            "discoveries": {
                "improvements": [
                    {
                        "description": improvement_description,
                        "feedback_count": len(feedback_ids) if feedback_ids else 0,
                        "metrics_delta": improvement_delta,
                        "source": "user_feedback_loop",
                    }
                ]
            },
            "recommendations_for_next_session": [],
            "_improvement": episode_data,
        }

        # Add specific recommendations based on metrics
        if improvement_delta:
            for metric, delta_data in improvement_delta.items():
                if delta_data["delta"] > 0:  # Improvement
                    insights["recommendations_for_next_session"].append(
                        f"Continue approach that improved {metric} by {delta_data['percent_change']:.1f}%"
                    )

        # Save to Graphiti
        result = await memory.save_session_insights(
            session_num=0,  # Improvements are session-independent
            insights=insights,
        )

        if result:
            logger.info(
                f"Improvement tracked: {improvement_description[:100]} "
                f"(based on {len(feedback_ids) if feedback_ids else 0} feedback items)"
            )
            if is_debug_enabled():
                debug_success(
                    "memory",
                    "Improvement tracked successfully",
                    improvement=improvement_description[:100],
                    feedback_count=len(feedback_ids) if feedback_ids else 0,
                    metrics_improved=list(improvement_delta.keys()),
                )

        return bool(result)

    except Exception as e:
        logger.warning(f"Failed to track improvement: {e}")
        if is_debug_enabled():
            debug_error("memory", "Improvement tracking failed", error=str(e))
        capture_exception(
            e,
            operation="track_improvement",
            improvement=improvement_description[:100],
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
        )
        return False
    finally:
        if memory is not None:
            try:
                await memory.close()
            except Exception:
                pass


async def save_user_correction(
    spec_dir: Path,
    project_dir: Path,
    what_was_wrong: str,
    what_was_corrected: str,
    correction_context: dict | None = None,
) -> bool:
    """
    Save a user correction to Graphiti memory.

    DEPRECATED: Use save_feedback() instead for new code.
    This is kept for backward compatibility with QA_FIX_REQUEST.md workflow.

    Called when the user manually edits QA_FIX_REQUEST.md to provide
    better guidance than the QA agent generated.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        what_was_wrong: Description of what the agent got wrong
        what_was_corrected: The user's corrected content
        correction_context: Additional context (spec_id, file_path, etc.)

    Returns:
        True if saved successfully, False otherwise
    """
    if not is_graphiti_enabled():
        if is_debug_enabled():
            debug("memory", "Graphiti not enabled, skipping user correction save")
        return False

    memory = None
    try:
        memory = await get_graphiti_memory(spec_dir, project_dir)
        if memory is None:
            if is_debug_enabled():
                debug_warning(
                    "memory", "GraphitiMemory not available for user correction"
                )
            return False

        # Store as a user correction episode
        episode_data = {
            "episode_type": "user_correction",
            "what_was_wrong": what_was_wrong,
            "what_was_corrected": what_was_corrected,
            "correction_context": correction_context or {},
        }

        result = await memory.save_session_insights(
            session_num=0,
            insights={
                "what_failed": [what_was_wrong],
                "what_worked": [what_was_corrected],
                "discoveries": {
                    "gotchas_encountered": [
                        {
                            "gotcha": what_was_wrong,
                            "solution": what_was_corrected[:500],
                            "source": "user_correction",
                        }
                    ],
                },
                "recommendations_for_next_session": [what_was_corrected[:500]],
                "subtasks_completed": [],
                "_user_correction": episode_data,
            },
        )

        if result:
            logger.info("User correction saved to Graphiti memory")
            if is_debug_enabled():
                debug_success("memory", "User correction saved to Graphiti")
        return bool(result)

    except Exception as e:
        logger.warning(f"Failed to save user correction: {e}")
        if is_debug_enabled():
            debug_error("memory", "User correction save failed", error=str(e))
        capture_exception(
            e,
            operation="save_user_correction",
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
        )
        return False
    finally:
        if memory is not None:
            try:
                await memory.close()
            except Exception:
                pass


# Keep the old function name as an alias for backwards compatibility
async def save_session_to_graphiti(
    spec_dir: Path,
    project_dir: Path,
    subtask_id: str,
    session_num: int,
    success: bool,
    subtasks_completed: list[str],
    discoveries: dict | None = None,
) -> bool:
    """Backwards compatibility wrapper for save_session_memory."""
    result, _ = await save_session_memory(
        spec_dir,
        project_dir,
        subtask_id,
        session_num,
        success,
        subtasks_completed,
        discoveries,
    )
    return result


async def detect_and_save_codebase_patterns(
    spec_dir: Path, project_dir: Path
) -> dict[str, int]:
    """
    Detect and save codebase patterns using pattern detectors.

    This function runs the three pattern detectors (naming, error handling, organization)
    on the project directory and saves all detected patterns to memory.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory

    Returns:
        Dictionary with counts of patterns saved by category:
        {
            "naming": 5,
            "error-handling": 3,
            "code-organization": 4
        }
    """
    if is_debug_enabled():
        debug(
            "memory",
            "Detecting and saving codebase patterns",
            project_dir=str(project_dir),
        )

    pattern_counts = {
        "naming": 0,
        "error-handling": 0,
        "code-organization": 0,
    }

    try:
        # Import detectors
        from analysis.analyzers.error_pattern_detector import ErrorPatternDetector
        from analysis.analyzers.naming_detector import NamingDetector
        from analysis.analyzers.organization_detector import OrganizationDetector

        # Detect primary language for naming analysis
        detected_language = "python"  # default
        try:
            from project.stack_detector import StackDetector

            stack = StackDetector(project_dir)
            stack.detect_languages()
            langs = stack.stack.languages
            if langs:
                detected_language = langs[0]
        except Exception:
            pass  # Fall back to "python"

        # Detect naming conventions
        try:
            naming_detector = NamingDetector(
                project_dir, {"language": detected_language}
            )
            naming_conventions = naming_detector.detect_naming_conventions()
            save_detected_patterns_from_naming(spec_dir, naming_conventions)
            pattern_counts["naming"] = sum(1 for v in naming_conventions.values() if v)
            if is_debug_enabled():
                debug(
                    "memory",
                    "Naming conventions detected",
                    count=pattern_counts["naming"],
                )
        except Exception as e:
            logger.warning(f"Failed to detect naming conventions: {e}")
            if is_debug_enabled():
                debug_warning("memory", "Naming detection failed", error=str(e))

        # Detect error handling patterns
        try:
            error_detector = ErrorPatternDetector(project_dir)
            error_patterns = error_detector.detect_error_patterns()
            save_detected_patterns_from_errors(spec_dir, error_patterns)
            pattern_counts["error-handling"] = sum(
                1 for v in error_patterns.values() if v
            )
            if is_debug_enabled():
                debug(
                    "memory",
                    "Error patterns detected",
                    count=pattern_counts["error-handling"],
                )
        except Exception as e:
            logger.warning(f"Failed to detect error patterns: {e}")
            if is_debug_enabled():
                debug_warning("memory", "Error pattern detection failed", error=str(e))

        # Detect organization patterns
        try:
            org_detector = OrganizationDetector(project_dir)
            org_patterns = org_detector.detect_organization_patterns()
            save_detected_patterns_from_organization(spec_dir, org_patterns)
            pattern_counts["code-organization"] = sum(
                1 for v in org_patterns.values() if v
            )
            if is_debug_enabled():
                debug(
                    "memory",
                    "Organization patterns detected",
                    count=pattern_counts["code-organization"],
                )
        except Exception as e:
            logger.warning(f"Failed to detect organization patterns: {e}")
            if is_debug_enabled():
                debug_warning("memory", "Organization detection failed", error=str(e))

        total_patterns = sum(pattern_counts.values())
        if is_debug_enabled():
            debug_success(
                "memory", "Pattern detection complete", total_patterns=total_patterns
            )
        logger.info(f"Detected and saved {total_patterns} codebase patterns")

    except Exception as e:
        logger.warning(f"Pattern detection failed: {e}")
        if is_debug_enabled():
            debug_error("memory", "Pattern detection failed", error=str(e))
        capture_exception(
            e,
            operation="detect_and_save_codebase_patterns",
            spec_dir=str(spec_dir),
            project_dir=str(project_dir),
        )

    return pattern_counts
