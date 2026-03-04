#!/usr/bin/env python3
"""
Tests for Migration Assistant Agent
====================================

Tests the migration_assistant.py module functionality including:
- Migration checkpoint validation
- Migration assistant session execution
- Checkpoint creation and verification
- Error handling and logging
"""

import platform
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents.migration_assistant import (
    run_migration_assistant,
    validate_migration_checkpoint,
)


class TestMigrationCheckpointValidation:
    """Tests for validate_migration_checkpoint() function."""

    def test_validation_fails_when_checkpoint_dir_missing(self, tmp_path):
        """Verify validation fails when checkpoint directory doesn't exist."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        project_dir = tmp_path

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is False
        assert "Checkpoint directory does not exist" in result["issues"]
        assert result["checkpoint_info"] == {}

    def test_validation_fails_when_no_commit_file(self, tmp_path):
        """Verify validation fails when no checkpoint commit file exists."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        checkpoint_dir.mkdir(parents=True)
        project_dir = tmp_path

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is False
        assert "No checkpoint metadata found" in result["issues"]

    def test_validation_fails_when_no_rollback_dir(self, tmp_path):
        """Verify validation fails when rollback directory is missing."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        checkpoint_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create checkpoint commit file
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123def456")

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is False
        assert "Rollback directory does not exist" in result["issues"]

    def test_validation_fails_when_no_rollback_scripts(self, tmp_path):
        """Verify validation fails when no rollback scripts exist."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create checkpoint commit file
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123def456")

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is False
        assert "No rollback scripts found" in result["issues"]

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix executable permissions not supported on Windows",
    )
    def test_validation_fails_when_script_not_executable(self, tmp_path):
        """Verify validation fails when rollback scripts are not executable (Unix only)."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create checkpoint commit file
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123def456")

        # Create rollback script without executable permissions
        script_file = rollback_dir / "checkpoint-001.sh"
        script_file.write_text("#!/bin/bash\necho 'rollback'")

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is False
        assert any("not executable" in issue for issue in result["issues"])

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix executable permissions not supported on Windows",
    )
    def test_validation_succeeds_with_valid_checkpoint(self, tmp_path):
        """Verify validation succeeds when checkpoint is properly structured (Unix only)."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create checkpoint commit file
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123def456")

        # Create executable rollback script
        script_file = rollback_dir / "checkpoint-001.sh"
        script_file.write_text("#!/bin/bash\necho 'rollback'")
        script_file.chmod(0o755)  # Make executable

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is True
        assert len(result["issues"]) == 0
        assert result["checkpoint_info"]["commit"] == "abc123def456"
        assert result["checkpoint_info"]["rollback_scripts"] == 1

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix executable permissions not supported on Windows",
    )
    def test_validation_reads_latest_checkpoint(self, tmp_path):
        """Verify validation reads the latest checkpoint when multiple exist (Unix only)."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create multiple checkpoint commit files
        (checkpoint_dir / "checkpoint-001-commit.txt").write_text("commit1")
        (checkpoint_dir / "checkpoint-002-commit.txt").write_text("commit2")
        (checkpoint_dir / "checkpoint-003-commit.txt").write_text("commit3")

        # Create rollback scripts
        for i in range(1, 4):
            script = rollback_dir / f"checkpoint-{i:03d}.sh"
            script.write_text("#!/bin/bash\necho 'rollback'")
            script.chmod(0o755)

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is True
        assert result["checkpoint_info"]["commit"] == "commit3"
        assert (
            result["checkpoint_info"]["checkpoint_file"] == "checkpoint-003-commit.txt"
        )
        assert result["checkpoint_info"]["rollback_scripts"] == 3

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix executable permissions not supported on Windows",
    )
    def test_validation_includes_migration_plan_when_exists(self, tmp_path):
        """Verify validation includes migration plan info when file exists (Unix only)."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create valid checkpoint structure
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123def456")

        script_file = rollback_dir / "checkpoint-001.sh"
        script_file.write_text("#!/bin/bash\necho 'rollback'")
        script_file.chmod(0o755)

        # Create migration plan
        migration_plan = project_dir / "migration_plan.md"
        migration_plan.write_text("# Migration Plan\n\nPhase 1: Analysis")

        result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is True
        assert result["checkpoint_info"]["migration_plan"] is True

    def test_validation_handles_commit_file_read_error(self, tmp_path):
        """Verify validation handles errors when reading commit file."""
        checkpoint_dir = tmp_path / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)
        project_dir = tmp_path

        # Create checkpoint commit file
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123def456")

        # Create rollback script
        script_file = rollback_dir / "checkpoint-001.sh"
        script_file.write_text("#!/bin/bash\necho 'rollback'")
        if platform.system() != "Windows":
            script_file.chmod(0o755)

        # Mock file open to raise an exception
        with patch("builtins.open", side_effect=PermissionError("Access denied")):
            result = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert result["valid"] is False
        assert any(
            "Failed to read checkpoint commit file" in issue
            for issue in result["issues"]
        )


class TestMigrationAssistantSession:
    """Tests for run_migration_assistant() async function."""

    @pytest.mark.asyncio
    async def test_run_fails_when_prompt_load_fails(self, tmp_path):
        """Verify run_migration_assistant fails gracefully when prompt can't be loaded."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                side_effect=FileNotFoundError("Prompt not found"),
            ):
                with patch(
                    "agents.migration_assistant.get_phase_model",
                    return_value="claude-sonnet-4",
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_thinking_budget",
                        return_value=10000,
                    ):
                        result = await run_migration_assistant(project_dir, spec_dir)

        assert result["success"] is False
        assert "Failed to load migration_assistant prompt" in result["error"]
        assert result["checkpoints_created"] == 0

    @pytest.mark.asyncio
    async def test_run_fails_when_client_creation_fails(self, tmp_path):
        """Verify run_migration_assistant fails when SDK client creation fails."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.get_phase_model",
                    return_value="claude-sonnet-4",
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_thinking_budget",
                        return_value=10000,
                    ):
                        with patch(
                            "agents.migration_assistant.create_client",
                            side_effect=RuntimeError("SDK error"),
                        ):
                            result = await run_migration_assistant(
                                project_dir, spec_dir
                            )

        assert result["success"] is False
        assert "Failed to create Claude SDK client" in result["error"]
        assert result["checkpoints_created"] == 0

    @pytest.mark.asyncio
    async def test_run_succeeds_with_minimal_setup(self, tmp_path):
        """Verify run_migration_assistant succeeds with minimal valid setup."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        # Mock dependencies
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            return_value={"response": "success"}
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_model",
                        return_value="claude-sonnet-4",
                    ):
                        with patch(
                            "agents.migration_assistant.get_phase_thinking_budget",
                            return_value=10000,
                        ):
                            result = await run_migration_assistant(
                                project_dir, spec_dir
                            )

        assert result["success"] is True
        assert result["checkpoints_created"] == 0  # No checkpoints created yet

    @pytest.mark.asyncio
    async def test_run_includes_migration_context_in_message(self, tmp_path):
        """Verify migration context is included in starting message when provided."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        migration_context = {
            "from_framework": "React 17",
            "to_framework": "React 18",
            "migration_type": "framework_upgrade",
        }

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            return_value={"response": "success"}
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_model",
                        return_value="claude-sonnet-4",
                    ):
                        with patch(
                            "agents.migration_assistant.get_phase_thinking_budget",
                            return_value=10000,
                        ):
                            await run_migration_assistant(
                                project_dir,
                                spec_dir,
                                migration_context=migration_context,
                            )

        # Verify create_agent_session was called with migration context
        call_args = mock_client.create_agent_session.call_args
        starting_message = call_args.kwargs["starting_message"]
        assert "Migration Context" in starting_message
        assert "React 17" in starting_message
        assert "React 18" in starting_message

    @pytest.mark.asyncio
    async def test_run_counts_checkpoints_correctly(self, tmp_path):
        """Verify run_migration_assistant correctly counts created checkpoints."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        # Create checkpoint directory with multiple checkpoints
        checkpoint_dir = project_dir / ".migration-checkpoints"
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)

        # Create 3 checkpoint files
        for i in range(1, 4):
            commit_file = checkpoint_dir / f"checkpoint-{i:03d}-commit.txt"
            commit_file.write_text(f"commit{i}")
            script_file = rollback_dir / f"checkpoint-{i:03d}.sh"
            script_file.write_text("#!/bin/bash\necho 'rollback'")
            if platform.system() != "Windows":
                script_file.chmod(0o755)

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            return_value={"response": "success"}
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_model",
                        return_value="claude-sonnet-4",
                    ):
                        with patch(
                            "agents.migration_assistant.get_phase_thinking_budget",
                            return_value=10000,
                        ):
                            result = await run_migration_assistant(
                                project_dir, spec_dir
                            )

        assert result["success"] is True
        assert result["checkpoints_created"] == 3

    @pytest.mark.asyncio
    async def test_run_returns_migration_plan_path_when_exists(self, tmp_path):
        """Verify run_migration_assistant returns migration plan path when created."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        # Create migration plan
        migration_plan = project_dir / "migration_plan.md"
        migration_plan.write_text("# Migration Plan\n\nPhase 1: Analysis")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            return_value={"response": "success"}
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_model",
                        return_value="claude-sonnet-4",
                    ):
                        with patch(
                            "agents.migration_assistant.get_phase_thinking_budget",
                            return_value=10000,
                        ):
                            result = await run_migration_assistant(
                                project_dir, spec_dir
                            )

        assert result["success"] is True
        assert result["migration_plan_path"] == "migration_plan.md"

    @pytest.mark.asyncio
    async def test_run_handles_session_exception(self, tmp_path):
        """Verify run_migration_assistant handles exceptions during session execution."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            side_effect=RuntimeError("Session failed")
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_model",
                        return_value="claude-sonnet-4",
                    ):
                        with patch(
                            "agents.migration_assistant.get_phase_thinking_budget",
                            return_value=10000,
                        ):
                            result = await run_migration_assistant(
                                project_dir, spec_dir
                            )

        assert result["success"] is False
        assert "Migration session failed" in result["error"]
        assert result["checkpoints_created"] == 0

    @pytest.mark.asyncio
    async def test_run_uses_custom_model_and_thinking_tokens(self, tmp_path):
        """Verify run_migration_assistant uses custom model and thinking tokens when provided."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            return_value={"response": "success"}
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ) as mock_create:
                    await run_migration_assistant(
                        project_dir,
                        spec_dir,
                        model="claude-opus-4",
                        max_thinking_tokens=16000,
                    )

        # Verify create_client was called with custom parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args.kwargs
        assert call_kwargs["model"] == "claude-opus-4"
        assert call_kwargs["max_thinking_tokens"] == 16000
        assert call_kwargs["agent_type"] == "migration_assistant"

    @pytest.mark.asyncio
    async def test_run_logs_checkpoint_validation_warnings(self, tmp_path):
        """Verify run_migration_assistant logs warnings for invalid checkpoints."""
        project_dir = tmp_path / "project"
        spec_dir = tmp_path / "spec"
        project_dir.mkdir()
        spec_dir.mkdir()

        # Create incomplete checkpoint (missing rollback dir)
        checkpoint_dir = project_dir / ".migration-checkpoints"
        checkpoint_dir.mkdir()
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123")

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_agent_session = AsyncMock(
            return_value={"response": "success"}
        )

        with patch("agents.migration_assistant.get_task_logger", return_value=None):
            with patch(
                "agents.migration_assistant.get_agent_prompt",
                return_value="Test prompt",
            ):
                with patch(
                    "agents.migration_assistant.create_client", return_value=mock_client
                ):
                    with patch(
                        "agents.migration_assistant.get_phase_model",
                        return_value="claude-sonnet-4",
                    ):
                        with patch(
                            "agents.migration_assistant.get_phase_thinking_budget",
                            return_value=10000,
                        ):
                            with patch(
                                "agents.migration_assistant.logger"
                            ) as mock_logger:
                                result = await run_migration_assistant(
                                    project_dir, spec_dir
                                )

        # Verify warning was logged for checkpoint validation issues
        assert result["success"] is True
        assert mock_logger.warning.called
        warning_message = str(mock_logger.warning.call_args[0][0])
        assert "Checkpoint validation issues" in warning_message
