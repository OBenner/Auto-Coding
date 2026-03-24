"""
Pattern Library Generator
=========================

Automatically generates language-specific pattern library modules from codebase analysis.
Extracts patterns using AST analysis and categorizes them using AI classification.
Produces Python modules compatible with the manual pattern library format.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from integrations.graphiti.pattern_categorizer import (
    categorize_pattern_sync,
)
from integrations.graphiti.pattern_extractor import PatternExtractor

logger = logging.getLogger(__name__)

# Language file extensions
LANGUAGE_EXTENSIONS = {
    "python": [".py"],
    "javascript": [".js", ".jsx"],
    "typescript": [".ts", ".tsx"],
    "go": [".go"],
    "rust": [".rs"],
    "java": [".java"],
    "csharp": [".cs"],
    "cpp": [".cpp", ".cc", ".cxx", ".hpp", ".h"],
    "ruby": [".rb"],
    "php": [".php"],
}


class PatternLibraryGenerator:
    """Generates pattern library modules from codebase analysis."""

    def __init__(self, project_dir: str | Path):
        """
        Initialize pattern library generator.

        Args:
            project_dir: Root directory of the project to analyze
        """
        self.project_dir = Path(project_dir).resolve()
        self.extractor = PatternExtractor(self.project_dir)

    def generate_library_file(
        self,
        output_path: str | Path,
        language: str,
        options: dict[str, Any],
    ) -> None:
        """
        Generate a pattern library module for the specified language.

        Args:
            output_path: Path where the generated module will be written
            language: Programming language to generate patterns for
                     (e.g., "python", "javascript", "go")
            options: Generation options:
                     - source_dir: Specific directory to analyze (default: project_dir)
                     - pattern_types: List of pattern types to extract
                     - max_patterns_per_category: Maximum patterns per category
                     - include_line_numbers: Include source line numbers in comments
        """
        # Parse options
        source_dir = Path(options.get("source_dir", self.project_dir))
        pattern_types = options.get("pattern_types")
        max_patterns = options.get("max_patterns_per_category", 50)
        include_line_numbers = options.get("include_line_numbers", False)

        # Validate language
        if language not in LANGUAGE_EXTENSIONS:
            supported = ", ".join(LANGUAGE_EXTENSIONS.keys())
            raise ValueError(
                f"Unsupported language: {language}. Supported: {supported}"
            )

        # Find source files for the language
        logger.info(f"Scanning {source_dir} for {language} files...")
        source_files = self._find_source_files(source_dir, language)
        logger.info(f"Found {len(source_files)} {language} files")

        if not source_files:
            logger.warning(f"No {language} files found in {source_dir}")
            # Still generate an empty library file
            self._write_empty_library(output_path, language)
            return

        # Extract patterns from source files
        logger.info(f"Extracting patterns from {language} files...")
        all_patterns = self._extract_all_patterns(
            source_files, pattern_types, include_line_numbers
        )
        logger.info(f"Extracted {len(all_patterns)} patterns")

        if not all_patterns:
            logger.warning("No patterns extracted")
            self._write_empty_library(output_path, language)
            return

        # Categorize patterns
        logger.info("Categorizing patterns...")
        categorized_patterns = self._categorize_patterns(all_patterns)

        # Limit patterns per category
        for category in categorized_patterns:
            if len(categorized_patterns[category]) > max_patterns:
                categorized_patterns[category] = categorized_patterns[category][
                    :max_patterns
                ]

        # Generate Python module code
        logger.info(f"Generating library module at {output_path}...")
        module_code = self._generate_module_code(language, categorized_patterns)

        # Write to file
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(module_code, encoding="utf-8")
        logger.info(f"Pattern library generated: {output_path}")

    def _find_source_files(self, source_dir: Path, language: str) -> list[Path]:
        """Find all source files for the specified language."""
        extensions = LANGUAGE_EXTENSIONS[language]
        source_files = []

        for ext in extensions:
            # Use glob to find files recursively
            source_files.extend(source_dir.rglob(f"*{ext}"))

        # Filter out common non-source directories
        exclude_dirs = {
            "node_modules",
            ".git",
            "__pycache__",
            ".venv",
            "venv",
            "build",
            "dist",
            ".auto-claude",
            ".worktrees",
        }

        filtered_files = []
        for file_path in source_files:
            # Check if any parent directory is in exclude list
            if not any(excluded in file_path.parts for excluded in exclude_dirs):
                filtered_files.append(file_path)

        return filtered_files

    def _extract_all_patterns(
        self,
        source_files: list[Path],
        pattern_types: list[str] | None,
        include_line_numbers: bool,
    ) -> list[dict[str, Any]]:
        """Extract patterns from all source files."""
        all_patterns = []

        for file_path in source_files:
            try:
                patterns = self.extractor.extract_patterns(file_path, pattern_types)
                for pattern in patterns:
                    # Add metadata
                    pattern["file"] = str(file_path.relative_to(self.project_dir))
                    if not include_line_numbers:
                        # Remove line numbers from code snippets for cleaner output
                        pattern.pop("line_number", None)
                    all_patterns.append(pattern)
            except Exception as e:
                logger.debug(f"Failed to extract patterns from {file_path}: {e}")
                continue

        return all_patterns

    # Extended fallback mapping from pattern type → category
    _TYPE_TO_CATEGORY: dict[str, str] = {
        "error": "error-handling",
        "api": "api-design",
        "state": "state-management",
        "import": "architecture",
        "class": "architecture",
        "function": "architecture",
        "security": "security",
        "performance": "performance",
        "test": "testing",
        "config": "configuration",
        "logging": "observability",
        "database": "database",
        "ui": "ui-ux",
        "deployment": "deployment",
    }

    def _categorize_patterns(
        self,
        patterns: list[dict[str, Any]],
        max_workers: int = 4,
    ) -> dict[str, list[dict[str, Any]]]:
        """Categorize patterns using AI classification with concurrent execution.

        Args:
            patterns: List of pattern dicts to categorize
            max_workers: Max threads for parallel categorization (default: 4)
        """
        categorized: dict[str, list[dict[str, Any]]] = defaultdict(list)

        def _classify(pattern: dict[str, Any]) -> tuple[dict[str, Any], str]:
            pattern_desc = (
                f"Type: {pattern['type']}\n"
                f"Pattern: {pattern['pattern']}\n"
                f"Code: {pattern['code_snippet']}"
            )
            result = categorize_pattern_sync(pattern_desc, self.project_dir)
            category = result["category"]

            if category == "uncategorized" and pattern.get("type"):
                category = self._TYPE_TO_CATEGORY.get(pattern["type"], "uncategorized")
            return pattern, category

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(_classify, p): p for p in patterns}
            for future in as_completed(futures):
                try:
                    pattern, category = future.result()
                    categorized[category].append(pattern)
                except Exception as e:
                    # Fallback: use the pattern's type mapping on classification error
                    p = futures[future]
                    fallback = self._TYPE_TO_CATEGORY.get(
                        p.get("type", ""), "uncategorized"
                    )
                    logger.debug(
                        f"Classification failed for pattern, using fallback '{fallback}': {e}"
                    )
                    categorized[fallback].append(p)

        return dict(categorized)

    def _generate_module_code(
        self, language: str, categorized_patterns: dict[str, list[dict[str, Any]]]
    ) -> str:
        """Generate Python module code for the pattern library."""
        # Module header
        module_code = f'"""\n{language.title()} Language Patterns Module\n'
        module_code += "=" * (len(language) + 25) + "\n\n"
        module_code += f"Auto-generated idiomatic {language.title()} code patterns "
        module_code += "for code generation and analysis.\n"
        module_code += '"""\n\n\n'

        # Generate category dictionaries
        for category in sorted(categorized_patterns.keys()):
            patterns = categorized_patterns[category]
            if not patterns:
                continue

            # Category header
            category_name = category.upper().replace("-", "_")
            module_code += "# " + "=" * 77 + "\n"
            module_code += f"# {category.upper().replace('-', ' ')} PATTERNS\n"
            module_code += "# " + "=" * 77 + "\n\n"

            # Dictionary name
            dict_name = f"{category_name}_PATTERNS"
            module_code += f"{dict_name} = {{\n"

            # Add patterns
            for i, pattern in enumerate(patterns):
                # Generate unique key
                key = self._generate_pattern_key(pattern, i)

                # Use json.dumps for safe, correct string escaping
                code = pattern["code_snippet"]
                code_literal = json.dumps(code)

                # Add pattern entry
                module_code += f"    {json.dumps(key)}: {code_literal},\n"

            module_code += "}\n\n\n"

        return module_code

    def _generate_pattern_key(self, pattern: dict[str, Any], index: int) -> str:
        """Generate a unique key for a pattern."""
        # Use pattern description or type as base
        base = pattern.get("pattern", pattern.get("type", "pattern"))

        # Sanitize to valid Python identifier
        key = base.lower()
        key = key.replace(" ", "_")
        key = key.replace("-", "_")
        key = "".join(c for c in key if c.isalnum() or c == "_")

        # Limit length
        if len(key) > 40:
            key = key[:40]

        # Add index if needed for uniqueness
        if index > 0:
            key = f"{key}_{index}"

        return key

    def _write_empty_library(self, output_path: Path, language: str) -> None:
        """Write an empty pattern library module."""
        module_code = f'"""\n{language.title()} Language Patterns Module\n'
        module_code += "=" * (len(language) + 25) + "\n\n"
        module_code += f"Auto-generated idiomatic {language.title()} code patterns.\n"
        module_code += "\nNo patterns were extracted from the codebase.\n"
        module_code += '"""\n\n'
        module_code += "# No patterns found\n"

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(module_code, encoding="utf-8")
