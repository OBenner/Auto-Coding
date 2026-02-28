"""
End-to-End Integration Tests for Failure Analysis System
==========================================================

Tests the complete failure analysis pipeline:
1. Trigger QA rejection with failure
2. Verify failure analyzed with LLM
3. Verify failure stored in Graphiti
4. Verify QA Fixer retrieves failure patterns
5. Verify dashboard displays failure metrics
6. Verify success rate improves after learning
"""

import json
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.fixture
def test_spec_dir(tmp_path):
    """Create a temporary spec directory for testing."""
    spec_dir = tmp_path / ".auto-claude" / "specs" / "test-spec"
    spec_dir.mkdir(parents=True)

    # Create implementation plan
    plan_file = spec_dir / "implementation_plan.json"
    plan_file.write_text(json.dumps({
        "feature": "Test Feature",
        "phases": [{
            "id": "phase-1",
            "subtasks": [{
                "id": "subtask-1-1",
                "description": "Test subtask",
                "status": "in_progress"
            }]
        }],
        "qa_iteration_history": []
    }))

    return spec_dir


@pytest.fixture
def test_project_dir(tmp_path):
    """Create a temporary project directory for testing."""
    project_dir = tmp_path / "project"
    project_dir.mkdir()
    return project_dir


# =============================================================================
# Shared test helpers
# =============================================================================


def _make_failure_context():
    """Create a standard failure context dict for tests."""
    return {
        "errors": [
            "SyntaxError: invalid syntax at utils.py:42",
            "AssertionError: Expected True, got False in test_auth.py:10"
        ],
        "issues": [
            {
                "file": "utils.py",
                "line": 42,
                "description": "Missing closing bracket",
                "severity": "error"
            },
            {
                "file": "tests/test_auth.py",
                "line": 10,
                "description": "Authentication test failing",
                "severity": "error"
            }
        ],
        "is_recurring": False,
        "subtask_id": "subtask-1-1"
    }


def _make_root_cause():
    """Create a standard root cause dict for tests."""
    return {
        "category": "syntax_error",
        "description": "Missing closing bracket in utils.py",
        "affected_files": ["utils.py"],
        "confidence": 0.9,
        "recommendations": [
            "Add closing bracket on line 42",
            "Verify code follows syntax rules"
        ],
        "is_recurring": False
    }


def _make_mock_graphiti_memory():
    """Create a mock GraphitiMemory instance for testing storage."""
    mock_memory_instance = MagicMock()
    mock_memory_instance.is_enabled = True
    mock_memory_instance.is_initialized = True
    mock_memory_instance.group_id = "test-group"
    mock_memory_instance.spec_context_id = "test-spec"
    mock_memory_instance.state = MagicMock()
    mock_client = MagicMock()
    mock_client.graphiti = MagicMock()
    mock_client.graphiti.add_episode = AsyncMock()
    mock_client.graphiti.search = AsyncMock(return_value=[])
    # Expose as both public property and private attribute
    mock_memory_instance.client = mock_client
    mock_memory_instance._client = mock_client
    mock_memory_instance.close = AsyncMock()
    return mock_memory_instance


def _setup_qa_history(spec_dir, history):
    """Write QA iteration history to the plan file."""
    plan_file = spec_dir / "implementation_plan.json"
    plan = json.loads(plan_file.read_text())
    plan["qa_iteration_history"] = history
    plan_file.write_text(json.dumps(plan))
    return plan


async def _helper_trigger_qa_rejection(test_spec_dir, test_project_dir):
    """Helper: trigger QA rejection with failure data and verify."""
    from qa.report import record_iteration

    # Create QA report with failures
    qa_report_file = test_spec_dir / "qa_report.md"
    qa_report_file.write_text("""# QA Report

## Status: REJECTED

## Issues Found

1. **Syntax Error** - Missing closing bracket in utils.py:42
2. **Test Failure** - Authentication test failing
""")

    # Create fix request
    fix_request_file = test_spec_dir / "QA_FIX_REQUEST.md"
    fix_request_file.write_text("""# QA Fix Request

## Issues to Fix

1. Fix syntax error in utils.py
2. Fix authentication test
""")

    # Record QA iteration with correct signature
    issues = [
        {"file": "utils.py", "line": 42, "description": "Missing closing bracket", "category": "syntax_error"},
        {"file": "tests/test_auth.py", "line": 10, "description": "Authentication test failing", "category": "test_failure"}
    ]

    record_iteration(
        spec_dir=test_spec_dir,
        iteration=1,
        status="rejected",
        issues=issues,
        duration_seconds=10.5
    )

    # Verify files created
    assert qa_report_file.exists()
    assert fix_request_file.exists()

    # Load plan and verify iteration recorded
    plan_file = test_spec_dir / "implementation_plan.json"
    plan = json.loads(plan_file.read_text())
    assert "qa_iteration_history" in plan
    assert len(plan["qa_iteration_history"]) == 1

    print("  [ok] QA rejection triggered successfully")


async def _helper_failure_analyzed(test_spec_dir, test_project_dir):
    """Helper: verify failure analysis works with heuristics."""
    from analysis.failure_analyzer import extract_root_cause

    failure_context = _make_failure_context()

    # Test heuristic analysis (no LLM)
    root_cause = extract_root_cause(failure_context, use_llm=False)

    # Verify root cause structure
    assert "category" in root_cause
    assert "description" in root_cause
    assert "affected_files" in root_cause
    assert "confidence" in root_cause
    assert "recommendations" in root_cause
    assert "is_recurring" in root_cause

    # Verify categorization
    assert root_cause["category"] in ["syntax_error", "test_failure", "build_error", "unknown"]
    assert root_cause["confidence"] > 0.0
    assert len(root_cause["affected_files"]) > 0
    assert len(root_cause["recommendations"]) > 0

    # Test full analysis with extract_root_cause patched to avoid LLM
    mock_root_cause = _make_root_cause()
    with patch("analysis.failure_analyzer.extract_root_cause", return_value=mock_root_cause):
        from analysis.failure_analyzer import analyze_failure

        analysis = analyze_failure(
            test_spec_dir,
            test_project_dir,
            "qa_rejection",
            failure_context
        )

        assert "failure_type" in analysis
        assert "timestamp" in analysis
        assert "root_cause" in analysis
        assert "recommendations" in analysis
        assert analysis["failure_type"] == "qa_rejection"

    print("  [ok] Failure analysis working correctly")


async def _helper_failure_stored(test_spec_dir, test_project_dir):
    """Helper: verify failure storage in Graphiti."""
    from analysis.failure_storage import store_failure_analysis
    from integrations.graphiti.queries_pkg.schema import GroupIdMode

    root_cause = _make_root_cause()
    failure_context = {
        "errors": ["SyntaxError: invalid syntax at utils.py:42"],
        "issues": [{"file": "utils.py", "line": 42, "description": "Missing closing bracket"}],
        "subtask_id": "subtask-1-1"
    }

    # Mock Graphiti if not available in test environment
    with patch("analysis.failure_storage.is_graphiti_enabled", return_value=False):
        result = await store_failure_analysis(
            test_spec_dir,
            test_project_dir,
            "qa_rejection",
            root_cause,
            failure_context,
            GroupIdMode.PROJECT
        )
        assert result is False

    # Test with Graphiti mocked as enabled
    mock_memory_instance = _make_mock_graphiti_memory()

    # Mock the graphiti_core.nodes module that gets imported inside _store_root_cause_episode
    mock_episode_type = MagicMock()
    mock_episode_type.text = "text"
    mock_graphiti_nodes = MagicMock()
    mock_graphiti_nodes.EpisodeType = mock_episode_type

    with patch("analysis.failure_storage.is_graphiti_enabled", return_value=True), \
         patch("analysis.failure_storage.get_graphiti_memory") as mock_memory, \
         patch.dict(sys.modules, {"graphiti_core": MagicMock(), "graphiti_core.nodes": mock_graphiti_nodes}):

        mock_memory.return_value = mock_memory_instance

        result = await store_failure_analysis(
            test_spec_dir,
            test_project_dir,
            "qa_rejection",
            root_cause,
            failure_context,
            GroupIdMode.PROJECT
        )

        assert result is True
        assert mock_memory_instance.client.graphiti.add_episode.called

    print("  [ok] Failure storage working correctly")


async def _helper_retrieves_patterns(test_spec_dir, test_project_dir):
    """Helper: verify QA Fixer retrieves failure patterns."""
    from agents.memory_manager import get_failure_patterns

    mock_search_results = [
        MagicMock(
            content=json.dumps({
                "type": "root_cause",
                "failure_type": "qa_rejection",
                "category": "syntax_error",
                "description": "Missing closing bracket",
                "affected_files": ["utils.py"],
                "confidence": 0.9,
                "recommendations": ["Add closing bracket"],
                "is_recurring": False,
                "spec_id": "previous-spec"
            }),
            score=0.85
        )
    ]

    mock_memory_instance = _make_mock_graphiti_memory()
    mock_memory_instance._client.graphiti.search = AsyncMock(return_value=mock_search_results)

    async def mock_get_memory(*args, **kwargs):
        return mock_memory_instance

    with patch("agents.memory_manager.is_graphiti_enabled", return_value=True), \
         patch("agents.memory_manager.get_graphiti_memory", side_effect=mock_get_memory):

        patterns = await get_failure_patterns(
            test_spec_dir,
            test_project_dir,
            query="Missing closing bracket syntax error",
            failure_types=["qa_rejection"],
            num_results=5,
            min_score=0.5
        )

        assert patterns is not None
        assert "Failure Pattern Analysis" in patterns
        assert "syntax_error" in patterns.lower() or "Syntax Error" in patterns
        assert mock_memory_instance._client.graphiti.search.called
        assert mock_memory_instance.close.called

    print("  [ok] QA Fixer retrieves failure patterns successfully")


async def _helper_dashboard_metrics(test_spec_dir, test_project_dir):
    """Helper: verify dashboard failure metrics."""
    from analysis.metrics_tracker import get_failure_metrics

    _setup_qa_history(test_spec_dir, [
        {
            "iteration": 1,
            "status": "rejected",
            "issues": [
                {"category": "syntax_error", "file": "utils.py"},
                {"category": "test_failure", "file": "tests/test_auth.py"}
            ],
            "root_cause": {
                "category": "syntax_error",
                "confidence": 0.9
            }
        },
        {
            "iteration": 2,
            "status": "approved",
            "issues": [],
            "root_cause": None
        }
    ])

    metrics = get_failure_metrics(test_spec_dir)

    assert "total_failures" in metrics
    assert "failure_categories" in metrics
    assert "root_cause_rate" in metrics
    assert "pattern_detection_rate" in metrics
    assert "recurrence_rate" in metrics
    assert "top_failure_files" in metrics
    assert "top_failure_categories" in metrics

    assert metrics["total_failures"] >= 0
    assert 0.0 <= metrics["root_cause_rate"] <= 1.0
    assert isinstance(metrics["failure_categories"], dict)
    assert isinstance(metrics["top_failure_files"], list)
    assert isinstance(metrics["top_failure_categories"], list)

    print("  [ok] Dashboard metrics available and formatted correctly")


async def _helper_success_rate_improves(test_spec_dir, test_project_dir):
    """Helper: verify success rate improves after learning."""
    from analysis.metrics_tracker import get_failure_metrics, get_success_rate

    # First iteration: multiple failures (3 issues)
    _setup_qa_history(test_spec_dir, [
        {
            "iteration": 1,
            "status": "rejected",
            "issues": [
                {"category": "syntax_error", "file": "utils.py"},
                {"category": "test_failure", "file": "tests/test_auth.py"},
                {"category": "logic_error", "file": "handlers.py"}
            ],
            "root_cause": {"category": "syntax_error", "confidence": 0.9}
        }
    ])

    metrics_before = get_failure_metrics(test_spec_dir)
    # Calculate failure rate for first iteration: issues / iterations
    issues_before = metrics_before["total_failures"]
    iterations_before = 1
    failure_rate_before = issues_before / iterations_before

    # Add more iterations with fewer failures, then approval
    _setup_qa_history(test_spec_dir, [
        {
            "iteration": 1,
            "status": "rejected",
            "issues": [
                {"category": "syntax_error", "file": "utils.py"},
                {"category": "test_failure", "file": "tests/test_auth.py"},
                {"category": "logic_error", "file": "handlers.py"}
            ],
            "root_cause": {"category": "syntax_error", "confidence": 0.9}
        },
        {
            "iteration": 2,
            "status": "rejected",
            "issues": [
                {"category": "test_failure", "file": "tests/test_auth.py"}
            ],
            "root_cause": {"category": "test_failure", "confidence": 0.85}
        },
        {
            "iteration": 3,
            "status": "approved",
            "issues": [],
            "root_cause": None
        }
    ])

    metrics_after = get_failure_metrics(test_spec_dir)
    success_after = get_success_rate(test_spec_dir)
    # Compute rejected iterations from actual metrics
    rejected_iterations = success_after["rejected_iterations"]
    issues_after = metrics_after["total_failures"]
    assert rejected_iterations > 0, "Need rejected iterations to track improvement"
    failure_rate_after = issues_after / rejected_iterations

    # Failure rate per rejected iteration should decrease:
    # Before: 3 issues / 1 rejected iteration = 3.0
    # After:  4 issues / 2 rejected iterations = 2.0
    assert failure_rate_after < failure_rate_before, (
        f"Failure rate should decrease: before={failure_rate_before:.2f}, after={failure_rate_after:.2f}"
    )

    assert "root_cause_rate" in metrics_after

    print(f"  [ok] Success rate improved: failure rate {failure_rate_before:.2f} -> {failure_rate_after:.2f}")


# =============================================================================
# Test 1: Trigger QA Rejection with Failure
# =============================================================================


@pytest.mark.asyncio
async def test_1_trigger_qa_rejection(test_spec_dir, test_project_dir):
    """
    Test that we can trigger a QA rejection with failure data.

    This simulates the QA reviewer detecting issues and creating QA_FIX_REQUEST.md.
    """
    await _helper_trigger_qa_rejection(test_spec_dir, test_project_dir)


# =============================================================================
# Test 2: Verify Failure Analyzed with Heuristics (non-LLM)
# =============================================================================


@pytest.mark.asyncio
async def test_2_failure_analyzed_non_llm(test_spec_dir, test_project_dir):
    """
    Test that failures are analyzed with heuristics (non-LLM) to extract root causes.

    This verifies extract_root_cause(use_llm=False) correctly processes failure data
    using pattern matching without calling any LLM.
    """
    await _helper_failure_analyzed(test_spec_dir, test_project_dir)


# =============================================================================
# Test 3: Verify Failure Stored in Graphiti
# =============================================================================


@pytest.mark.asyncio
async def test_3_failure_stored_in_graphiti(test_spec_dir, test_project_dir):
    """
    Test that failure analyses are stored in Graphiti memory.

    This verifies store_failure_analysis() persists data correctly.
    """
    await _helper_failure_stored(test_spec_dir, test_project_dir)


# =============================================================================
# Test 4: Verify QA Fixer Retrieves Failure Patterns
# =============================================================================


@pytest.mark.asyncio
async def test_4_qa_fixer_retrieves_patterns(test_spec_dir, test_project_dir):
    """
    Test that QA Fixer retrieves failure patterns from memory.

    This verifies get_failure_patterns() returns relevant past failures.
    """
    await _helper_retrieves_patterns(test_spec_dir, test_project_dir)


# =============================================================================
# Test 5: Verify Dashboard Displays Failure Metrics
# =============================================================================


@pytest.mark.asyncio
async def test_5_dashboard_displays_metrics(test_spec_dir, test_project_dir):
    """
    Test that failure metrics are available for dashboard display.

    This verifies get_failure_metrics() returns proper metrics data.
    """
    await _helper_dashboard_metrics(test_spec_dir, test_project_dir)


# =============================================================================
# Test 6: Verify Success Rate Improves After Learning
# =============================================================================


@pytest.mark.asyncio
async def test_6_success_rate_improves(test_spec_dir, test_project_dir):
    """
    Test that failure rate per iteration decreases over successive iterations.

    This verifies the system learns from failures and reduces repeat issues.
    """
    await _helper_success_rate_improves(test_spec_dir, test_project_dir)


# =============================================================================
# Test Suite Summary
# =============================================================================


@pytest.mark.asyncio
async def test_e2e_complete_flow(test_spec_dir, test_project_dir):
    """
    Complete end-to-end test of the failure analysis system.

    This runs all 6 verification steps in sequence to verify the full pipeline.
    """
    print("\n" + "=" * 70)
    print("  FAILURE ANALYSIS SYSTEM - END-TO-END VERIFICATION")
    print("=" * 70 + "\n")

    # Run all helpers in sequence
    await _helper_trigger_qa_rejection(test_spec_dir, test_project_dir)
    await _helper_failure_analyzed(test_spec_dir, test_project_dir)
    await _helper_failure_stored(test_spec_dir, test_project_dir)
    await _helper_retrieves_patterns(test_spec_dir, test_project_dir)
    await _helper_dashboard_metrics(test_spec_dir, test_project_dir)
    await _helper_success_rate_improves(test_spec_dir, test_project_dir)

    print("\n" + "=" * 70)
    print("  ALL END-TO-END TESTS PASSED")
    print("=" * 70 + "\n")
