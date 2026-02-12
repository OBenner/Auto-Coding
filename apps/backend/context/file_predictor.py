"""
File Predictor
==============

Predicts which files are likely to be modified based on task descriptions.
Uses keyword extraction and relevance scoring to rank files.
"""

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FilePrediction:
    """A predicted file that might be modified."""

    file_path: str
    score: float  # 0.0 to 1.0, higher is more relevant
    confidence: str  # "high", "medium", "low"
    reason: str  # Why this file was predicted
    match_factors: list[str] = field(default_factory=list)  # What contributed to the score

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "file_path": self.file_path,
            "score": self.score,
            "confidence": self.confidence,
            "reason": self.reason,
            "match_factors": self.match_factors,
        }


@dataclass
class FilePattern:
    """A file pattern for work type detection."""

    work_type: str
    path_patterns: list[str] = field(default_factory=list)
    name_patterns: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    score_boost: float = 0.2  # How much to boost score for matches


class FilePredictor:
    """Predicts relevant files for a task based on keywords and patterns."""

    # Common stopwords to filter out during keyword extraction
    STOPWORDS = {
        "a",
        "an",
        "the",
        "to",
        "for",
        "of",
        "in",
        "on",
        "at",
        "by",
        "with",
        "and",
        "or",
        "but",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "could",
        "should",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
        "i",
        "you",
        "we",
        "they",
        "it",
        "when",
        "if",
        "then",
        "else",
    }

    def __init__(self, project_dir: Path | None = None):
        """
        Initialize the file predictor.

        Args:
            project_dir: Project root directory (for file path resolution)
        """
        self.project_dir = project_dir
        self.file_patterns = self._get_file_patterns()

    def _get_file_patterns(self) -> dict[str, FilePattern]:
        """
        Get file patterns for different work types.

        Returns:
            Dictionary mapping work types to file patterns
        """
        return {
            "api_endpoint": FilePattern(
                work_type="api_endpoint",
                path_patterns=["routes", "api", "endpoints", "controllers"],
                name_patterns=["route", "endpoint", "controller", "api"],
                keywords=["endpoint", "api", "route", "request", "response"],
                score_boost=0.3,
            ),
            "database_model": FilePattern(
                work_type="database_model",
                path_patterns=["models", "db", "database", "schema"],
                name_patterns=["model", "schema", "entity"],
                keywords=["model", "database", "migration", "schema", "table"],
                score_boost=0.3,
            ),
            "frontend_component": FilePattern(
                work_type="frontend_component",
                path_patterns=["components", "views", "pages", "ui"],
                name_patterns=["component", "view", "page"],
                keywords=["component", "ui", "render", "state", "props"],
                score_boost=0.25,
            ),
            "service_logic": FilePattern(
                work_type="service_logic",
                path_patterns=["services", "business", "logic", "core"],
                name_patterns=["service", "manager", "handler"],
                keywords=["service", "business", "logic", "process"],
                score_boost=0.2,
            ),
            "authentication": FilePattern(
                work_type="authentication",
                path_patterns=["auth", "authentication", "security"],
                name_patterns=["auth", "login", "token", "session"],
                keywords=["auth", "login", "password", "token", "session"],
                score_boost=0.35,
            ),
            "testing": FilePattern(
                work_type="testing",
                path_patterns=["test", "tests", "__tests__", "spec"],
                name_patterns=["test", "spec"],
                keywords=["test", "spec", "mock", "fixture"],
                score_boost=0.15,
            ),
            "configuration": FilePattern(
                work_type="configuration",
                path_patterns=["config", "settings", "env"],
                name_patterns=["config", "settings", "env"],
                keywords=["config", "settings", "environment", "setup"],
                score_boost=0.2,
            ),
        }

    def detect_work_types(self, task: str) -> list[str]:
        """
        Detect what type of work this task involves.

        Args:
            task: Task description

        Returns:
            List of work types (e.g., ["api_endpoint", "database_model"])
        """
        work_types = []
        task_lower = task.lower()

        for work_type, pattern in self.file_patterns.items():
            # Check if task mentions keywords for this work type
            if any(keyword in task_lower for keyword in pattern.keywords):
                work_types.append(work_type)

        # If no work types detected, assume general service logic
        if not work_types:
            work_types.append("service_logic")

        return work_types

    def extract_keywords(self, task: str, max_keywords: int = 15) -> list[str]:
        """
        Extract search keywords from task description.

        Args:
            task: Task description string
            max_keywords: Maximum number of keywords to return

        Returns:
            List of extracted keywords, ordered by relevance
        """
        # Extract technical terms (identifiers, file names, etc.)
        tech_terms = re.findall(r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", task)

        # Extract quoted strings (likely file names or important terms)
        quoted_terms = re.findall(r'["\']([^"\']+)["\']', task)

        # Combine and normalize
        all_terms = tech_terms + quoted_terms
        keywords = [
            term.lower()
            for term in all_terms
            if term.lower() not in self.STOPWORDS and len(term) > 2
        ]

        # Deduplicate while preserving order
        seen = set()
        unique_keywords = []
        for kw in keywords:
            if kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)

        return unique_keywords[:max_keywords]

    def score_file(
        self,
        file_path: str,
        keywords: list[str],
        task: str,
        work_types: list[str] | None = None,
    ) -> tuple[float, list[str]]:
        """
        Score a file's relevance to the task using multiple factors.

        Args:
            file_path: Path to the file (relative or absolute)
            keywords: Extracted keywords from task
            task: Original task description
            work_types: Detected work types for the task

        Returns:
            Tuple of (score, match_factors) where:
                - score: Relevance score (0.0 to 1.0, higher is more relevant)
                - match_factors: List of reasons contributing to the score
        """
        score = 0.0
        match_factors = []
        file_path_lower = file_path.lower()
        task_lower = task.lower()
        file_name = Path(file_path).name.lower()

        # 1. Exact file path mentioned in task (very strong signal)
        if file_path in task or file_path_lower in task_lower:
            score += 0.5
            match_factors.append("explicitly_mentioned")

        # 2. File name contains keywords (strong signal)
        keyword_matches = 0
        for keyword in keywords:
            if keyword in file_name:
                keyword_matches += 1
                score += 0.25
        if keyword_matches > 0:
            match_factors.append(f"filename_keywords({keyword_matches})")

        # 3. File path contains keywords (medium signal)
        path_keyword_matches = 0
        for keyword in keywords:
            if keyword in file_path_lower and keyword not in file_name:
                path_keyword_matches += 1
                score += 0.12
        if path_keyword_matches > 0:
            match_factors.append(f"path_keywords({path_keyword_matches})")

        # 4. Work type pattern matching (medium signal)
        if work_types:
            for work_type in work_types:
                pattern = self.file_patterns.get(work_type)
                if pattern:
                    # Check path patterns
                    if any(p in file_path_lower for p in pattern.path_patterns):
                        score += pattern.score_boost
                        match_factors.append(f"work_type_path({work_type})")

                    # Check name patterns
                    if any(p in file_name for p in pattern.name_patterns):
                        score += pattern.score_boost * 0.7
                        match_factors.append(f"work_type_name({work_type})")

        # 5. File extension scoring (weak signal)
        extension_scores = {
            ".py": 0.08,
            ".ts": 0.08,
            ".tsx": 0.08,
            ".jsx": 0.08,
            ".js": 0.08,
            ".vue": 0.08,
            ".md": 0.03,
            ".json": 0.03,
            ".yaml": 0.03,
            ".yml": 0.03,
        }
        file_ext = Path(file_path).suffix
        ext_score = extension_scores.get(file_ext, 0.0)
        if ext_score > 0:
            score += ext_score
            match_factors.append(f"extension({file_ext})")

        # 6. Proximity scoring (files in same directory as mentioned files)
        if "/" in file_path or "\\" in file_path:
            file_dir = str(Path(file_path).parent).lower()
            if file_dir and any(
                file_dir in word.lower() for word in task.split() if len(word) > 3
            ):
                score += 0.1
                match_factors.append("directory_proximity")

        # 7. Penalty for generated/test files (unless explicitly testing work)
        penalize_patterns = ["__pycache__", "node_modules", ".git", "dist", "build"]
        if not any(wt == "testing" for wt in (work_types or [])):
            penalize_patterns.extend(["test", "spec", "__tests__"])

        if any(pattern in file_path_lower for pattern in penalize_patterns):
            score *= 0.4
            match_factors.append("penalized_pattern")

        # 8. Boost for common entry points
        entry_points = ["__init__", "index", "main", "app"]
        if any(ep in file_name for ep in entry_points):
            score += 0.05
            match_factors.append("entry_point")

        # Normalize score to 0.0-1.0 range
        normalized_score = min(score, 1.0)

        return normalized_score, match_factors

    def _get_confidence(self, score: float) -> str:
        """
        Determine confidence level from score.

        Args:
            score: Relevance score (0.0 to 1.0)

        Returns:
            Confidence level: "high", "medium", or "low"
        """
        if score >= 0.6:
            return "high"
        elif score >= 0.3:
            return "medium"
        else:
            return "low"

    def predict_files(
        self,
        task: str,
        available_files: list[str],
        max_predictions: int = 10,
        min_score: float = 0.1,
    ) -> list[FilePrediction]:
        """
        Predict which files are most likely to be modified.

        Args:
            task: Task description
            available_files: List of available file paths
            max_predictions: Maximum number of predictions to return
            min_score: Minimum score threshold (0.0 to 1.0)

        Returns:
            List of FilePrediction objects sorted by relevance score
        """
        # Extract keywords
        keywords = self.extract_keywords(task)

        # Detect work types
        work_types = self.detect_work_types(task)

        # Score all files
        predictions = []
        for file_path in available_files:
            score, match_factors = self.score_file(
                file_path, keywords, task, work_types
            )

            # Only include files above minimum threshold
            if score >= min_score:
                confidence = self._get_confidence(score)
                reason = self._generate_reason(
                    file_path, keywords, task, score, match_factors
                )

                prediction = FilePrediction(
                    file_path=file_path,
                    score=score,
                    confidence=confidence,
                    reason=reason,
                    match_factors=match_factors,
                )
                predictions.append(prediction)

        # Sort by score (highest first)
        predictions.sort(key=lambda p: p.score, reverse=True)

        # Return top predictions
        return predictions[:max_predictions]

    def predict_files_dict(
        self,
        task: str,
        available_files: list[str],
        max_predictions: int = 10,
        min_score: float = 0.1,
    ) -> list[dict]:
        """
        Predict files and return as dictionaries (for backward compatibility).

        Args:
            task: Task description
            available_files: List of available file paths
            max_predictions: Maximum number of predictions to return
            min_score: Minimum score threshold (0.0 to 1.0)

        Returns:
            List of prediction dictionaries sorted by relevance
        """
        predictions = self.predict_files(task, available_files, max_predictions, min_score)
        return [p.to_dict() for p in predictions]

    def _generate_reason(
        self,
        file_path: str,
        keywords: list[str],
        task: str,
        score: float,
        match_factors: list[str] | None = None,
    ) -> str:
        """
        Generate a human-readable reason for why a file was predicted.

        Args:
            file_path: Path to the file
            keywords: Extracted keywords
            task: Original task
            score: Calculated score
            match_factors: List of factors that contributed to the score

        Returns:
            Explanation string
        """
        reasons = []

        file_name = Path(file_path).name.lower()
        file_path_lower = file_path.lower()

        # Use match factors if available
        if match_factors:
            if "explicitly_mentioned" in match_factors:
                reasons.append("explicitly mentioned in task")

            # Extract keyword matches
            keyword_factors = [f for f in match_factors if "keywords" in f]
            if keyword_factors:
                matched_kw = [kw for kw in keywords if kw in file_name]
                if matched_kw:
                    reasons.append(f"filename contains '{matched_kw[0]}'")

            # Extract work type matches
            work_type_factors = [f for f in match_factors if "work_type" in f]
            if work_type_factors:
                reasons.append("matches work type pattern")

            # Add other significant factors
            if "directory_proximity" in match_factors:
                reasons.append("in relevant directory")
        else:
            # Fallback to old method
            matched_keywords = [kw for kw in keywords if kw in file_name]
            if matched_keywords:
                reasons.append(f"filename contains '{matched_keywords[0]}'")

            path_keywords = [
                kw for kw in keywords if kw in file_path_lower and kw not in file_name
            ]
            if path_keywords:
                reasons.append(f"path contains '{path_keywords[0]}'")

            if file_path.lower() in task.lower():
                reasons.append("explicitly mentioned in task")

        # Default reason if nothing else
        if not reasons:
            reasons.append(f"relevance score: {score:.2f}")

        return ", ".join(reasons)
