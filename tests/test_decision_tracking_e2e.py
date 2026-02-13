"""
End-to-end test for AI Decision Explainability feature.

Tests the full decision tracking pipeline:
- Backend decision tracking via DecisionTracker
- Logging decisions to task_logs.json
- Saving decisions to decisions.json
- Decision filtering and statistics
- Data format compatibility with frontend
"""

import json
import shutil
import tempfile
from pathlib import Path

import pytest

# Import decision tracking modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from agents.decision_tracker import DecisionTracker
from task_logger.decision_models import Alternative, DecisionPoint, DecisionType, ConfidenceLevel
from task_logger.logger import TaskLogger
from task_logger.models import LogPhase, LogEntryType


@pytest.fixture
def test_spec_dir():
    """Create a temporary spec directory for testing."""
    temp_dir = tempfile.mkdtemp(prefix="test_decision_tracking_")
    spec_dir = Path(temp_dir) / "specs" / "test-decision-tracking"
    spec_dir.mkdir(parents=True, exist_ok=True)
    yield spec_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def task_logger(test_spec_dir):
    """Create a TaskLogger for testing."""
    logger = TaskLogger(test_spec_dir, emit_markers=False)
    logger.start_phase(LogPhase.CODING, "Starting test phase")
    return logger


@pytest.fixture
def decision_tracker(test_spec_dir, task_logger):
    """Create a DecisionTracker for testing."""
    tracker = DecisionTracker(
        spec_dir=test_spec_dir,
        task_logger=task_logger,
        current_phase=LogPhase.CODING
    )
    tracker.set_session(1)
    tracker.set_subtask("test-subtask-1")
    return tracker


class TestDecisionTrackingE2E:
    """End-to-end tests for decision tracking."""

    def test_decision_lifecycle(self, decision_tracker, test_spec_dir):
        """Test complete decision tracking lifecycle."""
        # Track a decision
        decision = decision_tracker.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Need to validate user input for authentication",
            chosen_approach="Use Pydantic models for validation",
            reasoning="Type-safe, self-documenting, widely adopted in Python ecosystem",
            confidence=0.85,
            impact="Improves code maintainability and reduces runtime errors",
            reversible=True,
            dependencies=["pydantic library"]
        )

        # Verify decision was created correctly
        assert decision.decision_type == DecisionType.IMPLEMENTATION.value
        assert decision.confidence == 0.85
        assert decision.confidence_level == ConfidenceLevel.HIGH.value
        assert decision.phase == LogPhase.CODING.value
        assert decision.subtask_id == "test-subtask-1"
        assert decision.session == 1
        assert not decision.requires_review  # High confidence doesn't require review

        # Add alternatives
        alt1 = Alternative(
            description="Manual validation with if/else statements",
            reasoning="Simple approach, no external dependencies",
            rejected_reason="Harder to maintain, error-prone, lacks type safety",
            tradeoffs=["No dependencies", "More verbose code"]
        )
        decision_tracker.add_alternative(decision, alt1)

        alt2 = Alternative(
            description="Use Marshmallow for validation",
            reasoning="Popular validation library with good documentation",
            rejected_reason="Less type-safe than Pydantic, requires more boilerplate",
            tradeoffs=["More flexible", "Steeper learning curve"]
        )
        decision_tracker.add_alternative(decision, alt2)

        # Add reasoning chain
        decision_tracker.add_reasoning_step(
            decision,
            "Identified need for input validation in authentication flow"
        )
        decision_tracker.add_reasoning_step(
            decision,
            "Evaluated three main approaches: manual, Marshmallow, Pydantic"
        )
        decision_tracker.add_reasoning_step(
            decision,
            "Pydantic chosen for type safety and IDE support"
        )

        # Verify alternatives and reasoning chain
        assert len(decision.alternatives) == 2
        assert len(decision.reasoning_chain) == 3

        # Log the decision
        decision_tracker.log_decision(decision, print_to_console=False)

        # Verify decision was saved to decisions.json
        decisions_file = test_spec_dir / "decisions.json"
        assert decisions_file.exists()

        with open(decisions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert "decisions" in data
            assert len(data["decisions"]) == 1
            saved_decision = data["decisions"][0]
            assert saved_decision["chosen_approach"] == "Use Pydantic models for validation"
            assert len(saved_decision["alternatives"]) == 2
            assert len(saved_decision["reasoning_chain"]) == 3

        # Verify decision was logged to task_logs.json
        task_logs_file = test_spec_dir / "task_logs.json"
        assert task_logs_file.exists()

        with open(task_logs_file, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            # Find decision log entries (they use log_with_detail, so type is TEXT with detail field)
            decision_entries = [
                entry for phase_entries in log_data["phases"].values()
                for entry in phase_entries.get("entries", [])
                if "Decision:" in entry.get("content", "")
            ]
            assert len(decision_entries) > 0
            decision_entry = decision_entries[0]
            assert "Pydantic" in decision_entry["content"]
            assert "detail" in decision_entry  # Should have expandable detail

    def test_multiple_decision_types(self, decision_tracker, test_spec_dir):
        """Test tracking multiple decision types."""
        # Track different types of decisions
        decisions_data = [
            {
                "type": DecisionType.APPROACH,
                "context": "How to structure the authentication system",
                "approach": "JWT-based authentication with refresh tokens",
                "confidence": 0.92
            },
            {
                "type": DecisionType.TOOL_SELECTION,
                "context": "Which testing framework to use",
                "approach": "pytest with fixtures and parametrization",
                "confidence": 0.95
            },
            {
                "type": DecisionType.ARCHITECTURE,
                "context": "How to organize backend modules",
                "approach": "Feature-based structure with shared core",
                "confidence": 0.78
            },
            {
                "type": DecisionType.ERROR_RECOVERY,
                "context": "How to handle failed API requests",
                "approach": "Exponential backoff with max 3 retries",
                "confidence": 0.55  # Low confidence - should flag for review
            }
        ]

        for data in decisions_data:
            decision = decision_tracker.track_decision(
                decision_type=data["type"],
                context=data["context"],
                chosen_approach=data["approach"],
                reasoning=f"Reasoning for {data['approach']}",
                confidence=data["confidence"]
            )
            decision_tracker.log_decision(decision, print_to_console=False)

        # Verify all decisions were saved
        decisions_file = test_spec_dir / "decisions.json"
        with open(decisions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["decisions"]) == 4

            # Verify decision types are correct
            types = [d["decision_type"] for d in data["decisions"]]
            assert DecisionType.APPROACH.value in types
            assert DecisionType.TOOL_SELECTION.value in types
            assert DecisionType.ARCHITECTURE.value in types
            assert DecisionType.ERROR_RECOVERY.value in types

    def test_low_confidence_review_flagging(self, decision_tracker):
        """Test that low confidence decisions are flagged for review."""
        # Very low confidence decision
        decision1 = decision_tracker.track_decision(
            decision_type=DecisionType.OPTIMIZATION,
            context="Performance optimization strategy",
            chosen_approach="Implement caching layer",
            reasoning="Might improve performance, but not fully analyzed",
            confidence=0.35  # Very low confidence
        )
        assert decision1.requires_review
        assert decision1.confidence_level == ConfidenceLevel.VERY_LOW.value

        # Low confidence decision
        decision2 = decision_tracker.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Data storage approach",
            chosen_approach="Use SQLite for local storage",
            reasoning="Simple but might not scale well",
            confidence=0.55  # Low confidence
        )
        assert decision2.requires_review
        assert decision2.confidence_level == ConfidenceLevel.LOW.value

        # High confidence decision
        decision3 = decision_tracker.track_decision(
            decision_type=DecisionType.TOOL_SELECTION,
            context="Which database driver to use",
            chosen_approach="Use aiosqlite for async SQLite access",
            reasoning="Well-tested, widely adopted, good async support",
            confidence=0.90  # High confidence
        )
        assert not decision3.requires_review
        assert decision3.confidence_level == ConfidenceLevel.HIGH.value

        # Get decisions requiring review
        review_decisions = decision_tracker.get_decisions_requiring_review()
        assert len(review_decisions) == 2
        assert decision1 in review_decisions
        assert decision2 in review_decisions
        assert decision3 not in review_decisions

    def test_decision_filtering(self, decision_tracker):
        """Test filtering decisions by various criteria."""
        # Create decisions across multiple phases and types
        decision_tracker.set_phase(LogPhase.PLANNING)
        decision_tracker.set_subtask("subtask-1")
        decision_tracker.track_decision(
            decision_type=DecisionType.APPROACH,
            context="Planning phase decision",
            chosen_approach="Top-down planning approach",
            reasoning="Clear hierarchy and dependencies",
            confidence=0.88
        )

        decision_tracker.set_phase(LogPhase.CODING)
        decision_tracker.set_subtask("subtask-2")
        decision_tracker.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Coding phase decision",
            chosen_approach="Async/await pattern for I/O",
            reasoning="Better performance for concurrent operations",
            confidence=0.92
        )

        decision_tracker.set_subtask("subtask-3")
        decision_tracker.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Another coding decision",
            chosen_approach="Use dataclasses for models",
            reasoning="Built-in, type-safe, minimal boilerplate",
            confidence=0.45  # Low confidence
        )

        # Filter by phase
        planning_decisions = decision_tracker.get_decisions(phase=LogPhase.PLANNING)
        assert len(planning_decisions) == 1
        assert planning_decisions[0].phase == LogPhase.PLANNING.value

        coding_decisions = decision_tracker.get_decisions(phase=LogPhase.CODING)
        assert len(coding_decisions) == 2

        # Filter by decision type
        impl_decisions = decision_tracker.get_decisions(
            decision_type=DecisionType.IMPLEMENTATION
        )
        assert len(impl_decisions) == 2

        # Filter by subtask
        subtask2_decisions = decision_tracker.get_decisions(subtask_id="subtask-2")
        assert len(subtask2_decisions) == 1
        assert subtask2_decisions[0].subtask_id == "subtask-2"

        # Filter by minimum confidence
        high_conf_decisions = decision_tracker.get_decisions(min_confidence=0.8)
        assert len(high_conf_decisions) == 2

        # Filter by review requirement
        needs_review = decision_tracker.get_decisions(requires_review=True)
        assert len(needs_review) == 1
        assert needs_review[0].confidence == 0.45

    def test_decision_statistics(self, decision_tracker):
        """Test decision statistics generation."""
        # Track multiple decisions
        decisions_to_track = [
            (DecisionType.APPROACH, 0.92),
            (DecisionType.APPROACH, 0.88),
            (DecisionType.IMPLEMENTATION, 0.85),
            (DecisionType.IMPLEMENTATION, 0.78),
            (DecisionType.IMPLEMENTATION, 0.55),  # Low confidence
            (DecisionType.TOOL_SELECTION, 0.95),
            (DecisionType.ARCHITECTURE, 0.45),  # Low confidence
        ]

        for decision_type, confidence in decisions_to_track:
            decision_tracker.track_decision(
                decision_type=decision_type,
                context=f"Test {decision_type.value} decision",
                chosen_approach=f"Approach for {decision_type.value}",
                reasoning="Test reasoning",
                confidence=confidence
            )

        # Get statistics
        stats = decision_tracker.get_decision_stats()

        # Verify statistics
        assert stats["total"] == 7
        assert stats["by_type"][DecisionType.APPROACH.value] == 2
        assert stats["by_type"][DecisionType.IMPLEMENTATION.value] == 3
        assert stats["by_type"][DecisionType.TOOL_SELECTION.value] == 1
        assert stats["by_type"][DecisionType.ARCHITECTURE.value] == 1

        # Check confidence level distribution
        # 0.92, 0.88, 0.85 = HIGH (0.8-0.95)
        # 0.78 = MEDIUM (0.6-0.8)
        # 0.55, 0.45 = LOW (0.4-0.6)
        # 0.95 = VERY_HIGH (>= 0.95)
        assert stats["by_confidence_level"][ConfidenceLevel.VERY_HIGH.value] == 1  # 0.95
        assert stats["by_confidence_level"][ConfidenceLevel.HIGH.value] == 3  # 0.92, 0.88, 0.85
        assert stats["by_confidence_level"][ConfidenceLevel.MEDIUM.value] == 1  # 0.78
        assert stats["by_confidence_level"][ConfidenceLevel.LOW.value] == 2  # 0.55, 0.45

        # Check average confidence
        expected_avg = sum(c for _, c in decisions_to_track) / len(decisions_to_track)
        assert abs(stats["avg_confidence"] - expected_avg) < 0.01

        # Check decisions requiring review
        assert stats["requiring_review"] == 2  # 0.55 and 0.45

    def test_decision_persistence_and_reload(self, test_spec_dir, task_logger):
        """Test that decisions persist and can be reloaded."""
        # Create tracker and add decisions
        tracker1 = DecisionTracker(test_spec_dir, task_logger, LogPhase.CODING)
        tracker1.track_decision(
            decision_type=DecisionType.APPROACH,
            context="First decision",
            chosen_approach="Approach 1",
            reasoning="Reasoning 1",
            confidence=0.85
        )
        tracker1.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Second decision",
            chosen_approach="Approach 2",
            reasoning="Reasoning 2",
            confidence=0.92
        )
        tracker1._save_decisions()

        # Create new tracker (simulates new session)
        tracker2 = DecisionTracker(test_spec_dir, task_logger, LogPhase.CODING)

        # Verify decisions were loaded
        assert len(tracker2.decisions) == 2
        assert tracker2.decisions[0].chosen_approach == "Approach 1"
        assert tracker2.decisions[1].chosen_approach == "Approach 2"

        # Add another decision with new tracker
        tracker2.track_decision(
            decision_type=DecisionType.TOOL_SELECTION,
            context="Third decision",
            chosen_approach="Approach 3",
            reasoning="Reasoning 3",
            confidence=0.78
        )
        tracker2._save_decisions()

        # Verify all three decisions are in file
        decisions_file = test_spec_dir / "decisions.json"
        with open(decisions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            assert len(data["decisions"]) == 3

    def test_frontend_data_format_compatibility(self, decision_tracker, test_spec_dir):
        """Test that saved decision data is compatible with frontend TypeScript types."""
        # Create a comprehensive decision with all fields
        decision = decision_tracker.track_decision(
            decision_type=DecisionType.ARCHITECTURE,
            context="Design the plugin system architecture",
            chosen_approach="Event-driven plugin architecture with dependency injection",
            reasoning="Flexible, testable, and supports hot-reloading",
            confidence=0.87,
            impact="Enables extensibility without modifying core code",
            reversible=False,  # Architectural decisions are harder to reverse
            dependencies=["plugin loader", "event bus", "DI container"],
            metadata={"estimated_effort": "high", "risk_level": "medium"}
        )

        # Add alternatives
        alt = Alternative(
            description="Simple import-based plugin system",
            reasoning="Straightforward to implement",
            rejected_reason="Lacks flexibility and hot-reload support",
            confidence_impact="Would increase confidence to 0.95 due to simplicity",
            tradeoffs=["Simpler", "Less flexible", "Requires restart for changes"]
        )
        decision_tracker.add_alternative(decision, alt)

        # Add reasoning chain
        reasoning_steps = [
            "Analyzed requirements for plugin extensibility",
            "Considered three approaches: import-based, event-driven, and hybrid",
            "Evaluated trade-offs between simplicity and flexibility",
            "Chose event-driven for better long-term maintainability"
        ]
        for step in reasoning_steps:
            decision_tracker.add_reasoning_step(decision, step)

        # Save decision
        decision_tracker.log_decision(decision, print_to_console=False)

        # Load saved data and verify format
        decisions_file = test_spec_dir / "decisions.json"
        with open(decisions_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            saved_decision = data["decisions"][0]

            # Verify all required fields exist (matching TypeScript DecisionPoint interface)
            required_fields = [
                "timestamp", "decision_type", "context", "chosen_approach",
                "reasoning", "confidence", "confidence_level", "phase"
            ]
            for field in required_fields:
                assert field in saved_decision, f"Missing required field: {field}"

            # Verify optional fields
            assert saved_decision["subtask_id"] == "test-subtask-1"
            assert saved_decision["session"] == 1
            assert saved_decision["requires_review"] is False
            assert saved_decision["impact"] is not None
            assert saved_decision["reversible"] is False
            assert len(saved_decision["dependencies"]) == 3
            assert "metadata" in saved_decision

            # Verify alternatives structure
            assert len(saved_decision["alternatives"]) == 1
            alternative = saved_decision["alternatives"][0]
            assert "description" in alternative
            assert "reasoning" in alternative
            assert "rejected_reason" in alternative
            assert "confidence_impact" in alternative
            assert "tradeoffs" in alternative
            assert isinstance(alternative["tradeoffs"], list)

            # Verify reasoning chain
            assert len(saved_decision["reasoning_chain"]) == 4
            assert isinstance(saved_decision["reasoning_chain"], list)

            # Verify confidence level is valid
            valid_levels = ["very_low", "low", "medium", "high", "very_high"]
            assert saved_decision["confidence_level"] in valid_levels

            # Verify decision type is valid
            valid_types = [
                "approach", "implementation", "tool_selection",
                "file_modification", "error_recovery", "architecture",
                "optimization", "other"
            ]
            assert saved_decision["decision_type"] in valid_types

    def test_integration_with_task_logger_phases(self, test_spec_dir):
        """Test decision tracking across different task logger phases."""
        logger = TaskLogger(test_spec_dir, emit_markers=False)
        tracker = DecisionTracker(test_spec_dir, logger)

        # Planning phase
        logger.start_phase(LogPhase.PLANNING, "Starting planning")
        tracker.set_phase(LogPhase.PLANNING)
        decision1 = tracker.track_decision(
            decision_type=DecisionType.APPROACH,
            context="Planning the implementation strategy",
            chosen_approach="Bottom-up implementation starting with core modules",
            reasoning="Reduces dependencies and enables parallel development",
            confidence=0.88
        )
        tracker.log_decision(decision1, print_to_console=False)
        logger.end_phase(LogPhase.PLANNING, success=True)

        # Coding phase
        logger.start_phase(LogPhase.CODING, "Starting coding")
        tracker.set_phase(LogPhase.CODING)
        decision2 = tracker.track_decision(
            decision_type=DecisionType.IMPLEMENTATION,
            context="Implementing authentication logic",
            chosen_approach="JWT with HttpOnly cookies",
            reasoning="Secure and prevents XSS attacks",
            confidence=0.92
        )
        tracker.log_decision(decision2, print_to_console=False)
        logger.end_phase(LogPhase.CODING, success=True)

        # Validation phase
        logger.start_phase(LogPhase.VALIDATION, "Starting validation")
        tracker.set_phase(LogPhase.VALIDATION)
        decision3 = tracker.track_decision(
            decision_type=DecisionType.TOOL_SELECTION,
            context="Choosing testing approach",
            chosen_approach="Integration tests with pytest fixtures",
            reasoning="Covers real-world scenarios and edge cases",
            confidence=0.90
        )
        tracker.log_decision(decision3, print_to_console=False)
        logger.end_phase(LogPhase.VALIDATION, success=True)

        # Verify decisions are in correct phases
        planning_decisions = tracker.get_decisions(phase=LogPhase.PLANNING)
        coding_decisions = tracker.get_decisions(phase=LogPhase.CODING)
        validation_decisions = tracker.get_decisions(phase=LogPhase.VALIDATION)

        assert len(planning_decisions) == 1
        assert len(coding_decisions) == 1
        assert len(validation_decisions) == 1

        assert planning_decisions[0].phase == LogPhase.PLANNING.value
        assert coding_decisions[0].phase == LogPhase.CODING.value
        assert validation_decisions[0].phase == LogPhase.VALIDATION.value

        # Verify task logs have entries from all phases
        task_logs_file = test_spec_dir / "task_logs.json"
        with open(task_logs_file, "r", encoding="utf-8") as f:
            log_data = json.load(f)
            assert LogPhase.PLANNING.value in log_data["phases"]
            assert LogPhase.CODING.value in log_data["phases"]
            assert LogPhase.VALIDATION.value in log_data["phases"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
