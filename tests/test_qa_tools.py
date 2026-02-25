#!/usr/bin/env python3
"""
Tests for QA Tools
==================

Tests the qa.py tools module functionality including:
- get_qa_status tool for reading QA signoff data
- update_qa_status tool for updating QA signoff data
"""

import json
import pytest
import sys
from pathlib import Path
from unittest.mock import MagicMock

# Store original modules for cleanup
_original_modules = {}
_mocked_module_names = [
    'claude_agent_sdk',
]

for name in _mocked_module_names:
    if name in sys.modules:
        _original_modules[name] = sys.modules[name]

# Mock claude_agent_sdk before importing qa tools
# The SDK isn't available in the test environment
mock_agent_sdk = MagicMock()

# Create a mock tool decorator that just returns the function
def mock_tool_decorator(name, description, params):
    def decorator(func):
        func._tool_name = name
        func._tool_description = description
        func._tool_params = params
        return func
    return decorator

mock_agent_sdk.tool = mock_tool_decorator
sys.modules['claude_agent_sdk'] = mock_agent_sdk

# Force fresh import so the module picks up our mock_tool_decorator
for _mod in ['agents.tools_pkg.tools.qa', 'agents.tools_pkg.tools', 'agents.tools_pkg']:
    sys.modules.pop(_mod, None)

from agents.tools_pkg.tools.qa import create_qa_tools


# Cleanup fixture to restore original modules after all tests in this module
@pytest.fixture(scope="module", autouse=True)
def cleanup_mocked_modules():
    """Restore original modules after all tests in this module complete."""
    yield  # Run all tests first
    # Cleanup: restore original modules or remove mocks
    for name in _mocked_module_names:
        if name in _original_modules:
            sys.modules[name] = _original_modules[name]
        elif name in sys.modules:
            del sys.modules[name]


class TestCreateQATools:
    """Tests for create_qa_tools function."""

    def test_creates_two_tools(self, spec_dir: Path, project_dir: Path):
        """create_qa_tools returns both update_qa_status and get_qa_status tools."""
        tools = create_qa_tools(spec_dir, project_dir)

        assert len(tools) == 2
        assert tools[0]._tool_name == "update_qa_status"
        assert tools[1]._tool_name == "get_qa_status"


class TestGetQAStatus:
    """Tests for get_qa_status tool."""

    async def test_get_qa_status_complete_data(self, spec_dir: Path, project_dir: Path):
        """get_qa_status returns formatted QA data when all fields present."""
        # Create plan with complete QA signoff
        plan = {
            "feature": "Test Feature",
            "qa_signoff": {
                "status": "approved",
                "qa_session": 2,
                "timestamp": "2024-01-15T10:30:00",
                "ready_for_qa_revalidation": False,
                "issues_found": [],
                "tests_passed": {
                    "unit": True,
                    "integration": True,
                    "e2e": True,
                },
            },
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        assert "content" in result
        assert len(result["content"]) == 1
        text = result["content"][0]["text"]

        assert "QA Status: approved" in text
        assert "QA Session: 2" in text
        assert "Timestamp: 2024-01-15T10:30:00" in text
        assert "Ready for QA Revalidation: False" in text
        assert "Issues Found: None" in text
        assert "Tests Passed:" in text
        assert "✓ unit" in text
        assert "✓ integration" in text
        assert "✓ e2e" in text

    async def test_get_qa_status_with_issues(self, spec_dir: Path, project_dir: Path):
        """get_qa_status displays issues when present."""
        # Create plan with issues
        plan = {
            "feature": "Test Feature",
            "qa_signoff": {
                "status": "rejected",
                "qa_session": 1,
                "timestamp": "2024-01-15T10:30:00",
                "ready_for_qa_revalidation": False,
                "issues_found": [
                    {"description": "Missing unit tests"},
                    {"description": "API validation error"},
                    {"description": "UI not responsive"},
                ],
                "tests_passed": {
                    "unit": False,
                    "integration": True,
                },
            },
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]

        assert "QA Status: rejected" in text
        assert "Issues Found: 3" in text
        assert "1. Missing unit tests" in text
        assert "2. API validation error" in text
        assert "3. UI not responsive" in text
        assert "✗ unit" in text
        assert "✓ integration" in text

    async def test_get_qa_status_missing_qa_signoff(self, spec_dir: Path, project_dir: Path):
        """get_qa_status returns pending message when qa_signoff missing."""
        # Create plan without QA signoff
        plan = {
            "feature": "Test Feature",
            "phases": [],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]
        assert "QA has not been run yet" in text
        assert "Status: pending" in text

    async def test_get_qa_status_empty_qa_signoff(self, spec_dir: Path, project_dir: Path):
        """get_qa_status handles empty qa_signoff object."""
        # Create plan with empty QA signoff
        plan = {
            "feature": "Test Feature",
            "qa_signoff": {},
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]
        assert "QA has not been run yet" in text
        assert "Status: pending" in text

    async def test_get_qa_status_missing_plan_file(self, spec_dir: Path, project_dir: Path):
        """get_qa_status returns error when implementation_plan.json missing."""
        # Don't create plan file

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]
        assert "No implementation plan found" in text
        assert "Run the planner first" in text

    async def test_get_qa_status_different_statuses(self, spec_dir: Path, project_dir: Path):
        """get_qa_status handles different QA status values."""
        statuses = ["pending", "in_review", "approved", "rejected", "fixes_applied"]

        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        for status in statuses:
            # Create plan with this status
            plan = {
                "feature": "Test Feature",
                "qa_signoff": {
                    "status": status,
                    "qa_session": 1,
                    "timestamp": "2024-01-15T10:30:00",
                    "ready_for_qa_revalidation": status == "fixes_applied",
                    "issues_found": [],
                    "tests_passed": {},
                },
            }
            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(json.dumps(plan, indent=2))

            # Call the tool
            result = await get_qa_status({})

            # Check result
            text = result["content"][0]["text"]
            assert f"QA Status: {status}" in text

    async def test_get_qa_status_ready_for_revalidation(self, spec_dir: Path, project_dir: Path):
        """get_qa_status shows ready_for_qa_revalidation flag."""
        # Create plan with fixes_applied status
        plan = {
            "feature": "Test Feature",
            "qa_signoff": {
                "status": "fixes_applied",
                "qa_session": 1,
                "timestamp": "2024-01-15T10:30:00",
                "ready_for_qa_revalidation": True,
                "issues_found": [],
                "tests_passed": {},
            },
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]
        assert "Ready for QA Revalidation: True" in text

    async def test_get_qa_status_invalid_json(self, spec_dir: Path, project_dir: Path):
        """get_qa_status handles corrupted plan file gracefully."""
        # Create invalid JSON file
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text("{ invalid json }")

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]
        assert "Error reading QA status" in text

    async def test_get_qa_status_issue_as_string(self, spec_dir: Path, project_dir: Path):
        """get_qa_status handles issues as plain strings."""
        # Create plan with string issues (legacy format)
        plan = {
            "feature": "Test Feature",
            "qa_signoff": {
                "status": "rejected",
                "qa_session": 1,
                "timestamp": "2024-01-15T10:30:00",
                "ready_for_qa_revalidation": False,
                "issues_found": [
                    "Plain string issue",
                    {"description": "Dict issue"},
                ],
                "tests_passed": {},
            },
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        get_qa_status = tools[1]

        # Call the tool
        result = await get_qa_status({})

        # Check result
        text = result["content"][0]["text"]
        assert "Issues Found: 2" in text
        assert "1. Plain string issue" in text
        assert "2. Dict issue" in text


class TestUpdateQAStatus:
    """Tests for update_qa_status tool."""

    async def test_update_qa_status_creates_signoff(self, spec_dir: Path, project_dir: Path):
        """update_qa_status creates qa_signoff when it doesn't exist."""
        # Create plan without QA signoff
        plan = {
            "feature": "Test Feature",
            "phases": [],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        update_qa_status = tools[0]

        # Call the tool
        result = await update_qa_status({
            "status": "approved",
            "issues": "[]",
            "tests_passed": '{"unit": true, "integration": true}',
        })

        # Check result
        text = result["content"][0]["text"]
        assert "Updated QA status to 'approved'" in text

        # Verify plan was updated
        updated_plan = json.loads(plan_file.read_text())
        assert "qa_signoff" in updated_plan
        assert updated_plan["qa_signoff"]["status"] == "approved"

    async def test_update_qa_status_invalid_status(self, spec_dir: Path, project_dir: Path):
        """update_qa_status rejects invalid status values."""
        # Create plan
        plan = {
            "feature": "Test Feature",
            "phases": [],
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        update_qa_status = tools[0]

        # Call the tool with invalid status
        result = await update_qa_status({
            "status": "invalid_status",
            "issues": "[]",
            "tests_passed": "{}",
        })

        # Check result
        text = result["content"][0]["text"]
        assert "Error: Invalid QA status" in text

    async def test_update_qa_status_missing_plan(self, spec_dir: Path, project_dir: Path):
        """update_qa_status returns error when plan file missing."""
        # Don't create plan file

        # Get tools
        tools = create_qa_tools(spec_dir, project_dir)
        update_qa_status = tools[0]

        # Call the tool
        result = await update_qa_status({
            "status": "approved",
            "issues": "[]",
            "tests_passed": "{}",
        })

        # Check result
        text = result["content"][0]["text"]
        assert "Error: implementation_plan.json not found" in text
