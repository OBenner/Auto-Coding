#!/usr/bin/env python3
"""
Analytics CLI
=============

Command-line interface for accessing analytics data from the frontend.
Provides JSON output for IPC communication.

Usage:
    python analytics_cli.py summary --specs-dir <path>
    python analytics_cli.py agent-stats --specs-dir <path>
    python analytics_cli.py trends --specs-dir <path> --days <n>
    python analytics_cli.py report --specs-dir <path>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.analytics import AnalyticsService


def command_summary(args: argparse.Namespace) -> None:
    """Get metrics summary."""
    service = AnalyticsService(specs_dir=Path(args.specs_dir))
    summary = service.get_metrics_summary()
    print(json.dumps(summary.to_dict(), indent=2))


def command_agent_stats(args: argparse.Namespace) -> None:
    """Get agent-specific statistics."""
    service = AnalyticsService(specs_dir=Path(args.specs_dir))
    stats = service.get_agent_stats()
    result = {name: stat.to_dict() for name, stat in stats.items()}
    print(json.dumps(result, indent=2))


def command_trends(args: argparse.Namespace) -> None:
    """Get trend data."""
    service = AnalyticsService(specs_dir=Path(args.specs_dir))
    trends = service.get_trend_data(days=args.days)
    result = [trend.to_dict() for trend in trends]
    print(json.dumps(result, indent=2))


def command_report(args: argparse.Namespace) -> None:
    """Get comprehensive analytics report."""
    service = AnalyticsService(specs_dir=Path(args.specs_dir))
    report = service.get_analytics_report()
    print(json.dumps(report, indent=2))


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Analytics CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Summary command
    parser_summary = subparsers.add_parser("summary", help="Get metrics summary")
    parser_summary.add_argument("--specs-dir", required=True, help="Path to specs directory")

    # Agent stats command
    parser_agent = subparsers.add_parser("agent-stats", help="Get agent statistics")
    parser_agent.add_argument("--specs-dir", required=True, help="Path to specs directory")

    # Trends command
    parser_trends = subparsers.add_parser("trends", help="Get trend data")
    parser_trends.add_argument("--specs-dir", required=True, help="Path to specs directory")
    parser_trends.add_argument("--days", type=int, default=30, help="Number of days (default: 30)")

    # Report command
    parser_report = subparsers.add_parser("report", help="Get comprehensive report")
    parser_report.add_argument("--specs-dir", required=True, help="Path to specs directory")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "summary":
            command_summary(args)
        elif args.command == "agent-stats":
            command_agent_stats(args)
        elif args.command == "trends":
            command_trends(args)
        elif args.command == "report":
            command_report(args)
        else:
            print(f"Unknown command: {args.command}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
