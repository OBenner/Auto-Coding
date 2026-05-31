"""Tests for the fast event-loop installation (uvloop ordering).

These guard the regression where uvloop, installed late as an import side
effect, left a default asyncio loop under a uvloop policy with no child
watcher -- so ``create_subprocess_exec`` raised ``NotImplementedError`` and
broke every shell command. Installing at entry keeps loop and policy
consistent.
"""

from __future__ import annotations

import asyncio
import sys

import pytest
from core.event_loop import install_fast_event_loop
from core.platform import is_windows


def test_install_fast_event_loop_enables_subprocess():
    """After install, asyncio.run can spawn a subprocess (the bug's symptom)."""
    original = asyncio.get_event_loop_policy()
    try:
        install_fast_event_loop()

        async def _spawn() -> str:
            proc = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                "print('subprocess-ok')",
                stdout=asyncio.subprocess.PIPE,
            )
            out, _ = await proc.communicate()
            return out.decode().strip()

        assert asyncio.run(_spawn()) == "subprocess-ok"
    finally:
        asyncio.set_event_loop_policy(original)


def test_install_fast_event_loop_sets_uvloop_when_available():
    """On a non-Windows host with uvloop installed, the policy becomes uvloop."""
    if is_windows():
        pytest.skip("uvloop is not used on Windows")
    try:
        import uvloop
    except ImportError:
        pytest.skip("uvloop is not installed")

    original = asyncio.get_event_loop_policy()
    try:
        assert install_fast_event_loop() is True
        assert isinstance(asyncio.get_event_loop_policy(), uvloop.EventLoopPolicy)
    finally:
        asyncio.set_event_loop_policy(original)


def test_install_fast_event_loop_noops_on_windows(monkeypatch):
    """On Windows the proactor loop is kept; the policy is left untouched."""
    import core.event_loop as event_loop

    monkeypatch.setattr(event_loop, "is_windows", lambda: True)
    original = asyncio.get_event_loop_policy()
    assert event_loop.install_fast_event_loop() is False
    assert asyncio.get_event_loop_policy() is original
