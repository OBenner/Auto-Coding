"""
Tests for cost-aware task complexity routing.
"""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from core.providers.config import ProviderConfig
from core.providers.task_router import TaskComplexityRouter
from core.providers.task_router_config import load_model_routing_config


def _issue(likelihood: str) -> SimpleNamespace:
    return SimpleNamespace(likelihood=likelihood)


def test_calculate_complexity_score_for_trivial_task_is_low():
    """Trivial docs changes should be routed toward low complexity."""
    router = TaskComplexityRouter(config_path=Path("/missing/model_routing.yaml"))

    score = router._calculate_complexity_score(
        work_types=[],
        risk_issues=[],
        subtask={
            "description": "Fix typo in README documentation",
            "files_to_modify": ["README.md"],
            "files_to_create": [],
        },
    )

    assert score == pytest.approx(0.1)


def test_calculate_complexity_score_clamps_high_values():
    """Many risk and size signals should not push score above 1.0."""
    router = TaskComplexityRouter(config_path=Path("/missing/model_routing.yaml"))

    score = router._calculate_complexity_score(
        work_types=["authentication"],
        risk_issues=[_issue("high")] * 10 + [_issue("medium")] * 10,
        subtask={
            "description": "Rewrite and refactor authentication architecture",
            "files_to_modify": [f"auth/file_{i}.py" for i in range(12)],
            "files_to_create": [],
        },
    )

    assert score == 1.0


def test_calculate_complexity_score_boundary_values():
    """File thresholds should apply medium/high size bonuses at boundaries."""
    router = TaskComplexityRouter(config_path=Path("/missing/model_routing.yaml"))

    medium_score = router._calculate_complexity_score(
        work_types=[],
        risk_issues=[],
        subtask={
            "description": "Update backend handlers",
            "files_to_modify": [f"file_{i}.py" for i in range(5)],
        },
    )
    high_size_score = router._calculate_complexity_score(
        work_types=[],
        risk_issues=[],
        subtask={
            "description": "Update backend handlers",
            "files_to_modify": [f"file_{i}.py" for i in range(10)],
        },
    )

    assert medium_score == pytest.approx(0.45)
    assert high_size_score == pytest.approx(0.55)


def test_route_maps_score_to_configured_low_medium_high_models():
    """Routing table lookup should follow configured complexity thresholds."""
    router = TaskComplexityRouter(config_path=Path("/missing/model_routing.yaml"))
    router.risk_analyzer = MagicMock()

    router.risk_analyzer.analyze_subtask_risks.return_value = []
    low_route = router.route({"description": "Fix typo", "files_to_modify": []})

    router.risk_analyzer.analyze_subtask_risks.return_value = [_issue("medium")] * 2
    medium_route = router.route(
        {
            "description": "Add pagination endpoint",
            "files_to_modify": ["api/users.py", "tests/test_users.py"],
        },
        agent_type="coder",
    )

    router.risk_analyzer.analyze_subtask_risks.return_value = [_issue("high")] * 3
    high_route = router.route(
        {
            "description": "Refactor authentication module",
            "files_to_modify": [
                "auth/handlers.py",
                "auth/middleware.py",
                "auth/models.py",
                "config/settings.py",
                "tests/test_auth.py",
            ],
            "files_to_create": ["auth/oauth2.py"],
        }
    )

    assert low_route.complexity == "low"
    assert low_route.provider == "openai"
    assert low_route.model == "gpt-4o-mini"
    assert medium_route.complexity == "medium"
    assert medium_route.model == "gpt-4o"
    assert high_route.complexity == "high"
    assert high_route.provider == "claude"
    assert high_route.model == "claude-sonnet-4-5-20250929"
    assert high_route.risk_count == {"high": 3, "medium": 0, "low": 0}
    assert high_route.estimated_cost > medium_route.estimated_cost > low_route.estimated_cost


def test_yaml_loading_and_env_overrides(tmp_path, monkeypatch):
    """YAML routing config should load and env vars should override route entries."""
    config_path = tmp_path / "model_routing.yaml"
    config_path.write_text(
        """
complexity_thresholds:
  high: 0.8
  medium: 0.5
routing:
  high:
    provider: claude
    model: claude-sonnet-4-5-20250929
  medium:
    provider: openai
    model: gpt-4o
  low:
    provider: google
    model: gemini-2.0-flash
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("MODEL_ROUTER_LOW_PROVIDER", "openai")
    monkeypatch.setenv("MODEL_ROUTER_LOW_MODEL", "gpt-4o-mini")

    config = load_model_routing_config(config_path)

    assert config["complexity_thresholds"]["high"] == 0.8
    assert config["complexity_thresholds"]["medium"] == 0.5
    assert config["routing"]["low"]["provider"] == "openai"
    assert config["routing"]["low"]["model"] == "gpt-4o-mini"


def test_missing_yaml_uses_defaults():
    """Router config should work without a YAML file."""
    config = load_model_routing_config(Path("/missing/model_routing.yaml"))

    assert config["routing"]["high"]["provider"] == "claude"
    assert config["routing"]["medium"]["model"] == "gpt-4o"
    assert config["routing"]["low"]["model"] == "gpt-4o-mini"


def test_invalid_yaml_model_fails_validation(tmp_path):
    """Unknown model names should be rejected at config load time."""
    config_path = tmp_path / "model_routing.yaml"
    config_path.write_text(
        """
routing:
  low:
    provider: openai
    model: not-a-real-model
""",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Invalid model router model"):
        load_model_routing_config(config_path)


def test_route_handles_empty_subtask_and_unknown_work_type():
    """Empty subtasks and unknown work types should not crash scoring."""
    router = TaskComplexityRouter(config_path=Path("/missing/model_routing.yaml"))
    router.risk_analyzer = MagicMock()
    router.risk_analyzer.analyze_subtask_risks.return_value = []

    route = router.route({})
    score = router._calculate_complexity_score(
        work_types=["unknown_work_type"],
        risk_issues=[],
        subtask={},
    )

    assert route.complexity == "low"
    assert route.work_types == []
    assert score == pytest.approx(0.3)


def test_create_agent_session_without_subtask_keeps_existing_behavior(monkeypatch):
    """No-subtask calls should create a provider session without invoking routing."""
    from core.providers import factory

    class DummyProvider:
        name = "openai"

        def create_session(self, session_config):
            session = SimpleNamespace(client=object(), config=session_config)
            return session

    monkeypatch.setenv("AI_ENGINE_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-4o")

    with patch.object(
        factory.ProviderConfig,
        "from_env",
        return_value=ProviderConfig(provider="openai", openai_model="gpt-4o"),
    ) as from_env, patch.object(
        factory, "create_engine_provider", return_value=DummyProvider()
    ) as create_provider, patch(
        "core.providers.task_router.TaskComplexityRouter"
    ) as router_cls:
        session = factory.create_agent_session(
            agent_type="coder",
            project_dir=Path("/tmp/project"),
            spec_dir=Path("/tmp/project/.auto-claude/specs/001"),
        )

    from_env.assert_called_once_with(agent_type="coder")
    create_provider.assert_called_once()
    router_cls.assert_not_called()
    assert hasattr(session, "client")
    assert session.config.model is None


def test_create_agent_session_applies_route_when_subtask_provided():
    """A routed subtask should update provider config and session model."""
    from core.providers import factory

    class DummyProvider:
        name = "openai"

        def create_session(self, session_config):
            return SimpleNamespace(client=object(), config=session_config)

    route = SimpleNamespace(
        provider="openai",
        model="gpt-4o-mini",
        complexity="low",
        complexity_score=0.1,
        estimated_cost=0.00195,
        reasoning="low complexity",
    )
    router = MagicMock()
    router.route.return_value = route

    with patch.dict(os.environ, {}, clear=True), patch.object(
        factory.ProviderConfig,
        "from_env",
        return_value=ProviderConfig(provider="claude"),
    ), patch.object(
        factory, "create_engine_provider", return_value=DummyProvider()
    ) as create_provider, patch(
        "core.providers.task_router.TaskComplexityRouter", return_value=router
    ):
        session = factory.create_agent_session(
            agent_type="coder",
            project_dir=Path("/tmp/project"),
            spec_dir=Path("/tmp/project/.auto-claude/specs/001"),
            subtask={"description": "Fix typo"},
        )

    routed_config = create_provider.call_args.args[0]
    assert routed_config.provider == "openai"
    assert routed_config.openai_model == "gpt-4o-mini"
    assert session.config.model == "gpt-4o-mini"
