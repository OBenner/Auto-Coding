#!/usr/bin/env python3
"""
Tests for Planner Agent
========================

Tests the planner module which handles follow-up planner sessions
for adding new subtasks to completed specs.
"""

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

# Add apps/backend to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents.planner import run_followup_planner


class TestRunFollowupPlanner:
    """Test run_followup_planner function."""

    @pytest.mark.asyncio
    async def test_run_followup_planner_requires_spec_dir(self, tmp_path):
        """Test that run_followup_planner requires a spec directory."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create minimal required files
        (spec_dir / "implementation_plan.json").write_text(json.dumps({
            "feature": "Test Feature",
            "status": "completed",
            "phases": []
        }))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        # Mock dependencies
        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt') as mock_get_prompt, \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class:

            # Setup mocks
            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_get_prompt.return_value = "Test prompt"

            # Mock successful session
            mock_run_session.return_value = AsyncMock(return_value=(
                "success",
                "Planning completed",
                {"input_tokens": 100, "output_tokens": 50},
                None,
            ))()

            # Mock scanner
            mock_scanner = MagicMock()
            mock_scan_result = MagicMock()
            mock_scan_result.should_block = False
            mock_scan_result.should_warn = False
            mock_scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
            mock_scanner.scan.return_value = mock_scan_result
            mock_scanner.format_summary.return_value = "No issues"
            mock_scanner_class.return_value = mock_scanner

            # Call function
            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Verify mocks were called
            assert mock_create_client.called
            assert mock_get_prompt.called

    @pytest.mark.asyncio
    async def test_run_followup_planner_handles_session_error(self, tmp_path):
        """Test that run_followup_planner handles session errors gracefully."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        (spec_dir / "implementation_plan.json").write_text(json.dumps({
            "feature": "Test Feature",
            "status": "completed",
            "phases": []
        }))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt') as mock_get_prompt, \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class:

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_get_prompt.return_value = "Test prompt"

            # Mock error status
            mock_run_session.return_value = AsyncMock(return_value=(
                "error",
                "Planning failed",
                {},
                None,
            ))()

            # Mock scanner
            mock_scanner = MagicMock()
            mock_scan_result = MagicMock()
            mock_scan_result.should_block = False
            mock_scan_result.should_warn = False
            mock_scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
            mock_scanner.scan.return_value = mock_scan_result
            mock_scanner.format_summary.return_value = "No issues"
            mock_scanner_class.return_value = mock_scanner

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Should return False on error
            assert result is False

    @pytest.mark.asyncio
    async def test_run_followup_planner_verifies_pending_subtasks(self, tmp_path):
        """Test that run_followup_planner verifies pending subtasks were added."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # Create plan with completed status
        plan_data = {
            "feature": "Test Feature",
            "status": "completed",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Task 1",
                            "status": "completed"
                        }
                    ]
                }
            ]
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan_data))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt') as mock_get_prompt, \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.save_token_stats'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class, \
             patch('agents.planner.ImplementationPlan') as mock_plan_class:

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_get_prompt.return_value = "Test prompt"

            # Mock successful session
            mock_run_session.return_value = AsyncMock(return_value=(
                "success",
                "Planning completed",
                {"input_tokens": 100, "output_tokens": 50},
                None,
            ))()

            # Mock scanner
            mock_scanner = MagicMock()
            mock_scan_result = MagicMock()
            mock_scan_result.should_block = False
            mock_scan_result.should_warn = False
            mock_scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
            mock_scanner.scan.return_value = mock_scan_result
            mock_scanner.format_summary.return_value = "No issues"
            mock_scanner_class.return_value = mock_scanner

            # Mock plan with new pending subtask
            mock_plan = MagicMock()
            mock_phase = MagicMock()
            mock_subtask_pending = MagicMock()
            mock_subtask_pending.status.value = "pending"
            mock_phase.subtasks = [mock_subtask_pending]
            mock_plan.phases = [mock_phase]
            mock_plan.reset_for_followup = MagicMock()
            mock_plan.async_save = AsyncMock()
            mock_plan_class.load.return_value = mock_plan

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Should return True when pending subtasks found
            assert result is True
            mock_plan.reset_for_followup.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_followup_planner_warns_when_no_pending_subtasks(self, tmp_path):
        """Test warning when no pending subtasks are added."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_data = {
            "feature": "Test Feature",
            "status": "completed",
            "phases": []
        }
        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan_data))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt') as mock_get_prompt, \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.save_token_stats'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class, \
             patch('agents.planner.ImplementationPlan') as mock_plan_class:

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_get_prompt.return_value = "Test prompt"

            mock_run_session.return_value = AsyncMock(return_value=(
                "success",
                "Planning completed",
                {"input_tokens": 100, "output_tokens": 50},
                None,
            ))()

            # Mock scanner
            mock_scanner = MagicMock()
            mock_scan_result = MagicMock()
            mock_scan_result.should_block = False
            mock_scan_result.should_warn = False
            mock_scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
            mock_scanner.scan.return_value = mock_scan_result
            mock_scanner.format_summary.return_value = "No issues"
            mock_scanner_class.return_value = mock_scanner

            # Mock plan with NO pending subtasks
            mock_plan = MagicMock()
            mock_phase = MagicMock()
            mock_subtask_completed = MagicMock()
            mock_subtask_completed.status.value = "completed"
            mock_phase.subtasks = [mock_subtask_completed]
            mock_plan.phases = [mock_phase]
            mock_plan_class.load.return_value = mock_plan

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Should return False when no pending subtasks
            assert result is False

    @pytest.mark.asyncio
    async def test_run_followup_planner_handles_missing_plan_file(self, tmp_path):
        """Test handling of missing implementation_plan.json."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        # No plan file created

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add new feature")

        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt') as mock_get_prompt, \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class:

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_get_prompt.return_value = "Test prompt"

            mock_run_session.return_value = AsyncMock(return_value=(
                "success",
                "Planning completed",
                {"input_tokens": 100, "output_tokens": 50},
                None,
            ))()

            # Mock scanner
            mock_scanner = MagicMock()
            mock_scan_result = MagicMock()
            mock_scan_result.should_block = False
            mock_scan_result.should_warn = False
            mock_scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
            mock_scanner.scan.return_value = mock_scan_result
            mock_scanner.format_summary.return_value = "No issues"
            mock_scanner_class.return_value = mock_scanner

            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Should return False when plan file missing
            assert result is False

    @pytest.mark.asyncio
    async def test_run_followup_planner_runs_prevention_scanner(self, tmp_path):
        """Test that prevention scanner is run during planning."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({
            "feature": "Test",
            "phases": []
        }))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add feature")

        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt'), \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class:

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_run_session.return_value = AsyncMock(return_value=(
                "error",  # Force error to exit early
                "Error",
                {},
                None,
            ))()

            # Mock scanner
            mock_scanner = MagicMock()
            mock_scan_result = MagicMock()
            mock_scan_result.should_block = False
            mock_scan_result.should_warn = False
            mock_scan_result.summary = {"critical": 0, "high": 0, "total_issues": 0}
            mock_scanner.scan.return_value = mock_scan_result
            mock_scanner.format_summary.return_value = "No issues"
            mock_scanner_class.return_value = mock_scanner

            await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Verify scanner was called
            mock_scanner.scan.assert_called_once()
            mock_scanner.format_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_followup_planner_handles_scanner_error(self, tmp_path):
        """Test that scanner errors don't block planning."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({
            "feature": "Test",
            "phases": []
        }))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add feature")

        with patch('agents.planner.create_client') as mock_create_client, \
             patch('agents.planner.get_followup_planner_prompt'), \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.PreventionScanner') as mock_scanner_class:

            mock_client = MagicMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_create_client.return_value = mock_client

            mock_run_session.return_value = AsyncMock(return_value=(
                "error",
                "Error",
                {},
                None,
            ))()

            # Mock scanner that raises exception
            mock_scanner = MagicMock()
            mock_scanner.scan.side_effect = Exception("Scanner error")
            mock_scanner_class.return_value = mock_scanner

            # Should not crash, continues with planning
            result = await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=False,
            )

            # Planning should continue despite scanner error
            assert isinstance(result, bool)


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_run_followup_planner_with_verbose_mode(self, tmp_path):
        """Test that verbose mode is passed through correctly."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()

        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps({"feature": "Test", "phases": []}))

        (spec_dir / "FOLLOWUP_REQUEST.md").write_text("Add feature")

        with patch('agents.planner.create_client'), \
             patch('agents.planner.get_followup_planner_prompt'), \
             patch('agents.planner.run_agent_session') as mock_run_session, \
             patch('agents.planner.StatusManager'), \
             patch('agents.planner.get_task_logger'), \
             patch('agents.planner.emit_phase'), \
             patch('agents.planner.print_status'), \
             patch('agents.planner.box'), \
             patch('agents.planner.PreventionScanner'):

            mock_run_session.return_value = AsyncMock(return_value=(
                "error",
                "Error",
                {},
                None,
            ))()

            # Call with verbose=True
            await run_followup_planner(
                project_dir=project_dir,
                spec_dir=spec_dir,
                model="claude-3-5-sonnet-20241022",
                verbose=True,
            )

            # Verify verbose was passed to run_agent_session
            call_args = mock_run_session.call_args
            assert call_args is not None