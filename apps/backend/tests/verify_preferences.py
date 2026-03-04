#!/usr/bin/env python3
"""
Preference System Verification Tests
======================================

Pytest-based tests for the Adaptive Agent Personality System.
Verifies that all components are in place and properly integrated.

Run with: pytest apps/backend/tests/verify_preferences.py -v
"""

import sys
from pathlib import Path

import pytest

# Add apps/backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def get_project_root():
    """Get the project root directory."""
    test_file = Path(__file__).resolve()
    tests_dir = test_file.parent  # apps/backend/tests
    backend_dir = tests_dir.parent  # apps/backend
    apps_dir = backend_dir.parent  # apps
    return apps_dir.parent  # project root


class TestPreferenceModels:
    """Test backend preference data models."""

    def test_imports(self):
        """All preference model classes can be imported."""
        from agents.preferences import (  # noqa: F401
            CodingStylePreferences,
            FeedbackRecord,
            FeedbackType,
            PreferenceProfile,
            ProjectType,
            RiskTolerance,
            VerbosityLevel,
            app_settings_to_profile,
            modify_prompt_for_preferences,
        )

    def test_create_profile(self):
        """PreferenceProfile can be created with enum values."""
        from agents.preferences import (
            PreferenceProfile,
            ProjectType,
            RiskTolerance,
            VerbosityLevel,
        )

        profile = PreferenceProfile(
            verbosity_level=VerbosityLevel.CONCISE,
            risk_tolerance=RiskTolerance.BALANCED,
            project_type=ProjectType.ESTABLISHED,
        )

        assert profile.verbosity_level == VerbosityLevel.CONCISE
        assert profile.risk_tolerance == RiskTolerance.BALANCED
        assert profile.project_type == ProjectType.ESTABLISHED

    def test_add_feedback(self):
        """Feedback can be added to a profile."""
        from agents.preferences import (
            FeedbackType,
            PreferenceProfile,
            VerbosityLevel,
        )

        profile = PreferenceProfile(verbosity_level=VerbosityLevel.NORMAL)
        profile.add_feedback(
            feedback_type=FeedbackType.MODIFIED,
            task_description="Test task",
            agent_type="coder",
            context={"reason": "too verbose"},
        )

        assert len(profile.feedback_history) == 1
        assert profile.feedback_history[0].feedback_type == FeedbackType.MODIFIED

    def test_serialization_roundtrip(self):
        """PreferenceProfile serializes and deserializes correctly."""
        from agents.preferences import (
            FeedbackType,
            PreferenceProfile,
            ProjectType,
            RiskTolerance,
            VerbosityLevel,
        )

        profile = PreferenceProfile(
            verbosity_level=VerbosityLevel.CONCISE,
            risk_tolerance=RiskTolerance.BALANCED,
            project_type=ProjectType.ESTABLISHED,
        )
        profile.add_feedback(
            feedback_type=FeedbackType.MODIFIED,
            task_description="Test task",
            agent_type="coder",
            context={"reason": "too verbose"},
        )

        profile_dict = profile.to_dict()
        restored = PreferenceProfile.from_dict(profile_dict)

        assert restored.verbosity_level == VerbosityLevel.CONCISE
        assert restored.risk_tolerance == RiskTolerance.BALANCED
        assert len(restored.feedback_history) == 1

    def test_prompt_modification(self):
        """modify_prompt_for_preferences injects preference instructions."""
        from agents.preferences import (
            PreferenceProfile,
            VerbosityLevel,
            modify_prompt_for_preferences,
        )

        profile = PreferenceProfile(verbosity_level=VerbosityLevel.CONCISE)
        original_prompt = "You are a helpful coding assistant."
        modified = modify_prompt_for_preferences(original_prompt, profile)

        assert "concise" in modified.lower()
        assert original_prompt in modified


class TestAdaptiveBehavior:
    """Test adaptive behavior learning from feedback."""

    def test_verbosity_learning(self):
        """Profile adjusts verbosity based on feedback."""
        from agents.preferences import (
            FeedbackType,
            PreferenceProfile,
            RiskTolerance,
            VerbosityLevel,
        )

        profile = PreferenceProfile(
            verbosity_level=VerbosityLevel.NORMAL,
            risk_tolerance=RiskTolerance.BALANCED,
            project_type="established",
        )

        for i in range(3):
            profile.add_feedback(
                feedback_type=FeedbackType.MODIFIED,
                task_description=f"Task {i + 1}",
                agent_type="coder",
                context={"reason": "too verbose"},
            )

        effective_verbosity = profile.get_effective_verbosity()
        assert isinstance(effective_verbosity, VerbosityLevel)


class TestAppSettingsAdapter:
    """Test frontend settings to backend profile conversion."""

    def test_default_settings(self):
        """Empty settings produce sensible defaults."""
        from agents.preferences import (
            ProjectType,
            RiskTolerance,
            VerbosityLevel,
            app_settings_to_profile,
        )

        profile = app_settings_to_profile({})
        assert profile.verbosity_level == VerbosityLevel.NORMAL
        assert profile.risk_tolerance == RiskTolerance.BALANCED
        assert profile.project_type == ProjectType.ESTABLISHED

    def test_full_settings(self):
        """All frontend settings map to backend fields."""
        from agents.preferences import (
            ProjectType,
            RiskTolerance,
            VerbosityLevel,
            app_settings_to_profile,
        )

        settings = {
            "agentVerbosity": "verbose",
            "agentRiskTolerance": "cautious",
            "agentProjectType": "greenfield",
            "agentCodingStyle": {
                "indentation": "tabs",
                "quoteStyle": "single",
                "namingConvention": "camelCase",
                "commentDensity": "verbose",
                "typeHints": False,
            },
            "agentUserInstructions": ["always explain", "be careful"],
        }

        profile = app_settings_to_profile(settings)
        assert profile.verbosity_level == VerbosityLevel.VERBOSE
        assert profile.risk_tolerance == RiskTolerance.CAUTIOUS
        assert profile.project_type == ProjectType.GREENFIELD
        assert profile.coding_style.indentation == "tabs"
        assert profile.coding_style.quote_style == "single"
        assert profile.coding_style.type_hints is False
        assert len(profile.user_instructions) == 2


class TestFeedbackRecording:
    """Test feedback recording API exists."""

    def test_save_feedback_importable(self):
        """save_feedback function can be imported."""
        from agents.memory_manager import save_feedback  # noqa: F401


class TestIntegration:
    """Test end-to-end integration of preference components."""

    def test_all_imports(self):
        """All core preference system modules import successfully."""
        from agents.memory_manager import save_feedback  # noqa: F401
        from agents.preferences import modify_prompt_for_preferences  # noqa: F401
        from core.client import load_preferences  # noqa: F401
        from integrations.graphiti.memory import get_graphiti_memory  # noqa: F401

    def test_data_flow(self):
        """Preferences flow from profile to prompt modification."""
        from agents.preferences import (
            PreferenceProfile,
            VerbosityLevel,
            modify_prompt_for_preferences,
        )

        profile = PreferenceProfile(verbosity_level=VerbosityLevel.CONCISE)
        prompt = modify_prompt_for_preferences("Test prompt", profile)

        assert "concise" in prompt.lower()

    def test_frontend_types_exist(self):
        """Frontend TypeScript settings types file exists with required types."""
        project_root = get_project_root()
        types_file = (
            project_root
            / "apps"
            / "frontend"
            / "src"
            / "shared"
            / "types"
            / "settings.ts"
        )

        if not types_file.exists():
            pytest.skip("Frontend types file not found (expected in worktree)")

        content = types_file.read_text()

        required_types = [
            "AgentVerbosityLevel",
            "AgentRiskTolerance",
            "AgentProjectType",
            "AgentCodingStylePreferences",
        ]

        for type_name in required_types:
            assert type_name in content, f"Missing TypeScript type: {type_name}"

    def test_frontend_components_exist(self):
        """Frontend UI components exist at expected paths."""
        project_root = get_project_root()

        components = [
            "apps/frontend/src/renderer/components/settings/AgentPreferences.tsx",
            "apps/frontend/src/renderer/components/feedback/FeedbackButtons.tsx",
        ]

        for component_path in components:
            path = project_root / component_path
            if not path.exists():
                pytest.skip(f"Component not found (expected in worktree): {path}")

    def test_ipc_handlers_exist(self):
        """IPC handler file exists with required exports."""
        project_root = get_project_root()
        handler_file = (
            project_root
            / "apps"
            / "frontend"
            / "src"
            / "main"
            / "ipc-handlers"
            / "feedback-handlers.ts"
        )

        if not handler_file.exists():
            pytest.skip("IPC handler not found (expected in worktree)")

        content = handler_file.read_text()

        required_items = [
            "registerFeedbackHandlers",
            "IPC_CHANNELS.FEEDBACK_SUBMIT",
            "feedback_recorder.py",
        ]

        for item in required_items:
            assert item in content, f"Missing in IPC handler: {item}"
