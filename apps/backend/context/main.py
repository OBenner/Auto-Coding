#!/usr/bin/env python3
"""
Task Context Builder
====================

Builds focused context for a specific task by searching relevant services.
This is the "RAG-like" component that finds what files matter for THIS task.

Usage:
    # Find context for a task across specific services
    python auto-claude/context.py \
        --services backend,scraper \
        --keywords "retry,error,proxy" \
        --task "Add retry logic when proxies fail" \
        --output auto-claude/specs/001-retry/context.json

    # Use project index to auto-suggest services
    python auto-claude/context.py \
        --task "Add retry logic when proxies fail" \
        --output context.json

The context builder will:
1. Load project index (from analyzer)
2. Search specified services for relevant files
3. Find similar implementations to reference
4. Output focused context for AI agents
"""

import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from context import (
    ContextBuilder,
    FileMatch,
    TaskContext,
)
from context.serialization import serialize_context

# Backward compatibility exports
__all__ = [
    "ContextBuilder",
    "FileMatch",
    "TaskContext",
    "build_task_context",
]


def build_task_context(
    project_dir: Path,
    task: str,
    services: list[str] | None = None,
    keywords: list[str] | None = None,
    output_file: Path | None = None,
) -> dict:
    """
    Build context for a task and optionally save to file.

    Args:
        project_dir: Path to project root
        task: Task description
        services: Services to search (None = auto-detect)
        keywords: Keywords to search for (None = extract from task)
        output_file: Optional path to save JSON output

    Returns:
        Context as a dictionary
    """
    builder = ContextBuilder(project_dir)
    context = builder.build_context(task, services, keywords)

    result = serialize_context(context)

    if output_file:
        output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2)
        print(f"Task context saved to: {output_file}")

    return result


def cmd_build(args):
    """Build task context (original functionality)."""
    # Parse comma-separated args
    services = args.services.split(",") if args.services else None
    keywords = args.keywords.split(",") if args.keywords else None

    result = build_task_context(
        args.project_dir,
        args.task,
        services,
        keywords,
        args.output,
    )

    if not args.quiet or not args.output:
        print(json.dumps(result, indent=2))


def cmd_preload(args):
    """Preload context for a task."""
    # Determine cache directory
    cache_dir = args.cache_dir or (args.project_dir / ".auto-claude" / "cache")
    cache_dir.mkdir(parents=True, exist_ok=True)

    # Build context builder with cache
    builder = ContextBuilder(args.project_dir, cache_dir=cache_dir)

    if not builder.preloader:
        print("Error: Preloader not available (requires project_dir and cache_dir)")
        return

    # Map confidence level to numeric min_score
    confidence_to_min_score = {
        "high": 0.6,
        "medium": 0.3,
        "low": 0.1,
    }
    min_score = confidence_to_min_score.get(args.min_confidence, 0.3)

    # Preload context
    print(f"Preloading context for task: {args.task}")
    result = builder.preload_context(args.task, min_score=min_score)

    print(
        f"\nPreloaded {result['preloaded']} files "
        f"(cached: {result['cached']}, failed: {result['failed']})"
    )
    for pred in result["predictions"]:
        print(
            f"  - {pred['file_path']} "
            f"(confidence: {pred['confidence']}, score: {pred['score']:.2f})"
        )


def cmd_stats(args):
    """Show cache statistics."""
    # Determine cache directory
    cache_dir = args.cache_dir or (args.project_dir / ".auto-claude" / "cache")

    if not cache_dir.exists():
        print("No cache found")
        return

    # Build context builder with cache
    builder = ContextBuilder(args.project_dir, cache_dir=cache_dir)

    if not builder.preloader:
        print("Error: Preloader not available")
        return

    # Get cache stats
    stats = builder.get_cache_stats()

    print("Cache Statistics:")
    print(f"  Total files cached: {stats['file_count']}")
    print(f"  Total size: {stats['total_size_kb']:.1f} KB")
    print(f"  Cache directory: {cache_dir}")

    if stats.get("oldest_hours", 0) > 0:
        print(f"  Oldest entry: {stats['oldest_hours']:.1f} hours ago")


def cmd_clear(args):
    """Clear preloaded cache."""
    # Determine cache directory
    cache_dir = args.cache_dir or (args.project_dir / ".auto-claude" / "cache")

    if not cache_dir.exists():
        print("No cache found")
        return

    # Build context builder with cache
    builder = ContextBuilder(args.project_dir, cache_dir=cache_dir)

    if not builder.preloader:
        print("Error: Preloader not available")
        return

    # Clear cache
    builder.clear_preload_cache()
    print("Cache cleared successfully")


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Build and manage task-specific context",
        prog="context",
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=Path.cwd(),
        help="Project directory (default: current directory)",
    )

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Build command (original functionality)
    build_parser = subparsers.add_parser(
        "build",
        help="Build task context by searching the codebase",
    )
    build_parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Description of the task",
    )
    build_parser.add_argument(
        "--services",
        type=str,
        default=None,
        help="Comma-separated list of services to search",
    )
    build_parser.add_argument(
        "--keywords",
        type=str,
        default=None,
        help="Comma-separated list of keywords to search for",
    )
    build_parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output file for JSON results",
    )
    build_parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output JSON, no status messages",
    )

    # Preload command
    preload_parser = subparsers.add_parser(
        "preload",
        help="Preload context for a task (predict and cache files)",
    )
    preload_parser.add_argument(
        "--task",
        type=str,
        required=True,
        help="Description of the task",
    )
    preload_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory (default: .auto-claude/cache)",
    )
    preload_parser.add_argument(
        "--min-confidence",
        type=str,
        default="medium",
        choices=["high", "medium", "low"],
        help="Minimum confidence threshold for predictions",
    )

    # Stats command
    stats_parser = subparsers.add_parser(
        "stats",
        help="Show cache statistics",
    )
    stats_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory (default: .auto-claude/cache)",
    )

    # Clear command
    clear_parser = subparsers.add_parser(
        "clear",
        help="Clear preloaded cache",
    )
    clear_parser.add_argument(
        "--cache-dir",
        type=Path,
        default=None,
        help="Cache directory (default: .auto-claude/cache)",
    )

    args = parser.parse_args()

    # If no command specified, show help
    if not args.command:
        parser.print_help()
        return

    # Route to appropriate command handler
    if args.command == "build":
        cmd_build(args)
    elif args.command == "preload":
        cmd_preload(args)
    elif args.command == "stats":
        cmd_stats(args)
    elif args.command == "clear":
        cmd_clear(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
