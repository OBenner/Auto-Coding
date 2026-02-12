#!/usr/bin/env python3
"""
End-to-End Tests for Multi-Model Agent Orchestration
=====================================================

Tests the complete flow of multi-model agent orchestration:
- Agent-specific model configuration via task_metadata.json
- Cost tracking across different models
- Model fallback when models are unavailable
- Environment variable overrides

Note: Uses temp_git_repo fixture from conftest.py for proper git isolation.
"""

import json
import logging
import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))


# =============================================================================
# TEST FIXTURES
# =============================================================================


@pytest.fixture
def test_env(temp_git_repo: Path):
    """Create a test environment using the shared temp_git_repo fixture.

    Yields:
        tuple: (temp_dir, spec_dir, project_dir)
    """
    temp_dir = temp_git_repo
    spec_dir = temp_dir / ".auto-claude" / "specs" / "024-multi-model-test"
    project_dir = temp_dir

    spec_dir.mkdir(parents=True, exist_ok=True)

    yield temp_dir, spec_dir, project_dir


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def create_task_metadata(spec_dir: Path, agent_models: dict[str, str] | None = None) -> Path:
    """Create a task_metadata.json with agentModels configuration."""
    metadata = {
        "taskDescription": "Test multi-model orchestration",
        "timestamp": "2026-01-27T00:00:00.000Z",
    }
    if agent_models:
        metadata["agentModels"] = agent_models

    metadata_file = spec_dir / "task_metadata.json"
    metadata_file.write_text(json.dumps(metadata, indent=2))
    return metadata_file


def get_cost_report(spec_dir: Path) -> dict:
    """Load cost_report.json from spec directory."""
    cost_report_file = spec_dir / "cost_report.json"
    if not cost_report_file.exists():
        return {}
    return json.loads(cost_report_file.read_text())


# =============================================================================
# AGENT MODEL RESOLUTION TESTS
# =============================================================================


class TestAgentModelResolution:
    """Tests for agent-specific model resolution."""

    def test_get_agent_model_uses_task_metadata(self, test_env):
        """Test that get_agent_model() uses agentModels from task_metadata.json."""
        from phase_config import get_agent_model

        temp_dir, spec_dir, project_dir = test_env

        # Create task_metadata.json with custom agent models
        create_task_metadata(
            spec_dir,
            agent_models={
                "coder": "haiku",
                "planner": "opus",
                "qa_reviewer": "sonnet",
            },
        )

        # Verify each agent gets the correct model
        coder_model = get_agent_model(spec_dir, "coder")
        assert "haiku" in coder_model, f"Coder should use haiku, got {coder_model}"

        planner_model = get_agent_model(spec_dir, "planner")
        assert "opus" in planner_model, f"Planner should use opus, got {planner_model}"

        qa_model = get_agent_model(spec_dir, "qa_reviewer")
        assert "sonnet" in qa_model, f"QA reviewer should use sonnet, got {qa_model}"

    def test_get_agent_model_uses_defaults_when_no_config(self, test_env):
        """Test that get_agent_model() falls back to defaults without task_metadata.json."""
        from phase_config import get_agent_model, AGENT_DEFAULT_MODELS

        temp_dir, spec_dir, project_dir = test_env

        # No task_metadata.json created

        # Should use default from AGENT_DEFAULT_MODELS
        coder_model = get_agent_model(spec_dir, "coder")
        expected_default = AGENT_DEFAULT_MODELS["coder"]
        assert (
            expected_default.lower() in coder_model.lower()
        ), f"Should use default {expected_default}, got {coder_model}"

    def test_get_agent_model_cli_override(self, test_env):
        """Test that CLI model argument overrides task_metadata.json."""
        from phase_config import get_agent_model

        temp_dir, spec_dir, project_dir = test_env

        # Create task_metadata with coder=haiku
        create_task_metadata(spec_dir, agent_models={"coder": "haiku"})

        # CLI override with opus
        coder_model = get_agent_model(spec_dir, "coder", cli_model="opus")
        assert "opus" in coder_model, f"CLI override should use opus, got {coder_model}"

    def test_get_agent_model_env_var_override(self, test_env, monkeypatch):
        """Test that environment variable overrides task_metadata.json."""
        from phase_config import get_agent_model

        temp_dir, spec_dir, project_dir = test_env

        # Create task_metadata with coder=sonnet
        create_task_metadata(spec_dir, agent_models={"coder": "sonnet"})

        # Set environment variable override
        monkeypatch.setenv("AGENT_MODEL_CODER", "haiku")

        # Should use environment variable
        coder_model = get_agent_model(spec_dir, "coder")
        assert "haiku" in coder_model, f"Env var override should use haiku, got {coder_model}"

    def test_agent_model_priority_resolution(self, test_env, monkeypatch):
        """Test priority: CLI > env var > task_metadata > defaults."""
        from phase_config import get_agent_model

        temp_dir, spec_dir, project_dir = test_env

        # Setup: task_metadata=haiku, env var=sonnet, CLI=opus
        create_task_metadata(spec_dir, agent_models={"planner": "haiku"})
        monkeypatch.setenv("AGENT_MODEL_PLANNER", "sonnet")

        # Test 1: CLI overrides everything
        model = get_agent_model(spec_dir, "planner", cli_model="opus")
        assert "opus" in model, f"CLI should override everything, got {model}"

        # Test 2: Without CLI, env var overrides task_metadata
        model = get_agent_model(spec_dir, "planner")
        assert "sonnet" in model, f"Env var should override task_metadata, got {model}"

        # Test 3: Without env var, use task_metadata
        monkeypatch.delenv("AGENT_MODEL_PLANNER", raising=False)
        model = get_agent_model(spec_dir, "planner")
        assert "haiku" in model, f"Should use task_metadata, got {model}"


# =============================================================================
# COST TRACKING TESTS
# =============================================================================


class TestCostTracking:
    """Tests for cost tracking across different models."""

    def test_cost_tracker_creates_cost_report(self, test_env):
        """Test that CostTracker creates cost_report.json."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        tracker = CostTracker(spec_dir=spec_dir)

        # Log some usage
        tracker.log_usage(
            agent_type="coder",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=500,
        )

        # Verify cost_report.json exists
        cost_report_file = spec_dir / "cost_report.json"
        assert cost_report_file.exists(), "cost_report.json should be created"

        # Verify structure
        cost_report = get_cost_report(spec_dir)
        assert "total_cost" in cost_report, "Should have total_cost field"
        assert "records" in cost_report, "Should have records field"
        assert len(cost_report["records"]) == 1, "Should have 1 record"

    def test_cost_tracker_calculates_correctly(self, test_env):
        """Test that cost calculations are accurate."""
        from core.cost_tracking import CostTracker, MODEL_PRICING

        temp_dir, spec_dir, project_dir = test_env

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for sonnet
        model = "claude-sonnet-4-5-20250929"
        input_tokens = 1000
        output_tokens = 500

        tracker.log_usage(
            agent_type="coder",
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )

        # Calculate expected cost
        pricing = MODEL_PRICING[model]
        expected_cost = (input_tokens / 1_000_000 * pricing["input"]) + (
            output_tokens / 1_000_000 * pricing["output"]
        )

        # Verify cost
        cost_report = get_cost_report(spec_dir)
        actual_cost = cost_report["total_cost"]
        assert abs(actual_cost - expected_cost) < 0.001, (
            f"Cost mismatch: expected {expected_cost:.6f}, got {actual_cost:.6f}"
        )

    def test_cost_tracker_tracks_multiple_agents(self, test_env):
        """Test tracking costs for multiple agent types."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for different agents
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 1000, 500)
        tracker.log_usage("planner", "claude-opus-4-5-20251101", 2000, 1000)
        tracker.log_usage("qa_reviewer", "claude-haiku-4-5-20251001", 500, 250)

        # Verify all records are tracked
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 3, "Should have 3 records"

        # Verify agents are tracked
        agent_types = [r["agent_type"] for r in cost_report["records"]]
        assert "coder" in agent_types, "Should track coder"
        assert "planner" in agent_types, "Should track planner"
        assert "qa_reviewer" in agent_types, "Should track qa_reviewer"

    def test_cost_summary_breakdown_by_agent(self, test_env):
        """Test get_cost_summary() provides breakdown by agent type."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for different agents
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 10000, 5000)
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 5000, 2500)
        tracker.log_usage("planner", "claude-opus-4-5-20251101", 1000, 500)

        # Get summary
        summary = tracker.get_cost_summary()

        # Verify summary contains breakdown
        assert "Cost by Agent Type" in summary, "Should have agent breakdown"
        assert "coder" in summary, "Should show coder costs"
        assert "planner" in summary, "Should show planner costs"

    def test_cost_summary_breakdown_by_model(self, test_env):
        """Test get_cost_summary() provides breakdown by model."""
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        tracker = CostTracker(spec_dir=spec_dir)

        # Log usage for different models
        tracker.log_usage("coder", "claude-sonnet-4-5-20250929", 10000, 5000)
        tracker.log_usage("planner", "claude-opus-4-5-20251101", 5000, 2500)
        tracker.log_usage("qa_reviewer", "claude-haiku-4-5-20251001", 20000, 10000)

        # Get summary
        summary = tracker.get_cost_summary()

        # Verify summary contains model breakdown
        assert "Cost by Model" in summary, "Should have model breakdown"
        # Models might be abbreviated in summary
        assert any(
            model_name in summary
            for model_name in ["sonnet", "opus", "haiku", "claude-sonnet", "claude-opus", "claude-haiku"]
        ), "Should show model costs"


# =============================================================================
# MODEL FALLBACK TESTS
# =============================================================================


class TestModelFallback:
    """Tests for model fallback when models are unavailable."""

    def test_fallback_chain_defined(self, test_env):
        """Test that MODEL_FALLBACK_CHAIN is properly defined."""
        from core.model_fallback import MODEL_FALLBACK_CHAIN

        temp_dir, spec_dir, project_dir = test_env

        # Verify fallback chain exists
        assert "opus" in MODEL_FALLBACK_CHAIN, "Should have opus fallback chain"
        assert "sonnet" in MODEL_FALLBACK_CHAIN, "Should have sonnet fallback chain"
        assert "haiku" in MODEL_FALLBACK_CHAIN, "Should have haiku fallback chain"

        # Verify opus degrades to sonnet -> haiku
        assert MODEL_FALLBACK_CHAIN["opus"] == [
            "sonnet",
            "haiku",
        ], "Opus should fallback to sonnet -> haiku"

    def test_retry_with_fallback_function_exists(self, test_env):
        """Test that retry_with_fallback() function is implemented."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Function should be importable and callable
        assert callable(retry_with_fallback), "retry_with_fallback should be callable"

    def test_fallback_logging(self, test_env, caplog):
        """Test that fallback attempts are logged."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that fails once then succeeds
        call_count = 0

        def mock_fn(model: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call with opus fails (must be a retryable error)
                raise Exception("Rate limit exceeded - too many requests")
            # Second call with sonnet succeeds
            return f"Success with {model}"

        # Capture logs
        with caplog.at_level(logging.INFO):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Verify fallback occurred
        assert result is not None, "Should eventually succeed"
        assert "sonnet" in str(result).lower(), "Should have fallen back to sonnet"

        # Verify logging
        log_messages = caplog.text
        assert any(
            "fallback" in msg.lower() or "retry" in msg.lower() for msg in log_messages.split("\n")
        ), "Should log fallback attempts"

    def test_fallback_on_rate_limit_error(self, test_env, caplog):
        """Test that rate limit errors trigger fallback to degraded model."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that simulates rate limit error
        call_count = 0

        def mock_fn(model: str):
            nonlocal call_count
            call_count += 1
            if "opus" in model.lower():
                # Simulate rate limit error (429 Too Many Requests)
                raise Exception("RateLimitError: 429 Too Many Requests")
            # Fallback to sonnet succeeds
            return f"Success with {model}"

        # Capture logs at WARNING level to see fallback messages
        with caplog.at_level(logging.WARNING):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Verify fallback occurred
        assert "sonnet" in str(result).lower(), f"Should fall back to sonnet, got: {result}"

        # Verify fallback logging with [FALLBACK] tag
        log_messages = caplog.text
        assert "[FALLBACK]" in log_messages, "Should log with [FALLBACK] tag"
        assert "sonnet" in log_messages.lower(), "Should mention sonnet in logs"

    def test_fallback_on_connection_error(self, test_env, caplog):
        """Test that connection errors trigger fallback."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that simulates connection error
        def mock_fn(model: str):
            if "opus" in model.lower():
                raise ConnectionError("Connection timeout")
            return f"Success with {model}"

        with caplog.at_level(logging.WARNING):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Should fall back to sonnet
        assert "sonnet" in str(result).lower(), "Should fall back to sonnet"
        assert "[FALLBACK]" in caplog.text, "Should log fallback"

    def test_fallback_on_server_overload(self, test_env, caplog):
        """Test that server overload errors (503) trigger fallback."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that simulates server overload
        def mock_fn(model: str):
            if "opus" in model.lower():
                raise Exception("503 Service Temporarily Unavailable - Server overloaded")
            return f"Success with {model}"

        with caplog.at_level(logging.WARNING):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Should fall back to sonnet
        assert "sonnet" in str(result).lower(), "Should fall back to sonnet"
        assert "[FALLBACK]" in caplog.text, "Should log fallback"

    def test_non_retryable_error_raises_immediately(self, test_env, caplog):
        """Test that non-retryable errors don't trigger fallback."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that raises non-retryable error
        def mock_fn(model: str):
            # Validation error is not retryable
            raise ValueError("Invalid request format")

        # Non-retryable errors should raise immediately without fallback
        with pytest.raises(ValueError, match="Invalid request format"):
            retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Should not log fallback (error should be raised immediately)
        log_messages = caplog.text
        assert "[FALLBACK]" not in log_messages, "Should not attempt fallback for non-retryable errors"

    def test_fallback_chain_opus_to_haiku(self, test_env, caplog):
        """Test complete fallback chain: opus -> sonnet -> haiku."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that fails for opus and sonnet, succeeds with haiku
        def mock_fn(model: str):
            if "opus" in model.lower():
                raise Exception("RateLimitError: opus unavailable")
            elif "sonnet" in model.lower():
                raise Exception("RateLimitError: sonnet unavailable")
            # Haiku succeeds
            return f"Success with {model}"

        with caplog.at_level(logging.WARNING):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Should eventually fall back to haiku
        assert "haiku" in str(result).lower(), f"Should fall back to haiku, got: {result}"

        # Verify logging shows both fallback attempts
        log_messages = caplog.text
        assert log_messages.count("[FALLBACK]") >= 2, "Should log both fallback attempts (opus->sonnet, sonnet->haiku)"

    def test_fallback_exhausted_all_models(self, test_env, caplog):
        """Test that all models exhausted raises final exception."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that fails for all models
        def mock_fn(model: str):
            raise Exception(f"RateLimitError: {model} unavailable")

        # Should exhaust all models and raise final exception
        with pytest.raises(Exception, match="unavailable"):
            retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Verify [EXHAUSTED] or [FAILED] tag in logs
        log_messages = caplog.text
        assert "[FAILED]" in log_messages or "[EXHAUSTED]" in log_messages, (
            "Should log when all models exhausted"
        )

    def test_fallback_max_retries_per_model(self, test_env, caplog):
        """Test that max_retries_per_model is respected."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that counts retries
        retry_counts = {"opus": 0, "sonnet": 0}

        def mock_fn(model: str):
            model_key = "opus" if "opus" in model.lower() else "sonnet"
            retry_counts[model_key] += 1

            if retry_counts[model_key] <= 2:
                # Fail first 2 attempts
                raise Exception("RateLimitError: temporarily unavailable")
            # Succeed on 3rd attempt
            return f"Success with {model} after {retry_counts[model_key]} attempts"

        with caplog.at_level(logging.WARNING):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=3)

        # Should succeed after retries
        assert "Success" in str(result), f"Should eventually succeed, got: {result}"

        # Verify retry logging with [RETRY] tag
        log_messages = caplog.text
        assert "[RETRY]" in log_messages, "Should log retry attempts"

    def test_fallback_sonnet_to_haiku(self, test_env, caplog):
        """Test fallback chain from sonnet (not opus)."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Start with sonnet, fall back to haiku
        def mock_fn(model: str):
            if "sonnet" in model.lower():
                raise Exception("RateLimitError: sonnet unavailable")
            return f"Success with {model}"

        with caplog.at_level(logging.WARNING):
            result = retry_with_fallback(mock_fn, "sonnet", max_retries_per_model=1)

        # Should fall back to haiku
        assert "haiku" in str(result).lower(), "Should fall back to haiku"
        assert "[FALLBACK]" in caplog.text, "Should log fallback"

    def test_fallback_haiku_no_fallback(self, test_env, caplog):
        """Test that haiku has no fallback (final model in chain)."""
        from core.model_fallback import retry_with_fallback, MODEL_FALLBACK_CHAIN

        temp_dir, spec_dir, project_dir = test_env

        # Verify haiku has no fallback
        assert MODEL_FALLBACK_CHAIN["haiku"] == [], "Haiku should have no fallback"

        # Mock function that always fails
        def mock_fn(model: str):
            raise Exception("RateLimitError: model unavailable")

        # Should raise after exhausting haiku (no fallback)
        with pytest.raises(Exception, match="unavailable"):
            retry_with_fallback(mock_fn, "haiku", max_retries_per_model=1)

    def test_fallback_success_logging(self, test_env, caplog):
        """Test that successful fallback logs [SUCCESS] tag."""
        from core.model_fallback import retry_with_fallback

        temp_dir, spec_dir, project_dir = test_env

        # Mock function that fails once then succeeds
        def mock_fn(model: str):
            if "opus" in model.lower():
                raise Exception("RateLimitError: opus unavailable")
            return f"Success with {model}"

        with caplog.at_level(logging.INFO):
            result = retry_with_fallback(mock_fn, "opus", max_retries_per_model=1)

        # Verify success logging
        assert "Success" in str(result), "Should succeed"
        log_messages = caplog.text
        assert "[SUCCESS]" in log_messages, "Should log success with [SUCCESS] tag"


# =============================================================================
# END-TO-END INTEGRATION TESTS
# =============================================================================


class TestE2EMultiModelOrchestration:
    """End-to-end tests for complete multi-model orchestration flow."""

    def test_e2e_custom_agent_models_with_cost_tracking(self, test_env):
        """
        E2E Test: Create spec with custom agent models and verify:
        1. task_metadata.json with agentModels configuration
        2. Correct model is resolved for each agent
        3. cost_report.json is created with tracking data
        4. Logs show model selection process
        """
        from phase_config import get_agent_model
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        # Step 1: Create task_metadata.json with custom agent models
        custom_agent_models = {
            "planner": "opus",  # Use most capable model for planning
            "coder": "sonnet",  # Balanced model for coding
            "qa_reviewer": "haiku",  # Fast model for QA
        }
        create_task_metadata(spec_dir, agent_models=custom_agent_models)

        # Verify task_metadata.json was created
        metadata_file = spec_dir / "task_metadata.json"
        assert metadata_file.exists(), "task_metadata.json should be created"
        metadata = json.loads(metadata_file.read_text())
        assert "agentModels" in metadata, "Should have agentModels field"
        assert metadata["agentModels"]["planner"] == "opus", "Planner should be opus"

        # Step 2: Verify correct models are used for each agent
        planner_model = get_agent_model(spec_dir, "planner")
        assert "opus" in planner_model, f"Planner should use opus, got {planner_model}"

        coder_model = get_agent_model(spec_dir, "coder")
        assert "sonnet" in coder_model, f"Coder should use sonnet, got {coder_model}"

        qa_model = get_agent_model(spec_dir, "qa_reviewer")
        assert "haiku" in qa_model, f"QA reviewer should use haiku, got {qa_model}"

        # Step 3: Simulate agent sessions and track costs
        tracker = CostTracker(spec_dir=spec_dir)

        # Simulate planner agent (opus)
        tracker.log_usage(
            agent_type="planner",
            model=planner_model,
            input_tokens=5000,
            output_tokens=2000,
        )

        # Simulate coder agent (sonnet)
        tracker.log_usage(
            agent_type="coder",
            model=coder_model,
            input_tokens=10000,
            output_tokens=5000,
        )

        # Simulate QA agent (haiku)
        tracker.log_usage(
            agent_type="qa_reviewer",
            model=qa_model,
            input_tokens=3000,
            output_tokens=1000,
        )

        # Step 4: Verify cost_report.json is created with correct data
        cost_report = get_cost_report(spec_dir)
        assert cost_report, "cost_report.json should exist"
        assert "total_cost" in cost_report, "Should have total_cost"
        assert "records" in cost_report, "Should have records"
        assert len(cost_report["records"]) == 3, "Should have 3 usage records"

        # Verify each agent's usage is tracked
        agent_types = {r["agent_type"] for r in cost_report["records"]}
        assert agent_types == {
            "planner",
            "coder",
            "qa_reviewer",
        }, "Should track all agent types"

        # Verify models are tracked correctly
        models = {r["model"] for r in cost_report["records"]}
        assert any("opus" in m for m in models), "Should track opus usage"
        assert any("sonnet" in m for m in models), "Should track sonnet usage"
        assert any("haiku" in m for m in models), "Should track haiku usage"

        # Verify total cost is positive
        assert cost_report["total_cost"] > 0, "Total cost should be positive"

        # Step 5: Verify cost summary is generated correctly
        summary = tracker.get_cost_summary()
        assert summary, "Should generate cost summary"
        assert "Total Cost" in summary, "Summary should show total cost"
        assert "Cost by Agent Type" in summary, "Summary should show breakdown by agent"
        assert "Cost by Model" in summary, "Summary should show breakdown by model"

    def test_e2e_environment_variable_override(self, test_env, monkeypatch):
        """Test that environment variables override task_metadata.json."""
        from phase_config import get_agent_model
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        # Create task_metadata with coder=sonnet
        create_task_metadata(spec_dir, agent_models={"coder": "sonnet"})

        # Override with environment variable
        monkeypatch.setenv("AGENT_MODEL_CODER", "haiku")

        # Verify environment variable takes precedence
        coder_model = get_agent_model(spec_dir, "coder")
        assert "haiku" in coder_model, f"Env var should override, got {coder_model}"

        # Simulate and track usage
        tracker = CostTracker(spec_dir=spec_dir)
        tracker.log_usage("coder", coder_model, 1000, 500)

        # Verify haiku model is tracked
        cost_report = get_cost_report(spec_dir)
        coder_record = next(r for r in cost_report["records"] if r["agent_type"] == "coder")
        assert "haiku" in coder_record["model"], "Should track haiku model"

    def test_e2e_default_models_when_no_config(self, test_env):
        """Test that default models are used when no configuration exists."""
        from phase_config import get_agent_model, AGENT_DEFAULT_MODELS
        from core.cost_tracking import CostTracker

        temp_dir, spec_dir, project_dir = test_env

        # No task_metadata.json created

        # Get default models
        coder_default = AGENT_DEFAULT_MODELS["coder"]
        planner_default = AGENT_DEFAULT_MODELS["planner"]

        # Verify defaults are used
        coder_model = get_agent_model(spec_dir, "coder")
        assert coder_default.lower() in coder_model.lower(), (
            f"Should use default {coder_default}, got {coder_model}"
        )

        planner_model = get_agent_model(spec_dir, "planner")
        assert planner_default.lower() in planner_model.lower(), (
            f"Should use default {planner_default}, got {planner_model}"
        )

        # Track usage with defaults
        tracker = CostTracker(spec_dir=spec_dir)
        tracker.log_usage("coder", coder_model, 1000, 500)
        tracker.log_usage("planner", planner_model, 2000, 1000)

        # Verify tracking works with defaults
        cost_report = get_cost_report(spec_dir)
        assert len(cost_report["records"]) == 2, "Should track both agents"


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================


def run_all_tests():
    """Run all tests using pytest."""
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))


if __name__ == "__main__":
    run_all_tests()
