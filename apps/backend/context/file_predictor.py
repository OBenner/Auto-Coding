"""
File Predictor
==============

Predicts which files are likely to be modified based on task descriptions.
Uses keyword extraction and relevance scoring to rank files.
"""

import re
from pathlib import Path


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

    def score_file(self, file_path: str, keywords: list[str], task: str) -> float:
        """
        Score a file's relevance to the task.

        Args:
            file_path: Path to the file (relative or absolute)
            keywords: Extracted keywords from task
            task: Original task description

        Returns:
            Relevance score (0.0 to 1.0, higher is more relevant)
        """
        score = 0.0
        file_path_lower = file_path.lower()
        task_lower = task.lower()

        # File name contains keywords (strong signal)
        file_name = Path(file_path).name.lower()
        for keyword in keywords:
            if keyword in file_name:
                score += 0.3

        # File path contains keywords (medium signal)
        for keyword in keywords:
            if keyword in file_path_lower and keyword not in file_name:
                score += 0.15

        # Exact file path mentioned in task (very strong signal)
        if file_path in task or file_path_lower in task_lower:
            score += 0.5

        # File extension matches work type
        extension_scores = {
            ".py": 0.1,
            ".ts": 0.1,
            ".tsx": 0.1,
            ".jsx": 0.1,
            ".js": 0.1,
            ".vue": 0.1,
            ".md": 0.05,
            ".json": 0.05,
        }
        file_ext = Path(file_path).suffix
        score += extension_scores.get(file_ext, 0.0)

        # Directory patterns (weak signal)
        if any(
            pattern in file_path_lower
            for pattern in ["test", "spec", "__pycache__", "node_modules", ".git"]
        ):
            score *= 0.5  # Reduce score for test/generated files

        # Normalize score to 0.0-1.0 range
        return min(score, 1.0)

    def predict_files(
        self,
        task: str,
        available_files: list[str],
        max_predictions: int = 10,
    ) -> list[dict]:
        """
        Predict which files are most likely to be modified.

        Args:
            task: Task description
            available_files: List of available file paths
            max_predictions: Maximum number of predictions to return

        Returns:
            List of predictions sorted by relevance, each with:
                - file_path: Path to the file
                - score: Relevance score (0.0 to 1.0)
                - reason: Why this file was predicted
        """
        # Extract keywords
        keywords = self.extract_keywords(task)

        # Score all files
        scored_files = []
        for file_path in available_files:
            score = self.score_file(file_path, keywords, task)
            if score > 0.0:  # Only include files with some relevance
                reason = self._generate_reason(file_path, keywords, task, score)
                scored_files.append(
                    {
                        "file_path": file_path,
                        "score": score,
                        "reason": reason,
                    }
                )

        # Sort by score (highest first)
        scored_files.sort(key=lambda x: x["score"], reverse=True)

        # Return top predictions
        return scored_files[:max_predictions]

    def _generate_reason(
        self,
        file_path: str,
        keywords: list[str],
        task: str,
        score: float,
    ) -> str:
        """
        Generate a human-readable reason for why a file was predicted.

        Args:
            file_path: Path to the file
            keywords: Extracted keywords
            task: Original task
            score: Calculated score

        Returns:
            Explanation string
        """
        reasons = []

        file_name = Path(file_path).name.lower()
        file_path_lower = file_path.lower()

        # Check for keyword matches
        matched_keywords = [kw for kw in keywords if kw in file_name]
        if matched_keywords:
            reasons.append(f"filename contains '{matched_keywords[0]}'")

        # Check for path matches
        path_keywords = [
            kw for kw in keywords if kw in file_path_lower and kw not in file_name
        ]
        if path_keywords:
            reasons.append(f"path contains '{path_keywords[0]}'")

        # Check for exact mention
        if file_path.lower() in task.lower():
            reasons.append("explicitly mentioned in task")

        # Default reason
        if not reasons:
            reasons.append(f"relevance score: {score:.2f}")

        return ", ".join(reasons)
