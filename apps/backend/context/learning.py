"""
Learning Tracker
================

Tracks prediction accuracy metrics to improve file prediction over time.

This module handles:
- Recording prediction outcomes (hits vs misses)
- Calculating accuracy rates for different prediction types
- Storing learning data to disk for persistence
- Generating insights for prediction improvement
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class PredictionOutcome:
    """
    Record of a single prediction outcome.

    Tracks whether a predicted file was actually used/modified
    and associated metadata for learning.
    """

    file_path: str
    predicted: bool  # Was this file predicted?
    actually_used: bool  # Was this file actually modified/used?
    prediction_score: float = 0.0  # Original prediction score (0.0-1.0)
    confidence: str = "medium"  # "high", "medium", "low"
    timestamp: datetime = field(default_factory=datetime.now)
    task_description: str = ""  # Task that triggered the prediction
    match_factors: list[str] = field(default_factory=list)  # What led to prediction

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "file_path": self.file_path,
            "predicted": self.predicted,
            "actually_used": self.actually_used,
            "prediction_score": self.prediction_score,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat(),
            "task_description": self.task_description,
            "match_factors": self.match_factors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PredictionOutcome:
        """Create from dictionary."""
        return cls(
            file_path=data["file_path"],
            predicted=data.get("predicted", False),
            actually_used=data.get("actually_used", False),
            prediction_score=data.get("prediction_score", 0.0),
            confidence=data.get("confidence", "medium"),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            task_description=data.get("task_description", ""),
            match_factors=data.get("match_factors", []),
        )

    @property
    def is_true_positive(self) -> bool:
        """Was this a correct prediction (predicted and used)?"""
        return self.predicted and self.actually_used

    @property
    def is_false_positive(self) -> bool:
        """Was this a wrong prediction (predicted but not used)?"""
        return self.predicted and not self.actually_used

    @property
    def is_false_negative(self) -> bool:
        """Was this a missed prediction (not predicted but used)?"""
        return not self.predicted and self.actually_used

    @property
    def is_true_negative(self) -> bool:
        """Was this correctly not predicted (not predicted and not used)?"""
        return not self.predicted and not self.actually_used


@dataclass
class PredictionMetrics:
    """
    Aggregated metrics for prediction accuracy.

    Tracks overall performance and patterns in prediction quality.
    """

    total_predictions: int = 0
    true_positives: int = 0  # Correctly predicted files
    false_positives: int = 0  # Incorrectly predicted files
    false_negatives: int = 0  # Missed files that were used
    true_negatives: int = 0  # Correctly excluded files

    # Confidence-based metrics
    high_confidence_correct: int = 0
    high_confidence_total: int = 0
    medium_confidence_correct: int = 0
    medium_confidence_total: int = 0
    low_confidence_correct: int = 0
    low_confidence_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "total_predictions": self.total_predictions,
            "true_positives": self.true_positives,
            "false_positives": self.false_positives,
            "false_negatives": self.false_negatives,
            "true_negatives": self.true_negatives,
            "high_confidence_correct": self.high_confidence_correct,
            "high_confidence_total": self.high_confidence_total,
            "medium_confidence_correct": self.medium_confidence_correct,
            "medium_confidence_total": self.medium_confidence_total,
            "low_confidence_correct": self.low_confidence_correct,
            "low_confidence_total": self.low_confidence_total,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "accuracy": self.accuracy,
        }

    @property
    def precision(self) -> float:
        """
        Calculate precision (positive predictive value).

        Precision = TP / (TP + FP)
        How many predictions were correct?
        """
        total = self.true_positives + self.false_positives
        if total == 0:
            return 0.0
        return self.true_positives / total

    @property
    def recall(self) -> float:
        """
        Calculate recall (sensitivity).

        Recall = TP / (TP + FN)
        How many relevant files were found?
        """
        total = self.true_positives + self.false_negatives
        if total == 0:
            return 0.0
        return self.true_positives / total

    @property
    def f1_score(self) -> float:
        """
        Calculate F1 score (harmonic mean of precision and recall).

        F1 = 2 * (precision * recall) / (precision + recall)
        """
        if self.precision + self.recall == 0:
            return 0.0
        return 2 * (self.precision * self.recall) / (self.precision + self.recall)

    @property
    def accuracy(self) -> float:
        """
        Calculate overall accuracy.

        Accuracy = (TP + TN) / (TP + TN + FP + FN)
        """
        total = (
            self.true_positives
            + self.true_negatives
            + self.false_positives
            + self.false_negatives
        )
        if total == 0:
            return 0.0
        correct = self.true_positives + self.true_negatives
        return correct / total

    @property
    def high_confidence_accuracy(self) -> float:
        """Calculate accuracy for high confidence predictions."""
        if self.high_confidence_total == 0:
            return 0.0
        return self.high_confidence_correct / self.high_confidence_total

    @property
    def medium_confidence_accuracy(self) -> float:
        """Calculate accuracy for medium confidence predictions."""
        if self.medium_confidence_total == 0:
            return 0.0
        return self.medium_confidence_correct / self.medium_confidence_total

    @property
    def low_confidence_accuracy(self) -> float:
        """Calculate accuracy for low confidence predictions."""
        if self.low_confidence_total == 0:
            return 0.0
        return self.low_confidence_correct / self.low_confidence_total


class LearningTracker:
    """
    Tracks prediction accuracy to improve file prediction over time.

    Responsibilities:
    - Record prediction outcomes for each task
    - Calculate accuracy metrics (precision, recall, F1)
    - Store learning data to disk
    - Provide insights for prediction improvement
    """

    def __init__(self, storage_dir: Path | str):
        """
        Initialize the learning tracker.

        Args:
            storage_dir: Directory for learning data (e.g., .auto-claude/specs/XXX/)
        """
        self.storage_dir = Path(storage_dir).resolve()
        self.learning_dir = self.storage_dir / "learning"
        self.outcomes_file = self.learning_dir / "prediction_outcomes.json"
        self.metrics_file = self.learning_dir / "metrics.json"

        # Ensure directories exist
        self.learning_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"Learning tracker initialized at {self.learning_dir}")

    def record_prediction(
        self,
        predicted_files: list[dict],
        actually_used_files: list[str],
        task_description: str = "",
    ) -> None:
        """
        Record prediction outcomes for a task.

        Args:
            predicted_files: List of predictions with format:
                [{"file_path": str, "score": float, "confidence": str, "match_factors": list}, ...]
            actually_used_files: List of file paths that were actually modified/used
            task_description: Description of the task
        """
        try:
            outcomes = self._load_outcomes()
            predicted_paths = {p["file_path"] for p in predicted_files}
            actually_used_set = set(actually_used_files)

            # Record outcomes for all files involved
            all_files = predicted_paths | actually_used_set

            for file_path in all_files:
                is_predicted = file_path in predicted_paths
                is_used = file_path in actually_used_set

                # Get prediction details if predicted
                prediction_data = next(
                    (p for p in predicted_files if p["file_path"] == file_path),
                    None,
                )

                outcome = PredictionOutcome(
                    file_path=file_path,
                    predicted=is_predicted,
                    actually_used=is_used,
                    prediction_score=prediction_data["score"] if prediction_data else 0.0,
                    confidence=prediction_data.get("confidence", "medium")
                    if prediction_data
                    else "medium",
                    task_description=task_description,
                    match_factors=prediction_data.get("match_factors", [])
                    if prediction_data
                    else [],
                )

                outcomes.append(outcome)

            # Save outcomes
            self._save_outcomes(outcomes)

            # Update metrics
            self._update_metrics()

            logger.info(
                f"Recorded prediction outcomes: {len(predicted_files)} predicted, "
                f"{len(actually_used_files)} actually used"
            )

        except Exception as e:
            logger.error(f"Failed to record prediction outcomes: {e}")

    def get_metrics(self) -> PredictionMetrics:
        """
        Get current prediction accuracy metrics.

        Returns:
            Aggregated metrics for all recorded predictions
        """
        try:
            if not self.metrics_file.exists():
                return PredictionMetrics()

            with open(self.metrics_file, encoding="utf-8") as f:
                data = json.load(f)

            metrics = PredictionMetrics(
                total_predictions=data.get("total_predictions", 0),
                true_positives=data.get("true_positives", 0),
                false_positives=data.get("false_positives", 0),
                false_negatives=data.get("false_negatives", 0),
                true_negatives=data.get("true_negatives", 0),
                high_confidence_correct=data.get("high_confidence_correct", 0),
                high_confidence_total=data.get("high_confidence_total", 0),
                medium_confidence_correct=data.get("medium_confidence_correct", 0),
                medium_confidence_total=data.get("medium_confidence_total", 0),
                low_confidence_correct=data.get("low_confidence_correct", 0),
                low_confidence_total=data.get("low_confidence_total", 0),
            )

            return metrics

        except Exception as e:
            logger.error(f"Failed to load metrics: {e}")
            return PredictionMetrics()

    def get_insights(self) -> dict[str, Any]:
        """
        Get insights for prediction improvement.

        Returns:
            Dictionary with insights about prediction patterns:
            - Most common false positives
            - Most common false negatives
            - Best performing match factors
            - Confidence accuracy breakdown
        """
        try:
            outcomes = self._load_outcomes()
            metrics = self.get_metrics()

            # Analyze false positives
            false_positives = [o for o in outcomes if o.is_false_positive]
            fp_patterns = self._analyze_file_patterns(false_positives)

            # Analyze false negatives
            false_negatives = [o for o in outcomes if o.is_false_negative]
            fn_patterns = self._analyze_file_patterns(false_negatives)

            # Analyze match factors
            true_positives = [o for o in outcomes if o.is_true_positive]
            effective_factors = self._analyze_match_factors(true_positives)

            return {
                "metrics": metrics.to_dict(),
                "false_positive_patterns": fp_patterns,
                "false_negative_patterns": fn_patterns,
                "effective_match_factors": effective_factors,
                "total_outcomes_recorded": len(outcomes),
            }

        except Exception as e:
            logger.error(f"Failed to generate insights: {e}")
            return {"error": str(e)}

    def _load_outcomes(self) -> list[PredictionOutcome]:
        """Load prediction outcomes from disk."""
        if not self.outcomes_file.exists():
            return []

        try:
            with open(self.outcomes_file, encoding="utf-8") as f:
                data = json.load(f)

            outcomes = [PredictionOutcome.from_dict(o) for o in data]
            logger.debug(f"Loaded {len(outcomes)} prediction outcomes")
            return outcomes

        except Exception as e:
            logger.error(f"Failed to load outcomes: {e}")
            return []

    def _save_outcomes(self, outcomes: list[PredictionOutcome]) -> None:
        """Save prediction outcomes to disk."""
        try:
            data = [o.to_dict() for o in outcomes]

            with open(self.outcomes_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(outcomes)} prediction outcomes")

        except Exception as e:
            logger.error(f"Failed to save outcomes: {e}")

    def _update_metrics(self) -> None:
        """Update aggregated metrics from outcomes."""
        try:
            outcomes = self._load_outcomes()

            metrics = PredictionMetrics()
            metrics.total_predictions = sum(1 for o in outcomes if o.predicted)

            for outcome in outcomes:
                if outcome.is_true_positive:
                    metrics.true_positives += 1
                elif outcome.is_false_positive:
                    metrics.false_positives += 1
                elif outcome.is_false_negative:
                    metrics.false_negatives += 1
                elif outcome.is_true_negative:
                    metrics.true_negatives += 1

                # Track confidence-based metrics
                if outcome.predicted:
                    is_correct = outcome.is_true_positive

                    if outcome.confidence == "high":
                        metrics.high_confidence_total += 1
                        if is_correct:
                            metrics.high_confidence_correct += 1
                    elif outcome.confidence == "medium":
                        metrics.medium_confidence_total += 1
                        if is_correct:
                            metrics.medium_confidence_correct += 1
                    elif outcome.confidence == "low":
                        metrics.low_confidence_total += 1
                        if is_correct:
                            metrics.low_confidence_correct += 1

            # Save metrics
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump(metrics.to_dict(), f, indent=2)

            logger.debug("Updated prediction metrics")

        except Exception as e:
            logger.error(f"Failed to update metrics: {e}")

    def _analyze_file_patterns(
        self, outcomes: list[PredictionOutcome]
    ) -> dict[str, int]:
        """
        Analyze common file path patterns in outcomes.

        Returns:
            Dictionary of {pattern: count} for most common patterns
        """
        patterns = {}

        for outcome in outcomes:
            # Extract directory path as pattern
            path_parts = Path(outcome.file_path).parts
            if len(path_parts) > 1:
                # Use first 2 parts as pattern
                pattern = "/".join(path_parts[:2])
                patterns[pattern] = patterns.get(pattern, 0) + 1

        # Return top 10 patterns sorted by frequency
        sorted_patterns = sorted(patterns.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_patterns[:10])

    def _analyze_match_factors(
        self, outcomes: list[PredictionOutcome]
    ) -> dict[str, int]:
        """
        Analyze which match factors are most effective.

        Returns:
            Dictionary of {factor: count} for most effective factors
        """
        factors = {}

        for outcome in outcomes:
            for factor in outcome.match_factors:
                factors[factor] = factors.get(factor, 0) + 1

        # Return top 10 factors sorted by frequency
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_factors[:10])
