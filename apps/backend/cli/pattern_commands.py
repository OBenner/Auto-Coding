"""
Pattern Commands
================

CLI commands for managing learned codebase patterns
"""

import argparse
import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from integrations.graphiti.pattern_categorizer import get_pattern_categories
from integrations.graphiti.pattern_suggester import get_patterns_by_category
from memory.graphiti_helpers import get_graphiti_memory, is_graphiti_memory_enabled, run_async
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

# Import utils - handle both relative and absolute imports
try:
    from .utils import print_banner
except ImportError:
    from cli.utils import print_banner


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
                            get_patterns_by_category(client, group_id, category, num_results=50)
                        )
                        if results:
                            for i, result in enumerate(results, 1):
                                content = result.get("content", "")
                                score = result.get("score", 0.0)
                                result_category = result.get("category", "uncategorized")
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
            print(warning(f"{icon(Icons.WARNING)} Failed to load Graphiti patterns: {e}"))
            print()

    # Show available categories
    if not category:
        print(divider())
        print_header("Available Categories")
        print()
        categories = get_pattern_categories()
        for cat in categories:
            print(f"  • {cat}")
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

    # Write updated patterns back to file
    memory_dir = get_memory_dir(spec_dir)
    patterns_file = memory_dir / "patterns.md"

    with open(patterns_file, "w", encoding="utf-8") as f:
        f.write("# Code Patterns\n\n")
        f.write("Established patterns to follow in this codebase:\n\n")
        for pattern in patterns:
            f.write(f"- {pattern}\n")

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

    # Write updated patterns back to file
    memory_dir = get_memory_dir(spec_dir)
    patterns_file = memory_dir / "patterns.md"

    with open(patterns_file, "w", encoding="utf-8") as f:
        if patterns:
            f.write("# Code Patterns\n\n")
            f.write("Established patterns to follow in this codebase:\n\n")
            for pattern in patterns:
                f.write(f"- {pattern}\n")
        else:
            # Empty file if no patterns left
            f.write("# Code Patterns\n\n")
            f.write("No patterns yet.\n")

    print(warning(f"Deleted: {deleted_pattern}"))
    print()
    print(info("Pattern removed successfully"))
    print()


def handle_patterns_command(spec_dir: Path, args: argparse.Namespace) -> None:
    """
    Handle the pattern management command.

    Args:
        spec_dir: Spec directory path
        args: Parsed command-line arguments
    """
    action = args.action

    if action == "list":
        list_patterns(spec_dir, category=args.category)
    elif action == "show":
        if not args.index:
            print(warning(f"{icon(Icons.WARNING)} --index required for 'show' action"))
            sys.exit(1)
        show_pattern_details(spec_dir, args.index)
    elif action == "approve":
        if not args.index:
            print(warning(f"{icon(Icons.WARNING)} --index required for 'approve' action"))
            sys.exit(1)
        approve_pattern(spec_dir, args.index)
    elif action == "override":
        if not args.index or not args.text:
            print(
                warning(
                    f"{icon(Icons.WARNING)} --index and --text required for 'override' action"
                )
            )
            sys.exit(1)
        override_pattern(spec_dir, args.index, args.text)
    elif action == "delete":
        if not args.index:
            print(warning(f"{icon(Icons.WARNING)} --index required for 'delete' action"))
            sys.exit(1)
        delete_pattern(spec_dir, args.index)
    else:
        print(warning(f"{icon(Icons.WARNING)} Unknown action: {action}"))
        sys.exit(1)


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
        print(warning(f"{icon(Icons.WARNING)} Spec directory not found: {args.spec_dir}"))
        sys.exit(1)

    # Handle the command
    handle_patterns_command(args.spec_dir, args)


if __name__ == "__main__":
    main()
