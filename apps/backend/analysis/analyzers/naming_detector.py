"""
Naming Convention Detector Module
==================================

Detects and analyzes naming conventions used in codebases across different
programming languages. Identifies patterns for variables, functions, classes,
constants, and files to help maintain consistency.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .base import BaseAnalyzer, collect_files


class NamingDetector(BaseAnalyzer):
    """Analyzes and detects naming conventions in code."""

    def __init__(self, path: Path, analysis: dict[str, Any]):
        super().__init__(path)
        self.analysis = analysis

    def detect_naming_conventions(self) -> dict[str, Any]:
        """
        Detect naming conventions across the codebase.

        Returns:
            Dictionary containing detected naming conventions with keys:
            - variable_style: Detected variable naming style (snake_case, camelCase, etc.)
            - function_style: Detected function naming style
            - class_style: Detected class naming style (PascalCase, snake_case, etc.)
            - constant_style: Detected constant naming style (UPPER_CASE, etc.)
            - file_style: Detected file naming style (kebab-case, snake_case, etc.)
            - private_prefix: How private members are indicated (_ prefix, __ prefix, etc.)
            - examples: Sample identifiers for each category
        """
        conventions = {
            "variable_style": None,
            "function_style": None,
            "class_style": None,
            "constant_style": None,
            "file_style": None,
            "private_prefix": None,
            "examples": {},
        }

        # Detect language-specific conventions
        language = self.analysis.get("language", "").lower()

        if language in ["python"]:
            self._detect_python_conventions(conventions)
        elif language in ["javascript", "typescript"]:
            self._detect_javascript_conventions(conventions)
        elif language in ["go"]:
            self._detect_go_conventions(conventions)
        elif language in ["rust"]:
            self._detect_rust_conventions(conventions)
        elif language in ["ruby"]:
            self._detect_ruby_conventions(conventions)
        elif language in ["swift"]:
            self._detect_swift_conventions(conventions)

        return conventions

    def _detect_python_conventions(self, conventions: dict[str, Any]) -> None:
        """Detect Python naming conventions."""
        # Python community standards (PEP 8)
        conventions["variable_style"] = "snake_case"
        conventions["function_style"] = "snake_case"
        conventions["class_style"] = "PascalCase"
        conventions["constant_style"] = "UPPER_SNAKE_CASE"
        conventions["private_prefix"] = "_"
        conventions["file_style"] = "snake_case"

        # Sample from actual files to validate conventions
        py_files = collect_files(self.path, "*.py", limit=10)
        if py_files:
            samples = self._sample_python_identifiers(py_files)
            conventions["examples"] = samples

            # Override detected style if samples show different pattern
            if samples.get("functions"):
                detected_func_style = self._detect_case_style(samples["functions"])
                if detected_func_style:
                    conventions["function_style"] = detected_func_style

            if samples.get("classes"):
                detected_class_style = self._detect_case_style(samples["classes"])
                if detected_class_style:
                    conventions["class_style"] = detected_class_style

    def _detect_javascript_conventions(self, conventions: dict[str, Any]) -> None:
        """Detect JavaScript/TypeScript naming conventions."""
        conventions["variable_style"] = "camelCase"
        conventions["function_style"] = "camelCase"
        conventions["class_style"] = "PascalCase"
        conventions["constant_style"] = "UPPER_SNAKE_CASE"
        conventions["private_prefix"] = "#"  # Modern JS private fields
        conventions["file_style"] = "kebab-case"  # or camelCase depending on project

        # Sample from actual files
        js_files = collect_files(self.path, "*.js", limit=20) + collect_files(
            self.path, "*.ts", limit=20
        )
        if js_files:
            samples = self._sample_javascript_identifiers(js_files[:10])
            conventions["examples"] = samples

            # Detect file naming style
            file_names = [f.stem for f in js_files[:20]]
            conventions["file_style"] = self._detect_file_naming_style(file_names)

    def _detect_go_conventions(self, conventions: dict[str, Any]) -> None:
        """Detect Go naming conventions."""
        conventions["variable_style"] = "camelCase"
        conventions["function_style"] = "PascalCase"  # Exported functions
        conventions["class_style"] = "PascalCase"  # Exported types
        conventions["constant_style"] = "PascalCase"  # Go doesn't use UPPER_CASE
        conventions["private_prefix"] = (
            "lowercase"  # Unexported = starts with lowercase
        )
        conventions["file_style"] = "snake_case"

    def _detect_rust_conventions(self, conventions: dict[str, Any]) -> None:
        """Detect Rust naming conventions."""
        conventions["variable_style"] = "snake_case"
        conventions["function_style"] = "snake_case"
        conventions["class_style"] = "PascalCase"  # Structs, Enums
        conventions["constant_style"] = "UPPER_SNAKE_CASE"
        conventions["private_prefix"] = "module_scope"  # No prefix, use pub keyword
        conventions["file_style"] = "snake_case"

    def _detect_ruby_conventions(self, conventions: dict[str, Any]) -> None:
        """Detect Ruby naming conventions."""
        conventions["variable_style"] = "snake_case"
        conventions["function_style"] = "snake_case"
        conventions["class_style"] = "PascalCase"
        conventions["constant_style"] = "UPPER_SNAKE_CASE"
        conventions["private_prefix"] = "@"  # Instance variables
        conventions["file_style"] = "snake_case"

    def _detect_swift_conventions(self, conventions: dict[str, Any]) -> None:
        """Detect Swift naming conventions."""
        conventions["variable_style"] = "camelCase"
        conventions["function_style"] = "camelCase"
        conventions["class_style"] = "PascalCase"
        conventions["constant_style"] = (
            "camelCase"  # Swift uses camelCase for constants
        )
        conventions["private_prefix"] = "_"  # Convention, not enforced
        conventions["file_style"] = "PascalCase"

    def _sample_python_identifiers(self, files: list[Path]) -> dict[str, list[str]]:
        """Sample identifiers from Python files."""
        import ast

        samples = {"functions": [], "classes": [], "variables": [], "constants": []}

        for file in files:
            try:
                source = file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not node.name.startswith("_"):
                            samples["functions"].append(node.name)

                    elif isinstance(node, ast.ClassDef):
                        samples["classes"].append(node.name)

                    elif isinstance(node, ast.Assign):
                        for target in node.targets:
                            if isinstance(target, ast.Name):
                                name = target.id
                                if name.isupper():
                                    samples["constants"].append(name)
                                else:
                                    samples["variables"].append(name)

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        # Limit samples
        return {k: v[:10] for k, v in samples.items()}

    def _sample_javascript_identifiers(self, files: list[Path]) -> dict[str, list[str]]:
        """Sample identifiers from JavaScript/TypeScript files."""
        samples = {"functions": [], "classes": [], "variables": [], "constants": []}

        # Simple regex-based sampling (not full AST parsing)
        func_pattern = re.compile(r"function\s+(\w+)\s*\(")
        class_pattern = re.compile(r"class\s+(\w+)")
        const_pattern = re.compile(r"const\s+(\w+)\s*=")
        let_pattern = re.compile(r"let\s+(\w+)\s*=")
        var_pattern = re.compile(r"var\s+(\w+)\s*=")

        for file in files:
            try:
                source = file.read_text(encoding="utf-8")

                # Extract identifiers
                samples["functions"].extend(func_pattern.findall(source))
                samples["classes"].extend(class_pattern.findall(source))

                const_names = const_pattern.findall(source)
                for name in const_names:
                    if name.isupper():
                        samples["constants"].append(name)
                    else:
                        samples["variables"].append(name)

                samples["variables"].extend(let_pattern.findall(source))
                samples["variables"].extend(var_pattern.findall(source))

            except (OSError, UnicodeDecodeError):
                continue

        # Limit samples
        return {k: v[:10] for k, v in samples.items()}

    def _detect_case_style(self, identifiers: list[str]) -> str | None:
        """Instance method that delegates to the static version."""
        return NamingDetector.detect_case_style(identifiers)

    @staticmethod
    def detect_case_style(identifiers: list[str]) -> str | None:
        """
        Detect the predominant case style from a list of identifiers.

        Returns:
            One of: snake_case, camelCase, PascalCase, UPPER_SNAKE_CASE, or None
        """
        if not identifiers:
            return None

        styles = {
            "snake_case": 0,
            "camelCase": 0,
            "PascalCase": 0,
            "UPPER_SNAKE_CASE": 0,
        }

        for name in identifiers:
            if not name:
                continue
            if "_" in name:
                if name.isupper():
                    styles["UPPER_SNAKE_CASE"] += 1
                else:
                    styles["snake_case"] += 1
            elif name[0].isupper():
                styles["PascalCase"] += 1
            elif any(c.isupper() for c in name):
                styles["camelCase"] += 1

        # Return the most common style
        max_style = max(styles, key=styles.get)
        if styles[max_style] > 0:
            return max_style

        return None

    def _detect_file_naming_style(self, file_names: list[str]) -> str:
        """
        Detect file naming convention from a list of file names.

        Returns:
            One of: kebab-case, snake_case, camelCase, PascalCase
        """
        if not file_names:
            return "unknown"

        styles = {"kebab-case": 0, "snake_case": 0, "camelCase": 0, "PascalCase": 0}

        for name in file_names:
            if not name:
                continue
            if "-" in name:
                styles["kebab-case"] += 1
            elif "_" in name:
                styles["snake_case"] += 1
            elif name[0].isupper():
                styles["PascalCase"] += 1
            elif any(c.isupper() for c in name):
                styles["camelCase"] += 1

        # Return the most common style
        max_style = max(styles, key=styles.get)
        if styles[max_style] > 0:
            return max_style

        return "unknown"


def detect_naming_conventions(path: Path, analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Public API to detect naming conventions.

    Args:
        path: Path to project directory
        analysis: Existing analysis dictionary with detected language

    Returns:
        Dictionary containing detected naming conventions
    """
    detector = NamingDetector(path, analysis)
    return detector.detect_naming_conventions()
