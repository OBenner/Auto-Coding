"""
Main BugPredictor class that orchestrates prediction components.
"""

from pathlib import Path

from context.learning import LearningTracker

from .checklist_generator import ChecklistGenerator
from .formatter import ChecklistFormatter
from .memory_loader import MemoryLoader
from .models import PreImplementationChecklist
from .risk_analyzer import RiskAnalyzer


class BugPredictor:
    """
    Predicts likely bugs and generates pre-implementation checklists.

    This is the main orchestrator that coordinates the prediction components:
    - MemoryLoader: Loads historical data from memory files
    - RiskAnalyzer: Analyzes risks based on work type and history
    - ChecklistGenerator: Generates structured checklists
    - ChecklistFormatter: Formats checklists as markdown
    - LearningTracker: Tracks prediction accuracy for continuous improvement
    """

    def __init__(self, spec_dir: Path):
        """
        Initialize the bug predictor.

        Args:
            spec_dir: Path to the spec directory (e.g., auto-claude/specs/001-feature/)
        """
        self.spec_dir = Path(spec_dir)
        self.memory_dir = self.spec_dir / "memory"

        # Initialize components
        self.memory_loader = MemoryLoader(self.memory_dir)
        self.risk_analyzer = RiskAnalyzer()
        self.checklist_generator = ChecklistGenerator()
        self.formatter = ChecklistFormatter()
        self.learning_tracker = LearningTracker(self.spec_dir)

    def generate_checklist(self, subtask: dict) -> PreImplementationChecklist:
        """
        Generate a complete pre-implementation checklist for a subtask.

        Args:
            subtask: Subtask dictionary from implementation_plan.json

        Returns:
            PreImplementationChecklist ready for formatting
        """
        # Load historical data
        attempt_history = self.memory_loader.load_attempt_history()
        known_patterns = self.memory_loader.load_patterns()
        known_gotchas = self.memory_loader.load_gotchas()

        # Get learning insights to improve predictions
        learning_insights = self.learning_tracker.get_insights()

        # Enhance known_gotchas with patterns from false positives
        if "false_positive_patterns" in learning_insights:
            fp_patterns = learning_insights["false_positive_patterns"]
            if fp_patterns:
                # Add warning about overconfident predictions
                gotcha_msg = f"Warning: Prediction system has {len(fp_patterns)} false positive patterns. Be cautious with high-confidence file predictions."
                known_gotchas = known_gotchas + [gotcha_msg]

        # Analyze risks
        predicted_issues = self.risk_analyzer.analyze_subtask_risks(
            subtask, attempt_history
        )

        # Generate checklist
        checklist = self.checklist_generator.generate_checklist(
            subtask=subtask,
            predicted_issues=predicted_issues,
            known_patterns=known_patterns,
            known_gotchas=known_gotchas,
        )

        return checklist

    def format_checklist_markdown(self, checklist: PreImplementationChecklist) -> str:
        """
        Format checklist as markdown for agent consumption.

        Args:
            checklist: PreImplementationChecklist to format

        Returns:
            Markdown-formatted checklist string
        """
        return self.formatter.format_markdown(checklist)

    # Backward compatibility methods for direct access

    def load_known_gotchas(self) -> list[str]:
        """Load gotchas from previous sessions. (Backward compatibility)"""
        return self.memory_loader.load_gotchas()

    def load_known_patterns(self) -> list[str]:
        """Load successful patterns from previous sessions. (Backward compatibility)"""
        return self.memory_loader.load_patterns()

    def load_attempt_history(self) -> list[dict]:
        """Load historical subtask attempts. (Backward compatibility)"""
        return self.memory_loader.load_attempt_history()

    def analyze_subtask_risks(self, subtask: dict) -> list:
        """
        Predict likely issues for a subtask. (Backward compatibility)

        Args:
            subtask: Subtask dictionary

        Returns:
            List of predicted issues
        """
        attempt_history = self.memory_loader.load_attempt_history()
        return self.risk_analyzer.analyze_subtask_risks(subtask, attempt_history)

    def get_similar_past_failures(self, subtask: dict) -> list[dict]:
        """
        Find similar past failures. (Backward compatibility)

        Args:
            subtask: Current subtask to analyze

        Returns:
            List of similar failed attempts
        """
        attempt_history = self.memory_loader.load_attempt_history()
        return self.risk_analyzer.find_similar_failures(subtask, attempt_history)

    # Learning feedback methods

    def get_learning_metrics(self) -> dict:
        """
        Get prediction accuracy metrics from learning system.

        Returns:
            Dictionary with prediction metrics (precision, recall, F1, etc.)
        """
        metrics = self.learning_tracker.get_metrics()
        return metrics.to_dict()

    def get_learning_insights(self) -> dict:
        """
        Get insights from learning system for prediction improvement.

        Returns:
            Dictionary with insights about:
            - Most common false positives
            - Most common false negatives
            - Best performing match factors
            - Confidence accuracy breakdown
        """
        return self.learning_tracker.get_insights()

    def record_file_prediction_outcome(
        self,
        predicted_files: list[dict],
        worktree_path: Path | str,
        task_description: str = "",
        base_branch: str = "main",
    ) -> None:
        """
        Record prediction accuracy by comparing predictions with actual modifications.

        This allows the system to learn from its predictions and improve over time.

        Args:
            predicted_files: List of predictions with format:
                [{"file_path": str, "score": float, "confidence": str, "match_factors": list}, ...]
            worktree_path: Path to the worktree where task was executed
            task_description: Description of the task
            base_branch: Base branch to compare against (default: "main")
        """
        self.learning_tracker.record_task_outcome(
            predicted_files=predicted_files,
            worktree_path=worktree_path,
            task_description=task_description,
            base_branch=base_branch,
        )
