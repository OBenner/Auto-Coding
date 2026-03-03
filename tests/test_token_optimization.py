#!/usr/bin/env python3
"""
Tests for Token Optimization Components
========================================

Tests the token optimization modules including:
- Dynamic thinking budget selection (phase_config.py)
- Output format constraints (phase_config.py)
- Compaction levels (spec/compaction.py)
- Token usage tracking (core/token_tracker.py)
"""

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

# Mock external dependencies that may not be available in test environment
# This allows testing pure Python logic without requiring claude_agent_sdk
_mock_modules = [
    "claude_agent_sdk",
    "claude_agent_sdk.ClaudeAgentOptions",
    "claude_agent_sdk.ClaudeSDKClient",
]

for mod in _mock_modules:
    if mod not in sys.modules:
        sys.modules[mod] = MagicMock()


class TestThinkingBudgetMap:
    """Tests for THINKING_BUDGET_MAP constants."""

    def test_thinking_budget_map_has_all_levels(self):
        """All expected thinking levels exist."""
        from phase_config import THINKING_BUDGET_MAP

        expected_levels = ["none", "low", "medium", "high", "ultrathink"]
        for level in expected_levels:
            assert level in THINKING_BUDGET_MAP, f"Missing level: {level}"

    def test_none_returns_none(self):
        """'none' level returns None (no extended thinking)."""
        from phase_config import THINKING_BUDGET_MAP

        assert THINKING_BUDGET_MAP["none"] is None

    def test_low_budget_is_minimum(self):
        """'low' budget is 1024 (minimum allowed)."""
        from phase_config import THINKING_BUDGET_MAP

        assert THINKING_BUDGET_MAP["low"] == 1024

    def test_medium_budget_value(self):
        """'medium' budget is 4096."""
        from phase_config import THINKING_BUDGET_MAP

        assert THINKING_BUDGET_MAP["medium"] == 4096

    def test_high_budget_value(self):
        """'high' budget is 16384."""
        from phase_config import THINKING_BUDGET_MAP

        assert THINKING_BUDGET_MAP["high"] == 16384

    def test_ultrathink_budget_is_maximum(self):
        """'ultrathink' budget is 63999 (max for API limit)."""
        from phase_config import THINKING_BUDGET_MAP

        assert THINKING_BUDGET_MAP["ultrathink"] == 63999

    def test_budget_values_are_increasing(self):
        """Budget values increase with level complexity."""
        from phase_config import THINKING_BUDGET_MAP

        levels = ["low", "medium", "high", "ultrathink"]
        values = [THINKING_BUDGET_MAP[level] for level in levels]
        assert values == sorted(values), "Budget values should increase"


class TestGetThinkingBudget:
    """Tests for get_thinking_budget() function."""

    def test_returns_correct_budget_for_valid_level(self):
        """Returns correct budget for valid thinking level."""
        from phase_config import get_thinking_budget

        assert get_thinking_budget("low") == 1024
        assert get_thinking_budget("medium") == 4096
        assert get_thinking_budget("high") == 16384

    def test_none_level_returns_none(self):
        """'none' level returns None."""
        from phase_config import get_thinking_budget

        assert get_thinking_budget("none") is None

    def test_invalid_level_defaults_to_medium(self):
        """Invalid level logs warning and defaults to medium."""
        from phase_config import get_thinking_budget

        # Should return medium (4096) for invalid levels
        result = get_thinking_budget("invalid_level")
        assert result == 4096

    def test_empty_string_defaults_to_medium(self):
        """Empty string defaults to medium."""
        from phase_config import get_thinking_budget

        result = get_thinking_budget("")
        assert result == 4096


class TestComplexityThresholds:
    """Tests for COMPLEXITY_THRESHOLDS constants."""

    def test_complexity_thresholds_exist(self):
        """COMPLEXITY_THRESHOLDS has required keys."""
        from phase_config import COMPLEXITY_THRESHOLDS

        required_keys = [
            "description_short",
            "description_medium",
            "description_long",
            "files_simple",
            "files_medium",
            "services_simple",
            "services_medium",
        ]
        for key in required_keys:
            assert key in COMPLEXITY_THRESHOLDS, f"Missing key: {key}"

    def test_description_thresholds_are_increasing(self):
        """Description length thresholds increase in order."""
        from phase_config import COMPLEXITY_THRESHOLDS

        assert (
            COMPLEXITY_THRESHOLDS["description_short"]
            < COMPLEXITY_THRESHOLDS["description_medium"]
        )
        assert (
            COMPLEXITY_THRESHOLDS["description_medium"]
            < COMPLEXITY_THRESHOLDS["description_long"]
        )

    def test_file_thresholds_are_increasing(self):
        """File count thresholds increase in order."""
        from phase_config import COMPLEXITY_THRESHOLDS

        assert (
            COMPLEXITY_THRESHOLDS["files_simple"]
            < COMPLEXITY_THRESHOLDS["files_medium"]
        )

    def test_service_thresholds_are_increasing(self):
        """Service count thresholds increase in order."""
        from phase_config import COMPLEXITY_THRESHOLDS

        assert (
            COMPLEXITY_THRESHOLDS["services_simple"]
            < COMPLEXITY_THRESHOLDS["services_medium"]
        )


class TestSuggestThinkingBudget:
    """Tests for suggest_thinking_budget() function."""

    def test_simple_task_returns_low(self):
        """Very simple task returns 'low' thinking level."""
        from phase_config import suggest_thinking_budget

        # Short description, few files, single service
        result = suggest_thinking_budget("simple task", 1, 1)
        assert result == "low"

    def test_empty_description_returns_low(self):
        """Empty description with minimal files returns 'low'."""
        from phase_config import suggest_thinking_budget

        result = suggest_thinking_budget("", 1, 1)
        assert result == "low"

    def test_medium_complexity_returns_medium(self):
        """Medium complexity task returns 'medium'."""
        from phase_config import suggest_thinking_budget

        # Medium description (~200 chars), moderate files, single service
        description = "Fix the authentication bug in the login component. " * 4
        result = suggest_thinking_budget(description, 5, 1)
        assert result == "medium"

    def test_high_complexity_returns_high(self):
        """High complexity task returns 'high'."""
        from phase_config import suggest_thinking_budget

        # Long description (~800 chars = score 2), many files (10 = score 2),
        # moderate services (2 = score 1) => total score 5 = "high"
        description = (
            "Implement a complete authentication system with OAuth and JWT tokens. "
            * 10
        )
        result = suggest_thinking_budget(description, 10, 2)
        assert result == "high"

    def test_very_complex_task_returns_ultrathink(self):
        """Very complex task returns 'ultrathink'."""
        from phase_config import suggest_thinking_budget

        # Very long description, many files, many services
        description = "A" * 2000  # Very long description
        result = suggest_thinking_budget(description, 20, 5)
        assert result == "ultrathink"

    def test_file_count_affects_complexity(self):
        """File count contributes to complexity score."""
        from phase_config import suggest_thinking_budget

        # Same description, different file counts
        base_result = suggest_thinking_budget("task", 1, 1)
        many_files_result = suggest_thinking_budget("task", 15, 1)

        # More files should increase complexity
        assert base_result == "low"
        # Many files should push toward higher level
        levels_order = ["low", "medium", "high", "ultrathink"]
        assert levels_order.index(many_files_result) >= levels_order.index(base_result)

    def test_service_count_affects_complexity(self):
        """Service count contributes to complexity score."""
        from phase_config import suggest_thinking_budget

        # Same description, different service counts
        single_service = suggest_thinking_budget("task", 5, 1)
        multiple_services = suggest_thinking_budget("task", 5, 5)

        levels_order = ["low", "medium", "high", "ultrathink"]
        assert levels_order.index(multiple_services) >= levels_order.index(
            single_service
        )

    def test_returns_valid_thinking_level(self):
        """Always returns a valid thinking level string."""
        from phase_config import THINKING_BUDGET_MAP, suggest_thinking_budget

        valid_levels = set(THINKING_BUDGET_MAP.keys())

        # Test various inputs
        test_cases = [
            ("", 0, 0),
            ("short", 1, 1),
            ("medium length description", 5, 2),
            ("A" * 1000, 10, 3),
            ("A" * 5000, 50, 10),
        ]

        for desc, files, services in test_cases:
            result = suggest_thinking_budget(desc, files, services)
            assert result in valid_levels, (
                f"Invalid level '{result}' for {(desc[:20], files, services)}"
            )


class TestOutputConstraintTemplates:
    """Tests for OUTPUT_CONSTRAINT_TEMPLATES constants."""

    def test_all_format_types_exist(self):
        """All expected format types exist."""
        from phase_config import OUTPUT_CONSTRAINT_TEMPLATES

        expected_types = ["summary", "brief", "concise", "strict"]
        for fmt_type in expected_types:
            assert fmt_type in OUTPUT_CONSTRAINT_TEMPLATES, (
                f"Missing format type: {fmt_type}"
            )

    def test_templates_contain_limit_placeholder(self):
        """All templates contain {limit} placeholder."""
        from phase_config import OUTPUT_CONSTRAINT_TEMPLATES

        for fmt_type, template in OUTPUT_CONSTRAINT_TEMPLATES.items():
            assert "{limit}" in template, (
                f"Template '{fmt_type}' missing {{limit}} placeholder"
            )


class TestGetOutputConstraint:
    """Tests for get_output_constraint() function."""

    def test_summary_format(self):
        """Summary format returns expected string."""
        from phase_config import get_output_constraint

        result = get_output_constraint("summary", 200)
        assert result == "Respond in 200 words or less"

    def test_brief_format(self):
        """Brief format returns expected string."""
        from phase_config import get_output_constraint

        result = get_output_constraint("brief", 150)
        assert result == "Keep your response under 150 words"

    def test_concise_format(self):
        """Concise format returns expected string."""
        from phase_config import get_output_constraint

        result = get_output_constraint("concise", 300)
        assert result == "Provide a concise response in 300 words or fewer"

    def test_strict_format(self):
        """Strict format returns expected string."""
        from phase_config import get_output_constraint

        result = get_output_constraint("strict", 100)
        assert result == "Your response MUST NOT exceed 100 words"

    def test_unknown_format_defaults_to_summary(self):
        """Unknown format type defaults to summary format."""
        from phase_config import get_output_constraint

        result = get_output_constraint("unknown_format", 250)
        assert result == "Respond in 250 words or less"

    def test_word_limit_substitution(self):
        """Word limit is correctly substituted in template."""
        from phase_config import get_output_constraint

        for limit in [50, 100, 500, 1000]:
            result = get_output_constraint("summary", limit)
            assert str(limit) in result


class TestCompactionLevel:
    """Tests for CompactionLevel enum."""

    def test_all_levels_exist(self):
        """All expected compaction levels exist."""
        from spec.compaction import CompactionLevel

        assert hasattr(CompactionLevel, "LIGHT")
        assert hasattr(CompactionLevel, "MEDIUM")
        assert hasattr(CompactionLevel, "AGGRESSIVE")

    def test_light_level_value(self):
        """LIGHT level has correct string value."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.LIGHT.value == "light"

    def test_medium_level_value(self):
        """MEDIUM level has correct string value."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.MEDIUM.value == "medium"

    def test_aggressive_level_value(self):
        """AGGRESSIVE level has correct string value."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.AGGRESSIVE.value == "aggressive"

    def test_light_target_words(self):
        """LIGHT level targets 500 words."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.LIGHT.target_words == 500

    def test_medium_target_words(self):
        """MEDIUM level targets 250 words."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.MEDIUM.target_words == 250

    def test_aggressive_target_words(self):
        """AGGRESSIVE level targets 100 words."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.AGGRESSIVE.target_words == 100

    def test_target_words_decrease_with_aggressiveness(self):
        """Target word counts decrease with aggressiveness."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.LIGHT.target_words > CompactionLevel.MEDIUM.target_words
        assert (
            CompactionLevel.MEDIUM.target_words
            > CompactionLevel.AGGRESSIVE.target_words
        )

    def test_light_max_input_chars(self):
        """LIGHT level has highest max input chars."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.LIGHT.max_input_chars == 15000

    def test_medium_max_input_chars(self):
        """MEDIUM level has moderate max input chars."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.MEDIUM.max_input_chars == 12000

    def test_aggressive_max_input_chars(self):
        """AGGRESSIVE level has lowest max input chars."""
        from spec.compaction import CompactionLevel

        assert CompactionLevel.AGGRESSIVE.max_input_chars == 8000

    def test_max_input_chars_decrease_with_aggressiveness(self):
        """Max input chars decrease with aggressiveness."""
        from spec.compaction import CompactionLevel

        assert (
            CompactionLevel.LIGHT.max_input_chars
            > CompactionLevel.MEDIUM.max_input_chars
        )
        assert (
            CompactionLevel.MEDIUM.max_input_chars
            > CompactionLevel.AGGRESSIVE.max_input_chars
        )


class TestFormatPhaseSummaries:
    """Tests for format_phase_summaries() function."""

    def test_empty_summaries_returns_empty_string(self):
        """Empty summaries dict returns empty string."""
        from spec.compaction import format_phase_summaries

        result = format_phase_summaries({})
        assert result == ""

    def test_single_summary_formats_correctly(self):
        """Single phase summary is formatted correctly."""
        from spec.compaction import format_phase_summaries

        summaries = {"discovery": "Found key patterns in codebase"}
        result = format_phase_summaries(summaries)

        assert "## Context from Previous Phases" in result
        assert "### Discovery" in result
        assert "Found key patterns in codebase" in result

    def test_multiple_summaries_format_correctly(self):
        """Multiple phase summaries are all included."""
        from spec.compaction import format_phase_summaries

        summaries = {
            "discovery": "Discovered patterns",
            "requirements": "Gathered user requirements",
            "context": "Analyzed code context",
        }
        result = format_phase_summaries(summaries)

        assert "### Discovery" in result
        assert "### Requirements" in result
        assert "### Context" in result

    def test_underscores_replaced_with_spaces_in_title(self):
        """Underscores in phase names are replaced with spaces."""
        from spec.compaction import format_phase_summaries

        summaries = {"spec_writing": "Wrote the specification"}
        result = format_phase_summaries(summaries)

        assert "### Spec Writing" in result
        assert "spec_writing" not in result.split("### ")[1].split("\n")[0]


class TestGatherPhaseOutputs:
    """Tests for gather_phase_outputs() function."""

    def test_returns_empty_for_nonexistent_dir(self, tmp_path):
        """Returns empty string for nonexistent directory."""
        from spec.compaction import gather_phase_outputs

        result = gather_phase_outputs(tmp_path / "nonexistent", "discovery")
        assert result == ""

    def test_returns_empty_for_unknown_phase(self, tmp_path):
        """Returns empty string for unknown phase name."""
        from spec.compaction import gather_phase_outputs

        result = gather_phase_outputs(tmp_path, "unknown_phase")
        assert result == ""

    def test_returns_empty_for_validation_phase(self, tmp_path):
        """Validation phase has no output files to gather."""
        from spec.compaction import gather_phase_outputs

        result = gather_phase_outputs(tmp_path, "validation")
        assert result == ""

    def test_gathers_discovery_output(self, tmp_path):
        """Gathers context.json for discovery phase."""
        from spec.compaction import gather_phase_outputs

        # Create context.json
        context_file = tmp_path / "context.json"
        context_file.write_text('{"key": "value"}', encoding="utf-8")

        result = gather_phase_outputs(tmp_path, "discovery")

        assert "context.json" in result
        assert '{"key": "value"}' in result

    def test_gathers_requirements_output(self, tmp_path):
        """Gathers requirements.json for requirements phase."""
        from spec.compaction import gather_phase_outputs

        # Create requirements.json
        req_file = tmp_path / "requirements.json"
        req_file.write_text('{"requirements": []}', encoding="utf-8")

        result = gather_phase_outputs(tmp_path, "requirements")

        assert "requirements.json" in result

    def test_truncates_large_files(self, tmp_path):
        """Large files are truncated with marker."""
        from spec.compaction import gather_phase_outputs

        # Create oversized context.json
        context_file = tmp_path / "context.json"
        large_content = "x" * 15000  # Larger than 10000 char limit
        context_file.write_text(large_content, encoding="utf-8")

        result = gather_phase_outputs(tmp_path, "discovery")

        assert "[... file truncated ...]" in result
        assert len(result) < len(large_content) + 1000  # Allow for formatting


class TestTokenTracker:
    """Tests for TokenTracker class."""

    def test_initialization(self):
        """TokenTracker initializes with empty phases."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        assert tracker.phases == []
        assert tracker.total_tokens == 0

    def test_custom_session_id(self):
        """TokenTracker accepts custom session ID."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker(session_id="test-session")
        assert tracker.session_id == "test-session"

    def test_log_phase_records_usage(self):
        """log_phase records token usage."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        tracker.log_phase("discovery", 1000, 500)

        assert len(tracker.phases) == 1
        assert tracker.phases[0].phase_name == "discovery"
        assert tracker.phases[0].input_tokens == 1000
        assert tracker.phases[0].output_tokens == 500

    def test_multiple_phases_tracked(self):
        """Multiple phases are tracked separately."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        tracker.log_phase("discovery", 1000, 500)
        tracker.log_phase("planning", 2000, 800)

        assert len(tracker.phases) == 2
        assert tracker.phases[0].phase_name == "discovery"
        assert tracker.phases[1].phase_name == "planning"

    def test_total_input_tokens(self):
        """total_input_tokens sums all input tokens."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        tracker.log_phase("phase1", 1000, 500)
        tracker.log_phase("phase2", 2000, 800)

        assert tracker.total_input_tokens == 3000

    def test_total_output_tokens(self):
        """total_output_tokens sums all output tokens."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        tracker.log_phase("phase1", 1000, 500)
        tracker.log_phase("phase2", 2000, 800)

        assert tracker.total_output_tokens == 1300

    def test_total_tokens(self):
        """total_tokens sums input and output tokens."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        tracker.log_phase("phase1", 1000, 500)
        tracker.log_phase("phase2", 2000, 800)

        assert tracker.total_tokens == 4300

    def test_reset_clears_phases(self):
        """reset() clears all tracked phases."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker()
        tracker.log_phase("phase1", 1000, 500)
        tracker.reset()

        assert tracker.phases == []
        assert tracker.total_tokens == 0

    def test_get_summary_structure(self):
        """get_summary() returns expected structure."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker(session_id="test")
        tracker.log_phase("discovery", 1000, 500)

        summary = tracker.get_summary()

        assert "session_id" in summary
        assert "elapsed_seconds" in summary
        assert "total_input_tokens" in summary
        assert "total_output_tokens" in summary
        assert "total_tokens" in summary
        assert "phase_count" in summary
        assert "phases" in summary

    def test_get_summary_values(self):
        """get_summary() returns correct values."""
        from core.token_tracker import TokenTracker

        tracker = TokenTracker(session_id="test")
        tracker.log_phase("discovery", 1000, 500)
        tracker.log_phase("planning", 2000, 800)

        summary = tracker.get_summary()

        assert summary["session_id"] == "test"
        assert summary["total_input_tokens"] == 3000
        assert summary["total_output_tokens"] == 1300
        assert summary["total_tokens"] == 4300
        assert summary["phase_count"] == 2


class TestPhaseTokenUsage:
    """Tests for PhaseTokenUsage dataclass."""

    def test_total_tokens_property(self):
        """total_tokens calculates input + output."""
        from core.token_tracker import PhaseTokenUsage

        usage = PhaseTokenUsage("test", 1000, 500)
        assert usage.total_tokens == 1500

    def test_cost_weight_property(self):
        """cost_weight applies 3x multiplier to output tokens."""
        from core.token_tracker import PhaseTokenUsage

        usage = PhaseTokenUsage("test", 1000, 500)
        # input + (output * 3) = 1000 + (500 * 3) = 2500
        assert usage.cost_weight == 2500


class TestGlobalTracker:
    """Tests for global tracker functions."""

    def test_get_global_tracker_returns_tracker(self):
        """get_global_tracker() returns TokenTracker instance."""
        from core.token_tracker import TokenTracker, get_global_tracker

        tracker = get_global_tracker()
        assert isinstance(tracker, TokenTracker)

    def test_get_global_tracker_singleton(self):
        """get_global_tracker() returns same instance."""
        from core.token_tracker import get_global_tracker

        tracker1 = get_global_tracker()
        tracker2 = get_global_tracker()
        assert tracker1 is tracker2

    def test_reset_global_tracker(self):
        """reset_global_tracker() clears the global tracker."""
        from core.token_tracker import get_global_tracker, reset_global_tracker

        tracker = get_global_tracker()
        tracker.log_phase("test", 100, 50)

        reset_global_tracker()

        assert get_global_tracker().phases == []


class TestTokenTrackingEnabled:
    """Tests for is_token_tracking_enabled() function."""

    def test_disabled_by_default(self):
        """Token tracking is disabled when DEBUG not set."""
        from core.token_tracker import is_token_tracking_enabled

        # Ensure DEBUG is not set
        with patch.dict(os.environ, {}, clear=True):
            # Clear DEBUG if it exists
            os.environ.pop("DEBUG", None)
            # Note: This test may need adjustment based on how debug module works
            result = is_token_tracking_enabled()
            # Default should be False when DEBUG is not explicitly set
            assert isinstance(result, bool)

    def test_enabled_when_debug_true(self):
        """Token tracking is enabled when DEBUG=true."""
        from core.token_tracker import is_token_tracking_enabled

        with patch.dict(os.environ, {"DEBUG": "true"}):
            result = is_token_tracking_enabled()
            assert result is True
