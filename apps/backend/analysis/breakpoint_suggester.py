#!/usr/bin/env python3
"""
Breakpoint Suggester Module
============================

Analyzes code and error context to suggest strategic breakpoint locations for interactive debugging.
This module uses AST parsing to identify optimal breakpoint positions based on error patterns,
code structure, and execution flow.

The breakpoint suggester is used by:
- Debug Assistant: To provide breakpoint recommendations for debugging
- QA Agents: To know where to inspect code during error investigation
- Developers: To get intelligent breakpoint suggestions for manual debugging

Usage:
    from breakpoint_suggester import suggest_breakpoints, BreakpointSuggester

    suggester = BreakpointSuggester()
    breakpoints = suggester.suggest_for_error(
        code='''def my_function():
            x = compute()
            return x + 1
        ''',
        error_line=3,
        error_type='TypeError',
        language='python'
    )

    for bp in breakpoints:
        print(f"Line {bp['line']}: {bp['reason']}")
"""

from __future__ import annotations

import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# =============================================================================
# DATA CLASSES
# =============================================================================


@dataclass
class BreakpointSuggestion:
    """
    Represents a suggested breakpoint location.

    Attributes:
        line: Line number for the breakpoint
        reason: Explanation of why this breakpoint is useful
        confidence: Confidence score (0.0 to 1.0)
        category: Type of breakpoint (entry, conditional, pre_error, etc.)
        condition: Optional conditional expression for the breakpoint
    """

    line: int
    reason: str
    confidence: float
    category: str
    condition: str | None = None


@dataclass
class BreakpointAnalysis:
    """
    Result of breakpoint analysis.

    Attributes:
        suggestions: List of breakpoint suggestions
        total_breakpoints: Total number of suggestions
        high_priority_count: Number of high-priority breakpoints
        code_summary: Brief summary of analyzed code
    """

    suggestions: list[BreakpointSuggestion] = field(default_factory=list)
    total_breakpoints: int = 0
    high_priority_count: int = 0
    code_summary: str = ""


# =============================================================================
# BREAKPOINT SUGGESTER
# =============================================================================


class BreakpointSuggester:
    """
    Analyzes code to suggest strategic breakpoint locations.

    Identifies:
    - Function entry points in the call stack
    - Conditional statements near error locations
    - Loop boundaries
    - Exception handlers
    - Pre and post-error locations
    - Variable mutation points
    """

    def __init__(self):
        """Initialize the breakpoint suggester."""
        pass

    def suggest_for_file(
        self,
        file_path: str | Path,
        error_line: int,
        error_type: str = "Error",
        context_lines: int = 5,
    ) -> dict[str, Any]:
        """
        Suggest breakpoints for a file with an error.

        Args:
            file_path: Path to source file
            error_line: Line number where error occurred
            error_type: Type of error (e.g., "TypeError", "ValueError")
            context_lines: Number of lines around error to analyze

        Returns:
            Dictionary with breakpoint suggestions:
            {
                "suggestions": list of breakpoint dicts,
                "total_count": int,
                "high_priority_count": int,
                "file_path": str,
            }
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        try:
            code = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            raise ValueError(f"Unable to read file as UTF-8: {file_path}")

        return self.suggest_for_code(
            code=code,
            error_line=error_line,
            error_type=error_type,
            language=str(path.suffix).lstrip("."),
            context_lines=context_lines,
        )

    def suggest_for_code(
        self,
        code: str,
        error_line: int,
        error_type: str = "Error",
        language: str = "python",
        context_lines: int = 5,
    ) -> dict[str, Any]:
        """
        Suggest breakpoints for code with an error.

        Args:
            code: Source code as string
            error_line: Line number where error occurred (1-indexed)
            error_type: Type of error
            language: Programming language (only 'python' supported currently)
            context_lines: Number of lines around error to analyze

        Returns:
            Dictionary with breakpoint suggestions
        """
        if language.lower() != "python":
            logger.warning(f"Language '{language}' not supported, using heuristics")
            return self._heuristic_suggestions(code, error_line, error_type)

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"Syntax error in code: {e}")
            return self._heuristic_suggestions(code, error_line, error_type)

        analysis = self._analyze_breakpoints(
            tree, code, error_line, error_type, context_lines
        )

        return self._analysis_to_dict(analysis, code)

    def _analyze_breakpoints(
        self,
        tree: ast.AST,
        code: str,
        error_line: int,
        error_type: str,
        context_lines: int,
    ) -> BreakpointAnalysis:
        """
        Analyze AST to find optimal breakpoint locations.

        Args:
            tree: Parsed AST
            code: Source code
            error_line: Line where error occurred
            error_type: Type of error
            context_lines: Context window size

        Returns:
            BreakpointAnalysis with suggestions
        """
        suggestions = []
        lines = code.splitlines()
        total_lines = len(lines)

        # 1. Suggest pre-error breakpoint (most critical)
        if error_line > 1:
            pre_error_line = max(1, error_line - 1)
            suggestions.append(
                BreakpointSuggestion(
                    line=pre_error_line,
                    reason=f"Inspect state before error at line {error_line}",
                    confidence=0.95,
                    category="pre_error",
                )
            )

        # 2. Suggest entry points of functions in call stack
        func_entries = self._find_function_entries(tree, error_line)
        for func_line, func_name in func_entries[:3]:  # Top 3 functions
            suggestions.append(
                BreakpointSuggestion(
                    line=func_line,
                    reason=f"Entry point of '{func_name}' in call stack",
                    confidence=0.85,
                    category="function_entry",
                )
            )

        # 3. Find conditional statements near error
        conditionals = self._find_nearby_conditionals(tree, error_line, context_lines)
        for cond_line, cond_type in conditionals[:2]:  # Top 2 conditionals
            suggestions.append(
                BreakpointSuggestion(
                    line=cond_line,
                    reason=f"{cond_type} statement - check branch logic",
                    confidence=0.75,
                    category="conditional",
                )
            )

        # 4. Find loop boundaries near error
        loops = self._find_nearby_loops(tree, error_line, context_lines)
        for loop_line, loop_type in loops[:2]:  # Top 2 loops
            suggestions.append(
                BreakpointSuggestion(
                    line=loop_line,
                    reason=f"{loop_type} boundary - check iteration state",
                    confidence=0.70,
                    category="loop",
                )
            )

        # 5. Find exception handlers near error
        handlers = self._find_nearby_handlers(tree, error_line, context_lines)
        for handler_line in handlers[:2]:  # Top 2 handlers
            suggestions.append(
                BreakpointSuggestion(
                    line=handler_line,
                    reason="Exception handler - verify error catching",
                    confidence=0.80,
                    category="exception_handler",
                )
            )

        # 6. Suggest variable assignment points near error
        assignments = self._find_nearby_assignments(tree, error_line, context_lines)
        for assign_line, var_name in assignments[:3]:  # Top 3 assignments
            suggestions.append(
                BreakpointSuggestion(
                    line=assign_line,
                    reason=f"Variable '{var_name}' assignment - check value",
                    confidence=0.65,
                    category="assignment",
                )
            )

        # 7. Post-error breakpoint (if within file)
        if error_line < total_lines:
            post_error_line = min(total_lines, error_line + 1)
            suggestions.append(
                BreakpointSuggestion(
                    line=post_error_line,
                    reason="After error location - check cleanup/exit",
                    confidence=0.60,
                    category="post_error",
                )
            )

        # Sort by confidence and deduplicate
        suggestions = self._deduplicate_suggestions(suggestions)
        suggestions.sort(key=lambda s: s.confidence, reverse=True)

        # Generate code summary
        code_summary = self._generate_code_summary(lines, error_line, context_lines)

        return BreakpointAnalysis(
            suggestions=suggestions,
            total_breakpoints=len(suggestions),
            high_priority_count=len([s for s in suggestions if s.confidence >= 0.75]),
            code_summary=code_summary,
        )

    def _find_function_entries(
        self, tree: ast.AST, error_line: int
    ) -> list[tuple[int, str]]:
        """Find function entry points that might be in the call stack."""
        entries = []

        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                # Check if error_line is within this function
                if node.lineno <= error_line:
                    # Find end of function
                    end_line = self._find_node_end(node)
                    if error_line <= end_line:
                        entries.append((node.lineno, node.name))

        # Sort by proximity to error (closest first)
        entries.sort(key=lambda x: abs(x[0] - error_line))
        return entries

    def _find_nearby_conditionals(
        self, tree: ast.AST, error_line: int, context: int
    ) -> list[tuple[int, str]]:
        """Find conditional statements near the error line."""
        conditionals = []

        for node in ast.walk(tree):
            if isinstance(node, ast.If):
                if abs(node.lineno - error_line) <= context:
                    cond_type = "if/elif" if node.orelse else "if"
                    conditionals.append((node.lineno, cond_type))

        conditionals.sort(key=lambda x: abs(x[0] - error_line))
        return conditionals

    def _find_nearby_loops(
        self, tree: ast.AST, error_line: int, context: int
    ) -> list[tuple[int, str]]:
        """Find loop statements near the error line."""
        loops = []

        for node in ast.walk(tree):
            if isinstance(node, ast.For):
                if abs(node.lineno - error_line) <= context:
                    loops.append((node.lineno, "for loop"))
            elif isinstance(node, ast.While):
                if abs(node.lineno - error_line) <= context:
                    loops.append((node.lineno, "while loop"))

        loops.sort(key=lambda x: abs(x[0] - error_line))
        return loops

    def _find_nearby_handlers(
        self, tree: ast.AST, error_line: int, context: int
    ) -> list[int]:
        """Find exception handlers near the error line."""
        handlers = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Try):
                for handler in node.handlers:
                    if abs(handler.lineno - error_line) <= context:
                        handlers.append(handler.lineno)

        handlers.sort(key=lambda x: abs(x - error_line))
        return handlers

    def _find_nearby_assignments(
        self, tree: ast.AST, error_line: int, context: int
    ) -> list[tuple[int, str]]:
        """Find variable assignments near the error line."""
        assignments = []

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if abs(node.lineno - error_line) <= context:
                    # Get variable name(s)
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            assignments.append((node.lineno, target.id))
                        elif isinstance(target, ast.Attribute):
                            var_name = ast.unparse(target)
                            assignments.append((node.lineno, var_name))

        # Sort by proximity and uniqueness
        seen = set()
        unique_assignments = []
        for line, name in sorted(assignments, key=lambda x: abs(x[0] - error_line)):
            if name not in seen:
                seen.add(name)
                unique_assignments.append((line, name))

        return unique_assignments[:5]  # Top 5

    def _find_node_end(self, node: ast.AST) -> int:
        """Find the end line of a node."""
        end_line = node.lineno

        for child in ast.walk(node):
            if hasattr(child, "lineno") and child.lineno > end_line:
                end_line = child.lineno

        return end_line

    def _deduplicate_suggestions(
        self, suggestions: list[BreakpointSuggestion]
    ) -> list[BreakpointSuggestion]:
        """Remove duplicate suggestions (same line)."""
        seen_lines = {}
        for suggestion in suggestions:
            if suggestion.line not in seen_lines:
                seen_lines[suggestion.line] = suggestion
            else:
                # Keep the one with higher confidence
                if suggestion.confidence > seen_lines[suggestion.line].confidence:
                    seen_lines[suggestion.line] = suggestion

        return list(seen_lines.values())

    def _generate_code_summary(
        self, lines: list[str], error_line: int, context: int
    ) -> str:
        """Generate a brief summary of the code around the error."""
        start = max(0, error_line - context - 1)
        end = min(len(lines), error_line + context)

        return f"Lines {start + 1}-{end} of {len(lines)} total"

    def _analysis_to_dict(
        self, analysis: BreakpointAnalysis, code: str
    ) -> dict[str, Any]:
        """Convert BreakpointAnalysis to dictionary."""
        return {
            "suggestions": [
                {
                    "line": s.line,
                    "reason": s.reason,
                    "confidence": s.confidence,
                    "category": s.category,
                    "condition": s.condition,
                }
                for s in analysis.suggestions
            ],
            "total_count": analysis.total_breakpoints,
            "high_priority_count": analysis.high_priority_count,
            "code_summary": analysis.code_summary,
        }

    def _heuristic_suggestions(
        self, code: str, error_line: int, error_type: str
    ) -> dict[str, Any]:
        """
        Fallback heuristic suggestions when AST parsing fails.

        Provides basic breakpoint suggestions based on line proximity.
        """
        lines = code.splitlines()
        total_lines = len(lines)

        suggestions = []

        # Pre-error
        if error_line > 1:
            suggestions.append(
                {
                    "line": error_line - 1,
                    "reason": "Before error - inspect state",
                    "confidence": 0.90,
                    "category": "pre_error",
                    "condition": None,
                }
            )

        # Error line itself
        suggestions.append(
            {
                "line": error_line,
                "reason": f"Error location - {error_type}",
                "confidence": 0.95,
                "category": "error_line",
                "condition": None,
            }
        )

        # Post-error
        if error_line < total_lines:
            suggestions.append(
                {
                    "line": error_line + 1,
                    "reason": "After error - check cleanup",
                    "confidence": 0.70,
                    "category": "post_error",
                    "condition": None,
                }
            )

        return {
            "suggestions": suggestions,
            "total_count": len(suggestions),
            "high_priority_count": len(
                [s for s in suggestions if s["confidence"] >= 0.75]
            ),
            "code_summary": f"Lines 1-{total_lines} (heuristic analysis)",
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def suggest_breakpoints(
    code: str,
    error_line: int,
    error_type: str = "Error",
    language: str = "python",
    context_lines: int = 5,
) -> dict[str, Any]:
    """
    Suggest breakpoints for code with an error.

    Convenience function that creates a BreakpointSuggester and runs analysis.

    Args:
        code: Source code as string
        error_line: Line number where error occurred (1-indexed)
        error_type: Type of error (e.g., "TypeError", "ValueError")
        language: Programming language (only 'python' supported currently)
        context_lines: Number of lines around error to analyze

    Returns:
        Dictionary with breakpoint suggestions:
        {
            "suggestions": [
                {
                    "line": int,
                    "reason": str,
                    "confidence": float,
                    "category": str,
                    "condition": str | None,
                }
            ],
            "total_count": int,
            "high_priority_count": int,
            "code_summary": str,
        }
    """
    suggester = BreakpointSuggester()
    return suggester.suggest_for_code(
        code=code,
        error_line=error_line,
        error_type=error_type,
        language=language,
        context_lines=context_lines,
    )


def suggest_breakpoints_for_file(
    file_path: str | Path,
    error_line: int,
    error_type: str = "Error",
    context_lines: int = 5,
) -> dict[str, Any]:
    """
    Suggest breakpoints for a file with an error.

    Convenience function for file-based breakpoint suggestion.

    Args:
        file_path: Path to source file
        error_line: Line number where error occurred (1-indexed)
        error_type: Type of error
        context_lines: Number of lines around error to analyze

    Returns:
        Dictionary with breakpoint suggestions
    """
    suggester = BreakpointSuggester()
    return suggester.suggest_for_file(
        file_path=file_path,
        error_line=error_line,
        error_type=error_type,
        context_lines=context_lines,
    )
