"""
Shared utilities for analytics modules.

Contains common helper functions used by both model_usage_analytics.py
and productivity_analytics.py to avoid code duplication.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime


def parse_timestamp(ts: str | None) -> datetime | None:
    """Parse ISO timestamp string to timezone-aware UTC datetime.

    Returns None for invalid or missing timestamps.
    """
    if not ts:
        return None
    try:
        if ts.endswith("Z"):
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(ts)

        # Ensure timezone-aware in UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        else:
            dt = dt.astimezone(UTC)
        return dt
    except (ValueError, AttributeError):
        return None


def normalize_boundary(dt: datetime | None) -> datetime | None:
    """Normalize start/end boundary datetimes to timezone-aware UTC."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


def add_common_cli_args(parser: object) -> None:
    """Add shared CLI arguments (date filters, export options) to an argparse parser."""
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Export format (default: json)",
    )  # type: ignore[attr-defined]
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: auto-generated in analytics dir)",
    )  # type: ignore[attr-defined]
    parser.add_argument("--start-date", type=str, help="Start date filter (ISO format)")  # type: ignore[attr-defined]
    parser.add_argument("--end-date", type=str, help="End date filter (ISO format)")  # type: ignore[attr-defined]
    parser.add_argument(
        "--window-days",
        type=int,
        default=30,
        help="Number of days to look back for trends (default: 30)",
    )  # type: ignore[attr-defined]
    parser.add_argument(
        "--granularity",
        choices=["daily", "weekly", "monthly"],
        default="daily",
        help="Time granularity for trends (default: daily)",
    )  # type: ignore[attr-defined]


def parse_date_args(args: object) -> tuple[datetime | None, datetime | None]:
    """Parse --start-date and --end-date CLI arguments. Exits on invalid format."""

    def _parse(value: str | None, label: str) -> datetime | None:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            print(f"Error: Invalid {label} date format: {value}", file=sys.stderr)
            sys.exit(1)

    start = _parse(getattr(args, "start_date", None), "start")
    end = _parse(getattr(args, "end_date", None), "end")

    if start is not None and end is not None and start > end:
        print("Error: start date must be <= end date", file=sys.stderr)
        sys.exit(1)

    return (start, end)
