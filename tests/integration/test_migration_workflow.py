#!/usr/bin/env python3
"""
Integration Tests for Migration Workflow
=========================================

Tests the complete migration assistant workflow including:
- Migration planner and checkpoint manager integration
- End-to-end migration workflow with checkpoints
- CLI command integration
- Rollback and recovery scenarios
"""

import json
import platform
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add backend directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "apps" / "backend"))

from migrations.checkpoints import CheckpointManager, CheckpointStatus
from migrations.planner import MigrationPlanner, MigrationType

# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def migration_env(tmp_path):
    """Create a test environment for migration testing."""
    project_dir = tmp_path / "project"
    spec_dir = tmp_path / "spec"

    project_dir.mkdir(parents=True)
    spec_dir.mkdir(parents=True)

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_dir,
        capture_output=True,
    )

    # Create initial commit
    readme = project_dir / "README.md"
    readme.write_text("# Test Project")
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"], cwd=project_dir, capture_output=True
    )

    # Create spec files
    spec_file = spec_dir / "spec.md"
    spec_file.write_text("# Migration Spec\n\nMigrate to new framework.")

    plan_file = spec_dir / "implementation_plan.json"
    plan_data = {
        "feature": "Migration Test",
        "workflow_type": "migration",
        "phases": [],
    }
    plan_file.write_text(json.dumps(plan_data, indent=2))

    context_file = spec_dir / "context.json"
    context_file.write_text(json.dumps({"files": []}, indent=2))

    yield project_dir, spec_dir


@pytest.fixture
def sample_project_files(tmp_path):
    """Create a sample project with files that need migration."""
    project_dir = tmp_path / "react_project"
    project_dir.mkdir(parents=True)

    # Initialize git
    subprocess.run(["git", "init"], cwd=project_dir, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=project_dir,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=project_dir,
        capture_output=True,
    )

    # Create React class component that needs migration
    src_dir = project_dir / "src"
    src_dir.mkdir(parents=True)

    class_component = src_dir / "MyComponent.jsx"
    class_component.write_text("""
import React from 'react';

class MyComponent extends React.Component {
    constructor(props) {
        super(props);
        this.state = { count: 0 };
    }

    componentDidMount() {
        console.log('Component mounted');
    }

    render() {
        return <div>{this.state.count}</div>;
    }
}

export default MyComponent;
""")

    # Create package.json
    package_json = project_dir / "package.json"
    package_json.write_text(
        json.dumps(
            {
                "name": "test-react-app",
                "version": "1.0.0",
                "dependencies": {"react": "^16.8.0"},
            },
            indent=2,
        )
    )

    # Initial commit
    subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial React project"],
        cwd=project_dir,
        capture_output=True,
    )

    yield project_dir


# =============================================================================
# CHECKPOINT MANAGER INTEGRATION TESTS
# =============================================================================


class TestCheckpointManagerIntegration:
    """Integration tests for CheckpointManager."""

    def test_checkpoint_manager_initialization(self, migration_env):
        """Test that checkpoint manager initializes correctly."""
        project_dir, spec_dir = migration_env

        manager = CheckpointManager(project_dir, spec_dir)

        assert manager.checkpoints_dir.exists()
        assert manager.rollback_scripts_dir.exists()
        assert manager.checkpoints_file.exists()

        # Verify checkpoints file structure
        with open(manager.checkpoints_file) as f:
            data = json.load(f)

        assert "checkpoints" in data
        assert "baseline_commit" in data
        assert "metadata" in data
        assert isinstance(data["checkpoints"], list)

    def test_create_checkpoint_with_git_commit(self, migration_env):
        """Test creating a checkpoint with git commit."""
        project_dir, spec_dir = migration_env
        manager = CheckpointManager(project_dir, spec_dir)

        # Create a checkpoint
        checkpoint = manager.create_checkpoint(
            phase_id="phase-1",
            name="Initial migration checkpoint",
            notes="Created baseline checkpoint",
        )

        assert checkpoint is not None
        assert checkpoint.phase_id == "phase-1"
        assert checkpoint.status == CheckpointStatus.CREATED
        assert len(checkpoint.commit_hash) > 0

        # Verify checkpoint was persisted
        data = manager._load_checkpoints()
        assert len(data["checkpoints"]) == 1
        assert data["checkpoints"][0]["name"] == "Initial migration checkpoint"

    def test_checkpoint_rollback_script_generation(self, migration_env):
        """Test that rollback scripts are generated correctly."""
        project_dir, spec_dir = migration_env
        manager = CheckpointManager(project_dir, spec_dir)

        # Create checkpoint
        checkpoint = manager.create_checkpoint(
            phase_id="phase-1", name="Test checkpoint"
        )

        # Verify rollback script exists
        rollback_scripts = list(manager.rollback_scripts_dir.glob("*.sh"))
        assert len(rollback_scripts) > 0

        # Verify script content
        script = rollback_scripts[0]
        content = script.read_text()
        assert "#!/bin/bash" in content
        assert "git reset --hard" in content
        assert checkpoint.commit_hash in content

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Unix executable permissions not supported on Windows",
    )
    def test_rollback_script_is_executable(self, migration_env):
        """Test that rollback scripts are executable (Unix only)."""
        project_dir, spec_dir = migration_env
        manager = CheckpointManager(project_dir, spec_dir)

        manager.create_checkpoint(phase_id="phase-1", name="Test checkpoint")

        rollback_scripts = list(manager.rollback_scripts_dir.glob("*.sh"))
        script = rollback_scripts[0]

        # Check executable permission
        assert script.stat().st_mode & 0o100

    def test_multiple_checkpoints(self, migration_env):
        """Test creating multiple checkpoints in sequence."""
        project_dir, spec_dir = migration_env
        manager = CheckpointManager(project_dir, spec_dir)

        # Create multiple checkpoints
        checkpoint1 = manager.create_checkpoint(phase_id="phase-1", name="Checkpoint 1")

        # Make a change to create different commits
        test_file = project_dir / "test1.txt"
        test_file.write_text("Test content 1")
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Test change 1"],
            cwd=project_dir,
            capture_output=True,
        )

        checkpoint2 = manager.create_checkpoint(phase_id="phase-2", name="Checkpoint 2")

        # Verify both checkpoints exist
        data = manager._load_checkpoints()
        assert len(data["checkpoints"]) == 2
        assert checkpoint1.commit_hash != checkpoint2.commit_hash

    def test_rollback_to_checkpoint(self, migration_env):
        """Test rolling back to a previous checkpoint."""
        project_dir, spec_dir = migration_env
        manager = CheckpointManager(project_dir, spec_dir)

        # Create initial checkpoint
        checkpoint1 = manager.create_checkpoint(
            phase_id="phase-1", name="Before changes"
        )

        # Make changes
        test_file = project_dir / "test_rollback.txt"
        test_file.write_text("This will be rolled back")
        subprocess.run(["git", "add", "."], cwd=project_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Changes to roll back"],
            cwd=project_dir,
            capture_output=True,
        )

        # Verify file exists
        assert test_file.exists()

        # Rollback
        success = manager.rollback_to_checkpoint(checkpoint1.id)
        assert success

        # Verify file was removed
        assert not test_file.exists()


# =============================================================================
# MIGRATION PLANNER INTEGRATION TESTS
# =============================================================================


class TestMigrationPlannerIntegration:
    """Integration tests for MigrationPlanner."""

    def test_planner_initialization(self, migration_env):
        """Test that migration planner initializes correctly."""
        project_dir, spec_dir = migration_env

        planner = MigrationPlanner(project_dir)

        assert planner.project_dir == project_dir
        assert isinstance(planner.phases, list)
        assert isinstance(planner.checkpoints, list)

    def test_analyze_react_project(self, sample_project_files):
        """Test analyzing a React project for migration."""
        project_dir = sample_project_files
        planner = MigrationPlanner(project_dir)

        analysis = planner.analyze_project()

        assert "framework_info" in analysis
        assert "complexity_estimate" in analysis

    def test_create_migration_plan_for_react(self, sample_project_files):
        """Test creating a migration plan for React class to hooks."""
        project_dir = sample_project_files
        planner = MigrationPlanner(project_dir)

        plan = planner.create_plan(
            migration_type=MigrationType.REACT_CLASS_TO_HOOKS, target_version="^18.0.0"
        )

        assert "phases" in plan
        assert "checkpoints" in plan
        assert "migration_type" in plan
        assert len(plan["phases"]) > 0

    def test_plan_includes_rollback_strategy(self, sample_project_files):
        """Test that migration plan includes rollback strategy."""
        project_dir = sample_project_files
        planner = MigrationPlanner(project_dir)

        plan = planner.create_plan(
            migration_type=MigrationType.REACT_CLASS_TO_HOOKS, target_version="^18.0.0"
        )

        # Plan should have overall rollback strategy
        assert "rollback_strategy" in plan


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================


class TestMigrationWorkflowEndToEnd:
    """End-to-end tests for complete migration workflow."""

    @pytest.fixture(autouse=True)
    def mock_session_runner(self):
        """Patch the shared session driver used by run_migration_assistant.

        ``ClaudeSDKClient`` has no ``create_agent_session`` method; the inline
        migration session is driven by ``agents.session.run_agent_session``
        inside ``async with client``. Patch it to a success 4-tuple; tests that
        need a failure reconfigure ``self._mock_run`` (e.g. ``side_effect``).
        """
        self._mock_run = AsyncMock(
            return_value=("complete", "migration done", None, MagicMock())
        )
        with patch("agents.session.run_agent_session", new=self._mock_run):
            yield self._mock_run

    @pytest.mark.asyncio
    @patch("agents.migration_assistant.get_phase_thinking_budget")
    @patch("agents.migration_assistant.get_phase_model")
    @patch("agents.migration_assistant.create_client")
    async def test_migration_assistant_initialization_with_context(
        self,
        mock_create_client,
        mock_get_phase_model,
        mock_get_phase_thinking_budget,
        migration_env,
    ):
        """Test that migration assistant initializes with proper context."""
        from agents.migration_assistant import run_migration_assistant

        project_dir, spec_dir = migration_env

        # Mock phase config functions
        mock_get_phase_model.return_value = "claude-sonnet-4-5-20250929"
        mock_get_phase_thinking_budget.return_value = 4096

        # Mock the SDK client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client

        migration_context = {
            "from": "React 16",
            "to": "React 18",
            "type": "framework_upgrade",
        }

        await run_migration_assistant(
            project_dir=project_dir,
            spec_dir=spec_dir,
            migration_context=migration_context,
            model="claude-sonnet-4",
        )

        # Verify client was created with correct params
        mock_create_client.assert_called_once()
        call_kwargs = mock_create_client.call_args[1]
        assert call_kwargs["agent_type"] == "migration_assistant"
        assert call_kwargs["project_dir"] == project_dir
        assert call_kwargs["spec_dir"] == spec_dir

        # Verify the session was driven through the shared helper, with the
        # migration context carried in the message.
        self._mock_run.assert_awaited_once()
        message = self._mock_run.await_args.kwargs["message"]
        assert "React 16" in message
        assert "React 18" in message

    @pytest.mark.asyncio
    @patch("agents.migration_assistant.get_phase_thinking_budget")
    @patch("agents.migration_assistant.get_phase_model")
    @patch("agents.migration_assistant.create_client")
    async def test_migration_creates_checkpoints(
        self,
        mock_create_client,
        mock_get_phase_model,
        mock_get_phase_thinking_budget,
        migration_env,
    ):
        """Test that migration workflow creates checkpoints."""
        from agents.migration_assistant import run_migration_assistant

        project_dir, spec_dir = migration_env

        # Mock phase config functions
        mock_get_phase_model.return_value = "claude-sonnet-4-5-20250929"
        mock_get_phase_thinking_budget.return_value = 4096

        # Mock the SDK client
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client

        # Pre-create checkpoint structure to simulate agent creating it
        checkpoint_dir = project_dir / ".migration-checkpoints"
        checkpoint_dir.mkdir(parents=True)
        rollback_dir = checkpoint_dir / "rollback"
        rollback_dir.mkdir(parents=True)

        # Create checkpoint files
        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123")

        rollback_script = rollback_dir / "checkpoint-001.sh"
        rollback_script.write_text("#!/bin/bash\ngit reset --hard abc123")
        if platform.system() != "Windows":
            rollback_script.chmod(0o755)

        # Create migration plan
        migration_plan = project_dir / "migration_plan.md"
        migration_plan.write_text("# Migration Plan\n\nPhase 1: Setup")

        result = await run_migration_assistant(
            project_dir=project_dir, spec_dir=spec_dir
        )

        assert result["success"]
        assert result["checkpoints_created"] == 1
        assert result["migration_plan_path"] is not None

    @pytest.mark.asyncio
    @patch("agents.migration_assistant.get_phase_thinking_budget")
    @patch("agents.migration_assistant.get_phase_model")
    @patch("agents.migration_assistant.create_client")
    async def test_migration_handles_failures(
        self,
        mock_create_client,
        mock_get_phase_model,
        mock_get_phase_thinking_budget,
        migration_env,
    ):
        """Test that migration workflow handles failures gracefully."""
        from agents.migration_assistant import run_migration_assistant

        project_dir, spec_dir = migration_env

        # Mock phase config functions
        mock_get_phase_model.return_value = "claude-sonnet-4-5-20250929"
        mock_get_phase_thinking_budget.return_value = 4096

        # Mock client; the shared session driver raises mid-session.
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client
        self._mock_run.side_effect = Exception("Simulated failure")

        result = await run_migration_assistant(
            project_dir=project_dir, spec_dir=spec_dir
        )

        assert not result["success"]
        assert "error" in result
        assert "Simulated failure" in result["error"]
        assert result["checkpoints_created"] == 0


# =============================================================================
# CLI INTEGRATION TESTS
# =============================================================================


class TestMigrationCLIIntegration:
    """Integration tests for migration CLI commands."""

    def test_migration_commands_exist(self):
        """Test that migration CLI commands are available."""
        from cli import migration_commands

        assert hasattr(migration_commands, "handle_migration_command")
        assert hasattr(migration_commands, "handle_migration_status_command")

    @patch("cli.migration_commands.validate_environment", return_value=True)
    @patch("cli.migration_commands.asyncio.run")
    def test_handle_migration_command(
        self, mock_asyncio_run, mock_validate_env, migration_env
    ):
        """Test handling migration CLI command."""
        from cli.migration_commands import handle_migration_command

        project_dir, spec_dir = migration_env

        mock_asyncio_run.return_value = {
            "success": True,
            "checkpoints_created": 2,
            "migration_plan_path": "migration_plan.md",
        }

        # CLI command returns None (prints output)
        result = handle_migration_command(
            project_dir=project_dir, spec_dir=spec_dir, model="claude-sonnet-4"
        )

        assert result is None
        mock_asyncio_run.assert_called_once()

    def test_migration_status_with_checkpoints(self, migration_env):
        """Test getting migration status when checkpoints exist."""
        from cli.migration_commands import handle_migration_status_command

        project_dir, spec_dir = migration_env

        # Create checkpoint structure
        manager = CheckpointManager(project_dir, spec_dir)
        manager.create_checkpoint(phase_id="phase-1", name="Test checkpoint")

        # CLI command returns None (prints output), just verify it doesn't crash
        result = handle_migration_status_command(
            project_dir=project_dir, spec_dir=spec_dir
        )

        # Command should complete without errors
        assert result is None

    def test_migration_status_without_checkpoints(self, migration_env):
        """Test getting migration status when no checkpoints exist."""
        from cli.migration_commands import handle_migration_status_command

        project_dir, spec_dir = migration_env

        # CLI command returns None (prints output), just verify it doesn't crash
        result = handle_migration_status_command(
            project_dir=project_dir, spec_dir=spec_dir
        )

        # Command should complete without errors
        assert result is None


# =============================================================================
# VALIDATION AND ERROR HANDLING TESTS
# =============================================================================


class TestMigrationValidationAndErrors:
    """Tests for migration validation and error handling."""

    def test_checkpoint_validation_with_complete_checkpoint(self, migration_env):
        """Test validating a complete checkpoint."""
        from agents.migration_assistant import validate_migration_checkpoint

        project_dir, spec_dir = migration_env

        # Create complete checkpoint
        manager = CheckpointManager(project_dir, spec_dir)
        manager.create_checkpoint(phase_id="phase-1", name="Complete checkpoint")

        # Validate checkpoint
        validation = validate_migration_checkpoint(manager.checkpoints_dir, project_dir)

        # Executable permission check is now platform-gated (Unix only)
        # CheckpointManager makes scripts executable on Unix, skips on Windows
        assert validation["valid"], (
            f"Validation failed with issues: {validation['issues']}"
        )
        assert len(validation["issues"]) == 0
        assert "commit" in validation["checkpoint_info"]
        assert "rollback_scripts" in validation["checkpoint_info"]

    def test_checkpoint_validation_with_incomplete_checkpoint(self, migration_env):
        """Test validating an incomplete checkpoint."""
        from agents.migration_assistant import validate_migration_checkpoint

        project_dir, spec_dir = migration_env

        # Create incomplete checkpoint (missing rollback scripts)
        checkpoint_dir = spec_dir / "checkpoints"
        checkpoint_dir.mkdir(parents=True)

        commit_file = checkpoint_dir / "checkpoint-001-commit.txt"
        commit_file.write_text("abc123")

        # Validate
        validation = validate_migration_checkpoint(checkpoint_dir, project_dir)

        assert not validation["valid"]
        assert len(validation["issues"]) > 0
        assert any("rollback" in issue.lower() for issue in validation["issues"])

    def test_checkpoint_manager_handles_missing_git(self, tmp_path):
        """Test that checkpoint manager handles missing git gracefully."""
        # Create project dir without git
        project_dir = tmp_path / "no_git"
        project_dir.mkdir()
        spec_dir = tmp_path / "spec"
        spec_dir.mkdir()

        manager = CheckpointManager(project_dir, spec_dir)

        # Attempt to create checkpoint should handle error
        try:
            checkpoint = manager.create_checkpoint(phase_id="phase-1", name="Test")
            # If it succeeds, it should return None or handle gracefully
            assert checkpoint is None or hasattr(checkpoint, "commit_hash")
        except Exception as e:
            # Should raise a meaningful error
            assert "git" in str(e).lower() or "commit" in str(e).lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
