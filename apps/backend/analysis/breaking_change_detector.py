#!/usr/bin/env python3
"""
Breaking Change Detector Module
=================================

Analyzes code changes to detect breaking API contract violations.
This module helps prevent breaking changes before code is merged.

The breaking change detector is used by:
- Planner Agent: To identify potential breaking changes before implementation
- Prevention Scanner: As part of proactive issue detection
- QA Reviewer: To validate API contract stability

Usage:
    from analysis.breaking_change_detector import BreakingChangeDetector

    detector = BreakingChangeDetector()
    results = detector.analyze(old_code_dir, new_code_dir)

    if results.has_breaking_changes:
        print("Breaking changes detected - review before proceeding")
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class BreakingChange:
    """
    Represents a breaking change found during analysis.

    Attributes:
        severity: Severity level (critical, high, medium, low, info)
        change_type: Type of change (removed_function, signature_change, etc.)
        title: Short title of the breaking change
        description: Detailed description
        file: File where change was found
        old_signature: Original signature/definition
        new_signature: New signature/definition (None if removed)
        migration_guide: Suggested migration path
    """

    severity: str  # critical, high, medium, low, info
    change_type: str  # removed_function, signature_change, removed_class, etc.
    title: str
    description: str
    file: str
    old_signature: str
    new_signature: str | None = None
    migration_guide: str = ""


@dataclass
class BreakingChangeResult:
    """
    Result of a breaking change analysis.

    Attributes:
        breaking_changes: List of detected breaking changes
        analysis_errors: List of errors during analysis
        has_breaking_changes: Whether any breaking changes were found
        should_block: Whether these changes should block deployment
        files_analyzed: Number of files analyzed
    """

    breaking_changes: list[BreakingChange] = field(default_factory=list)
    analysis_errors: list[str] = field(default_factory=list)
    has_breaking_changes: bool = False
    should_block: bool = False
    files_analyzed: int = 0


@dataclass
class ApiElement:
    """
    Represents a public API element (function, class, method).

    Attributes:
        name: Element name
        element_type: Type (function, class, method)
        signature: Full signature
        params: List of parameter names
        param_types: Dictionary of parameter type annotations
        return_type: Return type annotation if available
        decorators: List of decorator names
        is_async: Whether function/method is async
        docstring: Docstring if available
    """

    name: str
    element_type: str  # function, class, method
    signature: str
    params: list[str] = field(default_factory=list)
    param_types: dict[str, str] = field(default_factory=dict)
    return_type: str | None = None
    decorators: list[str] = field(default_factory=list)
    is_async: bool = False
    docstring: str | None = None
    required_params: list[str] = field(default_factory=list)
    optional_params: list[str] = field(default_factory=list)


# =============================================================================
# BREAKING CHANGE DETECTOR
# =============================================================================


class BreakingChangeDetector:
    """
    Detects breaking changes in API contracts.

    Compares two versions of code to find:
    - Removed public functions/classes/methods
    - Changed function signatures (parameters, return types)
    - Changed exception handling
    - Removed or changed decorators that affect behavior
    """

    def __init__(self) -> None:
        """Initialize the breaking change detector."""
        pass

    def analyze(
        self,
        old_dir: Path | None = None,
        new_dir: Path | None = None,
        old_files: dict[str, str] | None = None,
        new_files: dict[str, str] | None = None,
        spec_dir: Path | None = None,
    ) -> BreakingChangeResult:
        """
        Analyze code changes for breaking API contracts.

        Can work in two modes:
        1. Directory comparison: Compare two directory trees
        2. File content comparison: Compare dictionaries of file contents

        Args:
            old_dir: Path to old version of code
            new_dir: Path to new version of code
            old_files: Dictionary mapping file paths to old content
            new_files: Dictionary mapping file paths to new content
            spec_dir: Path to spec directory (for storing results)

        Returns:
            BreakingChangeResult with all findings
        """
        result = BreakingChangeResult()

        # Determine analysis mode
        if old_files is not None and new_files is not None:
            # File content mode
            self._analyze_file_dicts(old_files, new_files, result)
        elif old_dir is not None and new_dir is not None:
            # Directory comparison mode
            self._analyze_directories(Path(old_dir), Path(new_dir), result)
        else:
            result.analysis_errors.append(
                "Must provide either (old_dir, new_dir) or (old_files, new_files)"
            )
            return result

        # Determine if has breaking changes
        result.has_breaking_changes = len(result.breaking_changes) > 0

        # Should block if any critical or high severity breaking changes
        result.should_block = any(
            change.severity in ["critical", "high"]
            for change in result.breaking_changes
        )

        # Save results if spec_dir provided
        if spec_dir:
            self._save_results(spec_dir, result)

        return result

    def analyze_file_change(
        self, old_content: str, new_content: str, file_path: str
    ) -> list[BreakingChange]:
        """
        Analyze a single file for breaking changes.

        Args:
            old_content: Original file content
            new_content: New file content
            file_path: File path for reporting

        Returns:
            List of breaking changes found
        """
        changes = []

        try:
            # Extract API elements from both versions
            old_api = self._extract_api_elements(old_content)
            new_api = self._extract_api_elements(new_content)

            # Compare APIs
            changes.extend(self._compare_apis(old_api, new_api, file_path))

        except SyntaxError:
            # Can't parse source code - skip this file
            pass

        return changes

    def _analyze_directories(
        self, old_dir: Path, new_dir: Path, result: BreakingChangeResult
    ) -> None:
        """
        Compare two directory trees for breaking changes.

        Args:
            old_dir: Old version directory
            new_dir: New version directory
            result: Result object to populate
        """
        # Find all Python files in old directory
        old_files = {str(f.relative_to(old_dir)): f for f in old_dir.glob("**/*.py")}

        # Find all Python files in new directory
        new_files = {str(f.relative_to(new_dir)): f for f in new_dir.glob("**/*.py")}

        # Check for removed files (potential breaking change)
        removed_files = set(old_files.keys()) - set(new_files.keys())
        for file_path in removed_files:
            # Read old file to see if it had public APIs
            try:
                old_content = old_files[file_path].read_text(encoding="utf-8")
                old_api = self._extract_api_elements(old_content)

                if old_api:
                    result.breaking_changes.append(
                        BreakingChange(
                            severity="critical",
                            change_type="removed_file",
                            title=f"File Removed: {file_path}",
                            description=f"File {file_path} was removed, which contained {len(old_api)} public API element(s).",
                            file=file_path,
                            old_signature=f"{len(old_api)} API elements",
                            new_signature=None,
                            migration_guide="Restore the file or provide alternative APIs.",
                        )
                    )

            except Exception as e:
                result.analysis_errors.append(
                    f"Error reading removed file {file_path}: {e}"
                )

        # Compare files that exist in both versions
        common_files = set(old_files.keys()) & set(new_files.keys())
        result.files_analyzed = len(common_files)

        for file_path in common_files:
            try:
                old_content = old_files[file_path].read_text(encoding="utf-8")
                new_content = new_files[file_path].read_text(encoding="utf-8")

                changes = self.analyze_file_change(old_content, new_content, file_path)
                result.breaking_changes.extend(changes)

            except Exception as e:
                result.analysis_errors.append(f"Error analyzing {file_path}: {e}")

    def _analyze_file_dicts(
        self,
        old_files: dict[str, str],
        new_files: dict[str, str],
        result: BreakingChangeResult,
    ) -> None:
        """
        Compare file content dictionaries for breaking changes.

        Args:
            old_files: Dictionary mapping file paths to old content
            new_files: Dictionary mapping file paths to new content
            result: Result object to populate
        """
        # Check for removed files
        removed_files = set(old_files.keys()) - set(new_files.keys())
        for file_path in removed_files:
            try:
                old_api = self._extract_api_elements(old_files[file_path])

                if old_api:
                    result.breaking_changes.append(
                        BreakingChange(
                            severity="critical",
                            change_type="removed_file",
                            title=f"File Removed: {file_path}",
                            description=f"File {file_path} was removed, which contained {len(old_api)} public API element(s).",
                            file=file_path,
                            old_signature=f"{len(old_api)} API elements",
                            new_signature=None,
                            migration_guide="Restore the file or provide alternative APIs.",
                        )
                    )

            except Exception as e:
                result.analysis_errors.append(
                    f"Error analyzing removed file {file_path}: {e}"
                )

        # Compare common files
        common_files = set(old_files.keys()) & set(new_files.keys())
        result.files_analyzed = len(common_files)

        for file_path in common_files:
            try:
                changes = self.analyze_file_change(
                    old_files[file_path], new_files[file_path], file_path
                )
                result.breaking_changes.extend(changes)

            except Exception as e:
                result.analysis_errors.append(f"Error analyzing {file_path}: {e}")

    def _extract_api_elements(self, source_code: str) -> list[ApiElement]:
        """
        Extract public API elements from source code.

        Args:
            source_code: Python source code

        Returns:
            List of API elements
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return []

        api_elements = []

        for node in tree.body:
            # Extract module-level functions
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    api_elements.append(self._function_to_api_element(node))

            # Extract module-level classes and their public methods
            elif isinstance(node, ast.ClassDef):
                if not node.name.startswith("_"):
                    api_elements.append(self._class_to_api_element(node))

                    for item in node.body:
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if not item.name.startswith("_"):
                                method = self._function_to_api_element(item)
                                method.element_type = "method"
                                method.name = f"{node.name}.{item.name}"
                                api_elements.append(method)

        return api_elements

    def _function_to_api_element(
        self, node: ast.FunctionDef | ast.AsyncFunctionDef
    ) -> ApiElement:
        """
        Convert AST function node to ApiElement.

        Args:
            node: AST function/method node

        Returns:
            ApiElement representing the function
        """
        # Extract parameters
        params = []
        param_types = {}

        for arg in node.args.args:
            params.append(arg.arg)
            if arg.annotation:
                param_types[arg.arg] = ast.unparse(arg.annotation)

        # Determine required vs optional params using defaults
        # node.args.defaults are right-aligned to args (last N args have defaults)
        num_defaults = len(node.args.defaults)
        num_args = len(node.args.args)
        required_params = (
            [arg.arg for arg in node.args.args[: num_args - num_defaults]]
            if num_defaults
            else [arg.arg for arg in node.args.args]
        )
        optional_params = (
            [arg.arg for arg in node.args.args[num_args - num_defaults :]]
            if num_defaults
            else []
        )

        # Also include keyword-only args with defaults as optional
        for i, kwarg in enumerate(node.args.kwonlyargs):
            if i < len(node.args.kw_defaults) and node.args.kw_defaults[i] is not None:
                optional_params.append(kwarg.arg)
            else:
                required_params.append(kwarg.arg)
            params.append(kwarg.arg)
            if kwarg.annotation:
                param_types[kwarg.arg] = ast.unparse(kwarg.annotation)

        # Extract return type
        return_type = None
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        # Build signature
        param_strs = []
        for param in params:
            if param in param_types:
                param_strs.append(f"{param}: {param_types[param]}")
            else:
                param_strs.append(param)

        signature = f"{'async ' if isinstance(node, ast.AsyncFunctionDef) else ''}def {node.name}({', '.join(param_strs)})"
        if return_type:
            signature += f" -> {return_type}"

        # Extract docstring
        docstring = ast.get_docstring(node)

        return ApiElement(
            name=node.name,
            element_type="function",
            signature=signature,
            params=params,
            param_types=param_types,
            return_type=return_type,
            decorators=decorators,
            is_async=isinstance(node, ast.AsyncFunctionDef),
            docstring=docstring,
            required_params=required_params,
            optional_params=optional_params,
        )

    def _class_to_api_element(self, node: ast.ClassDef) -> ApiElement:
        """
        Convert AST class node to ApiElement.

        Args:
            node: AST class node

        Returns:
            ApiElement representing the class
        """
        # Extract base classes
        bases = [ast.unparse(base) for base in node.bases]

        # Extract decorators
        decorators = [ast.unparse(dec) for dec in node.decorator_list]

        # Build signature
        signature = f"class {node.name}"
        if bases:
            signature += f"({', '.join(bases)})"

        # Extract docstring
        docstring = ast.get_docstring(node)

        return ApiElement(
            name=node.name,
            element_type="class",
            signature=signature,
            params=bases,  # Base classes as params
            decorators=decorators,
            docstring=docstring,
        )

    def _compare_apis(
        self, old_api: list[ApiElement], new_api: list[ApiElement], file_path: str
    ) -> list[BreakingChange]:
        """
        Compare two API lists to find breaking changes.

        Args:
            old_api: API elements from old version
            new_api: API elements from new version
            file_path: File path for reporting

        Returns:
            List of breaking changes
        """
        changes = []

        # Create lookup dictionaries
        old_dict = {elem.name: elem for elem in old_api}
        new_dict = {elem.name: elem for elem in new_api}

        # Check for removed APIs
        removed = set(old_dict.keys()) - set(new_dict.keys())
        for name in removed:
            old_elem = old_dict[name]
            changes.append(
                BreakingChange(
                    severity="critical",
                    change_type=f"removed_{old_elem.element_type}",
                    title=f"Removed {old_elem.element_type.capitalize()}: {name}",
                    description=f"Public {old_elem.element_type} '{name}' was removed from {file_path}.",
                    file=file_path,
                    old_signature=old_elem.signature,
                    new_signature=None,
                    migration_guide=f"Restore '{name}' or provide a replacement API with similar functionality.",
                )
            )

        # Check for signature changes in common APIs
        common = set(old_dict.keys()) & set(new_dict.keys())
        for name in common:
            old_elem = old_dict[name]
            new_elem = new_dict[name]

            # Check for parameter changes
            if old_elem.params != new_elem.params:
                # Determine severity based on change type
                severity = self._determine_param_change_severity(old_elem, new_elem)

                changes.append(
                    BreakingChange(
                        severity=severity,
                        change_type="signature_change",
                        title=f"Signature Changed: {name}",
                        description=f"Parameters changed for {old_elem.element_type} '{name}' in {file_path}.\n"
                        f"Old params: {old_elem.params}\n"
                        f"New params: {new_elem.params}",
                        file=file_path,
                        old_signature=old_elem.signature,
                        new_signature=new_elem.signature,
                        migration_guide=self._generate_migration_guide(
                            old_elem, new_elem
                        ),
                    )
                )

            # Check for return type changes
            if old_elem.return_type != new_elem.return_type:
                changes.append(
                    BreakingChange(
                        severity="high",
                        change_type="return_type_change",
                        title=f"Return Type Changed: {name}",
                        description=f"Return type changed for {old_elem.element_type} '{name}' in {file_path}.\n"
                        f"Old: {old_elem.return_type or 'None'}\n"
                        f"New: {new_elem.return_type or 'None'}",
                        file=file_path,
                        old_signature=old_elem.signature,
                        new_signature=new_elem.signature,
                        migration_guide="Update all call sites to handle the new return type.",
                    )
                )

            # Check for async/sync changes
            if old_elem.is_async != new_elem.is_async:
                changes.append(
                    BreakingChange(
                        severity="critical",
                        change_type="async_sync_change",
                        title=f"Async/Sync Change: {name}",
                        description=f"Function '{name}' changed from {'async' if old_elem.is_async else 'sync'} "
                        f"to {'async' if new_elem.is_async else 'sync'} in {file_path}.",
                        file=file_path,
                        old_signature=old_elem.signature,
                        new_signature=new_elem.signature,
                        migration_guide="Update all call sites to use 'await' if now async, or remove 'await' if now sync.",
                    )
                )

        return changes

    def _determine_param_change_severity(
        self, old_elem: ApiElement, new_elem: ApiElement
    ) -> str:
        """
        Determine severity of parameter changes.

        Args:
            old_elem: Old API element
            new_elem: New API element

        Returns:
            Severity string (critical, high, medium)
        """
        # Removed parameters is critical
        removed_params = set(old_elem.params) - set(new_elem.params)
        if removed_params:
            return "critical"

        # Added parameters - severity depends on whether they have defaults
        added_params = set(new_elem.params) - set(old_elem.params)
        if added_params:
            optional_added = set(new_elem.optional_params) & added_params
            required_added = added_params - optional_added
            if required_added:
                # New required parameters break existing callers
                return "high"
            # All added params are optional (have defaults) - lower severity
            return "medium"

        # Reordered parameters is high severity
        if old_elem.params != new_elem.params:
            return "high"

        # Type changes are medium
        return "medium"

    def _generate_migration_guide(
        self, old_elem: ApiElement, new_elem: ApiElement
    ) -> str:
        """
        Generate migration guide for breaking changes.

        Args:
            old_elem: Old API element
            new_elem: New API element

        Returns:
            Migration guide string
        """
        removed_params = set(old_elem.params) - set(new_elem.params)
        added_params = set(new_elem.params) - set(old_elem.params)

        guide_parts = []

        if removed_params:
            guide_parts.append(
                f"Removed parameters: {', '.join(removed_params)}. "
                "Update call sites to remove these arguments."
            )

        if added_params:
            guide_parts.append(
                f"Added parameters: {', '.join(added_params)}. "
                "Update call sites to provide these arguments or ensure they have default values."
            )

        if old_elem.params != new_elem.params and not (removed_params or added_params):
            guide_parts.append(
                "Parameters were reordered. Update call sites to use keyword arguments."
            )

        return (
            " ".join(guide_parts)
            if guide_parts
            else "Review and update all call sites."
        )

    def _save_results(self, spec_dir: Path, result: BreakingChangeResult) -> None:
        """
        Save breaking change results to spec directory.

        Args:
            spec_dir: Spec directory path
            result: Result to save
        """

        from analysis.io_utils import (
            atomic_json_write,
            build_issue_summary,
            prepare_save_dir,
        )

        spec_dir, output_file = prepare_save_dir(spec_dir, "breaking_changes.json")

        data = build_issue_summary(result, items_attr="breaking_changes")
        data["breaking_changes"] = [
            {
                "severity": change.severity,
                "change_type": change.change_type,
                "title": change.title,
                "description": change.description,
                "file": change.file,
                "old_signature": change.old_signature,
                "new_signature": change.new_signature,
                "migration_guide": change.migration_guide,
            }
            for change in result.breaking_changes
        ]

        atomic_json_write(data, output_file, dir=spec_dir, prefix="breaking_changes_")

    def format_report(self, result: BreakingChangeResult) -> str:
        """
        Format breaking change results as a human-readable report.

        Args:
            result: Result to format

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 80)
        lines.append("BREAKING CHANGE ANALYSIS REPORT")
        lines.append("=" * 80)
        lines.append(f"\nFiles Analyzed: {result.files_analyzed}")
        lines.append(f"Total Breaking Changes: {len(result.breaking_changes)}")

        if result.should_block:
            lines.append(
                "\n🚫 CRITICAL BREAKING CHANGES FOUND - SHOULD BLOCK DEPLOYMENT"
            )

        from analysis.io_utils import SEVERITY_ORDER, group_by_severity

        by_severity = group_by_severity(result.breaking_changes)

        for severity in SEVERITY_ORDER:
            changes = by_severity[severity]
            if not changes:
                continue

            lines.append(f"\n{severity.upper()} Breaking Changes ({len(changes)}):")
            lines.append("-" * 80)

            for change in changes:
                lines.append(f"\n🔴 {change.title}")
                lines.append(f"   File: {change.file}")
                lines.append(f"   Type: {change.change_type}")
                lines.append(f"   {change.description}")
                lines.append(f"   Old: {change.old_signature}")
                if change.new_signature:
                    lines.append(f"   New: {change.new_signature}")
                else:
                    lines.append("   New: [REMOVED]")
                if change.migration_guide:
                    lines.append(f"   📖 Migration: {change.migration_guide}")

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


def detect_breaking_changes(
    old_dir: Path | None = None,
    new_dir: Path | None = None,
    old_files: dict[str, str] | None = None,
    new_files: dict[str, str] | None = None,
    spec_dir: Path | None = None,
) -> BreakingChangeResult:
    """
    Convenience function to detect breaking changes.

    Args:
        old_dir: Path to old version of code
        new_dir: Path to new version of code
        old_files: Dictionary mapping file paths to old content
        new_files: Dictionary mapping file paths to new content
        spec_dir: Optional spec directory to save results

    Returns:
        BreakingChangeResult with all findings
    """
    detector = BreakingChangeDetector()
    return detector.analyze(old_dir, new_dir, old_files, new_files, spec_dir)


def has_breaking_changes(old_code: str, new_code: str) -> bool:
    """
    Quick check if code change has breaking changes.

    Args:
        old_code: Old version of code
        new_code: New version of code

    Returns:
        True if breaking changes detected
    """
    detector = BreakingChangeDetector()
    changes = detector.analyze_file_change(old_code, new_code, "<string>")
    return len(changes) > 0


# =============================================================================
# CLI
# =============================================================================


def main() -> None:
    """CLI entry point for testing."""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Detect breaking changes in code")
    parser.add_argument("--old-dir", type=Path, help="Path to old version directory")
    parser.add_argument("--new-dir", type=Path, help="Path to new version directory")
    parser.add_argument("--spec-dir", type=Path, help="Path to spec directory")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    if not args.old_dir or not args.new_dir:
        parser.error("Both --old-dir and --new-dir are required")

    detector = BreakingChangeDetector()
    result = detector.analyze(
        old_dir=args.old_dir, new_dir=args.new_dir, spec_dir=args.spec_dir
    )

    if args.json:
        data = {
            "files_analyzed": result.files_analyzed,
            "total_breaking_changes": len(result.breaking_changes),
            "has_breaking_changes": result.has_breaking_changes,
            "should_block": result.should_block,
            "breaking_changes": [
                {
                    "severity": c.severity,
                    "change_type": c.change_type,
                    "title": c.title,
                    "description": c.description,
                    "file": c.file,
                    "old_signature": c.old_signature,
                    "new_signature": c.new_signature,
                    "migration_guide": c.migration_guide,
                }
                for c in result.breaking_changes
            ],
            "errors": result.analysis_errors,
        }
        print(json.dumps(data, indent=2))
    else:
        print(detector.format_report(result))


if __name__ == "__main__":
    main()
