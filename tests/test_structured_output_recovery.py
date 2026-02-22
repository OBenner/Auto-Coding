"""
Tests for Structured Output Recovery
=====================================

Tests the three-tier recovery system for PR review structured outputs:
- Tier 1: Full structured output (normal path)
- Tier 2: Extraction call with minimal schema (FollowupExtractionResponse)
- Tier 3: Text parsing fallback

Also tests:
- RECOVERABLE_ERRORS constant
- ExtractedFindingSummary / FollowupExtractionResponse models
- create_finding_from_summary() recovery helper
- Agent configuration for extraction
"""

import importlib.util
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

# Direct imports to avoid runners package chain.
# We have a models.py name collision: tools_pkg/models.py (AGENT_CONFIGS)
# and runners/github/models.py (PRReviewFinding). Handle carefully.

_project_root = Path(__file__).parent.parent

# 1. Set up paths for github runner models (PRReviewFinding, ReviewSeverity, etc.)
_github_runner_path = _project_root / "apps" / "backend" / "runners" / "github"
sys.path.insert(0, str(_github_runner_path))

_services_path = _github_runner_path / "services"
sys.path.insert(0, str(_services_path))

# 2. Import recovery_utils at module level BEFORE tools_pkg/models.py
#    gets cached in sys.modules (it also has a models.py)
from recovery_utils import (
    create_finding_from_summary,
    generate_recovery_finding_id,
    parse_severity_from_summary,
)

# 3. For AGENT_CONFIGS, load tools_pkg/models.py via importlib to avoid
#    the models.py name collision with runners/github/models.py
_tools_models_file = (
    _project_root / "apps" / "backend" / "agents" / "tools_pkg" / "models.py"
)
_spec = importlib.util.spec_from_file_location("_tools_models", str(_tools_models_file))
_tools_models = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_tools_models)
AGENT_CONFIGS = _tools_models.AGENT_CONFIGS


# =============================================================================
# Test RECOVERABLE_ERRORS
# =============================================================================


class TestRecoverableErrors:
    """Tests for RECOVERABLE_ERRORS constant in sdk_utils."""

    def test_recoverable_errors_exists(self):
        """Test that RECOVERABLE_ERRORS is defined."""
        from sdk_utils import RECOVERABLE_ERRORS

        assert isinstance(RECOVERABLE_ERRORS, set)

    def test_structured_output_validation_is_recoverable(self):
        """Test that structured_output_validation_failed is recoverable."""
        from sdk_utils import RECOVERABLE_ERRORS

        assert "structured_output_validation_failed" in RECOVERABLE_ERRORS

    def test_tool_use_concurrency_is_recoverable(self):
        """Test that tool_use_concurrency_error is recoverable."""
        from sdk_utils import RECOVERABLE_ERRORS

        assert "tool_use_concurrency_error" in RECOVERABLE_ERRORS

    def test_auth_errors_not_recoverable(self):
        """Test that auth/fatal errors are NOT in recoverable set."""
        from sdk_utils import RECOVERABLE_ERRORS

        # These should propagate as fatal errors, not trigger recovery
        assert "authentication_error" not in RECOVERABLE_ERRORS
        assert "rate_limit_error" not in RECOVERABLE_ERRORS
        assert "invalid_request" not in RECOVERABLE_ERRORS


# =============================================================================
# Test Extraction Models
# =============================================================================


class TestExtractedFindingSummary:
    """Tests for ExtractedFindingSummary model."""

    def test_valid_summary(self):
        """Test valid finding summary."""
        from pydantic_models import ExtractedFindingSummary

        data = {
            "severity": "high",
            "description": "Missing null check in parser.py",
            "file": "parser.py",
            "line": 42,
        }
        result = ExtractedFindingSummary.model_validate(data)
        assert result.severity == "high"
        assert result.description == "Missing null check in parser.py"
        assert result.file == "parser.py"
        assert result.line == 42

    def test_defaults(self):
        """Test default values for optional fields."""
        from pydantic_models import ExtractedFindingSummary

        data = {
            "severity": "medium",
            "description": "Some issue",
        }
        result = ExtractedFindingSummary.model_validate(data)
        assert result.file == "unknown"
        assert result.line == 0

    def test_severity_normalization(self):
        """Test that severity is normalized (case-insensitive, default to medium)."""
        from pydantic_models import ExtractedFindingSummary

        # Case-insensitive
        data = {"severity": "HIGH", "description": "test"}
        assert ExtractedFindingSummary.model_validate(data).severity == "high"

        # Invalid → medium
        data = {"severity": "extreme", "description": "test"}
        assert ExtractedFindingSummary.model_validate(data).severity == "medium"


class TestFollowupExtractionResponse:
    """Tests for FollowupExtractionResponse model."""

    def test_valid_response(self):
        """Test valid extraction response."""
        from pydantic_models import FollowupExtractionResponse

        data = {
            "verdict": "NEEDS_REVISION",
            "verdict_reasoning": "Found security issue",
            "new_finding_summaries": [
                {
                    "severity": "high",
                    "description": "SQL injection in query builder",
                    "file": "db/query.py",
                    "line": 55,
                }
            ],
        }
        result = FollowupExtractionResponse.model_validate(data)
        assert result.verdict == "NEEDS_REVISION"
        assert len(result.new_finding_summaries) == 1
        assert result.new_finding_summaries[0].severity == "high"

    def test_defaults(self):
        """Test default values — response should be valid with empty dict."""
        from pydantic_models import FollowupExtractionResponse

        data = {}
        result = FollowupExtractionResponse.model_validate(data)
        assert result.verdict == "NEEDS_REVISION"
        assert result.verdict_reasoning == "Recovered via extraction"
        assert result.new_finding_summaries == []

    def test_schema_generation(self):
        """Test that JSON schema is generated correctly for SDK use."""
        from pydantic_models import FollowupExtractionResponse

        schema = FollowupExtractionResponse.model_json_schema()
        assert "properties" in schema
        assert "verdict" in schema["properties"]
        assert "new_finding_summaries" in schema["properties"]


# =============================================================================
# Test Recovery Utilities
# =============================================================================


class TestCreateFindingFromSummary:
    """Tests for create_finding_from_summary from recovery_utils."""

    def test_basic_finding(self):
        """Test creating a finding from a basic summary string."""
        finding = create_finding_from_summary(
            summary="HIGH: Missing null check in parser.py",
            index=0,
        )
        assert finding.id.startswith("FR-")
        assert finding.severity.value == "high"
        assert "Missing null check" in finding.title
        assert "[Recovered via extraction]" in finding.description

    def test_severity_parsing(self):
        """Test that severity is parsed from prefix."""
        from recovery_utils import create_finding_from_summary

        for prefix, expected in [
            ("CRITICAL:", "critical"),
            ("HIGH:", "high"),
            ("MEDIUM:", "medium"),
            ("LOW:", "low"),
        ]:
            finding = create_finding_from_summary(
                summary=f"{prefix} test issue", index=0
            )
            assert finding.severity.value == expected

    def test_default_severity(self):
        """Test default severity when no prefix found."""
        finding = create_finding_from_summary(
            summary="No severity prefix here",
            index=0,
        )
        assert finding.severity.value == "medium"

    def test_custom_prefix(self):
        """Test custom ID prefix."""
        finding = create_finding_from_summary(
            summary="HIGH: test", index=0, id_prefix="FU"
        )
        assert finding.id.startswith("FU-")

    def test_file_and_line_preserved(self):
        """Test that file and line info is preserved (PR #1857)."""
        finding = create_finding_from_summary(
            summary="HIGH: Missing check",
            index=0,
            file="src/parser.py",
            line=42,
        )
        assert finding.file == "src/parser.py"
        assert finding.line == 42

    def test_severity_override(self):
        """Test severity override parameter."""
        finding = create_finding_from_summary(
            summary="LOW: minor issue",
            index=0,
            severity_override="CRITICAL",
        )
        assert finding.severity.value == "critical"


# =============================================================================
# Test Agent Configuration
# =============================================================================


class TestExtractionAgentConfig:
    """Tests for pr_followup_extraction agent configuration."""

    def test_extraction_agent_exists(self):
        """Test that pr_followup_extraction agent is configured."""
        assert "pr_followup_extraction" in AGENT_CONFIGS

    def test_extraction_agent_no_tools(self):
        """Test that extraction agent has no tools (pure extraction)."""
        config = AGENT_CONFIGS["pr_followup_extraction"]
        assert config["tools"] == []
        assert config["mcp_servers"] == []
        assert config["auto_claude_tools"] == []

    def test_extraction_agent_low_thinking(self):
        """Test that extraction agent uses low thinking (cheap extraction)."""
        config = AGENT_CONFIGS["pr_followup_extraction"]
        assert config["thinking_default"] == "low"


# =============================================================================
# Test Parallel Models with Validators
# =============================================================================


class TestParallelOrchestratorFinding:
    """Tests for ParallelOrchestratorFinding with normalization validators."""

    def test_valid_finding(self):
        """Test valid finding with correct values."""
        from pydantic_models import ParallelOrchestratorFinding

        data = {
            "id": "test-1",
            "file": "src/api.py",
            "line": 25,
            "title": "Missing error handling",
            "description": "API endpoint lacks try-catch",
            "category": "quality",
            "severity": "medium",
        }
        result = ParallelOrchestratorFinding.model_validate(data)
        assert result.severity == "medium"
        assert result.category == "quality"

    def test_severity_normalized(self):
        """Test severity normalization (case insensitive, default to medium)."""
        from pydantic_models import ParallelOrchestratorFinding

        data = {
            "id": "test-1",
            "file": "test.py",
            "title": "Test",
            "description": "Test",
            "category": "quality",
            "severity": "CRITICAL",
        }
        result = ParallelOrchestratorFinding.model_validate(data)
        assert result.severity == "critical"

        # Invalid → medium
        data["severity"] = "extreme"
        result = ParallelOrchestratorFinding.model_validate(data)
        assert result.severity == "medium"

    def test_category_normalized(self):
        """Test category normalization (case insensitive, default to quality)."""
        from pydantic_models import ParallelOrchestratorFinding

        data = {
            "id": "test-1",
            "file": "test.py",
            "title": "Test",
            "description": "Test",
            "category": "SECURITY",
            "severity": "high",
        }
        result = ParallelOrchestratorFinding.model_validate(data)
        assert result.category == "security"

        # Invalid → quality
        data["category"] = "unknown_category"
        result = ParallelOrchestratorFinding.model_validate(data)
        assert result.category == "quality"


class TestParallelFollowupFinding:
    """Tests for ParallelFollowupFinding with normalization validators."""

    def test_valid_finding(self):
        """Test valid finding."""
        from pydantic_models import ParallelFollowupFinding

        data = {
            "id": "pf-1",
            "file": "src/handler.py",
            "line": 10,
            "title": "Missing validation",
            "description": "Input not validated",
            "category": "security",
            "severity": "high",
            "source_agent": "new-code-reviewer",
        }
        result = ParallelFollowupFinding.model_validate(data)
        assert result.severity == "high"
        assert result.category == "security"

    def test_severity_normalized(self):
        """Test severity normalization."""
        from pydantic_models import ParallelFollowupFinding

        data = {
            "id": "pf-1",
            "file": "test.py",
            "title": "Test",
            "description": "Test",
            "category": "quality",
            "severity": "UNKNOWN",
            "source_agent": "test",
        }
        result = ParallelFollowupFinding.model_validate(data)
        assert result.severity == "medium"

    def test_category_normalized(self):
        """Test category normalization including regression/incomplete_fix."""
        from pydantic_models import ParallelFollowupFinding

        # Valid followup-specific categories
        for cat in ["regression", "incomplete_fix"]:
            data = {
                "id": "pf-1",
                "file": "test.py",
                "title": "Test",
                "description": "Test",
                "category": cat,
                "severity": "medium",
                "source_agent": "test",
            }
            result = ParallelFollowupFinding.model_validate(data)
            assert result.category == cat

        # Invalid → quality
        data["category"] = "bogus"
        result = ParallelFollowupFinding.model_validate(data)
        assert result.category == "quality"


class TestResolutionVerification:
    """Tests for ResolutionVerification evidence field relaxation."""

    def test_empty_evidence_allowed(self):
        """Test that empty evidence is now allowed (was min_length=1)."""
        from pydantic_models import ResolutionVerification

        data = {
            "finding_id": "prev-1",
            "status": "resolved",
            "evidence": "",  # Was rejected before PR #1806
        }
        result = ResolutionVerification.model_validate(data)
        assert result.evidence == ""

    def test_evidence_default(self):
        """Test evidence defaults to empty string."""
        from pydantic_models import ResolutionVerification

        data = {
            "finding_id": "prev-1",
            "status": "resolved",
        }
        result = ResolutionVerification.model_validate(data)
        assert result.evidence == ""
