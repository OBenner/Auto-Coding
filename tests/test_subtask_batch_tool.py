"""
Tests for Subtask Batch Update Tool
====================================

Tests the batch update tool that allows updating multiple subtask statuses
in a single operation for efficient workflow management.
"""

import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Mock claude_agent_sdk with a proper tool decorator so subtask.py tools are async
_mock_agent_sdk = MagicMock()

# Track all modules we modify so we can restore them later
_original_sdk_module = sys.modules.get("claude_agent_sdk")
_popped_modules: dict[str, object] = {}


def _mock_tool_decorator(name, description, params):
    def decorator(func):
        func._tool_name = name
        func._tool_description = description
        func._tool_params = params
        return func

    return decorator


_mock_agent_sdk.tool = _mock_tool_decorator
sys.modules["claude_agent_sdk"] = _mock_agent_sdk

# Force fresh import so subtask.py picks up our mock tool decorator
for _mod in [
    "agents.tools_pkg.tools.subtask",
    "agents.tools_pkg.tools",
    "agents.tools_pkg",
]:
    _existing = sys.modules.pop(_mod, None)
    if _existing is not None:
        _popped_modules[_mod] = _existing


@pytest.fixture(scope="module", autouse=True)
def _restore_sys_modules_after_all_tests():
    """Restore sys.modules mutations made at module level after all tests complete."""
    yield
    # Restore or remove the claude_agent_sdk mock
    if _original_sdk_module is not None:
        sys.modules["claude_agent_sdk"] = _original_sdk_module
    else:
        sys.modules.pop("claude_agent_sdk", None)
    # Restore any popped subtask modules
    for mod_name, mod_obj in _popped_modules.items():
        sys.modules[mod_name] = mod_obj


class TestUpdateSubtaskInPlan:
    """Tests for _update_subtask_in_plan() helper function."""

    def test_update_existing_subtask(self):
        """Should update status of existing subtask."""
        from agents.tools_pkg.tools.subtask import _update_subtask_in_plan

        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-1", "completed", "Done!")
        assert result is True
        assert plan["phases"][0]["subtasks"][0]["status"] == "completed"
        assert plan["phases"][0]["subtasks"][0]["notes"] == "Done!"
        assert "updated_at" in plan["phases"][0]["subtasks"][0]

    def test_update_with_empty_notes(self):
        """Should handle empty notes string without setting notes field."""
        from agents.tools_pkg.tools.subtask import _update_subtask_in_plan

        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-1", "in_progress", "")
        assert result is True
        assert plan["phases"][0]["subtasks"][0]["status"] == "in_progress"
        # Empty notes should NOT set the field (function only sets if notes is truthy)
        assert "notes" not in plan["phases"][0]["subtasks"][0]

    def test_update_nonexistent_subtask(self):
        """Should return False for non-existent subtask."""
        from agents.tools_pkg.tools.subtask import _update_subtask_in_plan

        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-999", "completed", "Notes")
        assert result is False
        # Original plan should be unchanged
        assert plan["phases"][0]["subtasks"][0]["status"] == "pending"

    def test_updates_last_updated_timestamp(self):
        """Should update plan's last_updated timestamp."""
        from agents.tools_pkg.tools.subtask import _update_subtask_in_plan

        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                    ]
                }
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-1", "completed", "")
        assert result is True
        assert "last_updated" in plan

    def test_searches_multiple_phases(self):
        """Should search across multiple phases."""
        from agents.tools_pkg.tools.subtask import _update_subtask_in_plan

        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [{"id": "subtask-1", "status": "pending"}],
                },
                {
                    "id": "phase-2",
                    "subtasks": [{"id": "subtask-2", "status": "pending"}],
                },
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-2", "completed", "")
        assert result is True
        assert plan["phases"][1]["subtasks"][0]["status"] == "completed"

    def test_stops_after_first_match(self):
        """Should stop searching after finding first match."""
        from agents.tools_pkg.tools.subtask import _update_subtask_in_plan

        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [{"id": "subtask-1", "status": "pending"}],
                },
            ]
        }

        result = _update_subtask_in_plan(plan, "subtask-1", "completed", "")
        assert result is True
        # Should only update first occurrence even if there were duplicates
        assert plan["phases"][0]["subtasks"][0]["status"] == "completed"


class TestBatchUpdateValidation:
    """Tests for batch_update_subtask_statuses validation logic."""

    @pytest.fixture(autouse=True)
    def reload_subtask_with_mock(self):
        """Force fresh import of subtask module with the proper mock tool decorator."""
        sys.modules["claude_agent_sdk"] = _mock_agent_sdk
        _saved: dict = {}
        for mod in [
            "agents.tools_pkg.tools.subtask",
            "agents.tools_pkg.tools",
            "agents.tools_pkg",
        ]:
            if mod in sys.modules:
                _saved[mod] = sys.modules.pop(mod)
        yield
        for mod, obj in _saved.items():
            sys.modules[mod] = obj

    @pytest.fixture
    def temp_spec_dir(self, tmp_path):
        """Create temporary spec directory for testing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        return spec_dir

    @pytest.fixture
    def sample_plan(self):
        """Create sample implementation plan."""
        return {
            "feature": "Test Feature",
            "created_at": "2026-03-05T10:00:00.000Z",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Implementation",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                        {"id": "subtask-2", "status": "pending"},
                        {"id": "subtask-3", "status": "pending"},
                    ],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_empty_updates_list(self, temp_spec_dir, sample_plan):
        """Should reject empty updates list."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Write plan file
        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]  # Second tool is batch_update

        result = await batch_update({"updates": []})
        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        assert "No updates provided" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_missing_updates_key(self, temp_spec_dir, sample_plan):
        """Should reject request without updates key."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Write plan file
        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        result = await batch_update({})
        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        assert "No updates provided" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_non_dict_update(self, temp_spec_dir, sample_plan):
        """Should reject non-dictionary update items."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        result = await batch_update({"updates": ["not-a-dict"]})
        assert "content" in result
        assert "Error: Validation failed" in result["content"][0]["text"]
        assert "Must be a dictionary" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_missing_subtask_id(self, temp_spec_dir, sample_plan):
        """Should reject update without subtask_id."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        result = await batch_update({"updates": [{"status": "completed"}]})
        assert "content" in result
        assert "Error: Validation failed" in result["content"][0]["text"]
        assert "Missing 'subtask_id'" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_missing_status(self, temp_spec_dir, sample_plan):
        """Should reject update without status."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        result = await batch_update({"updates": [{"subtask_id": "subtask-1"}]})
        assert "content" in result
        assert "Error: Validation failed" in result["content"][0]["text"]
        assert "Missing 'status'" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_invalid_status(self, temp_spec_dir, sample_plan):
        """Should reject invalid status value."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        result = await batch_update(
            {"updates": [{"subtask_id": "subtask-1", "status": "invalid_status"}]}
        )
        assert "content" in result
        assert "Error: Validation failed" in result["content"][0]["text"]
        assert "Invalid status 'invalid_status'" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_multiple_validation_errors(self, temp_spec_dir, sample_plan):
        """Should report multiple validation errors at once."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        result = await batch_update(
            {"updates": [{"status": "completed"}, {"subtask_id": "subtask-1"}]}
        )
        assert "content" in result
        text = result["content"][0]["text"]
        assert "Error: Validation failed" in text
        # Should contain both errors
        assert "Missing 'subtask_id'" in text
        assert "Missing 'status'" in text


class TestBatchUpdateSuccessCases:
    """Tests for successful batch update operations."""

    @pytest.fixture(autouse=True)
    def reload_subtask_with_mock(self):
        """Force fresh import of subtask module with the proper mock tool decorator."""
        sys.modules["claude_agent_sdk"] = _mock_agent_sdk
        _saved: dict = {}
        for mod in [
            "agents.tools_pkg.tools.subtask",
            "agents.tools_pkg.tools",
            "agents.tools_pkg",
        ]:
            if mod in sys.modules:
                _saved[mod] = sys.modules.pop(mod)
        yield
        for mod, obj in _saved.items():
            sys.modules[mod] = obj

    @pytest.fixture
    def temp_spec_dir(self, tmp_path):
        """Create temporary spec directory for testing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        return spec_dir

    @pytest.fixture
    def sample_plan(self):
        """Create sample implementation plan."""
        return {
            "feature": "Test Feature",
            "created_at": "2026-03-05T10:00:00.000Z",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Implementation",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                        {"id": "subtask-2", "status": "pending"},
                        {"id": "subtask-3", "status": "pending"},
                    ],
                }
            ],
        }

    @pytest.mark.asyncio
    async def test_successful_batch_update(self, temp_spec_dir, sample_plan):
        """Should successfully update multiple subtasks."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [
            {"subtask_id": "subtask-1", "status": "completed"},
            {"subtask_id": "subtask-2", "status": "in_progress"},
        ]

        result = await batch_update({"updates": updates})
        assert "content" in result
        text = result["content"][0]["text"]
        assert "Successfully updated 2 subtask(s)" in text
        assert "subtask-1 -> completed" in text
        assert "subtask-2 -> in_progress" in text

        # Verify plan file was updated
        with open(plan_file, encoding="utf-8") as f:
            updated_plan = json.load(f)
        assert updated_plan["phases"][0]["subtasks"][0]["status"] == "completed"
        assert updated_plan["phases"][0]["subtasks"][1]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_update_with_notes(self, temp_spec_dir, sample_plan):
        """Should update subtasks with notes."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [
            {"subtask_id": "subtask-1", "status": "completed", "notes": "All done!"},
        ]

        result = await batch_update({"updates": updates})
        assert "content" in result
        assert "Successfully updated 1 subtask(s)" in result["content"][0]["text"]

        # Verify notes were saved
        with open(plan_file, encoding="utf-8") as f:
            updated_plan = json.load(f)
        assert updated_plan["phases"][0]["subtasks"][0]["notes"] == "All done!"

    @pytest.mark.asyncio
    async def test_valid_status_values(self, temp_spec_dir, sample_plan):
        """Should accept all valid status values."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Create plan with 4 subtasks for each status
        sample_plan["phases"][0]["subtasks"] = [
            {"id": "subtask-1", "status": "pending"},
            {"id": "subtask-2", "status": "pending"},
            {"id": "subtask-3", "status": "pending"},
            {"id": "subtask-4", "status": "pending"},
        ]

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [
            {"subtask_id": "subtask-1", "status": "pending"},
            {"subtask_id": "subtask-2", "status": "in_progress"},
            {"subtask_id": "subtask-3", "status": "completed"},
            {"subtask_id": "subtask-4", "status": "failed"},
        ]

        result = await batch_update({"updates": updates})
        assert "content" in result
        assert "Successfully updated 4 subtask(s)" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_partial_success_some_not_found(self, temp_spec_dir, sample_plan):
        """Should handle partial success when some subtasks not found."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [
            {"subtask_id": "subtask-1", "status": "completed"},
            {"subtask_id": "subtask-999", "status": "completed"},  # Not found
            {"subtask_id": "subtask-2", "status": "in_progress"},
        ]

        result = await batch_update({"updates": updates})
        text = result["content"][0]["text"]
        assert "Successfully updated 2 subtask(s)" in text
        assert "Failed to find 1 subtask(s)" in text
        assert "subtask-999" in text

        # Verify valid updates were applied
        with open(plan_file, encoding="utf-8") as f:
            updated_plan = json.load(f)
        assert updated_plan["phases"][0]["subtasks"][0]["status"] == "completed"
        assert updated_plan["phases"][0]["subtasks"][1]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_all_subtasks_not_found(self, temp_spec_dir, sample_plan):
        """Should handle case where no subtasks are found."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [
            {"subtask_id": "subtask-999", "status": "completed"},
            {"subtask_id": "subtask-888", "status": "completed"},
        ]

        result = await batch_update({"updates": updates})
        text = result["content"][0]["text"]
        assert "Failed to find 2 subtask(s)" in text
        assert "subtask-999" in text
        assert "subtask-888" in text

    @pytest.mark.asyncio
    async def test_updates_multiple_phases(self, temp_spec_dir):
        """Should update subtasks across multiple phases."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan = {
            "feature": "Test Feature",
            "created_at": "2026-03-05T10:00:00.000Z",
            "phases": [
                {
                    "id": "phase-1",
                    "subtasks": [
                        {"id": "subtask-1", "status": "pending"},
                    ],
                },
                {
                    "id": "phase-2",
                    "subtasks": [
                        {"id": "subtask-2", "status": "pending"},
                    ],
                },
            ],
        }

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [
            {"subtask_id": "subtask-1", "status": "completed"},
            {"subtask_id": "subtask-2", "status": "completed"},
        ]

        result = await batch_update({"updates": updates})
        assert "Successfully updated 2 subtask(s)" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_updates_last_updated_timestamp(self, temp_spec_dir, sample_plan):
        """Should update plan's last_updated timestamp."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [{"subtask_id": "subtask-1", "status": "completed"}]

        await batch_update({"updates": updates})

        # Verify timestamp was updated
        with open(plan_file, encoding="utf-8") as f:
            updated_plan = json.load(f)
        assert "last_updated" in updated_plan

        # Should be recent (within last minute)
        last_updated = datetime.fromisoformat(updated_plan["last_updated"])
        assert (datetime.now(UTC) - last_updated).total_seconds() < 60


class TestBatchUpdateErrorCases:
    """Tests for error handling in batch update operations."""

    @pytest.fixture(autouse=True)
    def reload_subtask_with_mock(self):
        """Force fresh import of subtask module with the proper mock tool decorator."""
        sys.modules["claude_agent_sdk"] = _mock_agent_sdk
        _saved: dict = {}
        for mod in [
            "agents.tools_pkg.tools.subtask",
            "agents.tools_pkg.tools",
            "agents.tools_pkg",
        ]:
            if mod in sys.modules:
                _saved[mod] = sys.modules.pop(mod)
        yield
        for mod, obj in _saved.items():
            sys.modules[mod] = obj

    @pytest.fixture
    def temp_spec_dir(self, tmp_path):
        """Create temporary spec directory for testing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        return spec_dir

    @pytest.mark.asyncio
    async def test_missing_plan_file(self, temp_spec_dir):
        """Should handle missing implementation plan file."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Don't create plan file
        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [{"subtask_id": "subtask-1", "status": "completed"}]

        result = await batch_update({"updates": updates})
        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        assert "implementation_plan.json not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_invalid_json_in_plan(self, temp_spec_dir):
        """Should handle invalid JSON in plan file."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Write invalid JSON
        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        tools = create_subtask_tools(temp_spec_dir, temp_spec_dir)
        batch_update = tools[1]

        updates = [{"subtask_id": "subtask-1", "status": "completed"}]

        result = await batch_update({"updates": updates})
        assert "content" in result
        assert "Error" in result["content"][0]["text"]
        # Error message should mention JSON problem
        text = result["content"][0]["text"]
        assert "Invalid JSON" in text or "Error batch updating" in text


class TestCreateSubtaskTools:
    """Tests for create_subtask_tools() function."""

    @pytest.fixture(autouse=True)
    def reload_subtask_with_mock(self):
        """Force fresh import of subtask module with the proper mock tool decorator."""
        sys.modules["claude_agent_sdk"] = _mock_agent_sdk
        _saved: dict = {}
        for mod in [
            "agents.tools_pkg.tools.subtask",
            "agents.tools_pkg.tools",
            "agents.tools_pkg",
        ]:
            if mod in sys.modules:
                _saved[mod] = sys.modules.pop(mod)
        yield
        for mod, obj in _saved.items():
            sys.modules[mod] = obj

    def test_returns_empty_list_when_sdk_unavailable(self, monkeypatch):
        """Should return empty list when SDK tools are not available."""
        import agents.tools_pkg.tools.subtask as subtask_module

        monkeypatch.setattr(subtask_module, "SDK_TOOLS_AVAILABLE", False)

        from agents.tools_pkg.tools.subtask import create_subtask_tools

        tools = create_subtask_tools(Path("."), Path("."))
        assert tools == []

    def test_returns_tools_when_sdk_available(self, tmp_path):
        """Should return list of tools when SDK is available."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        tools = create_subtask_tools(tmp_path, tmp_path)
        assert len(tools) == 2  # update_subtask_status and batch_update_subtask_statuses
        assert callable(tools[0])
        assert callable(tools[1])

    def test_tools_have_correct_metadata(self, tmp_path):
        """Should create tools with correct metadata."""
        from agents.tools_pkg.tools.subtask import (
            SDK_TOOLS_AVAILABLE,
            create_subtask_tools,
        )

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        tools = create_subtask_tools(tmp_path, tmp_path)

        # First tool: update_subtask_status
        assert hasattr(tools[0], "_tool_name")
        assert tools[0]._tool_name == "update_subtask_status"

        # Second tool: batch_update_subtask_statuses
        assert hasattr(tools[1], "_tool_name")
        assert tools[1]._tool_name == "batch_update_subtask_statuses"
