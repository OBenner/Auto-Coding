"""Tests for cross-backend plugin prompt augmentation on the Direct-API path.

The Claude SDK backend augments the system prompt inside ``create_client()``.
Direct providers carry their instructions in the agent message, so coder.py
appends the same plugin contributions to that message — but only for non-claude
providers, so the claude path is never augmented twice.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "apps" / "backend"))

from agents.coder import _augment_direct_api_prompt

_TARGET = "plugins.runtime.apply_plugin_prompt_augmentations"


def test_claude_provider_is_not_augmented(tmp_path):
    # Claude already augments via create_client(); the message must be left
    # untouched so contributions are not applied twice.
    with patch(_TARGET) as apply_mock:
        out = _augment_direct_api_prompt(
            "BASE", "claude", tmp_path, tmp_path, "coder", None
        )
    assert out == "BASE"
    apply_mock.assert_not_called()


def test_direct_provider_is_augmented(tmp_path):
    augmented = "BASE\n\n# Plugin Runtime Instructions\n## demo\nhello"
    with patch(_TARGET, return_value=augmented) as apply_mock:
        out = _augment_direct_api_prompt(
            "BASE", "openai", tmp_path, tmp_path, "coder", {"subtask_id": "s1"}
        )
    apply_mock.assert_called_once_with(
        "BASE", tmp_path, tmp_path, "coder", metadata={"subtask_id": "s1"}
    )
    assert out == augmented


def test_codex_provider_is_augmented(tmp_path):
    with patch(_TARGET, return_value="BASE+X") as apply_mock:
        out = _augment_direct_api_prompt(
            "BASE", "codex", tmp_path, tmp_path, "planner", None
        )
    apply_mock.assert_called_once()
    assert out == "BASE+X"


def test_augmentation_failure_degrades_to_base_prompt(tmp_path):
    with patch(_TARGET, side_effect=RuntimeError("boom")):
        out = _augment_direct_api_prompt(
            "BASE", "openai", tmp_path, tmp_path, "coder", None
        )
    assert out == "BASE"
