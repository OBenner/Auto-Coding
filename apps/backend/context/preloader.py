"""
Context Preloader
=================

Main preloader class that orchestrates predictive context preloading.
Predicts which files will be needed for a task and preloads them into cache.
"""

from pathlib import Path

from .cache import ContextCache
from .file_predictor import FilePrediction, FilePredictor


class ContextPreloader:
    """
    Orchestrates predictive context preloading.

    This is the main orchestrator that coordinates the preloading components:
    - FilePredictor: Predicts which files are likely to be modified
    - ContextCache: Caches preloaded file contents
    """

    def __init__(
        self,
        project_dir: Path | None,
        cache_dir: Path | None,
        available_files: list[str] | None = None,
    ):
        """
        Initialize the context preloader.

        Args:
            project_dir: Project root directory
            cache_dir: Directory for cache storage (e.g., spec_dir / "cache")
            available_files: List of available files in project (optional)
        """
        self.project_dir = project_dir
        self.cache_dir = cache_dir
        self.available_files = available_files or []

        # Initialize components
        self.predictor = FilePredictor(project_dir)
        self.cache = ContextCache(cache_dir, project_root=project_dir)

    def predict_files(
        self,
        task: str,
        max_predictions: int = 10,
        min_score: float = 0.1,
    ) -> list[FilePrediction]:
        """
        Predict which files are likely to be modified for a task.

        Args:
            task: Task description
            max_predictions: Maximum number of predictions to return
            min_score: Minimum relevance score threshold

        Returns:
            List of FilePrediction objects sorted by relevance
        """
        return self.predictor.predict_files(
            task, self.available_files, max_predictions, min_score
        )

    def preload_context(
        self,
        task: str,
        max_files: int = 10,
        min_score: float = 0.2,
        skip_cache: bool = False,
    ) -> dict:
        """
        Predict and preload file contents for a task.

        Args:
            task: Task description
            max_files: Maximum number of files to preload
            min_score: Minimum relevance score to preload
            skip_cache: If True, reload files even if cached

        Returns:
            Dictionary with preloading results:
            - predictions: List of FilePrediction objects
            - preloaded: Number of files successfully preloaded
            - cached: Number of files already cached
            - failed: Number of files that failed to load
        """
        # Predict likely files
        predictions = self.predict_files(task, max_files, min_score)

        preloaded_count = 0
        cached_count = 0
        failed_count = 0

        # Preload each predicted file
        for prediction in predictions:
            file_path = prediction.file_path

            # Check if already cached
            cached_content = self.cache.get_cached_content(file_path, skip_cache)
            if cached_content is not None:
                cached_count += 1
                continue

            # Try to read and cache the file
            try:
                if self.project_dir:
                    full_path = self.project_dir / file_path
                else:
                    full_path = Path(file_path)

                if full_path.exists() and full_path.is_file():
                    content = full_path.read_text(encoding="utf-8")
                    file_mtime = full_path.stat().st_mtime

                    # Save to cache
                    self.cache.save_content(file_path, content, file_mtime)
                    preloaded_count += 1
                else:
                    failed_count += 1
            except (OSError, UnicodeDecodeError, PermissionError):
                failed_count += 1

        return {
            "predictions": [p.to_dict() for p in predictions],
            "preloaded": preloaded_count,
            "cached": cached_count,
            "failed": failed_count,
            "total": len(predictions),
        }

    def get_preloaded_content(self, file_path: str) -> str | None:
        """
        Get preloaded content for a specific file.

        Args:
            file_path: Path to the file

        Returns:
            File content if cached, None otherwise
        """
        cached_entry = self.cache.get_cached_content(file_path)
        if cached_entry:
            return cached_entry.get("content")
        return None

    def get_cache_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (file count, size, age)
        """
        return self.cache.get_cache_stats()

    def clear_cache(self) -> None:
        """Clear all preloaded content from cache."""
        self.cache.clear_cache()

    # Backward compatibility methods for direct component access

    def predict_files_dict(
        self,
        task: str,
        max_predictions: int = 10,
        min_score: float = 0.1,
    ) -> list[dict]:
        """
        Predict files and return as dictionaries. (Backward compatibility)

        Args:
            task: Task description
            max_predictions: Maximum number of predictions
            min_score: Minimum score threshold

        Returns:
            List of prediction dictionaries
        """
        predictions = self.predict_files(task, max_predictions, min_score)
        return [p.to_dict() for p in predictions]

    def extract_keywords(self, task: str) -> list[str]:
        """Extract keywords from task description. (Backward compatibility)"""
        return self.predictor.extract_keywords(task)

    def detect_work_types(self, task: str) -> list[str]:
        """Detect work types from task description. (Backward compatibility)"""
        return self.predictor.detect_work_types(task)
