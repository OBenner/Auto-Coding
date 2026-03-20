"""
Setup utilities for Auto Code first-run configuration.

This package contains modules for detecting first-run state,
validating dependencies, and guiding users through initial setup.
"""

from .first_run_detector import detect_first_run

__all__ = ["detect_first_run"]
