"""
Shared mock setup helpers for QA test files (test_qa_fixer.py, test_qa_reviewer.py).

Both QA test files need to mock the same set of modules before importing
their module-under-test. This module centralizes the common mock definitions
to reduce code duplication.
"""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# Modules to mock for QA module imports to succeed
QA_MODULES_TO_MOCK = [
    "claude_agent_sdk",
    "claude_agent_sdk.types",
    "ui",
    "progress",
    "task_logger",
    "linear_updater",
    "client",
    "core.client",
    "core.model_fallback",
    "agents",
    "agents.memory_manager",
    "agents.session",
    "agents.e2e_generator",
    "agents.test_generator",
    "agents.coder",
    "agents.planner",
    "agents.code_reviewer",
    "agents.documentation_generator",
    "agents.utils",
    "agents.base",
    "debug",
    "phase_config",
    "phase_event",
    "security.tool_input_validator",
    "security.constants",
    "services.recovery",
    "analysis.coverage_analyzer",
    "analysis.code_analyzer",
    "analysis.coverage_reporter",
    "analysis.failure_analyzer",
    "analysis.ts_analyzer",
    "prompts_pkg",
    "spec.coverage_config",
    "integrations",
    "integrations.graphiti",
    "integrations.graphiti.memory",
]


def ensure_backend_path():
    """Add apps/backend to sys.path if not already present.

    Returns the original sys.path snapshot for use with restore_backend_path().
    """
    original = list(sys.path)
    backend_path = str(Path(__file__).parent.parent / "apps" / "backend")
    if backend_path not in sys.path:
        sys.path.insert(0, backend_path)
    return original


def restore_backend_path(original_sys_path):
    """Restore sys.path to the state before ensure_backend_path() was called."""
    sys.path[:] = original_sys_path


def create_base_mocks(**overrides):
    """Create the standard mock dict for QA module imports.

    Returns a dict mapping module names to mock objects. Pass overrides
    to replace specific mocks (e.g., services.recovery, analysis.coverage_analyzer).
    """
    mock_agents_pkg = MagicMock()
    mock_agents_pkg.__path__ = []

    mock_mm = MagicMock()
    mock_mm.get_graphiti_context = AsyncMock(return_value=None)
    mock_mm.save_session_memory = AsyncMock(return_value=(True, "file"))

    mocks = {
        "claude_agent_sdk": MagicMock(
            ClaudeSDKClient=MagicMock, ClaudeAgentOptions=MagicMock
        ),
        "claude_agent_sdk.types": MagicMock(),
        "ui": MagicMock(print_status=MagicMock()),
        "progress": MagicMock(
            count_subtasks=MagicMock(return_value=(3, 3)),
            is_build_complete=MagicMock(return_value=True),
        ),
        "task_logger": MagicMock(
            LogPhase=MagicMock(),
            LogEntryType=MagicMock(),
            get_task_logger=MagicMock(return_value=None),
        ),
        "linear_updater": MagicMock(is_linear_enabled=MagicMock(return_value=False)),
        "client": MagicMock(),
        "core.client": MagicMock(create_client=MagicMock()),
        "core.model_fallback": MagicMock(),
        "agents": mock_agents_pkg,
        "agents.memory_manager": mock_mm,
        "agents.session": MagicMock(),
        "agents.e2e_generator": MagicMock(),
        "agents.test_generator": MagicMock(),
        "agents.coder": MagicMock(),
        "agents.planner": MagicMock(),
        "agents.code_reviewer": MagicMock(),
        "agents.documentation_generator": MagicMock(),
        "agents.utils": MagicMock(),
        "agents.base": MagicMock(),
        "debug": MagicMock(),
        "phase_config": MagicMock(
            resolve_model_id=MagicMock(return_value="claude-haiku")
        ),
        "phase_event": MagicMock(),
        "security.tool_input_validator": MagicMock(
            get_safe_tool_input=MagicMock(return_value=None)
        ),
        "security.constants": MagicMock(),
        "services.recovery": MagicMock(),
        "analysis.coverage_analyzer": MagicMock(),
        "analysis.code_analyzer": MagicMock(),
        "analysis.coverage_reporter": MagicMock(),
        "analysis.failure_analyzer": MagicMock(),
        "analysis.ts_analyzer": MagicMock(),
        "prompts_pkg": MagicMock(
            get_qa_reviewer_prompt=MagicMock(return_value="QA reviewer prompt")
        ),
        "spec.coverage_config": MagicMock(),
        "integrations": MagicMock(),
        "integrations.graphiti": MagicMock(),
        "integrations.graphiti.memory": MagicMock(),
    }
    mocks.update(overrides)
    return mocks


def install_mocks_and_import(mocks):
    """Install mocks into sys.modules, returning saved originals for restore.

    Args:
        mocks: dict mapping module names to mock objects

    Returns:
        dict of saved original modules for use with restore_modules()
    """
    saved = {}
    for name in QA_MODULES_TO_MOCK:
        if name in sys.modules:
            saved[name] = sys.modules[name]
    for name, mock in mocks.items():
        sys.modules[name] = mock
    return saved


def restore_modules(saved):
    """Restore sys.modules to pre-mock state."""
    for name in QA_MODULES_TO_MOCK:
        if name in saved:
            sys.modules[name] = saved[name]
        elif name in sys.modules:
            del sys.modules[name]


async def aiter_empty():
    """Empty async iterator for mock receive_response."""
    if False:
        yield


def make_text_message(text):
    """Create a mock AssistantMessage with a TextBlock."""
    block = MagicMock()
    type(block).__name__ = "TextBlock"
    block.text = text
    msg = MagicMock()
    type(msg).__name__ = "AssistantMessage"
    msg.content = [block]
    return msg


async def aiter_messages(*messages):
    """Async iterator yielding mock messages."""
    for msg in messages:
        yield msg
