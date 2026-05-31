"""Fast event-loop installation, ordered before any loop is created.

uvloop provides a faster asyncio loop, but installing it as a *late* import
side effect (as ``core/client.py`` historically did) can leave a default
asyncio loop running under the uvloop policy. That policy exposes no child
watcher, so ``asyncio.create_subprocess_exec`` raises ``NotImplementedError``
and breaks every shell command the runtime issues (coder/QA commands, the
provider e2e mini-pipeline test runner, the CLI runner, the MCP bridge, ...).

Call :func:`install_fast_event_loop` at process entry, before any
``asyncio.run()`` creates a loop, so the loop and policy are consistently
uvloop. See ``run.py`` for the entrypoint wiring.
"""

from __future__ import annotations

import logging

from core.platform import is_windows

logger = logging.getLogger(__name__)


def install_fast_event_loop() -> bool:
    """Install uvloop as the asyncio event-loop policy when available.

    Returns ``True`` when uvloop was installed, ``False`` otherwise. No-ops on
    Windows (which uses the proactor loop) and when uvloop is not installed.
    Safe to call more than once.
    """
    if is_windows():
        return False
    try:
        import uvloop
    except ImportError:
        logger.debug("uvloop not available; using the default asyncio event loop")
        return False
    uvloop.install()
    logger.debug("uvloop installed for improved async performance")
    return True
