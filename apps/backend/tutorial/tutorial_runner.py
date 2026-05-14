"""
Tutorial Runner
===============

Lightweight runner that executes tutorial build with phase tracking.
Emits phase_start, phase_progress, phase_complete events for frontend UI updates.

This orchestrates a simplified autonomous build specifically for the onboarding
tutorial, using a fixed spec (login form example) and providing real-time
feedback to help new users understand the autonomous development workflow.
"""

import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger(__name__)


class TutorialPhase(Enum):
    """Tutorial build phases."""

    SPEC = "spec"
    PLANNING = "planning"
    CODING = "coding"
    QA = "qa"
    COMPLETE = "complete"


@dataclass
class PhaseEvent:
    """Event emitted during phase execution."""

    phase: TutorialPhase
    timestamp: datetime
    data: dict[str, Any]


class TutorialRunner:
    """
    Executes tutorial build with phase tracking and event callbacks.

    This is a simplified version of the main build runner, designed specifically
    for the onboarding tutorial. It runs a fixed example (login form component)
    through all phases of autonomous development.

    Example:
        >>> runner = TutorialRunner()
        >>> runner.on_phase_start(lambda event: print(f"Starting {event.phase}"))
        >>> runner.on_phase_progress(lambda event: print(f"Progress: {event.data}"))
        >>> runner.on_phase_complete(lambda event: print(f"Completed {event.phase}"))
        >>> runner.run()
    """

    def __init__(self, project_dir: Path | None = None, spec_dir: Path | None = None):
        """
        Initialize tutorial runner.

        Args:
            project_dir: Project root directory (defaults to current working directory)
            spec_dir: Spec directory for tutorial (defaults to .auto-claude/specs/tutorial)
        """
        self.project_dir = project_dir or Path.cwd()
        self.spec_dir = spec_dir or (
            self.project_dir / ".auto-claude" / "specs" / "tutorial"
        )

        # Event callbacks
        self._on_phase_start_callbacks: list[Callable[[PhaseEvent], None]] = []
        self._on_phase_progress_callbacks: list[Callable[[PhaseEvent], None]] = []
        self._on_phase_complete_callbacks: list[Callable[[PhaseEvent], None]] = []

        # State tracking
        self.current_phase: TutorialPhase | None = None
        self.phase_history: list[PhaseEvent] = []
        self.is_running = False
        self.is_cancelled = False

        logger.info(
            f"Initialized TutorialRunner (project_dir={self.project_dir}, spec_dir={self.spec_dir})"
        )

    # ========================================================================
    # Event Registration
    # ========================================================================

    def on_phase_start(self, callback: Callable[[PhaseEvent], None]) -> None:
        """Register callback for phase start events."""
        self._on_phase_start_callbacks.append(callback)

    def on_phase_progress(self, callback: Callable[[PhaseEvent], None]) -> None:
        """Register callback for phase progress events."""
        self._on_phase_progress_callbacks.append(callback)

    def on_phase_complete(self, callback: Callable[[PhaseEvent], None]) -> None:
        """Register callback for phase complete events."""
        self._on_phase_complete_callbacks.append(callback)

    # ========================================================================
    # Event Emission
    # ========================================================================

    def _emit_phase_start(self, phase: TutorialPhase, data: dict[str, Any] | None = None) -> None:
        """Emit phase start event."""
        event = PhaseEvent(
            phase=phase, timestamp=datetime.now(), data=data or {}
        )
        self.phase_history.append(event)
        self.current_phase = phase

        logger.info(f"Phase started: {phase.value}")
        for callback in self._on_phase_start_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in phase_start callback: {e}", exc_info=True)

    def _emit_phase_progress(self, data: dict[str, Any]) -> None:
        """Emit phase progress event."""
        if not self.current_phase:
            logger.warning("Cannot emit progress - no current phase")
            return

        event = PhaseEvent(
            phase=self.current_phase, timestamp=datetime.now(), data=data
        )

        logger.debug(f"Phase progress: {self.current_phase.value} - {data}")
        for callback in self._on_phase_progress_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in phase_progress callback: {e}", exc_info=True)

    def _emit_phase_complete(self, data: dict[str, Any] | None = None) -> None:
        """Emit phase complete event."""
        if not self.current_phase:
            logger.warning("Cannot emit complete - no current phase")
            return

        event = PhaseEvent(
            phase=self.current_phase, timestamp=datetime.now(), data=data or {}
        )
        self.phase_history.append(event)

        logger.info(f"Phase completed: {self.current_phase.value}")
        for callback in self._on_phase_complete_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Error in phase_complete callback: {e}", exc_info=True)

    # ========================================================================
    # Phase Execution
    # ========================================================================

    def _run_spec_phase(self) -> None:
        """Execute spec creation phase."""
        from .tutorial_spec_generator import generate_tutorial_spec

        self._emit_phase_start(TutorialPhase.SPEC, {"description": "Creating feature specification"})

        # Generate tutorial spec
        self._emit_phase_progress({"status": "Generating spec for login form component"})
        spec = generate_tutorial_spec()

        # Save spec to disk
        self.spec_dir.mkdir(parents=True, exist_ok=True)
        spec_file = self.spec_dir / "spec.md"

        self._emit_phase_progress({"status": "Writing spec.md"})
        with spec_file.open("w", encoding="utf-8") as f:
            f.write(f"# {spec['title']}\n\n")
            f.write(f"{spec['description']}\n\n")
            f.write("## Acceptance Criteria\n\n")
            for criterion in spec["acceptance_criteria"]:
                f.write(f"- [ ] {criterion}\n")

        # Save structured spec data
        spec_json_file = self.spec_dir / "spec.json"
        with spec_json_file.open("w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)

        self._emit_phase_complete({
            "spec_file": str(spec_file),
            "title": spec["title"],
            "criteria_count": len(spec["acceptance_criteria"]),
        })

    def _run_planning_phase(self) -> None:
        """Execute implementation planning phase."""
        self._emit_phase_start(TutorialPhase.PLANNING, {"description": "Creating implementation plan"})

        # Simulate planning steps (in a real build, this would call the planner agent)
        self._emit_phase_progress({"status": "Analyzing project structure"})
        self._emit_phase_progress({"status": "Identifying dependencies"})
        self._emit_phase_progress({"status": "Creating subtasks"})

        # Create a simplified implementation plan for tutorial
        plan = {
            "phases": [
                {
                    "id": "phase-1",
                    "name": "Component Implementation",
                    "subtasks": [
                        {
                            "id": "subtask-1",
                            "description": "Create LoginForm component",
                            "status": "pending",
                        },
                        {
                            "id": "subtask-2",
                            "description": "Add form validation",
                            "status": "pending",
                        },
                        {
                            "id": "subtask-3",
                            "description": "Add unit tests",
                            "status": "pending",
                        },
                    ],
                }
            ],
            "created_at": datetime.now().isoformat(),
        }

        # Save plan
        plan_file = self.spec_dir / "implementation_plan.json"
        with plan_file.open("w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        self._emit_phase_complete({
            "plan_file": str(plan_file),
            "phase_count": len(plan["phases"]),
            "subtask_count": sum(len(p["subtasks"]) for p in plan["phases"]),
        })

    def _run_coding_phase(self) -> None:
        """Execute implementation phase."""
        self._emit_phase_start(TutorialPhase.CODING, {"description": "Implementing features"})

        # Simulate coding progress (in a real build, this would run the coder agent)
        plan_file = self.spec_dir / "implementation_plan.json"
        with plan_file.open("r", encoding="utf-8") as f:
            plan = json.load(f)

        for phase in plan["phases"]:
            for subtask in phase["subtasks"]:
                self._emit_phase_progress({
                    "status": f"Working on: {subtask['description']}",
                    "subtask_id": subtask["id"],
                })
                # Mark as completed (simulated)
                subtask["status"] = "completed"

        # Update plan with completed subtasks
        with plan_file.open("w", encoding="utf-8") as f:
            json.dump(plan, f, indent=2)

        self._emit_phase_complete({
            "subtasks_completed": sum(len(p["subtasks"]) for p in plan["phases"]),
        })

    def _run_qa_phase(self) -> None:
        """Execute QA validation phase."""
        self._emit_phase_start(TutorialPhase.QA, {"description": "Validating implementation"})

        # Simulate QA steps (in a real build, this would run the QA agent)
        self._emit_phase_progress({"status": "Running acceptance criteria checks"})
        self._emit_phase_progress({"status": "Validating code quality"})
        self._emit_phase_progress({"status": "Running tests"})

        # Create QA report
        qa_report = {
            "status": "approved",
            "timestamp": datetime.now().isoformat(),
            "criteria_passed": 8,
            "criteria_total": 8,
            "issues": [],
        }

        qa_file = self.spec_dir / "qa_report.json"
        with qa_file.open("w", encoding="utf-8") as f:
            json.dump(qa_report, f, indent=2)

        self._emit_phase_complete({
            "qa_file": str(qa_file),
            "status": qa_report["status"],
            "criteria_passed": qa_report["criteria_passed"],
        })

    # ========================================================================
    # Main Execution
    # ========================================================================

    def run(self) -> dict[str, Any]:
        """
        Run complete tutorial build.

        Executes all phases: spec → planning → coding → qa → complete

        Returns:
            dict: Build result with status, spec_dir, and phase history
        """
        if self.is_running:
            raise RuntimeError("Tutorial is already running")

        self.is_running = True
        self.is_cancelled = False

        try:
            logger.info("Starting tutorial build")

            # Execute phases sequentially
            self._run_spec_phase()
            if self.is_cancelled:
                return self._get_cancelled_result()

            self._run_planning_phase()
            if self.is_cancelled:
                return self._get_cancelled_result()

            self._run_coding_phase()
            if self.is_cancelled:
                return self._get_cancelled_result()

            self._run_qa_phase()
            if self.is_cancelled:
                return self._get_cancelled_result()

            # Mark complete
            self._emit_phase_start(TutorialPhase.COMPLETE, {"description": "Tutorial completed"})
            self._emit_phase_complete({
                "total_phases": 4,
                "spec_dir": str(self.spec_dir),
            })

            logger.info("Tutorial build completed successfully")
            return {
                "status": "success",
                "spec_dir": str(self.spec_dir),
                "phase_count": len(self.phase_history),
            }

        except Exception as e:
            logger.error(f"Tutorial build failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "phase_count": len(self.phase_history),
            }

        finally:
            self.is_running = False
            self.current_phase = None

    def cancel(self) -> None:
        """Cancel the tutorial build."""
        logger.info("Cancelling tutorial build")
        self.is_cancelled = True

    def _get_cancelled_result(self) -> dict[str, Any]:
        """Get result for cancelled build."""
        logger.info("Tutorial build cancelled")
        return {
            "status": "cancelled",
            "phase_count": len(self.phase_history),
        }

    def get_status(self) -> dict[str, Any]:
        """
        Get current tutorial status.

        Returns:
            dict: Current status including running state, current phase, and history
        """
        return {
            "is_running": self.is_running,
            "is_cancelled": self.is_cancelled,
            "current_phase": self.current_phase.value if self.current_phase else None,
            "phase_count": len(self.phase_history),
            "spec_dir": str(self.spec_dir),
        }
