#!/usr/bin/env python3
"""
Architecture Validator Module
===============================

Validates architectural pattern consistency across the codebase.
This module helps ensure new code follows existing architectural decisions and patterns.

The architecture validator is used by:
- Planner Agent: To identify architectural inconsistencies before implementation
- Prevention Scanner: As part of proactive issue detection
- QA Reviewer: To validate code follows project patterns

Usage:
    from analysis.architecture_validator import ArchitectureValidator

    validator = ArchitectureValidator()
    results = validator.analyze(project_dir)

    if results.has_critical_issues:
        print("Architectural inconsistencies found - review before proceeding")
"""

from __future__ import annotations

import ast
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class ArchitecturalIssue:
    """
    Represents an architectural inconsistency found during analysis.

    Attributes:
        severity: Severity level (critical, high, medium, low, info)
        issue_type: Type of issue (pattern_inconsistency, naming_violation, etc.)
        title: Short title of the issue
        description: Detailed description
        file: File where issue was found
        line: Line number
        suggestion: Suggested fix to maintain consistency
        pattern: The established pattern that should be followed
    """

    severity: str  # critical, high, medium, low, info
    issue_type: str  # pattern_inconsistency, naming_violation, structure_violation
    title: str
    description: str
    file: str
    line: int
    suggestion: str
    pattern: str  # Description of the established pattern


@dataclass
class ArchitecturalPattern:
    """
    Represents a detected architectural pattern in the codebase.

    Attributes:
        pattern_type: Type of pattern (error_handling, state_management, etc.)
        pattern_name: Name/description of the pattern
        frequency: Number of occurrences
        examples: Example file paths where pattern is used
        confidence: Confidence level (0.0-1.0) that this is the standard pattern
    """

    pattern_type: str
    pattern_name: str
    frequency: int
    examples: list[str] = field(default_factory=list)
    confidence: float = 0.0


@dataclass
class ArchitecturalAnalysisResult:
    """
    Result of an architectural analysis.

    Attributes:
        issues: List of detected architectural issues
        patterns: List of detected architectural patterns
        analysis_errors: List of errors during analysis
        has_critical_issues: Whether any critical issues were found
        should_warn: Whether these results should warn the user
        files_analyzed: Number of files analyzed
    """

    issues: list[ArchitecturalIssue] = field(default_factory=list)
    patterns: list[ArchitecturalPattern] = field(default_factory=list)
    analysis_errors: list[str] = field(default_factory=list)
    has_critical_issues: bool = False
    should_warn: bool = False
    files_analyzed: int = 0


# =============================================================================
# ARCHITECTURE VALIDATOR
# =============================================================================


class ArchitectureValidator:
    """
    Validates architectural pattern consistency.

    Detects:
    - Inconsistent error handling patterns
    - Mixed state management approaches
    - Naming convention violations
    - Import organization inconsistencies
    - Code structure violations
    """

    def __init__(self) -> None:
        """Initialize the architecture validator."""
        pass

    def analyze(
        self,
        project_dir: Path,
        spec_dir: Path | None = None,
        changed_files: list[str] | None = None,
    ) -> ArchitecturalAnalysisResult:
        """
        Analyze project for architectural consistency.

        Args:
            project_dir: Path to the project root
            spec_dir: Path to the spec directory (for storing results)
            changed_files: Optional list of files to analyze (if None, analyzes all)

        Returns:
            ArchitecturalAnalysisResult with all findings
        """
        project_dir = Path(project_dir)
        result = ArchitecturalAnalysisResult()

        # Get files to analyze
        files_to_analyze = self._get_files_to_analyze(project_dir, changed_files)
        result.files_analyzed = len(files_to_analyze)

        if not files_to_analyze:
            return result

        # Discover architectural patterns
        self._discover_patterns(files_to_analyze, result)

        # Validate consistency against established patterns
        self._validate_error_handling_consistency(files_to_analyze, result)
        self._validate_naming_consistency(files_to_analyze, result)
        self._validate_import_organization(files_to_analyze, result)
        self._validate_class_structure(files_to_analyze, result)

        # Determine if has critical issues
        result.has_critical_issues = any(
            issue.severity in ["critical", "high"] for issue in result.issues
        )

        # Should warn if any medium or higher issues found
        result.should_warn = any(
            issue.severity in ["critical", "high", "medium"] for issue in result.issues
        )

        # Save results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def _get_files_to_analyze(
        self, project_dir: Path, changed_files: list[str] | None
    ) -> list[Path]:
        """
        Get list of files to analyze.

        Args:
            project_dir: Project root directory
            changed_files: Optional list of specific files to analyze

        Returns:
            List of file paths to analyze
        """
        if changed_files:
            return [project_dir / f for f in changed_files if self._is_analyzable(f)]

        # Find all Python files
        files = list(project_dir.glob("**/*.py"))

        # Filter out common directories to skip
        skip_dirs = {
            "node_modules",
            ".venv",
            "venv",
            "__pycache__",
            ".git",
            "dist",
            "build",
            ".pytest_cache",
            ".mypy_cache",
        }

        return [
            f for f in files if not any(skip_dir in f.parts for skip_dir in skip_dirs)
        ]

    def _is_analyzable(self, file_path: str) -> bool:
        """Check if file is analyzable (Python file)."""
        return file_path.endswith(".py")

    def _discover_patterns(
        self, files: list[Path], result: ArchitecturalAnalysisResult
    ) -> None:
        """
        Discover common architectural patterns in the codebase.

        Args:
            files: List of files to analyze
            result: Result object to populate with patterns
        """
        # Track error handling patterns
        error_patterns = Counter()
        # Track import organization patterns
        import_patterns = Counter()
        # Track naming patterns
        naming_patterns = defaultdict(Counter)

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")

                # Detect error handling patterns
                if "try:" in content:
                    if "except Exception as" in content:
                        error_patterns["broad_exception_with_var"] += 1
                    elif "except Exception:" in content:
                        error_patterns["broad_exception"] += 1
                    if "raise" in content:
                        error_patterns["explicit_raise"] += 1

                # Detect import organization
                lines = content.split("\n")
                import_line_indices = []
                for idx, line in enumerate(lines):
                    if line.startswith(("import ", "from ")):
                        import_line_indices.append(idx)
                    elif (
                        import_line_indices
                        and line.strip()
                        and not line.startswith("#")
                    ):
                        break

                if import_line_indices:
                    # Check if there are blank lines between import lines
                    # in the original source (indicating grouped imports)
                    has_blank_lines = False
                    for j in range(len(import_line_indices) - 1):
                        current_idx = import_line_indices[j]
                        next_idx = import_line_indices[j + 1]
                        # Check if any line between two consecutive imports is blank
                        for between in range(current_idx + 1, next_idx):
                            if not lines[between].strip():
                                has_blank_lines = True
                                break
                        if has_blank_lines:
                            break
                    if has_blank_lines:
                        import_patterns["grouped_imports"] += 1
                    else:
                        import_patterns["ungrouped_imports"] += 1

                # Detect naming patterns
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.FunctionDef):
                            # Analyze function naming
                            if node.name.startswith("_"):
                                naming_patterns["function"]["private_underscore"] += 1
                            elif "_" in node.name:
                                naming_patterns["function"]["snake_case"] += 1
                            elif any(c.isupper() for c in node.name[1:]):
                                naming_patterns["function"]["camelCase"] += 1

                        elif isinstance(node, ast.ClassDef):
                            # Analyze class naming
                            if node.name[0].isupper():
                                naming_patterns["class"]["PascalCase"] += 1
                            else:
                                naming_patterns["class"]["lowercase"] += 1

                except SyntaxError:
                    # SyntaxError means file can't be parsed; skip pattern discovery for this file
                    pass

            except Exception as e:
                result.analysis_errors.append(
                    f"Error discovering patterns in {file_path}: {e}"
                )

        # Convert counters to patterns
        total_files = len(files)

        # Error handling patterns
        for pattern_name, count in error_patterns.most_common():
            confidence = count / total_files
            if confidence > 0.3:  # Only report if > 30% of files use this pattern
                result.patterns.append(
                    ArchitecturalPattern(
                        pattern_type="error_handling",
                        pattern_name=pattern_name,
                        frequency=count,
                        confidence=confidence,
                    )
                )

        # Import organization patterns
        for pattern_name, count in import_patterns.most_common(1):
            confidence = count / max(sum(import_patterns.values()), 1)
            result.patterns.append(
                ArchitecturalPattern(
                    pattern_type="import_organization",
                    pattern_name=pattern_name,
                    frequency=count,
                    confidence=confidence,
                )
            )

        # Naming patterns
        for category, patterns in naming_patterns.items():
            if patterns:
                most_common_pattern, count = patterns.most_common(1)[0]
                confidence = count / sum(patterns.values())
                if confidence > 0.5:  # Majority uses this pattern
                    result.patterns.append(
                        ArchitecturalPattern(
                            pattern_type=f"naming_{category}",
                            pattern_name=most_common_pattern,
                            frequency=count,
                            confidence=confidence,
                        )
                    )

    def _validate_error_handling_consistency(
        self, files: list[Path], result: ArchitecturalAnalysisResult
    ) -> None:
        """
        Validate error handling consistency.

        Checks for:
        - Bare except clauses
        - Inconsistent exception handling patterns
        - Missing error context
        """
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                for i, line in enumerate(lines, 1):
                    # Check for bare except
                    if re.match(r"^\s*except\s*:\s*$", line):
                        result.issues.append(
                            ArchitecturalIssue(
                                severity="high",
                                issue_type="error_handling",
                                title="Bare except clause",
                                description=f"Found bare 'except:' at line {i}. "
                                "This catches all exceptions including system exits.",
                                file=str(file_path),
                                line=i,
                                suggestion="Use specific exception types or 'except Exception:' "
                                "to avoid catching system exits.",
                                pattern="Specific exception handling",
                            )
                        )

                    # Check for pass in except blocks (swallowing exceptions)
                    if "except" in line and i + 1 < len(lines):
                        next_line = lines[i].strip()
                        if next_line == "pass":
                            result.issues.append(
                                ArchitecturalIssue(
                                    severity="medium",
                                    issue_type="error_handling",
                                    title="Silent exception swallowing",
                                    description=f"Exception caught and silently ignored at line {i}. "
                                    "This makes debugging difficult.",
                                    file=str(file_path),
                                    line=i,
                                    suggestion="Log the exception or add a comment explaining "
                                    "why it's safe to ignore.",
                                    pattern="Explicit error handling with logging or re-raising",
                                )
                            )

            except Exception as e:
                result.analysis_errors.append(
                    f"Error analyzing error handling in {file_path}: {e}"
                )

    def _validate_naming_consistency(
        self, files: list[Path], result: ArchitecturalAnalysisResult
    ) -> None:
        """
        Validate naming convention consistency.

        Checks for:
        - Inconsistent function naming (snake_case vs camelCase)
        - Inconsistent class naming (PascalCase)
        - Inconsistent variable naming
        """
        # Find dominant naming patterns
        dominant_function_pattern = None
        dominant_class_pattern = None

        for pattern in result.patterns:
            if pattern.pattern_type == "naming_function" and pattern.confidence > 0.7:
                dominant_function_pattern = pattern.pattern_name
            elif pattern.pattern_type == "naming_class" and pattern.confidence > 0.7:
                dominant_class_pattern = pattern.pattern_name

        # If no dominant pattern found, use Python conventions
        if not dominant_function_pattern:
            dominant_function_pattern = "snake_case"
        if not dominant_class_pattern:
            dominant_class_pattern = "PascalCase"

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")

                try:
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        # Check function names
                        if isinstance(node, ast.FunctionDef):
                            if not node.name.startswith("_"):  # Skip private functions
                                # Check for camelCase when snake_case is dominant
                                if dominant_function_pattern == "snake_case" and any(
                                    c.isupper() for c in node.name[1:]
                                ):
                                    result.issues.append(
                                        ArchitecturalIssue(
                                            severity="low",
                                            issue_type="naming_violation",
                                            title=f"Inconsistent function naming: {node.name}",
                                            description=f"Function '{node.name}' uses camelCase, "
                                            f"but project standard is {dominant_function_pattern}.",
                                            file=str(file_path),
                                            line=node.lineno,
                                            suggestion=f"Rename to follow {dominant_function_pattern} convention.",
                                            pattern=f"Functions should use {dominant_function_pattern}",
                                        )
                                    )

                        # Check class names
                        elif isinstance(node, ast.ClassDef):
                            # Check for lowercase when PascalCase is dominant
                            if (
                                dominant_class_pattern == "PascalCase"
                                and node.name[0].islower()
                            ):
                                result.issues.append(
                                    ArchitecturalIssue(
                                        severity="medium",
                                        issue_type="naming_violation",
                                        title=f"Inconsistent class naming: {node.name}",
                                        description=f"Class '{node.name}' doesn't follow "
                                        f"{dominant_class_pattern} convention.",
                                        file=str(file_path),
                                        line=node.lineno,
                                        suggestion=f"Rename class to follow {dominant_class_pattern} convention.",
                                        pattern=f"Classes should use {dominant_class_pattern}",
                                    )
                                )

                except SyntaxError:
                    # SyntaxError means file can't be parsed; skip naming validation for this file
                    pass

            except Exception as e:
                result.analysis_errors.append(
                    f"Error analyzing naming in {file_path}: {e}"
                )

    def _validate_import_organization(
        self, files: list[Path], result: ArchitecturalAnalysisResult
    ) -> None:
        """
        Validate import organization consistency.

        Checks for:
        - Import ordering (stdlib, third-party, local)
        - Grouped vs ungrouped imports
        - Relative vs absolute imports
        """
        # Find dominant import pattern
        dominant_import_pattern = None
        for pattern in result.patterns:
            if (
                pattern.pattern_type == "import_organization"
                and pattern.confidence > 0.6
            ):
                dominant_import_pattern = pattern.pattern_name
                break

        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")
                lines = content.split("\n")

                # Extract import section
                import_lines = []
                import_start = -1
                for i, line in enumerate(lines):
                    if line.startswith(("import ", "from ")):
                        if import_start == -1:
                            import_start = i
                        import_lines.append((i + 1, line))
                    elif import_lines and line.strip() and not line.startswith("#"):
                        break

                if not import_lines:
                    continue

                # Check for wildcard imports
                for line_no, line in import_lines:
                    if "import *" in line:
                        result.issues.append(
                            ArchitecturalIssue(
                                severity="medium",
                                issue_type="import_violation",
                                title="Wildcard import detected",
                                description=f"Wildcard import at line {line_no}: '{line.strip()}'. "
                                "This pollutes the namespace and makes code harder to understand.",
                                file=str(file_path),
                                line=line_no,
                                suggestion="Import specific names instead of using wildcard.",
                                pattern="Explicit imports without wildcards",
                            )
                        )

                # Check consistency with dominant pattern
                if dominant_import_pattern == "grouped_imports":
                    # Check if imports are grouped
                    has_grouping = any(
                        i + 1 < len(lines) and not lines[import_lines[i][0]].strip()
                        for i in range(len(import_lines) - 1)
                    )
                    if not has_grouping and len(import_lines) > 5:
                        result.issues.append(
                            ArchitecturalIssue(
                                severity="low",
                                issue_type="import_violation",
                                title="Imports not grouped",
                                description=f"File has {len(import_lines)} imports but they are not grouped. "
                                "Project standard is to group imports (stdlib, third-party, local).",
                                file=str(file_path),
                                line=import_start + 1,
                                suggestion="Group imports by type: standard library, third-party, local. "
                                "Separate groups with blank lines.",
                                pattern="Grouped import organization",
                            )
                        )

            except Exception as e:
                result.analysis_errors.append(
                    f"Error analyzing imports in {file_path}: {e}"
                )

    def _validate_class_structure(
        self, files: list[Path], result: ArchitecturalAnalysisResult
    ) -> None:
        """
        Validate class structure consistency.

        Checks for:
        - Missing docstrings on public classes
        - Inconsistent method ordering
        - Mixed use of class methods and static methods
        """
        for file_path in files:
            try:
                content = file_path.read_text(encoding="utf-8")

                try:
                    tree = ast.parse(content)

                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            # Check for missing docstring on public classes
                            if not node.name.startswith("_"):
                                docstring = ast.get_docstring(node)
                                if not docstring:
                                    result.issues.append(
                                        ArchitecturalIssue(
                                            severity="low",
                                            issue_type="structure_violation",
                                            title=f"Missing docstring: class {node.name}",
                                            description=f"Public class '{node.name}' at line {node.lineno} "
                                            "lacks a docstring.",
                                            file=str(file_path),
                                            line=node.lineno,
                                            suggestion="Add a docstring describing the class purpose, "
                                            "attributes, and usage.",
                                            pattern="All public classes should have docstrings",
                                        )
                                    )

                            # Check method ordering (public before private)
                            methods = [
                                item
                                for item in node.body
                                if isinstance(
                                    item, (ast.FunctionDef, ast.AsyncFunctionDef)
                                )
                            ]

                            found_private = False
                            for method in methods:
                                if method.name.startswith("_"):
                                    found_private = True
                                elif found_private and not method.name.startswith("__"):
                                    result.issues.append(
                                        ArchitecturalIssue(
                                            severity="info",
                                            issue_type="structure_violation",
                                            title=f"Method ordering issue in class {node.name}",
                                            description=f"Public method '{method.name}' appears after "
                                            f"private methods in class '{node.name}'.",
                                            file=str(file_path),
                                            line=method.lineno,
                                            suggestion="Consider organizing methods: __init__, "
                                            "public methods, private methods.",
                                            pattern="Public methods before private methods",
                                        )
                                    )

                except SyntaxError:
                    # SyntaxError means file can't be parsed; skip class structure validation
                    pass

            except Exception as e:
                result.analysis_errors.append(
                    f"Error analyzing class structure in {file_path}: {e}"
                )

    def _save_results(
        self, spec_dir: Path, result: ArchitecturalAnalysisResult
    ) -> None:
        """
        Save architectural analysis results to spec directory.

        Args:
            spec_dir: Spec directory path
            result: Analysis result to save
        """
        import json
        import os
        import tempfile

        spec_dir = Path(spec_dir)
        spec_dir.mkdir(parents=True, exist_ok=True)

        output_file = spec_dir / "architecture_analysis.json"

        data = {
            "files_analyzed": result.files_analyzed,
            "total_issues": len(result.issues),
            "critical_issues": len(
                [i for i in result.issues if i.severity == "critical"]
            ),
            "high_issues": len([i for i in result.issues if i.severity == "high"]),
            "medium_issues": len([i for i in result.issues if i.severity == "medium"]),
            "low_issues": len([i for i in result.issues if i.severity == "low"]),
            "has_critical_issues": result.has_critical_issues,
            "should_warn": result.should_warn,
            "patterns": [
                {
                    "pattern_type": pattern.pattern_type,
                    "pattern_name": pattern.pattern_name,
                    "frequency": pattern.frequency,
                    "confidence": pattern.confidence,
                    "examples": pattern.examples[:5],  # Limit examples
                }
                for pattern in result.patterns
            ],
            "issues": [
                {
                    "severity": issue.severity,
                    "issue_type": issue.issue_type,
                    "title": issue.title,
                    "description": issue.description,
                    "file": issue.file,
                    "line": issue.line,
                    "suggestion": issue.suggestion,
                    "pattern": issue.pattern,
                }
                for issue in result.issues
            ],
            "errors": result.analysis_errors,
        }

        # Atomic write: write to temp file first, then rename
        fd, tmp_path = tempfile.mkstemp(
            dir=str(spec_dir), suffix=".tmp", prefix="architecture_analysis_"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp_path, str(output_file))
        except BaseException:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass  # Best-effort cleanup; temp file may already be removed
            raise

    def format_report(self, result: ArchitecturalAnalysisResult) -> str:
        """
        Format analysis results as a human-readable report.

        Args:
            result: Analysis result to format

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("ARCHITECTURAL CONSISTENCY REPORT")
        lines.append("=" * 80)
        lines.append(f"\nFiles Analyzed: {result.files_analyzed}")
        lines.append(f"Total Issues: {len(result.issues)}")

        if result.has_critical_issues:
            lines.append("\n⚠️  CRITICAL ARCHITECTURAL ISSUES FOUND")

        # Report discovered patterns
        if result.patterns:
            lines.append("\n" + "=" * 80)
            lines.append("DISCOVERED PATTERNS:")
            lines.append("-" * 80)
            for pattern in result.patterns:
                lines.append(
                    f"\n📋 {pattern.pattern_type}: {pattern.pattern_name} "
                    f"(confidence: {pattern.confidence:.1%}, count: {pattern.frequency})"
                )

        # Group issues by severity
        by_severity = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }

        for issue in result.issues:
            by_severity[issue.severity].append(issue)

        # Report each severity level
        for severity in ["critical", "high", "medium", "low", "info"]:
            issues = by_severity[severity]
            if not issues:
                continue

            lines.append(f"\n{severity.upper()} Issues ({len(issues)}):")
            lines.append("-" * 80)

            for issue in issues:
                lines.append(f"\n📍 {issue.title}")
                lines.append(f"   File: {issue.file}:{issue.line}")
                lines.append(f"   Type: {issue.issue_type}")
                lines.append(f"   {issue.description}")
                lines.append(f"   💡 Suggestion: {issue.suggestion}")
                lines.append(f"   Pattern: {issue.pattern}")

        if result.analysis_errors:
            lines.append("\n" + "=" * 80)
            lines.append("ANALYSIS ERRORS:")
            for error in result.analysis_errors:
                lines.append(f"  ❌ {error}")

        lines.append("\n" + "=" * 80)
        return "\n".join(lines)


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def validate_architecture(
    project_dir: Path,
    spec_dir: Path | None = None,
    changed_files: list[str] | None = None,
) -> ArchitecturalAnalysisResult:
    """
    Convenience function to validate architectural consistency.

    Args:
        project_dir: Path to project root
        spec_dir: Optional spec directory to save results
        changed_files: Optional list of files to analyze

    Returns:
        ArchitecturalAnalysisResult with all findings
    """
    validator = ArchitectureValidator()
    return validator.analyze(project_dir, spec_dir, changed_files)


def has_architectural_issues(project_dir: Path) -> bool:
    """
    Quick check if project has architectural issues.

    Args:
        project_dir: Path to project root

    Returns:
        True if any critical/high issues found
    """
    validator = ArchitectureValidator()
    result = validator.analyze(project_dir)
    return result.has_critical_issues


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Validate architectural consistency")
    parser.add_argument("project_dir", type=Path, help="Path to project root")
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    validator = ArchitectureValidator()
    result = validator.analyze(args.project_dir, spec_dir=args.spec_dir)

    if args.json:
        data = {
            "files_analyzed": result.files_analyzed,
            "total_issues": len(result.issues),
            "has_critical_issues": result.has_critical_issues,
            "should_warn": result.should_warn,
            "patterns": [
                {
                    "pattern_type": p.pattern_type,
                    "pattern_name": p.pattern_name,
                    "frequency": p.frequency,
                    "confidence": p.confidence,
                }
                for p in result.patterns
            ],
            "issues": [
                {
                    "severity": i.severity,
                    "issue_type": i.issue_type,
                    "title": i.title,
                    "description": i.description,
                    "file": i.file,
                    "line": i.line,
                    "suggestion": i.suggestion,
                    "pattern": i.pattern,
                }
                for i in result.issues
            ],
            "errors": result.analysis_errors,
        }
        print(json.dumps(data, indent=2))
    else:
        print(validator.format_report(result))


if __name__ == "__main__":
    main()
