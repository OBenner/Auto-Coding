"""
Pattern Commands
================

CLI commands for managing learned codebase patterns
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

from cli.utils import print_banner
from integrations.graphiti.pattern_categorizer import get_pattern_categories
from integrations.graphiti.pattern_suggester import get_patterns_by_category
from memory.graphiti_helpers import (
    get_graphiti_memory,
    is_graphiti_memory_enabled,
    run_async,
)
from memory.patterns import load_patterns
from ui import (
    Icons,
    divider,
    icon,
    info,
    muted,
    print_header,
    print_key_value,
    success,
    warning,
)


def list_patterns(spec_dir: Path, category: str | None = None) -> None:
    """
    List all learned patterns, optionally filtered by category.

    Args:
        spec_dir: Spec directory path
        category: Optional category filter (naming-conventions, error-handling, code-organization)
    """
    print_banner()
    print(f"\n{icon(Icons.LIST)} Learned Patterns for: {spec_dir.name}\n")

    # Load patterns from file-based memory
    patterns = load_patterns(spec_dir)

    if not patterns and not is_graphiti_memory_enabled():
        print(info(f"{icon(Icons.INFO)} No patterns learned yet"))
        print(muted("Patterns are automatically detected during spec discovery"))
        print()
        return

    # Display file-based patterns
    if patterns:
        print_header("File-Based Patterns")
        print()

        if category:
            # Filter by category
            filtered = [p for p in patterns if f"[category: {category}]" in p]
            if not filtered:
                print(muted(f"No patterns found in category: {category}"))
                print()
            else:
                for i, pattern in enumerate(filtered, 1):
                    _print_pattern_line(i, pattern)
                print()
        else:
            # Show all patterns
            for i, pattern in enumerate(patterns, 1):
                _print_pattern_line(i, pattern)
            print()

    # Load patterns from Graphiti if enabled
    if is_graphiti_memory_enabled():
        print(divider())
        print_header("Graphiti Memory Patterns")
        print()

        try:
            graphiti = run_async(get_graphiti_memory(spec_dir))
            if graphiti:
                group_id = graphiti._group_id

                if category:
                    # Get patterns for specific category
                    from integrations.graphiti.queries_pkg.client import get_client

                    client = run_async(get_client(spec_dir))
                    if client:
                        results = run_async(
                            get_patterns_by_category(
                                client, group_id, category, num_results=50
                            )
                        )
                        if results:
                            for i, result in enumerate(results, 1):
                                content = result.get("content", "")
                                score = result.get("score", 0.0)
                                result_category = result.get(
                                    "category", "uncategorized"
                                )
                                print(f"{i}. {content}")
                                print(
                                    muted(
                                        f"   [category: {result_category}, relevance: {score:.2f}]"
                                    )
                                )
                            print()
                        else:
                            print(muted(f"No patterns found in category: {category}"))
                            print()
                else:
                    # Get all patterns via search
                    all_patterns, _ = run_async(
                        graphiti.get_patterns_and_gotchas(
                            query="all patterns", num_results=50, min_score=0.0
                        )
                    )
                    if all_patterns:
                        for i, pattern in enumerate(all_patterns, 1):
                            content = pattern.get("content", "")
                            print(f"{i}. {content}")
                        print()
                    else:
                        print(muted("No patterns stored in Graphiti yet"))
                        print()

                run_async(graphiti.close())
        except Exception as e:
            print(
                warning(f"{icon(Icons.WARNING)} Failed to load Graphiti patterns: {e}")
            )
            print()

    # Show available categories
    if not category:
        print(divider())
        print_header("Available Categories")
        print()
        categories = get_pattern_categories()
        for cat in categories:
            print(f"  * {cat}")
        print()
        print(muted("Use --category to filter by specific category"))
        print()


def _print_pattern_line(index: int, pattern: str) -> None:
    """
    Print a single pattern line with formatting.

    Args:
        index: Pattern number
        pattern: Pattern string (may include metadata)
    """
    # Split pattern text from metadata
    parts = pattern.split(" [")
    pattern_text = parts[0]
    metadata = " [".join(parts[1:]) if len(parts) > 1 else ""

    print(f"{index}. {pattern_text}")
    if metadata:
        print(muted(f"   [{metadata}"))


def show_pattern_details(spec_dir: Path, pattern_index: int) -> None:
    """
    Show detailed information about a specific pattern.

    Args:
        spec_dir: Spec directory path
        pattern_index: 1-based index of pattern to show
    """
    print_banner()
    print(f"\n{icon(Icons.INFO)} Pattern Details\n")

    patterns = load_patterns(spec_dir)

    if not patterns:
        print(warning(f"{icon(Icons.WARNING)} No patterns found"))
        print()
        return

    if pattern_index < 1 or pattern_index > len(patterns):
        print(warning(f"{icon(Icons.WARNING)} Invalid pattern index: {pattern_index}"))
        print(muted(f"Valid range: 1-{len(patterns)}"))
        print()
        return

    pattern = patterns[pattern_index - 1]

    # Parse pattern metadata
    parts = pattern.split(" [")
    pattern_text = parts[0]

    category = None
    confidence = None
    reasoning = None

    for part in parts[1:]:
        if part.startswith("category: "):
            category = part.replace("category: ", "").rstrip("]")
        elif part.startswith("confidence: "):
            confidence = part.replace("confidence: ", "").rstrip("]")
        elif part.startswith("reasoning: "):
            reasoning = part.replace("reasoning: ", "").rstrip("]")

    print_key_value("Pattern", pattern_text)
    if category:
        print_key_value("Category", category)
    if confidence:
        print_key_value("Confidence", confidence)
    if reasoning:
        print_key_value("Reasoning", reasoning)
    print()


def approve_pattern(spec_dir: Path, pattern_index: int) -> None:
    """
    Approve a learned pattern (mark as verified).

    Args:
        spec_dir: Spec directory path
        pattern_index: 1-based index of pattern to approve
    """
    print_banner()
    print(f"\n{icon(Icons.SUCCESS)} Approving Pattern\n")

    patterns = load_patterns(spec_dir)

    if not patterns:
        print(warning(f"{icon(Icons.WARNING)} No patterns found"))
        print()
        return

    if pattern_index < 1 or pattern_index > len(patterns):
        print(warning(f"{icon(Icons.WARNING)} Invalid pattern index: {pattern_index}"))
        print(muted(f"Valid range: 1-{len(patterns)}"))
        print()
        return

    pattern = patterns[pattern_index - 1]
    print(success(f"Pattern approved: {pattern}"))
    print()
    print(muted("Pattern will continue to be applied by agents"))
    print()


def override_pattern(spec_dir: Path, pattern_index: int, new_text: str) -> None:
    """
    Override a pattern with new text.

    Args:
        spec_dir: Spec directory path
        pattern_index: 1-based index of pattern to override
        new_text: New pattern text
    """
    print_banner()
    print(f"\n{icon(Icons.EDIT)} Overriding Pattern\n")

    from memory.paths import get_memory_dir

    patterns = load_patterns(spec_dir)

    if not patterns:
        print(warning(f"{icon(Icons.WARNING)} No patterns found"))
        print()
        return

    if pattern_index < 1 or pattern_index > len(patterns):
        print(warning(f"{icon(Icons.WARNING)} Invalid pattern index: {pattern_index}"))
        print(muted(f"Valid range: 1-{len(patterns)}"))
        print()
        return

    old_pattern = patterns[pattern_index - 1]
    patterns[pattern_index - 1] = new_text

    # Write updated patterns back to file atomically
    memory_dir = get_memory_dir(spec_dir)
    patterns_file = memory_dir / "patterns.md"

    fd, tmp_path = tempfile.mkstemp(dir=str(memory_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("# Code Patterns\n\n")
            f.write("Established patterns to follow in this codebase:\n\n")
            for pattern in patterns:
                f.write(f"- {pattern}\n")
        os.replace(tmp_path, str(patterns_file))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    print(muted(f"Old: {old_pattern}"))
    print(success(f"New: {new_text}"))
    print()
    print(info("Pattern updated successfully"))
    print()


def delete_pattern(spec_dir: Path, pattern_index: int) -> None:
    """
    Delete a learned pattern.

    Args:
        spec_dir: Spec directory path
        pattern_index: 1-based index of pattern to delete
    """
    print_banner()
    print(f"\n{icon(Icons.DELETE)} Deleting Pattern\n")

    from memory.paths import get_memory_dir

    patterns = load_patterns(spec_dir)

    if not patterns:
        print(warning(f"{icon(Icons.WARNING)} No patterns found"))
        print()
        return

    if pattern_index < 1 or pattern_index > len(patterns):
        print(warning(f"{icon(Icons.WARNING)} Invalid pattern index: {pattern_index}"))
        print(muted(f"Valid range: 1-{len(patterns)}"))
        print()
        return

    deleted_pattern = patterns.pop(pattern_index - 1)

    # Write updated patterns back to file atomically
    memory_dir = get_memory_dir(spec_dir)
    patterns_file = memory_dir / "patterns.md"

    fd, tmp_path = tempfile.mkstemp(dir=str(memory_dir), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            if patterns:
                f.write("# Code Patterns\n\n")
                f.write("Established patterns to follow in this codebase:\n\n")
                for pattern in patterns:
                    f.write(f"- {pattern}\n")
            else:
                # Empty file if no patterns left
                f.write("# Code Patterns\n\n")
                f.write("No patterns yet.\n")
        os.replace(tmp_path, str(patterns_file))
    except BaseException:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    print(warning(f"Deleted: {deleted_pattern}"))
    print()
    print(info("Pattern removed successfully"))
    print()


def handle_patterns_command(spec_dir: Path, args: argparse.Namespace) -> int:
    """
    Handle the pattern management command.

    Args:
        spec_dir: Spec directory path
        args: Parsed command-line arguments

    Returns:
        0 on success, 1 on error
    """
    action = args.action

    if action == "list":
        list_patterns(spec_dir, category=args.category)
    elif action == "show":
        if not args.index:
            print(warning(f"{icon(Icons.WARNING)} --index required for 'show' action"))
            return 1
        show_pattern_details(spec_dir, args.index)
    elif action == "approve":
        if not args.index:
            print(
                warning(f"{icon(Icons.WARNING)} --index required for 'approve' action")
            )
            return 1
        approve_pattern(spec_dir, args.index)
    elif action == "override":
        if not args.index or not args.text:
            print(
                warning(
                    f"{icon(Icons.WARNING)} --index and --text required for 'override' action"
                )
            )
            return 1
        override_pattern(spec_dir, args.index, args.text)
    elif action == "delete":
        if not args.index:
            print(
                warning(f"{icon(Icons.WARNING)} --index required for 'delete' action")
            )
            return 1
        delete_pattern(spec_dir, args.index)
    else:
        print(warning(f"{icon(Icons.WARNING)} Unknown action: {action}"))
        return 1

    return 0


def main() -> None:
    """
    Main entry point for pattern commands CLI.
    """
    parser = argparse.ArgumentParser(
        description="Manage learned codebase patterns",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all patterns
  python pattern_commands.py list --spec-dir .auto-claude/specs/001-feature

  # List patterns in specific category
  python pattern_commands.py list --spec-dir .auto-claude/specs/001-feature --category naming-conventions

  # Show pattern details
  python pattern_commands.py show --spec-dir .auto-claude/specs/001-feature --index 3

  # Approve a pattern
  python pattern_commands.py approve --spec-dir .auto-claude/specs/001-feature --index 5

  # Override a pattern
  python pattern_commands.py override --spec-dir .auto-claude/specs/001-feature --index 2 --text "New pattern text"

  # Delete a pattern
  python pattern_commands.py delete --spec-dir .auto-claude/specs/001-feature --index 7
        """,
    )

    parser.add_argument(
        "action",
        choices=["list", "show", "approve", "override", "delete"],
        help="Action to perform",
    )

    parser.add_argument(
        "--spec-dir",
        type=Path,
        required=True,
        help="Path to spec directory",
    )

    parser.add_argument(
        "--category",
        type=str,
        help="Filter patterns by category (for 'list' action)",
    )

    parser.add_argument(
        "--index",
        type=int,
        help="Pattern index (1-based, for show/approve/override/delete actions)",
    )

    parser.add_argument(
        "--text",
        type=str,
        help="New pattern text (for 'override' action)",
    )

    args = parser.parse_args()

    # Validate spec_dir exists
    if not args.spec_dir.exists():
        print(
            warning(f"{icon(Icons.WARNING)} Spec directory not found: {args.spec_dir}")
        )
        return

    # Handle the command
    handle_patterns_command(args.spec_dir, args)


def handle_pattern_analyze_command(
    project_dir: Path,
    spec_id: str | None = None,
    output_json: bool = False,
) -> None:
    """
    Handle the failure pattern analyze command.

    Args:
        project_dir: Project root directory
        spec_id: Optional spec ID to analyze (if None, analyze all specs)
        output_json: Whether to output results as JSON
    """
    print_banner()
    print(f"\n{icon(Icons.ANALYSIS)} Failure Pattern Analysis")
    print(f"Project: {project_dir}\n")

    # Try to import pattern analysis components
    try:
        from analysis.failure_pattern_extractor import FailurePatternExtractor
    except ImportError:
        print(
            warning(
                f"{icon(Icons.WARNING)} Failure pattern analysis not available. "
                "Please ensure analysis modules are installed."
            )
        )
        return

    # Find specs directory
    from cli.utils import find_specs_dir

    specs_dir = find_specs_dir(project_dir)

    if spec_id:
        # Analyze specific spec
        spec_dir = specs_dir / spec_id
        if not spec_dir.exists():
            print(
                warning(f"{icon(Icons.WARNING)} Spec directory not found: {spec_dir}")
            )
            return

        spec_dirs = [spec_dir]
    else:
        # Analyze all specs
        spec_dirs = [d for d in specs_dir.iterdir() if d.is_dir()]

    all_patterns = []
    for spec_dir in spec_dirs:
        print(info(f"{icon(Icons.INFO)} Analyzing spec: {spec_dir.name}"))

        try:
            extractor = FailurePatternExtractor(spec_dir)

            # Load attempt history
            if not extractor.attempt_history_file.exists():
                print(
                    muted(f"  {icon(Icons.MINUS)} No attempt history found, skipping")
                )
                continue

            attempt_history = extractor.load_attempt_history()
            if not attempt_history.get("attempts"):
                print(
                    muted(f"  {icon(Icons.MINUS)} No attempts recorded, skipping")
                )
                continue

            # Extract patterns
            analysis = extractor.extract_all_patterns()

            if output_json:
                all_patterns.append(
                    {
                        "spec": spec_dir.name,
                        "analysis": analysis,
                    }
                )
            else:
                # Display patterns in human-readable format
                _display_failure_pattern_analysis(spec_dir.name, analysis)

        except Exception as e:
            print(warning(f"  {icon(Icons.WARNING)} Failed to analyze: {e}"))
            continue

    if output_json:
        import json

        print(json.dumps(all_patterns, indent=2))
    else:
        print(success(f"\n{icon(Icons.SUCCESS)} Pattern analysis complete"))


def _display_failure_pattern_analysis(spec_name: str, analysis: dict) -> None:
    """Display failure pattern analysis in human-readable format."""
    total_attempts = analysis.get("total_attempts", 0)
    failed_attempts = analysis.get("failed_attempts", 0)
    patterns = analysis.get("patterns", [])

    print(f"  {icon(Icons.CHART)} Attempts: {total_attempts} ({failed_attempts} failed)")

    if not patterns:
        print(muted(f"  {icon(Icons.MINUS)} No failure patterns detected"))
        return

    print(f"  {icon(Icons.PATTERN)} Patterns detected: {len(patterns)}\n")

    for pattern in patterns:
        pattern_type = pattern.get("pattern_type", "unknown")
        description = pattern.get("description", "")
        frequency = pattern.get("frequency", 0)
        confidence = pattern.get("confidence", 0.0)

        print(f"    [{pattern_type.upper()}] ({frequency}x, {confidence:.0%})")
        print(f"    {description}")

        recommendations = pattern.get("recovery_recommendations", [])
        if recommendations:
            print(f"    Recommendations:")
            for rec in recommendations[:3]:  # Show top 3
                print(f"      • {rec}")
        print()


def handle_pattern_query_command(
    project_dir: Path,
    spec_dir: Path,
    query: str,
    pattern_type: str | None = None,
    min_confidence: float = 0.0,
    num_results: int = 10,
    output_json: bool = False,
) -> None:
    """
    Handle the failure pattern query command.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory for context
        query: Search query for patterns
        pattern_type: Optional pattern type filter
        min_confidence: Minimum confidence score
        num_results: Maximum number of results
        output_json: Whether to output results as JSON
    """
    print_banner()
    print(f"\n{icon(Icons.SEARCH)} Querying Failure Patterns")
    print(f"Query: {query}\n")

    # Try to import pattern store components
    try:
        from integrations.graphiti.failure_pattern_store import FailurePatternStore
        from integrations.graphiti.memory import get_graphiti_memory
    except ImportError:
        print(
            warning(
                f"{icon(Icons.WARNING)} Pattern store not available. "
                "Please ensure Graphiti integration is installed."
            )
        )
        return

    import asyncio

    async def _query_patterns():
        """Async query function."""
        try:
            # Get Graphiti memory
            memory = get_graphiti_memory(spec_dir, project_dir)

            # Create pattern store
            spec_id = spec_dir.name
            group_id = f"spec_{spec_id}"
            pattern_store = FailurePatternStore(
                client=memory.client,
                group_id=group_id,
                spec_context_id=spec_id,
                group_id_mode="spec",
                project_dir=project_dir,
            )

            # Query patterns
            patterns = await pattern_store.query_failure_patterns(
                query=query,
                pattern_type=pattern_type,
                min_confidence=min_confidence,
                num_results=num_results,
                include_project_patterns=True,
            )

            return patterns

        except Exception as e:
            print(warning(f"{icon(Icons.WARNING)} Failed to query patterns: {e}"))
            return None

    # Run async query
    patterns = asyncio.run(_query_patterns())

    if patterns is None:
        return

    if not patterns:
        print(muted(f"{icon(Icons.MINUS)} No matching patterns found"))
        return

    if output_json:
        import json

        print(json.dumps(patterns, indent=2))
    else:
        _display_failure_pattern_query_results(patterns, query)

    print(success(f"\n{icon(Icons.SUCCESS)} Found {len(patterns)} pattern(s)"))


def _display_failure_pattern_query_results(patterns: list[dict], query: str) -> None:
    """Display failure pattern query results in human-readable format."""
    print(f"Results for: {query}\n")

    for i, pattern in enumerate(patterns, 1):
        pattern_type = pattern.get("pattern_type", "unknown")
        description = pattern.get("description", "")
        frequency = pattern.get("frequency", 0)
        confidence = pattern.get("confidence", 0.0)
        relevance = pattern.get("relevance_score", 0.0)

        print(f"{i}. [{pattern_type.upper()}]")
        print(f"   {description}")
        print(f"   Frequency: {frequency}x | Confidence: {confidence:.0%} | Relevance: {relevance:.0%}")

        affected_subtasks = pattern.get("affected_subtasks", [])
        if affected_subtasks:
            print(f"   Affected: {', '.join(affected_subtasks[:3])}")

        recommendations = pattern.get("recovery_recommendations", [])
        if recommendations:
            print(f"   Recovery strategies:")
            for rec in recommendations[:2]:
                print(f"     • {rec}")
        print()


def handle_pattern_stats_command(
    project_dir: Path,
    spec_dir: Path,
    output_json: bool = False,
) -> None:
    """
    Handle the failure pattern statistics command.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory for context
        output_json: Whether to output results as JSON
    """
    print_banner()
    print(f"\n{icon(Icons.CHART)} Failure Pattern Statistics")
    print(f"Spec: {spec_dir.name}\n")

    # Try to import pattern store components
    try:
        from integrations.graphiti.failure_pattern_store import FailurePatternStore
        from integrations.graphiti.memory import get_graphiti_memory
    except ImportError:
        print(
            warning(
                f"{icon(Icons.WARNING)} Pattern store not available. "
                "Please ensure Graphiti integration is installed."
            )
        )
        return

    import asyncio

    async def _get_stats():
        """Async stats function."""
        try:
            # Get Graphiti memory
            memory = get_graphiti_memory(spec_dir, project_dir)

            # Create pattern store
            spec_id = spec_dir.name
            group_id = f"spec_{spec_id}"
            pattern_store = FailurePatternStore(
                client=memory.client,
                group_id=group_id,
                spec_context_id=spec_id,
                group_id_mode="spec",
                project_dir=project_dir,
            )

            # Get statistics
            stats = await pattern_store.get_pattern_statistics()

            return stats

        except Exception as e:
            print(warning(f"{icon(Icons.WARNING)} Failed to get statistics: {e}"))
            return None

    # Run async query
    stats = asyncio.run(_get_stats())

    if stats is None:
        return

    if output_json:
        import json

        print(json.dumps(stats, indent=2))
    else:
        _display_failure_pattern_statistics(stats)

    print(success(f"\n{icon(Icons.SUCCESS)} Statistics complete"))


def _display_failure_pattern_statistics(stats: dict) -> None:
    """Display failure pattern statistics in human-readable format."""
    total_patterns = stats.get("total_patterns", 0)
    patterns_by_type = stats.get("patterns_by_type", {})
    most_common = stats.get("most_common_patterns", [])
    high_frequency_count = stats.get("high_frequency_patterns", 0)
    avg_confidence = stats.get("average_confidence", 0.0)

    print(f"Total Patterns: {total_patterns}")
    print(f"High-Frequency Patterns: {high_frequency_count}")
    print(f"Average Confidence: {avg_confidence:.1%}\n")

    if patterns_by_type:
        print("Patterns by Type:")
        for pattern_type, count in sorted(
            patterns_by_type.items(), key=lambda x: x[1], reverse=True
        ):
            print(f"  {pattern_type}: {count}")
        print()

    if most_common:
        print("Most Common Patterns:")
        for i, pattern in enumerate(most_common, 1):
            pattern_type = pattern.get("pattern_type", "unknown")
            description = pattern.get("description", "")
            frequency = pattern.get("frequency", 0)

            # Truncate description for display
            desc_short = (
                description[:60] + "..." if len(description) > 60 else description
            )

            print(f"  {i}. [{pattern_type}] ({frequency}x)")
            print(f"     {desc_short}")


def register_pattern_commands(subparsers: argparse._SubParsersAction) -> None:
    """
    Register failure pattern CLI commands.

    Args:
        subparsers: ArgumentParser subparsers object to add commands to
    """
    # Pattern analyze command
    analyze_parser = subparsers.add_parser(
        "failure-pattern-analyze",
        help="Analyze failure patterns from attempt history",
        description="Extract and analyze failure patterns from recovery attempt history",
    )
    analyze_parser.add_argument(
        "--spec",
        type=str,
        default=None,
        help="Spec ID to analyze (default: all specs)",
    )
    analyze_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    analyze_parser.set_defaults(
        func=lambda args: handle_pattern_analyze_command(
            project_dir=args.project_dir,
            spec_id=args.spec,
            output_json=args.json,
        )
    )

    # Pattern query command
    query_parser = subparsers.add_parser(
        "failure-pattern-query",
        help="Query stored failure patterns",
        description="Search and retrieve failure patterns from Graphiti memory",
    )
    query_parser.add_argument(
        "query",
        type=str,
        help="Search query for patterns",
    )
    query_parser.add_argument(
        "--pattern-type",
        type=str,
        default=None,
        choices=[
            "recurring_error",
            "escalating_complexity",
            "model_limitation",
            "circular_fix",
            "context_exhaustion",
        ],
        help="Filter by pattern type",
    )
    query_parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence score (default: 0.0)",
    )
    query_parser.add_argument(
        "--num-results",
        type=int,
        default=10,
        help="Maximum number of results (default: 10)",
    )
    query_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    query_parser.set_defaults(
        func=lambda args: handle_pattern_query_command(
            project_dir=args.project_dir,
            spec_dir=args.spec_dir,
            query=args.query,
            pattern_type=args.pattern_type,
            min_confidence=args.min_confidence,
            num_results=args.num_results,
            output_json=args.json,
        )
    )

    # Pattern statistics command
    stats_parser = subparsers.add_parser(
        "failure-pattern-stats",
        help="Show failure pattern statistics",
        description="Display statistics about stored failure patterns",
    )
    stats_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )
    stats_parser.set_defaults(
        func=lambda args: handle_pattern_stats_command(
            project_dir=args.project_dir,
            spec_dir=args.spec_dir,
            output_json=args.json,
        )
    )


if __name__ == "__main__":
    main()
