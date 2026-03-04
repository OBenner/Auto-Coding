"""
Debug Helper Factory
====================

Provides a factory function to create module-scoped debug wrappers,
eliminating the need to duplicate the debug import/fallback pattern
across every module.

Usage:
    from agents.debug_helpers import create_debug_helpers

    _debug, _debug_error, _debug_success, _debug_verbose, _debug_warning = (
        create_debug_helpers("agents.my_module")
    )
"""

from __future__ import annotations


def create_debug_helpers(source: str):
    """
    Create a set of debug helper functions bound to the given source module name.

    Args:
        source: Module identifier string (e.g. "agents.process_isolator")

    Returns:
        Tuple of (debug, debug_error, debug_success, debug_verbose, debug_warning)
    """
    try:
        from debug import (
            debug as _raw_debug,
        )
        from debug import (
            debug_error as _raw_debug_error,
        )
        from debug import (
            debug_success as _raw_debug_success,
        )
        from debug import (
            debug_verbose as _raw_debug_verbose,
        )
        from debug import (
            debug_warning as _raw_debug_warning,
        )
    except ImportError:

        def _raw_debug(*_args, **_kwargs):
            """No-op fallback when debug module is unavailable."""

        _raw_debug_error = _raw_debug
        _raw_debug_success = _raw_debug
        _raw_debug_verbose = _raw_debug
        _raw_debug_warning = _raw_debug

    def _debug(msg: str, **kwargs) -> None:
        _raw_debug(source, msg, **kwargs)

    def _debug_error(msg: str, **kwargs) -> None:
        _raw_debug_error(source, msg, **kwargs)

    def _debug_success(msg: str, **kwargs) -> None:
        _raw_debug_success(source, msg, **kwargs)

    def _debug_verbose(msg: str, **kwargs) -> None:
        _raw_debug_verbose(source, msg, **kwargs)

    def _debug_warning(msg: str, **kwargs) -> None:
        _raw_debug_warning(source, msg, **kwargs)

    return _debug, _debug_error, _debug_success, _debug_verbose, _debug_warning
