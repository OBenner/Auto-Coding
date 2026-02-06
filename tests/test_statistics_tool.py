"""
Tests for Spec Statistics Tool
================================

Tests the statistics calculation tool that provides comprehensive build metrics
including time tracking, completion velocity, session counts, and QA iterations.
"""

import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Add backend to path
backend_path = Path(__file__).parent.parent / "apps" / "backend"
sys.path.insert(0, str(backend_path))

# Ensure claude_agent_sdk has a proper tool decorator (passthrough)
# This is needed when the full test suite runs and another test module
# already mocked claude_agent_sdk with a MagicMock
def _mock_tool_decorator(name, description, params):
    def decorator(func):
        func._tool_name = name
        return func
    return decorator

_mock_sdk = MagicMock()
_mock_sdk.tool = _mock_tool_decorator
sys.modules.setdefault('claude_agent_sdk', _mock_sdk)

# Patch the statistics module directly if already imported
try:
    import agents.tools_pkg.tools.statistics as _stats_mod
    _stats_mod.tool = _mock_tool_decorator
    _stats_mod.SDK_TOOLS_AVAILABLE = True
except ImportError:
    pass


class TestTimestampParsing:
    """Tests for _parse_timestamp() helper function."""

    def test_parse_iso_timestamp_with_z(self):
        """Should parse ISO timestamp with Z suffix."""
        from agents.tools_pkg.tools.statistics import _parse_timestamp

        result = _parse_timestamp("2026-01-26T10:30:00.000Z")
        assert result is not None
        assert result.year == 2026
        assert result.month == 1
        assert result.day == 26
        assert result.hour == 10
        assert result.minute == 30

    def test_parse_iso_timestamp_with_offset(self):
        """Should parse ISO timestamp with timezone offset."""
        from agents.tools_pkg.tools.statistics import _parse_timestamp

        result = _parse_timestamp("2026-01-26T10:30:00.000+00:00")
        assert result is not None
        assert result.year == 2026
        assert result.hour == 10

    def test_parse_iso_timestamp_without_timezone(self):
        """Should parse ISO timestamp without timezone info."""
        from agents.tools_pkg.tools.statistics import _parse_timestamp

        result = _parse_timestamp("2026-01-26T10:30:00.000")
        assert result is not None
        assert result.year == 2026

    def test_parse_none_timestamp(self):
        """Should return None for None input."""
        from agents.tools_pkg.tools.statistics import _parse_timestamp

        result = _parse_timestamp(None)
        assert result is None

    def test_parse_empty_string(self):
        """Should return None for empty string."""
        from agents.tools_pkg.tools.statistics import _parse_timestamp

        result = _parse_timestamp("")
        assert result is None

    def test_parse_invalid_timestamp(self):
        """Should return None for invalid timestamp format."""
        from agents.tools_pkg.tools.statistics import _parse_timestamp

        result = _parse_timestamp("not-a-timestamp")
        assert result is None


class TestDurationFormatting:
    """Tests for _format_duration() helper function."""

    def test_format_seconds(self):
        """Should format durations under 60 seconds as seconds."""
        from agents.tools_pkg.tools.statistics import _format_duration

        assert _format_duration(30) == "30s"
        assert _format_duration(59.9) == "60s"

    def test_format_minutes(self):
        """Should format durations under 1 hour as minutes."""
        from agents.tools_pkg.tools.statistics import _format_duration

        assert _format_duration(60) == "1.0m"
        assert _format_duration(90) == "1.5m"
        assert _format_duration(3599) == "60.0m"

    def test_format_hours(self):
        """Should format durations under 24 hours as hours."""
        from agents.tools_pkg.tools.statistics import _format_duration

        assert _format_duration(3600) == "1.0h"
        assert _format_duration(7200) == "2.0h"
        assert _format_duration(86399) == "24.0h"

    def test_format_days(self):
        """Should format durations over 24 hours as days."""
        from agents.tools_pkg.tools.statistics import _format_duration

        assert _format_duration(86400) == "1.0d"
        assert _format_duration(172800) == "2.0d"
        assert _format_duration(259200) == "3.0d"


class TestPhaseDurationCalculation:
    """Tests for _calculate_phase_durations() function."""

    def test_empty_phases(self):
        """Should handle empty phase list."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        result = _calculate_phase_durations([])
        assert result == {}

    def test_phase_with_no_subtasks(self):
        """Should handle phase with no subtasks."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        phases = [
            {
                "id": "phase-1",
                "name": "Setup",
                "subtasks": []
            }
        ]

        result = _calculate_phase_durations(phases)
        assert "phase-1" in result
        assert result["phase-1"]["duration_seconds"] == 0
        assert result["phase-1"]["duration_formatted"] == "0s"
        assert result["phase-1"]["status"] == "not_started"

    def test_phase_with_completed_subtasks(self):
        """Should calculate duration for phase with completed subtasks."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        start_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 1, 26, 11, 30, 0, tzinfo=timezone.utc)

        phases = [
            {
                "id": "phase-1",
                "name": "Implementation",
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "status": "completed",
                        "started_at": start_time.isoformat(),
                        "completed_at": end_time.isoformat(),
                    }
                ]
            }
        ]

        result = _calculate_phase_durations(phases)
        assert "phase-1" in result
        assert result["phase-1"]["status"] == "completed"
        assert result["phase-1"]["duration_seconds"] == 5400  # 1.5 hours
        assert result["phase-1"]["subtasks_completed"] == 1
        assert result["phase-1"]["subtasks_total"] == 1

    def test_phase_with_multiple_subtasks(self):
        """Should calculate duration across multiple subtasks."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        start_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        mid_time = datetime(2026, 1, 26, 10, 30, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 1, 26, 11, 0, 0, tzinfo=timezone.utc)

        phases = [
            {
                "id": "phase-1",
                "name": "Implementation",
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "status": "completed",
                        "started_at": start_time.isoformat(),
                        "completed_at": mid_time.isoformat(),
                    },
                    {
                        "id": "subtask-2",
                        "status": "completed",
                        "started_at": mid_time.isoformat(),
                        "completed_at": end_time.isoformat(),
                    }
                ]
            }
        ]

        result = _calculate_phase_durations(phases)
        assert "phase-1" in result
        # Duration from earliest start to latest end
        assert result["phase-1"]["duration_seconds"] == 3600  # 1 hour
        assert result["phase-1"]["subtasks_completed"] == 2

    def test_phase_in_progress(self):
        """Should handle in-progress phase status."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        start_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)

        phases = [
            {
                "id": "phase-1",
                "name": "Implementation",
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "status": "completed",
                        "started_at": start_time.isoformat(),
                        "completed_at": (start_time + timedelta(minutes=30)).isoformat(),
                    },
                    {
                        "id": "subtask-2",
                        "status": "in_progress",
                        "started_at": (start_time + timedelta(minutes=30)).isoformat(),
                    }
                ]
            }
        ]

        result = _calculate_phase_durations(phases)
        assert "phase-1" in result
        assert result["phase-1"]["status"] == "in_progress"
        assert result["phase-1"]["subtasks_completed"] == 1
        assert result["phase-1"]["subtasks_total"] == 2

    def test_phase_not_started(self):
        """Should detect not started phase."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        phases = [
            {
                "id": "phase-1",
                "name": "Future Phase",
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "status": "pending",
                    }
                ]
            }
        ]

        result = _calculate_phase_durations(phases)
        assert "phase-1" in result
        assert result["phase-1"]["status"] == "not_started"

    def test_fallback_to_updated_at(self):
        """Should use updated_at when started_at/completed_at missing."""
        from agents.tools_pkg.tools.statistics import _calculate_phase_durations

        start_time = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        end_time = datetime(2026, 1, 26, 11, 0, 0, tzinfo=timezone.utc)

        phases = [
            {
                "id": "phase-1",
                "name": "Implementation",
                "subtasks": [
                    {
                        "id": "subtask-1",
                        "status": "completed",
                        "updated_at": end_time.isoformat(),
                    }
                ]
            }
        ]

        result = _calculate_phase_durations(phases)
        assert "phase-1" in result
        assert result["phase-1"]["status"] == "completed"


class TestCompletionVelocity:
    """Tests for _calculate_completion_velocity() function."""

    def test_no_created_at_timestamp(self):
        """Should handle missing created_at timestamp."""
        from agents.tools_pkg.tools.statistics import _calculate_completion_velocity

        plan = {}
        phase_durations = {}

        result = _calculate_completion_velocity(plan, phase_durations)
        assert result["subtasks_per_hour"] == 0
        assert result["subtasks_per_day"] == 0
        assert result["average_subtask_duration"] == "N/A"

    def test_zero_elapsed_time(self):
        """Should handle zero elapsed time."""
        from agents.tools_pkg.tools.statistics import _calculate_completion_velocity

        # Use current time to simulate zero elapsed time
        now = datetime.now(timezone.utc)
        plan = {
            "created_at": now.isoformat(),
            "phases": []
        }
        phase_durations = {}

        result = _calculate_completion_velocity(plan, phase_durations)
        assert result["subtasks_per_hour"] == 0

    def test_velocity_calculation(self):
        """Should calculate velocity correctly."""
        from agents.tools_pkg.tools.statistics import _calculate_completion_velocity

        # Created 2 hours ago, completed 4 subtasks
        created_at = datetime.now(timezone.utc) - timedelta(hours=2)
        plan = {
            "created_at": created_at.isoformat(),
            "phases": [
                {
                    "subtasks": [
                        {"status": "completed"},
                        {"status": "completed"},
                        {"status": "completed"},
                        {"status": "completed"},
                        {"status": "pending"},
                    ]
                }
            ]
        }
        phase_durations = {}

        result = _calculate_completion_velocity(plan, phase_durations)
        # 4 subtasks in 2 hours = 2 per hour = 48 per day
        assert result["subtasks_per_hour"] == 2.0
        assert result["subtasks_per_day"] == 48.0
        assert "s" in result["average_subtask_duration"] or "m" in result["average_subtask_duration"]

    def test_no_completed_subtasks(self):
        """Should handle no completed subtasks."""
        from agents.tools_pkg.tools.statistics import _calculate_completion_velocity

        created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        plan = {
            "created_at": created_at.isoformat(),
            "phases": [
                {
                    "subtasks": [
                        {"status": "pending"},
                        {"status": "in_progress"},
                    ]
                }
            ]
        }
        phase_durations = {}

        result = _calculate_completion_velocity(plan, phase_durations)
        assert result["subtasks_per_hour"] == 0
        assert result["subtasks_per_day"] == 0
        assert result["average_subtask_duration"] == "N/A"


class TestSessionCounting:
    """Tests for _count_unique_sessions() function."""

    def test_no_sessions(self):
        """Should return 0 for plan with no sessions."""
        from agents.tools_pkg.tools.statistics import _count_unique_sessions

        plan = {"phases": []}
        result = _count_unique_sessions(plan)
        assert result == 0

    def test_single_session(self):
        """Should count single unique session."""
        from agents.tools_pkg.tools.statistics import _count_unique_sessions

        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"session_id": "session-1"},
                        {"session_id": "session-1"},
                    ]
                }
            ]
        }
        result = _count_unique_sessions(plan)
        assert result == 1

    def test_multiple_sessions(self):
        """Should count multiple unique sessions."""
        from agents.tools_pkg.tools.statistics import _count_unique_sessions

        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"session_id": "session-1"},
                        {"session_id": "session-2"},
                        {"session_id": "session-1"},  # Duplicate
                    ]
                },
                {
                    "subtasks": [
                        {"session_id": "session-3"},
                    ]
                }
            ]
        }
        result = _count_unique_sessions(plan)
        assert result == 3

    def test_missing_session_ids(self):
        """Should handle subtasks without session_id."""
        from agents.tools_pkg.tools.statistics import _count_unique_sessions

        plan = {
            "phases": [
                {
                    "subtasks": [
                        {"session_id": "session-1"},
                        {},  # No session_id
                        {"session_id": None},  # Explicit None
                    ]
                }
            ]
        }
        result = _count_unique_sessions(plan)
        assert result == 1


class TestCreateStatisticsTools:
    """Tests for create_statistics_tools() function."""

    def test_returns_empty_list_when_sdk_unavailable(self, monkeypatch):
        """Should return empty list when SDK tools are not available."""
        import agents.tools_pkg.tools.statistics as stats_module

        monkeypatch.setattr(stats_module, "SDK_TOOLS_AVAILABLE", False)

        from agents.tools_pkg.tools.statistics import create_statistics_tools

        tools = create_statistics_tools(Path("."), Path("."))
        assert tools == []

    def test_returns_tools_when_sdk_available(self, tmp_path):
        """Should return list of tools when SDK is available."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        tools = create_statistics_tools(tmp_path, tmp_path)
        assert len(tools) == 1
        assert callable(tools[0])


class TestGetSpecStatistics:
    """Tests for the get_spec_statistics tool function."""

    @pytest.fixture
    def temp_spec_dir(self, tmp_path):
        """Create temporary spec directory for testing."""
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()
        return spec_dir

    @pytest.fixture
    def sample_plan(self):
        """Create sample implementation plan."""
        created_at = datetime(2026, 1, 26, 10, 0, 0, tzinfo=timezone.utc)
        return {
            "feature": "Test Feature",
            "created_at": created_at.isoformat(),
            "last_updated": (created_at + timedelta(hours=2)).isoformat(),
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Implementation",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "status": "completed",
                            "started_at": created_at.isoformat(),
                            "completed_at": (created_at + timedelta(hours=1)).isoformat(),
                            "session_id": "session-1"
                        },
                        {
                            "id": "subtask-2",
                            "status": "in_progress",
                            "started_at": (created_at + timedelta(hours=1)).isoformat(),
                            "session_id": "session-1"
                        }
                    ]
                }
            ],
            "qa_signoff": {
                "status": "pending",
                "qa_session": 0
            }
        }

    @pytest.mark.asyncio
    async def test_no_plan_file(self, temp_spec_dir):
        """Should handle missing implementation plan file."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        tools = create_statistics_tools(temp_spec_dir, temp_spec_dir)
        get_stats = tools[0]

        result = await get_stats({})
        assert "content" in result
        assert "No implementation plan found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_calculates_statistics(self, temp_spec_dir, sample_plan):
        """Should calculate comprehensive statistics from plan."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Write plan file
        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_statistics_tools(temp_spec_dir, temp_spec_dir)
        get_stats = tools[0]

        result = await get_stats({})
        assert "content" in result
        text = result["content"][0]["text"]

        # Verify key sections are present
        assert "Spec Statistics" in text
        assert "Time Tracking:" in text
        assert "Total Build Time:" in text
        assert "Subtask Progress:" in text
        assert "Completion Velocity:" in text
        assert "QA Metrics:" in text
        assert "Phase Durations:" in text

    @pytest.mark.asyncio
    async def test_handles_invalid_json(self, temp_spec_dir):
        """Should handle invalid JSON in plan file."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        # Write invalid JSON
        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            f.write("{ invalid json }")

        tools = create_statistics_tools(temp_spec_dir, temp_spec_dir)
        get_stats = tools[0]

        result = await get_stats({})
        assert "content" in result
        assert "Error calculating statistics" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_includes_qa_iterations(self, temp_spec_dir, sample_plan):
        """Should include QA iteration count in output."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        sample_plan["qa_signoff"]["qa_session"] = 3
        sample_plan["qa_signoff"]["status"] = "approved"

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_statistics_tools(temp_spec_dir, temp_spec_dir)
        get_stats = tools[0]

        result = await get_stats({})
        text = result["content"][0]["text"]

        assert "QA Iterations: 3" in text
        assert "QA Status: approved" in text

    @pytest.mark.asyncio
    async def test_includes_session_count(self, temp_spec_dir, sample_plan):
        """Should include unique session count in output."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_statistics_tools(temp_spec_dir, temp_spec_dir)
        get_stats = tools[0]

        result = await get_stats({})
        text = result["content"][0]["text"]

        assert "Session Count: 1" in text

    @pytest.mark.asyncio
    async def test_includes_completion_rate(self, temp_spec_dir, sample_plan):
        """Should calculate and include completion rate."""
        from agents.tools_pkg.tools.statistics import create_statistics_tools, SDK_TOOLS_AVAILABLE

        if not SDK_TOOLS_AVAILABLE:
            pytest.skip("SDK not available")

        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file, "w", encoding="utf-8") as f:
            json.dump(sample_plan, f)

        tools = create_statistics_tools(temp_spec_dir, temp_spec_dir)
        get_stats = tools[0]

        result = await get_stats({})
        text = result["content"][0]["text"]

        # 1 completed out of 2 total = 50%
        assert "50.0% (1/2)" in text
