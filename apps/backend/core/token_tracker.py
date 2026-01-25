#!/usr/bin/env python3
"""
Token Usage Tracking Utility
============================

Centralized token usage tracking for the Auto-Claude framework.
Controlled via environment variables:
  - DEBUG=true          Enable debug mode (required for token logging)
  - DEBUG_LEVEL=1|2|3   Log verbosity (1=basic, 2=detailed, 3=verbose)
  - DEBUG_LOG_FILE=path Optional file output

Usage:
    from core.token_tracker import TokenTracker, get_global_tracker

    # Instance-based tracking
    tracker = TokenTracker()
    tracker.log_phase("discovery", input_tokens=1500, output_tokens=800)
    tracker.log_phase("spec_writing", input_tokens=3000, output_tokens=1200)
    summary = tracker.get_summary()

    # Global tracker for cross-module tracking
    get_global_tracker().log_phase("planning", 2000, 500)
"""

import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from core.debug import (
    Colors,
    _get_debug_enabled,
    _get_debug_level,
    _write_log,
    is_debug_enabled,
)


@dataclass
class PhaseTokenUsage:
    """Token usage data for a single phase."""

    phase_name: str
    input_tokens: int
    output_tokens: int
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output)."""
        return self.input_tokens + self.output_tokens

    @property
    def cost_weight(self) -> float:
        """
        Weighted cost estimate.
        Output tokens are typically 2-5x more expensive than input tokens.
        Uses 3x as a reasonable middle estimate.
        """
        return self.input_tokens + (self.output_tokens * 3)


class TokenTracker:
    """
    Tracks token usage across phases for debugging and optimization.

    Only logs when DEBUG=true is set in environment.
    """

    def __init__(self, session_id: str | None = None):
        """
        Initialize a new token tracker.

        Args:
            session_id: Optional identifier for this tracking session.
        """
        self._phases: list[PhaseTokenUsage] = []
        self._session_id = session_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self._start_time = datetime.now()

    @property
    def session_id(self) -> str:
        """Get the session identifier."""
        return self._session_id

    @property
    def phases(self) -> list[PhaseTokenUsage]:
        """Get list of all tracked phases."""
        return self._phases.copy()

    @property
    def total_input_tokens(self) -> int:
        """Total input tokens across all phases."""
        return sum(p.input_tokens for p in self._phases)

    @property
    def total_output_tokens(self) -> int:
        """Total output tokens across all phases."""
        return sum(p.output_tokens for p in self._phases)

    @property
    def total_tokens(self) -> int:
        """Total tokens (input + output) across all phases."""
        return self.total_input_tokens + self.total_output_tokens

    def log_phase(
        self,
        phase_name: str,
        input_tokens: int,
        output_tokens: int,
        **kwargs: Any,
    ) -> None:
        """
        Log token usage for a phase.

        Args:
            phase_name: Name of the phase (e.g., "discovery", "planning")
            input_tokens: Number of input tokens consumed
            output_tokens: Number of output tokens generated
            **kwargs: Additional metadata to log
        """
        # Always track internally for summary
        usage = PhaseTokenUsage(
            phase_name=phase_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        self._phases.append(usage)

        # Only log to console/file if debug is enabled
        if not _get_debug_enabled():
            return

        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Build the log line
        log_line = (
            f"{Colors.TIMESTAMP}[{timestamp}]{Colors.RESET} "
            f"{Colors.DEBUG}[TOKENS]{Colors.RESET} "
            f"{Colors.MODULE}[{phase_name}]{Colors.RESET} "
            f"{Colors.DEBUG_DIM}Token usage{Colors.RESET}"
        )

        # Add token details
        log_line += (
            f"\n  {Colors.KEY}input{Colors.RESET}: "
            f"{Colors.VALUE}{input_tokens:,}{Colors.RESET}"
        )
        log_line += (
            f"\n  {Colors.KEY}output{Colors.RESET}: "
            f"{Colors.VALUE}{output_tokens:,}{Colors.RESET}"
        )
        log_line += (
            f"\n  {Colors.KEY}total{Colors.RESET}: "
            f"{Colors.VALUE}{usage.total_tokens:,}{Colors.RESET}"
        )

        # Add any extra kwargs
        for key, value in kwargs.items():
            log_line += (
                f"\n  {Colors.KEY}{key}{Colors.RESET}: "
                f"{Colors.VALUE}{value}{Colors.RESET}"
            )

        _write_log(log_line)

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of token usage across all phases.

        Returns:
            Dictionary with session summary including per-phase breakdown
            and totals.
        """
        elapsed = (datetime.now() - self._start_time).total_seconds()

        summary = {
            "session_id": self._session_id,
            "elapsed_seconds": round(elapsed, 2),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "phase_count": len(self._phases),
            "phases": [
                {
                    "name": p.phase_name,
                    "input": p.input_tokens,
                    "output": p.output_tokens,
                    "total": p.total_tokens,
                }
                for p in self._phases
            ],
        }

        return summary

    def log_summary(self) -> None:
        """
        Log a formatted summary of all token usage.

        Only outputs if DEBUG=true is set.
        """
        if not _get_debug_enabled():
            return

        summary = self.get_summary()
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

        # Build summary header
        separator = "─" * 50
        log_line = (
            f"\n{Colors.TIMESTAMP}[{timestamp}]{Colors.RESET} "
            f"{Colors.DEBUG}{Colors.BOLD}┌{separator}┐{Colors.RESET}"
        )
        title = f"Token Usage Summary (Session: {self._session_id})"
        padding = 50 - len(title) - 1
        log_line += (
            f"\n{Colors.TIMESTAMP}         {Colors.RESET} "
            f"{Colors.DEBUG}{Colors.BOLD}│ {title}{' ' * padding}│{Colors.RESET}"
        )
        log_line += (
            f"\n{Colors.TIMESTAMP}         {Colors.RESET} "
            f"{Colors.DEBUG}{Colors.BOLD}└{separator}┘{Colors.RESET}"
        )

        # Add per-phase breakdown
        if self._phases:
            log_line += f"\n  {Colors.KEY}Phases:{Colors.RESET}"
            for phase in self._phases:
                log_line += (
                    f"\n    {Colors.MODULE}{phase.phase_name}{Colors.RESET}: "
                    f"in={phase.input_tokens:,} out={phase.output_tokens:,} "
                    f"total={phase.total_tokens:,}"
                )

        # Add totals
        log_line += f"\n  {Colors.KEY}Totals:{Colors.RESET}"
        log_line += (
            f"\n    {Colors.SUCCESS}Input:{Colors.RESET} "
            f"{Colors.VALUE}{summary['total_input_tokens']:,}{Colors.RESET}"
        )
        log_line += (
            f"\n    {Colors.WARNING}Output:{Colors.RESET} "
            f"{Colors.VALUE}{summary['total_output_tokens']:,}{Colors.RESET}"
        )
        log_line += (
            f"\n    {Colors.DEBUG}Total:{Colors.RESET} "
            f"{Colors.VALUE}{summary['total_tokens']:,}{Colors.RESET}"
        )
        log_line += (
            f"\n    {Colors.DIM}Elapsed:{Colors.RESET} "
            f"{Colors.VALUE}{summary['elapsed_seconds']}s{Colors.RESET}"
        )

        _write_log(log_line)

    def reset(self) -> None:
        """Clear all tracked phases and reset the session."""
        self._phases.clear()
        self._start_time = datetime.now()


# Global tracker instance for cross-module usage
_global_tracker: TokenTracker | None = None


def get_global_tracker() -> TokenTracker:
    """
    Get the global token tracker instance.

    Creates a new instance if one doesn't exist.
    """
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = TokenTracker(session_id="global")
    return _global_tracker


def reset_global_tracker() -> None:
    """Reset the global tracker instance."""
    global _global_tracker
    if _global_tracker is not None:
        _global_tracker.reset()


def is_token_tracking_enabled() -> bool:
    """
    Check if token tracking is enabled.

    Token tracking is enabled when DEBUG=true.
    """
    return _get_debug_enabled()
