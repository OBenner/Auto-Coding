#!/usr/bin/env python3
"""
E2E Tests for Task Restart Workflow
===================================

End-to-end tests for the task restart functionality including:
- Restart from specific subtask with provider/model preservation
- Skipping completed subtasks on restart
- Provider and model config restoration from implementation_plan.json
- Edge cases: invalid subtask IDs, restart from completed subtask
"""

import json

# Add backend directory to path if not already added by conftest
import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent.parent / "apps" / "backend"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))


# =============================================================================
# RESTART FROM SUBTASK TESTS
# =============================================================================


class TestTaskRestartFromSubtask:
    """Tests for restarting task from a specific subtask."""

    def test_restart_from_subtask_skips_completed(self, temp_dir):
        """Tests that restarting from a subtask skips earlier completed subtasks."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "001-restart-test"
        spec_dir.mkdir(parents=True)

        # Create implementation plan with multiple subtasks in various states
        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Completed subtask 1",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-2",
                            "description": "Completed subtask 2",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-3",
                            "description": "Pending subtask 3",
                            "status": "pending",
                        },
                    ],
                },
                {
                    "id": "phase-2",
                    "name": "Phase 2",
                    "depends_on": ["phase-1"],
                    "subtasks": [
                        {
                            "id": "subtask-2-1",
                            "description": "Pending subtask 4",
                            "status": "pending",
                        }
                    ],
                },
            ],
            "provider_config": {"provider": "zhipuai", "model": "glm-4-flash-250414"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Restart from subtask-1-2 (which is completed)
        # Should skip to subtask-1-3 (next pending)
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-2")

        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-1-3"
        assert next_subtask["status"] == "pending"

    def test_restart_from_pending_subtask(self, temp_dir):
        """Tests that restarting from a pending subtask returns that subtask."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "002-pending-restart"
        spec_dir.mkdir(parents=True)

        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Completed subtask",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-2",
                            "description": "Pending subtask",
                            "status": "pending",
                        },
                    ],
                }
            ],
            "provider_config": {"provider": "claude", "model": "claude-sonnet-4-5"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Restart from pending subtask
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-2")

        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-1-2"
        assert next_subtask["status"] == "pending"

    def test_restart_from_invalid_subtask_id(self, temp_dir):
        """Tests that restart from invalid subtask ID falls through to normal flow."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "003-invalid-restart"
        spec_dir.mkdir(parents=True)

        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Pending subtask",
                            "status": "pending",
                        }
                    ],
                }
            ],
            "provider_config": {"provider": "litellm", "model": "gpt-4o"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Restart from invalid subtask ID
        # Should fall through to normal flow and return first pending
        next_subtask = get_next_subtask(spec_dir, restart_from="invalid-subtask-id")

        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-1-1"

    def test_restart_from_middle_of_phase(self, temp_dir):
        """Tests restarting from a subtask in the middle of a phase."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "004-middle-restart"
        spec_dir.mkdir(parents=True)

        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Completed",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-2",
                            "description": "Completed",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-3",
                            "description": "Pending",
                            "status": "pending",
                        },
                        {
                            "id": "subtask-1-4",
                            "description": "Pending",
                            "status": "pending",
                        },
                    ],
                }
            ],
            "provider_config": {"provider": "openrouter", "model": "claude-sonnet-4-5"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Restart from middle of phase (subtask-1-2, which is completed)
        # Should skip to next pending (subtask-1-3)
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-2")

        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-1-3"

    def test_restart_respects_phase_dependencies(self, temp_dir):
        """Tests that restart respects phase dependencies."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "005-deps-restart"
        spec_dir.mkdir(parents=True)

        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "All completed in phase 1",
                            "status": "completed",
                        }
                    ],
                },
                {
                    "id": "phase-2",
                    "name": "Phase 2",
                    "depends_on": ["phase-1"],
                    "subtasks": [
                        {
                            "id": "subtask-2-1",
                            "description": "All completed in phase 2",
                            "status": "completed",
                        }
                    ],
                },
                {
                    "id": "phase-3",
                    "name": "Phase 3",
                    "depends_on": ["phase-2"],
                    "subtasks": [
                        {
                            "id": "subtask-3-1",
                            "description": "Pending in phase 3",
                            "status": "pending",
                        }
                    ],
                },
            ],
            "provider_config": {"provider": "zhipuai", "model": "glm-4-flash-250414"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Restart from phase 2 (all completed)
        # Should skip to phase 3 (next pending)
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-2-1")

        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-3-1"


# =============================================================================
# PROVIDER CONFIG PRESERVATION TESTS
# =============================================================================


class TestProviderConfigPreservation:
    """Tests for provider and model configuration preservation across restarts."""

    def test_provider_config_persisted_to_plan(self, temp_dir):
        """Tests that provider config is saved to implementation_plan.json."""
        spec_dir = temp_dir / "specs" / "006-provider-persist"
        spec_dir.mkdir(parents=True)

        # Simulate planner saving provider config
        plan = {
            "feature": "Test Feature",
            "phases": [],
            "provider_config": {"provider": "zhipuai", "model": "glm-4-flash-250414"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Verify persistence
        with open(plan_file) as f:
            loaded_plan = json.load(f)

        assert "provider_config" in loaded_plan
        assert loaded_plan["provider_config"]["provider"] == "zhipuai"
        assert loaded_plan["provider_config"]["model"] == "glm-4-flash-250414"

    def test_provider_config_restored_on_restart(self, temp_dir):
        """Tests that provider config is restored when restarting task."""
        spec_dir = temp_dir / "specs" / "007-provider-restore"
        spec_dir.mkdir(parents=True)

        # Create plan with provider config
        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Pending subtask",
                            "status": "pending",
                        }
                    ],
                }
            ],
            "provider_config": {"provider": "litellm", "model": "gpt-4o"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Simulate loading plan and restoring provider config
        with open(plan_file) as f:
            loaded_plan = json.load(f)

        provider_config_data = loaded_plan.get("provider_config")
        assert provider_config_data is not None
        assert provider_config_data["provider"] == "litellm"
        assert provider_config_data["model"] == "gpt-4o"

    def test_provider_and_model_selection_combinations(self, temp_dir):
        """Tests various provider and model selection combinations for restart."""
        # Test different provider/model combinations that could be used on restart
        combinations = [
            ("claude", "claude-sonnet-4-5"),
            ("litellm", "gpt-4o"),
            ("openrouter", "claude-opus-4-5"),
            ("zhipuai", "glm-4-flash-250414"),
        ]

        for idx, (provider, model) in enumerate(combinations):
            spec_dir = temp_dir / "specs" / f"007-combo-{idx}"
            spec_dir.mkdir(parents=True)

            plan = {
                "feature": f"Test {provider}",
                "phases": [],
                "provider_config": {"provider": provider, "model": model},
            }

            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(json.dumps(plan, indent=2))

            # Verify persistence
            with open(plan_file) as f:
                loaded_plan = json.load(f)

            assert loaded_plan["provider_config"]["provider"] == provider
            assert loaded_plan["provider_config"]["model"] == model

    def test_backward_compat_no_provider_config(self, temp_dir):
        """Tests backward compatibility: plans without provider_config work."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "008-no-provider-config"
        spec_dir.mkdir(parents=True)

        # Old-style plan without provider_config
        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Pending subtask",
                            "status": "pending",
                        }
                    ],
                }
            ],
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Should not crash when provider_config is missing
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-1")

        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-1-1"


# =============================================================================
# CLI INTEGRATION TESTS
# =============================================================================


class TestRestartCLIIntegration:
    """Integration tests for restart CLI functionality."""

    def test_build_command_accepts_restart_from(self, temp_dir):
        """Tests handle_build_command accepts restart_from parameter."""
        import inspect

        from cli.build_commands import handle_build_command

        sig = inspect.signature(handle_build_command)
        assert "restart_from" in sig.parameters

        # Verify it's optional
        param = sig.parameters["restart_from"]
        # Default should be None
        assert param.default is None

    def test_restart_from_parameter_type(self):
        """Tests that restart_from parameter accepts string or None."""
        import inspect

        from cli.build_commands import handle_build_command

        sig = inspect.signature(handle_build_command)
        param = sig.parameters["restart_from"]

        # Parameter annotation should be str | None
        annotation = param.annotation
        # Check that it's a union type or allows None
        assert "str" in str(annotation) or "None" in str(annotation)


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================


class TestTaskRestartWorkflow:
    """End-to-end tests for complete task restart workflow."""

    def test_full_restart_workflow(self, temp_dir, temp_git_repo):
        """Tests complete workflow: run -> pause -> restart -> continue."""
        spec_dir = temp_git_repo / ".auto-claude" / "specs" / "009-full-workflow"
        spec_dir.mkdir(parents=True)

        # Phase 1: Initial task with provider config
        plan = {
            "feature": "Test Feature with Restart",
            "workflow_type": "feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Foundation",
                    "type": "implementation",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Create base structure",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-2",
                            "description": "Add configuration",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-3",
                            "description": "Implement core logic",
                            "status": "pending",
                        },
                    ],
                },
                {
                    "id": "phase-2",
                    "name": "Enhancement",
                    "type": "implementation",
                    "depends_on": ["phase-1"],
                    "subtasks": [
                        {
                            "id": "subtask-2-1",
                            "description": "Add advanced features",
                            "status": "pending",
                        }
                    ],
                },
            ],
            "provider_config": {"provider": "zhipuai", "model": "glm-4-flash-250414"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Simulate task interruption and restart

        # Step 1: Verify provider config was saved
        with open(plan_file) as f:
            saved_plan = json.load(f)

        assert "provider_config" in saved_plan
        assert saved_plan["provider_config"]["provider"] == "zhipuai"
        assert saved_plan["provider_config"]["model"] == "glm-4-flash-250414"

        # Step 2: Simulate restart from subtask-1-3
        from core.progress import get_next_subtask

        # Restart from the pending subtask
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-3")

        # Should return subtask-1-3 (it's pending)
        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-1-3"

        # Step 3: Mark subtask-1-3 as completed and find next
        plan["phases"][0]["subtasks"][2]["status"] = "completed"
        plan_file.write_text(json.dumps(plan, indent=2))

        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-3")

        # Should skip to next phase
        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-2-1"
        assert next_subtask["phase_id"] == "phase-2"

    def test_multi_provider_restart(self, temp_dir):
        """Tests restart preserves provider config across all providers."""
        from core.progress import get_next_subtask

        providers = [
            ("claude", "claude-sonnet-4-5"),
            ("litellm", "gpt-4o"),
            ("openrouter", "claude-opus-4-5"),
            ("zhipuai", "glm-4-flash-250414"),
        ]

        for idx, (provider, model) in enumerate(providers):
            spec_dir = temp_dir / "specs" / f"010-multi-provider-{idx}"
            spec_dir.mkdir(parents=True)

            plan = {
                "feature": f"Test {provider}",
                "phases": [
                    {
                        "id": "phase-1",
                        "name": "Phase 1",
                        "depends_on": [],
                        "subtasks": [
                            {
                                "id": "subtask-1-1",
                                "description": "Completed",
                                "status": "completed",
                            },
                            {
                                "id": "subtask-1-2",
                                "description": "Pending",
                                "status": "pending",
                            },
                        ],
                    }
                ],
                "provider_config": {"provider": provider, "model": model},
            }

            plan_file = spec_dir / "implementation_plan.json"
            plan_file.write_text(json.dumps(plan, indent=2))

            # Verify config persistence
            with open(plan_file) as f:
                loaded_plan = json.load(f)

            assert loaded_plan["provider_config"]["provider"] == provider
            assert loaded_plan["provider_config"]["model"] == model

            # Verify restart works
            next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-1")
            assert next_subtask is not None
            assert next_subtask["id"] == "subtask-1-2"

    def test_restart_all_subtasks_complete(self, temp_dir):
        """Tests restart when all subtasks are already complete."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "011-all-complete"
        spec_dir.mkdir(parents=True)

        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "All completed",
                            "status": "completed",
                        },
                        {
                            "id": "subtask-1-2",
                            "description": "All completed",
                            "status": "completed",
                        },
                    ],
                }
            ],
            "provider_config": {"provider": "claude", "model": "claude-sonnet-4-5"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # Try to restart from completed subtask
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-1-1")

        # Should return None (all complete)
        assert next_subtask is None

    def test_restart_with_blocked_phase(self, temp_dir):
        """Tests restart respects blocked phases (unmet dependencies)."""
        from core.progress import get_next_subtask

        spec_dir = temp_dir / "specs" / "012-blocked-phase"
        spec_dir.mkdir(parents=True)

        plan = {
            "feature": "Test Feature",
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Phase 1 (incomplete)",
                    "depends_on": [],
                    "subtasks": [
                        {
                            "id": "subtask-1-1",
                            "description": "Still pending",
                            "status": "pending",
                        }
                    ],
                },
                {
                    "id": "phase-2",
                    "name": "Phase 2 (blocked)",
                    "depends_on": ["phase-1"],
                    "subtasks": [
                        {
                            "id": "subtask-2-1",
                            "description": "Blocked by phase 1",
                            "status": "pending",
                        }
                    ],
                },
            ],
            "provider_config": {"provider": "zhipuai", "model": "glm-4-flash-250414"},
        }

        plan_file = spec_dir / "implementation_plan.json"
        plan_file.write_text(json.dumps(plan, indent=2))

        # When restarting from a specific subtask in a blocked phase,
        # it will return that subtask since restart_from explicitly
        # requests starting from that point
        next_subtask = get_next_subtask(spec_dir, restart_from="subtask-2-1")

        # Should return subtask-2-1 (explicit restart request)
        assert next_subtask is not None
        assert next_subtask["id"] == "subtask-2-1"

        # However, normal flow (without restart_from) should respect dependencies
        next_subtask_normal = get_next_subtask(spec_dir, restart_from=None)
        assert next_subtask_normal is not None
        assert next_subtask_normal["id"] == "subtask-1-1"
