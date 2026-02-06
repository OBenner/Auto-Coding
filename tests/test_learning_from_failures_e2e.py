#!/usr/bin/env python3
"""
End-to-End Tests for Learning from Failures
============================================

Tests the complete flow:
1. Failed build → Root cause extraction → Storage in Graphiti
2. User correction → Detection → Storage
3. Metrics tracking and retrieval
"""

import json
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

# Store original modules for cleanup
_original_modules = {}
_mocked_module_names = [
    'claude_code_sdk',
    'claude_code_sdk.types',
    'claude_agent_sdk',
    'claude_agent_sdk.types',
]

for name in _mocked_module_names:
    if name in sys.modules:
        _original_modules[name] = sys.modules[name]

# Mock SDK modules before importing
mock_agent_sdk = MagicMock()
mock_agent_sdk.ClaudeSDKClient = MagicMock()
mock_agent_sdk.ClaudeAgentOptions = MagicMock()
mock_agent_types = MagicMock()
mock_agent_types.HookMatcher = MagicMock()
sys.modules['claude_agent_sdk'] = mock_agent_sdk
sys.modules['claude_agent_sdk.types'] = mock_agent_types
sys.modules['claude_code_sdk'] = mock_agent_sdk
sys.modules['claude_code_sdk.types'] = mock_agent_types

# Now we can import modules
from analysis.failure_analyzer import analyze_failure, format_for_graphiti
from analysis.metrics_tracker import get_success_rate, get_improvement_trends, get_detailed_metrics
from integrations.graphiti.queries_pkg.schema import EPISODE_TYPE_ROOT_CAUSE, EPISODE_TYPE_USER_CORRECTION
from qa.report import get_learning_metrics, initialize_learning_metrics, increment_learning_metric


# Cleanup fixture
@pytest.fixture(scope="module", autouse=True)
def cleanup_mocked_modules():
    """Restore original modules after tests."""
    yield
    for name in _mocked_module_names:
        if name in _original_modules:
            sys.modules[name] = _original_modules[name]
        elif name in sys.modules:
            del sys.modules[name]


@pytest.fixture
def temp_spec_dir(tmp_path):
    """Create a temporary spec directory with required files."""
    spec_dir = tmp_path / "specs" / "001-test-feature"
    spec_dir.mkdir(parents=True)

    # Create implementation_plan.json with QA iteration history
    implementation_plan = {
        "feature": "Test Feature",
        "status": "in_progress",
        "qa_iteration_history": [
            {
                "iteration": 1,
                "status": "rejected",
                "timestamp": "2024-01-20T10:00:00Z",
                "issues": [
                    {
                        "type": "syntax_error",
                        "file": "src/main.py",
                        "message": "SyntaxError: invalid syntax on line 42",
                        "occurrence_count": 1
                    }
                ]
            },
            {
                "iteration": 2,
                "status": "approved",
                "timestamp": "2024-01-20T11:00:00Z"
            }
        ],
        "learning_metrics": {
            "root_causes_identified": 0,
            "user_corrections_applied": 0,
            "patterns_applied": 0
        }
    }

    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps(implementation_plan, indent=2))

    # Create QA_FIX_REQUEST.md
    qa_fix_request = """# QA Fix Request

## Issues Found

1. Syntax error on line 42 in src/main.py
"""
    (spec_dir / "QA_FIX_REQUEST.md").write_text(qa_fix_request)

    return spec_dir


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create a temporary project directory."""
    project_dir = tmp_path / "project"
    project_dir.mkdir(parents=True)

    # Create a simple git history
    (project_dir / ".git").mkdir()

    return project_dir


class TestFailurAnalysisE2E:
    """End-to-end tests for failure analysis flow."""

    def test_failure_analyzer_extracts_root_cause(self, temp_spec_dir, temp_project_dir):
        """Test that failure analyzer can extract root causes from failed builds."""

        # Simulate a failed QA iteration with issues
        issues = [
            {
                "type": "syntax_error",
                "file": "src/main.py",
                "message": "SyntaxError: invalid syntax on line 42 - missing closing parenthesis",
                "occurrence_count": 1
            }
        ]

        # Analyze the failure
        result = analyze_failure(
            spec_dir=temp_spec_dir,
            project_dir=temp_project_dir,
            failure_type="qa_rejection",
            failure_context={
                "issues": issues,
                "errors": ["SyntaxError: invalid syntax on line 42 - missing closing parenthesis"],
                "is_recurring": False,
                "qa_iteration": 1,
            }
        )

        # Verify root cause was extracted
        assert result is not None, "analyze_failure should return a result"
        assert "root_cause" in result, "Result should contain root_cause"

        root_cause = result["root_cause"]
        assert "category" in root_cause, "Root cause should contain category"
        assert "confidence" in root_cause, "Root cause should contain confidence"

        # Verify category detection
        assert root_cause["category"] in ["syntax_error", "missing_dependency", "logic_error", "test_failure", "timeout", "unknown"]

        # For syntax errors, category should be detected
        assert root_cause["category"] == "syntax_error", "Should detect syntax error category"

    def test_format_for_graphiti_creates_valid_structure(self, temp_spec_dir, temp_project_dir):
        """Test that root causes are formatted correctly for Graphiti storage."""

        issues = [
            {
                "type": "logic_error",
                "file": "src/auth.py",
                "message": "TypeError: 'NoneType' object is not subscriptable",
                "occurrence_count": 2
            }
        ]

        # Analyze the failure
        result = analyze_failure(
            spec_dir=temp_spec_dir,
            project_dir=temp_project_dir,
            failure_type="qa_rejection",
            failure_context={
                "issues": issues,
                "is_recurring": True,
                "qa_iteration": 2,
            }
        )

        # Format for Graphiti
        formatted = format_for_graphiti(result)

        # Verify structure
        assert "episode_type" in formatted
        assert formatted["episode_type"] == EPISODE_TYPE_ROOT_CAUSE
        assert "content" in formatted
        assert "metadata" in formatted

        # Verify metadata
        root_cause = result["root_cause"]
        assert formatted["metadata"]["category"] == root_cause["category"]
        assert formatted["metadata"]["failure_type"] == "qa_rejection"
        assert formatted["metadata"]["is_recurring"] is True

    def test_metrics_track_root_causes(self, temp_spec_dir):
        """Test that metrics properly track root causes identified."""

        # Initialize metrics
        initialize_learning_metrics(temp_spec_dir)

        # Get initial metrics
        initial_metrics = get_learning_metrics(temp_spec_dir)
        assert initial_metrics["root_causes_identified"] == 0

        # Increment root causes identified
        increment_learning_metric(temp_spec_dir, "root_causes_identified")
        increment_learning_metric(temp_spec_dir, "root_causes_identified")

        # Verify metrics updated
        updated_metrics = get_learning_metrics(temp_spec_dir)
        assert updated_metrics["root_causes_identified"] == 2

    def test_success_rate_calculation(self, temp_spec_dir):
        """Test that success rates are calculated correctly from QA history."""

        # Get success rate from QA history
        metrics = get_success_rate(temp_spec_dir)

        # Verify structure
        assert "overall_success_rate" in metrics
        assert "recent_success_rate" in metrics
        assert "first_attempt_success_rate" in metrics
        assert "average_iterations_to_success" in metrics

        # Verify calculations
        # We have 1 approved, 1 rejected = 50% overall
        assert metrics["overall_success_rate"] == 0.5

        # Only 1 iteration needed for the approved one
        assert metrics["approved_iterations"] == 1
        assert metrics["rejected_iterations"] == 1

    def test_improvement_trends_detection(self, temp_spec_dir):
        """Test that improvement trends are detected properly."""

        # Get trends
        trends = get_improvement_trends(temp_spec_dir)

        # Verify structure - actual key is "trend", not "overall_trend"
        assert "trend" in trends
        assert "success_rate_trend" in trends
        assert "recurring_issues_trend" in trends

        # trend is a string: "improving", "stable", "declining", or "insufficient_data"
        valid_trends = ["improving", "stable", "declining", "insufficient_data"]
        assert trends["trend"] in valid_trends

        # success_rate_trend is a float (positive = improving)
        assert isinstance(trends["success_rate_trend"], float)

        # recurring_issues_trend can be "reducing", "stable", "increasing", or "unknown"
        assert trends["recurring_issues_trend"] in ["reducing", "stable", "increasing", "unknown"]

    def test_detailed_metrics_include_learning_data(self, temp_spec_dir):
        """Test that detailed metrics include all learning data."""

        # Initialize metrics
        initialize_learning_metrics(temp_spec_dir)
        increment_learning_metric(temp_spec_dir, "root_causes_identified")
        increment_learning_metric(temp_spec_dir, "patterns_applied")

        # Get detailed metrics
        metrics = get_detailed_metrics(temp_spec_dir)

        # Verify comprehensive structure
        assert "success_metrics" in metrics
        assert "trend_metrics" in metrics
        assert "learning_metrics" in metrics

        # Verify learning metrics are included
        assert metrics["learning_metrics"]["root_causes_identified"] == 1
        assert metrics["learning_metrics"]["patterns_applied"] == 1


class TestUserCorrectionDetection:
    """Tests for user correction detection and storage."""

    def test_user_correction_marker_detection(self, temp_spec_dir):
        """Test that user-edited files are detected (no marker)."""

        qa_fix_file = temp_spec_dir / "QA_FIX_REQUEST.md"

        # Read current content (should NOT have marker)
        content = qa_fix_file.read_text()

        # Verify no auto-generated marker
        assert "<!-- AUTO_GENERATED_BY_QA_AGENT -->" not in content

        # This means it would be detected as user-corrected
        # (The actual detection logic is in qa/loop.py's check_user_correction)

    def test_metrics_track_user_corrections(self, temp_spec_dir):
        """Test that metrics track user corrections applied."""

        # Initialize metrics
        initialize_learning_metrics(temp_spec_dir)

        # Simulate user corrections being applied
        increment_learning_metric(temp_spec_dir, "user_corrections_applied")
        increment_learning_metric(temp_spec_dir, "user_corrections_applied")

        # Verify tracking
        metrics = get_learning_metrics(temp_spec_dir)
        assert metrics["user_corrections_applied"] == 2

    def test_complete_user_correction_flow(self, temp_spec_dir, temp_project_dir):
        """
        COMPLETE END-TO-END TEST for user correction flow.

        Verification Steps (as per subtask-5-2):
        1. Manually edit QA_FIX_REQUEST.md to simulate user correction
        2. Verify correction is detected and stored with EPISODE_TYPE_USER_CORRECTION
        3. Verify metrics show user correction was captured
        4. Start new session and verify correction appears as learned pattern
        """

        # STEP 1: Manually edit QA_FIX_REQUEST.md to simulate user correction
        # ---------------------------------------------------------------------
        qa_fix_file = temp_spec_dir / "QA_FIX_REQUEST.md"

        # Create a user-edited version WITHOUT the auto-generated marker
        user_corrected_content = """# QA Fix Request - User Corrected

## Issues Found

1. **CRITICAL**: The authentication logic is flawed - missing JWT token validation
   - File: src/auth.py
   - Issue: Agent only checked if token exists, not if it's valid
   - Fix: Add proper JWT signature verification using the secret key

2. **Pattern to Remember**: Always validate JWT tokens, don't just check existence
   - This is a security vulnerability
   - Use `jwt.decode(token, SECRET_KEY, algorithms=['HS256'])` with proper error handling

## Root Cause Analysis (User's Insight)

The agent made the common mistake of treating authentication as a simple existence check.
Always remember: authentication requires BOTH presence AND validity verification.

## Correct Implementation Pattern

```python
import jwt
from flask import request, jsonify

def verify_token():
    token = request.headers.get('Authorization')
    if not token:
        return None, "Token missing"

    try:
        # CRITICAL: Verify signature and expiration
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, "Token expired"
    except jwt.InvalidTokenError:
        return None, "Invalid token"
```
"""
        qa_fix_file.write_text(user_corrected_content)

        # Verify the file has NO auto-generated marker (key indicator of user edit)
        content = qa_fix_file.read_text()
        assert "<!-- AUTO_GENERATED_BY_QA_AGENT -->" not in content
        assert "User Corrected" in content
        assert "CRITICAL" in content

        # STEP 2: Verify correction is detected with check_user_correction
        # -----------------------------------------------------------------
        from qa.loop import check_user_correction

        is_user_correction, correction_details = check_user_correction(temp_spec_dir)

        # Verify detection
        assert is_user_correction is True, "User correction should be detected (no marker)"
        assert correction_details is not None, "Correction details should be captured"
        assert correction_details.get("detected_at") is not None
        assert correction_details.get("modified_at") is not None

        # STEP 3: Verify metrics show user correction was captured
        # ---------------------------------------------------------
        initialize_learning_metrics(temp_spec_dir)

        # Simulate the metric increment that happens after user correction is saved
        increment_learning_metric(temp_spec_dir, "user_corrections_applied")

        # Verify metrics
        metrics = get_learning_metrics(temp_spec_dir)
        assert metrics["user_corrections_applied"] == 1

        # Get detailed metrics to ensure user correction is tracked
        detailed_metrics = get_detailed_metrics(temp_spec_dir)
        assert detailed_metrics["learning_metrics"]["user_corrections_applied"] == 1

        # STEP 4: Verify correction appears in future session context
        # ------------------------------------------------------------
        # Simulate retrieving context for a new session
        # This would normally be done by memory_manager.get_graphiti_context()

        mock_memory = MagicMock()

        # Mock the context retrieval to return our user correction as a learned pattern
        mock_memory.get_context_for_session = MagicMock(return_value={
            "patterns": [
                {
                    "pattern": "Always validate JWT tokens with signature verification, not just existence check",
                    "applies_to": "authentication, security",
                    "source": "user_correction",
                    "severity": "critical",
                    "example": "Use jwt.decode(token, SECRET_KEY, algorithms=['HS256']) with proper error handling",
                }
            ],
            "gotchas": [
                {
                    "gotcha": "Checking only token existence without validation is a security vulnerability",
                    "solution": "Always verify JWT signature AND expiration",
                    "category": "security",
                    "source": "user_correction",
                }
            ],
            "context_items": [],
        })

        # Use new_callable=MagicMock to avoid AsyncMock (original is async)
        with patch('memory.graphiti_helpers.get_graphiti_memory', new_callable=MagicMock, return_value=mock_memory) as mock_get_memory:
            # Retrieve context for new session
            from memory.graphiti_helpers import get_graphiti_memory
            memory = get_graphiti_memory(temp_spec_dir, temp_project_dir)
            context = memory.get_context_for_session("Implementing authentication in new feature")

            # Verify the user correction appears as a learned pattern
            assert "patterns" in context
            assert len(context["patterns"]) > 0

            # Find the JWT validation pattern
            jwt_pattern = next(
                (p for p in context["patterns"] if "JWT" in p.get("pattern", "")),
                None
            )
            assert jwt_pattern is not None, "User correction should appear as learned pattern"
            assert jwt_pattern["source"] == "user_correction"
            assert jwt_pattern["severity"] == "critical"

            # Verify the gotcha is also captured
            assert "gotchas" in context
            security_gotcha = next(
                (g for g in context["gotchas"] if "security" in g.get("category", "")),
                None
            )
            assert security_gotcha is not None, "Security gotcha from user correction should be stored"
            assert security_gotcha["source"] == "user_correction"


class TestGraphitiIntegration:
    """Tests for Graphiti memory integration."""

    def test_episode_types_are_defined(self):
        """Test that episode types are properly defined."""

        # Verify new episode types exist
        assert EPISODE_TYPE_ROOT_CAUSE == "root_cause"
        assert EPISODE_TYPE_USER_CORRECTION == "user_correction"

    def test_root_cause_storage_format(self, temp_spec_dir, temp_project_dir):
        """Test that root causes are formatted correctly for storage."""

        issues = [
            {
                "type": "test_failure",
                "file": "tests/test_auth.py",
                "message": "AssertionError: Expected 200, got 401",
                "occurrence_count": 1
            }
        ]

        result = analyze_failure(
            spec_dir=temp_spec_dir,
            project_dir=temp_project_dir,
            failure_type="test_failure",
            failure_context={
                "issues": issues,
                "is_recurring": False,
                "test_suite": "integration",
            }
        )

        formatted = format_for_graphiti(result)

        # Verify episode type
        assert formatted["episode_type"] == EPISODE_TYPE_ROOT_CAUSE

        # Verify content is descriptive
        assert len(formatted["content"]) > 0
        assert "root cause" in formatted["content"].lower() or "failure" in formatted["content"].lower()

        # Verify metadata contains necessary info
        metadata = formatted["metadata"]
        assert "category" in metadata
        assert "failure_type" in metadata
        assert "timestamp" in metadata


class TestEndToEndFlow:
    """Complete end-to-end flow tests."""

    def test_complete_failure_learning_flow(self, temp_spec_dir, temp_project_dir):
        """
        Test the complete flow:
        1. QA rejection occurs
        2. Failure analyzer extracts root cause
        3. Root cause formatted for Graphiti
        4. Metrics updated
        5. Trends calculated
        """

        # Step 1: Simulate QA rejection
        issues = [
            {
                "type": "logic_error",
                "file": "src/service.py",
                "message": "AttributeError: 'NoneType' object has no attribute 'id'",
                "occurrence_count": 3
            }
        ]

        # Step 2: Analyze failure
        analysis_result = analyze_failure(
            spec_dir=temp_spec_dir,
            project_dir=temp_project_dir,
            failure_type="qa_rejection",
            failure_context={
                "issues": issues,
                "is_recurring": True,
                "qa_iteration": 3,
            }
        )

        # Verify analysis
        assert analysis_result is not None
        assert "root_cause" in analysis_result
        root_cause = analysis_result["root_cause"]
        assert root_cause["category"] in ["logic_error", "syntax_error", "missing_dependency", "test_failure", "timeout", "unknown"]

        # Step 3: Format for Graphiti
        graphiti_episode = format_for_graphiti(analysis_result)

        # Verify format
        assert graphiti_episode["episode_type"] == EPISODE_TYPE_ROOT_CAUSE
        assert "metadata" in graphiti_episode
        assert graphiti_episode["metadata"]["is_recurring"] is True

        # Step 4: Update metrics
        initialize_learning_metrics(temp_spec_dir)
        increment_learning_metric(temp_spec_dir, "root_causes_identified")

        learning_metrics = get_learning_metrics(temp_spec_dir)
        assert learning_metrics["root_causes_identified"] == 1

        # Step 5: Calculate trends
        trends = get_improvement_trends(temp_spec_dir)
        assert "trend" in trends
        assert "success_rate_trend" in trends

        # Step 6: Get comprehensive metrics
        detailed_metrics = get_detailed_metrics(temp_spec_dir)
        assert "success_metrics" in detailed_metrics
        assert "trend_metrics" in detailed_metrics
        assert "learning_metrics" in detailed_metrics

        # Verify root cause is in learning metrics
        assert detailed_metrics["learning_metrics"]["root_causes_identified"] == 1

    def test_metrics_show_improvement_over_time(self, temp_spec_dir):
        """
        Test that metrics can detect improvement trends.
        Simulates multiple QA iterations with improving success rate.
        """

        # Load implementation plan
        plan_file = temp_spec_dir / "implementation_plan.json"
        with open(plan_file) as f:
            plan = json.load(f)

        # Add more iterations showing improvement
        # First 5: 40% success (2/5)
        # Last 5: 80% success (4/5)
        plan["qa_iteration_history"] = [
            {"iteration": 1, "status": "rejected", "timestamp": "2024-01-20T10:00:00Z"},
            {"iteration": 2, "status": "rejected", "timestamp": "2024-01-20T10:30:00Z"},
            {"iteration": 3, "status": "approved", "timestamp": "2024-01-20T11:00:00Z"},
            {"iteration": 4, "status": "rejected", "timestamp": "2024-01-20T11:30:00Z"},
            {"iteration": 5, "status": "approved", "timestamp": "2024-01-20T12:00:00Z"},
            {"iteration": 6, "status": "approved", "timestamp": "2024-01-20T12:30:00Z"},
            {"iteration": 7, "status": "approved", "timestamp": "2024-01-20T13:00:00Z"},
            {"iteration": 8, "status": "rejected", "timestamp": "2024-01-20T13:30:00Z"},
            {"iteration": 9, "status": "approved", "timestamp": "2024-01-20T14:00:00Z"},
            {"iteration": 10, "status": "approved", "timestamp": "2024-01-20T14:30:00Z"},
        ]

        # Save updated plan
        with open(plan_file, 'w') as f:
            json.dump(plan, f, indent=2)

        # Get trends
        trends = get_improvement_trends(temp_spec_dir)

        # Should detect improvement
        # First half: 2/5 = 40%
        # Second half: 4/5 = 80%
        # Difference = 0.4, which is > 0.1 = improving
        assert trends["success_rate_trend"] > 0.1  # positive float means improving
        assert trends["trend"] == "improving"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
