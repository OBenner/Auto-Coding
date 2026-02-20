"""
Organization Pattern Detector Module
=====================================

Detects and analyzes code organization patterns in codebases.
Identifies directory structures, file organization, module patterns, and architectural styles.

This module helps agents understand and replicate the organizational conventions
used in a codebase to maintain consistency.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .base import SKIP_DIRS, BaseAnalyzer, collect_files


class OrganizationDetector(BaseAnalyzer):
    """Analyzes and detects code organization patterns."""

    def __init__(self, path: Path):
        super().__init__(path)
        self.organization_patterns: dict[str, Any] = {
            "directory_structure": {},
            "file_organization": {},
            "module_patterns": {},
            "architectural_style": None,
        }

    def detect_organization_patterns(self) -> dict[str, Any]:
        """
        Detect code organization patterns across the codebase.

        Returns:
            Dictionary containing detected organization patterns with keys:
            - directory_structure: How directories are organized (layered, feature-based, etc.)
            - file_organization: File size, naming, and grouping patterns
            - module_patterns: Import organization, dependencies
            - architectural_style: Overall architecture (MVC, hexagonal, etc.)
            - separation_patterns: How concerns are separated
        """
        # Analyze directory structure
        self._analyze_directory_structure()

        # Analyze file organization
        self._analyze_file_organization()

        # Analyze module patterns (for Python projects)
        self._analyze_module_patterns()

        # Infer architectural style
        self._infer_architectural_style()

        # Detect separation patterns
        self._detect_separation_patterns()

        return self._summarize_patterns()

    def _analyze_directory_structure(self) -> None:
        """Analyze how directories are organized."""
        dirs = [
            d
            for d in self.path.rglob("*")
            if d.is_dir() and not any(skip in d.parts for skip in SKIP_DIRS)
        ]

        # Common organizational patterns
        layered_indicators = {
            "controllers",
            "services",
            "models",
            "views",
            "repositories",
            "dao",
            "dto",
            "entities",
        }
        feature_indicators = {"features", "modules", "domains"}
        mvc_indicators = {"models", "views", "controllers"}
        hexagonal_indicators = {"domain", "application", "infrastructure", "adapters"}
        functional_indicators = {
            "handlers",
            "routers",
            "middleware",
            "utils",
            "helpers",
        }

        found_dirs = {d.name.lower() for d in dirs}

        # Detect patterns
        has_layered = len(found_dirs & layered_indicators) >= 2
        has_feature_based = len(found_dirs & feature_indicators) >= 1
        has_mvc = len(found_dirs & mvc_indicators) >= 2
        has_hexagonal = len(found_dirs & hexagonal_indicators) >= 2
        has_functional = len(found_dirs & functional_indicators) >= 3

        # Calculate directory depth statistics
        depths = [len(d.relative_to(self.path).parts) for d in dirs]
        avg_depth = sum(depths) / len(depths) if depths else 0
        max_depth = max(depths) if depths else 0

        self.organization_patterns["directory_structure"] = {
            "has_layered_architecture": has_layered,
            "has_feature_based": has_feature_based,
            "has_mvc": has_mvc,
            "has_hexagonal": has_hexagonal,
            "has_functional": has_functional,
            "average_depth": round(avg_depth, 2),
            "max_depth": max_depth,
            "total_directories": len(dirs),
            "common_directories": sorted(
                [
                    d
                    for d in found_dirs
                    if d
                    in (
                        layered_indicators
                        | feature_indicators
                        | mvc_indicators
                        | hexagonal_indicators
                        | functional_indicators
                    )
                ]
            )[:10],
        }

    def _analyze_file_organization(self) -> None:
        """Analyze how files are organized."""
        # Focus on source code files
        py_files = collect_files(self.path, "*.py")
        js_files = collect_files(self.path, "*.js")
        ts_files = collect_files(self.path, "*.ts")

        all_files = py_files + js_files + ts_files

        if not all_files:
            return

        # Analyze file sizes
        file_sizes = []
        for file in all_files[:100]:  # Sample first 100 files
            try:
                lines = len(file.read_text(encoding="utf-8").splitlines())
                file_sizes.append(lines)
            except (OSError, UnicodeDecodeError):
                continue

        avg_file_size = sum(file_sizes) / len(file_sizes) if file_sizes else 0
        max_file_size = max(file_sizes) if file_sizes else 0

        # Analyze files per directory
        files_per_dir = defaultdict(int)
        for file in all_files:
            parent = file.parent
            files_per_dir[parent] += 1

        avg_files_per_dir = (
            sum(files_per_dir.values()) / len(files_per_dir) if files_per_dir else 0
        )

        # Detect one-class-per-file pattern (for Python)
        classes_per_file = []
        if py_files:
            for file in py_files[:50]:  # Sample
                try:
                    source = file.read_text(encoding="utf-8")
                    tree = ast.parse(source)
                    num_classes = sum(
                        1 for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
                    )
                    classes_per_file.append(num_classes)
                except (OSError, UnicodeDecodeError, SyntaxError):
                    continue

        avg_classes_per_file = (
            sum(classes_per_file) / len(classes_per_file) if classes_per_file else 0
        )
        one_class_per_file = avg_classes_per_file <= 1.5  # Allow some flexibility

        self.organization_patterns["file_organization"] = {
            "average_file_size_lines": round(avg_file_size),
            "max_file_size_lines": max_file_size,
            "average_files_per_directory": round(avg_files_per_dir, 2),
            "one_class_per_file": one_class_per_file,
            "average_classes_per_file": round(avg_classes_per_file, 2),
            "total_source_files": len(all_files),
        }

    def _analyze_module_patterns(self) -> None:
        """Analyze module organization patterns (Python-specific)."""
        py_files = collect_files(self.path, "*.py")

        if not py_files:
            return

        import_patterns = {
            "relative_imports": 0,
            "absolute_imports": 0,
            "wildcard_imports": 0,
            "grouped_imports": 0,
        }

        common_imports = Counter()
        imports_per_file = []

        for file in py_files[:50]:  # Sample
            try:
                source = file.read_text(encoding="utf-8")
                tree = ast.parse(source)

                file_imports = 0
                import_groups = []
                last_import_line = -1

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        file_imports += 1
                        import_patterns["absolute_imports"] += 1
                        for alias in node.names:
                            common_imports[alias.name.split(".")[0]] += 1

                        # Check if imports are grouped
                        if (
                            last_import_line >= 0
                            and node.lineno - last_import_line <= 2
                        ):
                            import_groups.append(True)
                        last_import_line = node.lineno

                    elif isinstance(node, ast.ImportFrom):
                        file_imports += 1
                        if node.level > 0:
                            import_patterns["relative_imports"] += 1
                        else:
                            import_patterns["absolute_imports"] += 1

                        if node.module:
                            common_imports[node.module.split(".")[0]] += 1

                        # Check for wildcard imports
                        for alias in node.names:
                            if alias.name == "*":
                                import_patterns["wildcard_imports"] += 1

                        # Check if imports are grouped
                        if (
                            last_import_line >= 0
                            and node.lineno - last_import_line <= 2
                        ):
                            import_groups.append(True)
                        last_import_line = node.lineno

                imports_per_file.append(file_imports)
                if len(import_groups) > 0:
                    import_patterns["grouped_imports"] += 1

            except (OSError, UnicodeDecodeError, SyntaxError):
                continue

        avg_imports_per_file = (
            sum(imports_per_file) / len(imports_per_file) if imports_per_file else 0
        )

        # Determine import style preference
        total_imports = (
            import_patterns["relative_imports"] + import_patterns["absolute_imports"]
        )
        prefers_relative = (
            import_patterns["relative_imports"] / total_imports > 0.5
            if total_imports > 0
            else False
        )

        self.organization_patterns["module_patterns"] = {
            "average_imports_per_file": round(avg_imports_per_file, 2),
            "prefers_relative_imports": prefers_relative,
            "uses_wildcard_imports": import_patterns["wildcard_imports"] > 0,
            "groups_imports": import_patterns["grouped_imports"]
            > len(py_files[:50]) * 0.5,
            "common_dependencies": [
                {"module": module, "count": count}
                for module, count in common_imports.most_common(10)
            ],
            "import_statistics": {
                "relative": import_patterns["relative_imports"],
                "absolute": import_patterns["absolute_imports"],
                "wildcard": import_patterns["wildcard_imports"],
            },
        }

    def _infer_architectural_style(self) -> None:
        """Infer the overall architectural style from detected patterns."""
        dir_structure = self.organization_patterns["directory_structure"]

        styles = []

        if dir_structure.get("has_mvc"):
            styles.append("MVC")
        if dir_structure.get("has_layered_architecture"):
            styles.append("Layered")
        if dir_structure.get("has_hexagonal"):
            styles.append("Hexagonal/Clean")
        if dir_structure.get("has_feature_based"):
            styles.append("Feature-based")
        if dir_structure.get("has_functional"):
            styles.append("Functional")

        # Determine primary style
        if len(styles) == 0:
            primary_style = "Flat/Unknown"
        elif len(styles) == 1:
            primary_style = styles[0]
        else:
            # Multiple patterns - take the most specific
            if "Hexagonal/Clean" in styles:
                primary_style = "Hexagonal/Clean"
            elif "MVC" in styles:
                primary_style = "MVC"
            elif "Feature-based" in styles:
                primary_style = "Feature-based"
            else:
                primary_style = "Hybrid"

        self.organization_patterns["architectural_style"] = {
            "primary": primary_style,
            "detected_patterns": styles,
        }

    def _detect_separation_patterns(self) -> None:
        """Detect how concerns are separated in the codebase."""
        # Look for common separation patterns
        config_locations = []
        constants_locations = []
        test_locations = []

        for path_str in ["config", "settings", "configuration", ".env"]:
            if self._exists(path_str):
                config_locations.append(path_str)

        for path_str in ["constants", "const", "enums"]:
            if self._exists(path_str):
                constants_locations.append(path_str)

        for path_str in ["tests", "test", "__tests__", "spec"]:
            if self._exists(path_str):
                test_locations.append(path_str)

        # Check if tests are colocated or separate
        tests_colocated = any(
            f.name.startswith("test_") or f.name.endswith("_test.py")
            for f in self.path.rglob("*.py")
            if f.parent.name not in ["tests", "test", "__tests__"]
        )

        self.organization_patterns["separation_patterns"] = {
            "config_centralized": len(config_locations) > 0,
            "config_locations": config_locations,
            "constants_centralized": len(constants_locations) > 0,
            "constants_locations": constants_locations,
            "tests_separate": len(test_locations) > 0,
            "tests_colocated": tests_colocated,
            "test_locations": test_locations,
        }

    def _summarize_patterns(self) -> dict[str, Any]:
        """Summarize detected organization patterns into actionable insights."""
        return {
            "architectural_style": self.organization_patterns["architectural_style"],
            "directory_organization": {
                "depth": {
                    "average": self.organization_patterns["directory_structure"].get(
                        "average_depth"
                    ),
                    "max": self.organization_patterns["directory_structure"].get(
                        "max_depth"
                    ),
                },
                "common_dirs": self.organization_patterns["directory_structure"].get(
                    "common_directories", []
                ),
                "patterns": {
                    "layered": self.organization_patterns["directory_structure"].get(
                        "has_layered_architecture"
                    ),
                    "feature_based": self.organization_patterns[
                        "directory_structure"
                    ].get("has_feature_based"),
                    "mvc": self.organization_patterns["directory_structure"].get(
                        "has_mvc"
                    ),
                },
            },
            "file_organization": {
                "file_size": {
                    "average_lines": self.organization_patterns[
                        "file_organization"
                    ].get("average_file_size_lines"),
                    "max_lines": self.organization_patterns["file_organization"].get(
                        "max_file_size_lines"
                    ),
                },
                "one_class_per_file": self.organization_patterns[
                    "file_organization"
                ].get("one_class_per_file"),
                "files_per_directory": self.organization_patterns[
                    "file_organization"
                ].get("average_files_per_directory"),
            },
            "module_organization": self.organization_patterns.get(
                "module_patterns", {}
            ),
            "separation_of_concerns": self.organization_patterns.get(
                "separation_patterns", {}
            ),
        }


def detect_organization_patterns(path: Path) -> dict[str, Any]:
    """
    Public API to detect code organization patterns in a codebase.

    Args:
        path: Path to project directory

    Returns:
        Dictionary containing detected organization patterns
    """
    detector = OrganizationDetector(path)
    return detector.detect_organization_patterns()
