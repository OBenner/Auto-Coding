#!/usr/bin/env python3
"""
Exit Codes for CI/CD Mode
=========================

Defines standard exit codes for build results in CI/CD pipelines.
These codes enable automation tools to determine build status programmatically.
"""

from enum import IntEnum


class ExitCode(IntEnum):
    """Standard exit codes for Auto Claude build results.

    These codes follow Unix conventions where 0 indicates success and
    non-zero values indicate various failure modes.

    Usage:
        sys.exit(ExitCode.SUCCESS)      # Build completed successfully
        sys.exit(ExitCode.BUILD_FAILED) # Coder agent failed to implement
        sys.exit(ExitCode.QA_FAILED)    # Build passed but QA rejected
        sys.exit(ExitCode.SYSTEM_ERROR) # Unexpected error/exception
        sys.exit(ExitCode.INTERRUPTED)  # Build paused/interrupted by user
    """

    SUCCESS = 0  # Build completed and passed QA
    BUILD_FAILED = 1  # Coder agent failed to implement feature
    QA_FAILED = 2  # Build completed but QA validation failed
    SYSTEM_ERROR = 3  # Unexpected system error or exception
    INTERRUPTED = 130  # Build was interrupted/paused by user (SIGINT convention)
