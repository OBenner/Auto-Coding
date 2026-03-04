"""
Debugging Tools
===============

MCP tools for intelligent debugging assistance. Provides stack trace analysis,
error explanations, fix suggestions, historical error lookup, and breakpoint
suggestions for AI agents.
"""

import json
import logging
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def create_debugging_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create debugging assistance tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of debugging tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: debug_error
    # -------------------------------------------------------------------------
    @tool(
        "debug_error",
        "Comprehensively debug an error. Analyzes stack traces, identifies root causes, explains errors in plain language, suggests fixes with code examples, looks up historical errors, and verifies fixes before applying. Use this when you encounter an error or exception.",
        {
            "error_trace": str,
            "code_context": str,
            "log_content": str,
            "use_historical": bool,
        },
    )
    async def debug_error(args: dict[str, Any]) -> dict[str, Any]:
        """
        Debug an error with comprehensive analysis.

        Provides complete debugging report including:
        - Parsed stack trace
        - Error pattern matching
        - Fix suggestions with code examples
        - Fix verification
        - Historical error lookup
        - Log analysis (if provided)
        - Plain language explanations
        """
        error_trace = args.get("error_trace", "")
        code_context_str = args.get("code_context", "")
        log_content = args.get("log_content", "")
        use_historical = args.get("use_historical", True)

        if not error_trace:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: error_trace parameter is required",
                    }
                ]
            }

        try:
            # Parse code_context if provided as JSON string
            code_context = None
            if code_context_str:
                try:
                    code_context = json.loads(code_context_str)
                except json.JSONDecodeError:
                    # If not valid JSON, treat as plain text context
                    code_context = {"context": code_context_str}

            # Import debug assistant
            from analysis.debug_assistant import DebugAssistant

            # Create assistant and debug
            assistant = DebugAssistant(project_dir=project_dir, spec_dir=spec_dir)
            report = assistant.debug_error(
                error_trace=error_trace,
                code_context=code_context,
                log_content=log_content or None,
                use_historical=use_historical,
            )

            # Format report for display
            formatted_report = _format_debug_report(report)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": formatted_report,
                    }
                ]
            }

        except ImportError as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Debug assistant module not available: {e}",
                    }
                ]
            }
        except Exception as e:
            logging.exception("Error during debug_error tool execution")
            return {
                "content": [{"type": "text", "text": f"Error debugging error: {e}"}]
            }

    tools.append(debug_error)

    # -------------------------------------------------------------------------
    # Tool: explain_error
    # -------------------------------------------------------------------------
    @tool(
        "explain_error",
        "Explain an error in plain language without jargon. Provides error type, message, plain language explanation, likely causes, affected code location, and suggested actions. Use this for quick error explanations when you don't need full debugging.",
        {"error_trace": str, "detail_level": str},
    )
    async def explain_error(args: dict[str, Any]) -> dict[str, Any]:
        """
        Explain an error in plain language.

        Provides user-friendly explanation without technical jargon.
        """
        error_trace = args.get("error_trace", "")
        detail_level = args.get("detail_level", "basic")

        valid_levels = ["basic", "detailed", "comprehensive"]
        if detail_level not in valid_levels:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Invalid detail_level '{detail_level}'. Must be one of: {valid_levels}",
                    }
                ]
            }

        if not error_trace:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: error_trace parameter is required",
                    }
                ]
            }

        try:
            from analysis.debug_assistant import DebugAssistant

            # Create assistant and explain
            assistant = DebugAssistant()
            explanation = assistant.explain_error(error_trace, detail_level)

            # Format explanation
            formatted = _format_error_explanation(explanation)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": formatted,
                    }
                ]
            }

        except ImportError as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Debug assistant module not available: {e}",
                    }
                ]
            }
        except Exception as e:
            logging.exception("Error during explain_error tool execution")
            return {
                "content": [{"type": "text", "text": f"Error explaining error: {e}"}]
            }

    tools.append(explain_error)

    # -------------------------------------------------------------------------
    # Tool: suggest_breakpoints
    # -------------------------------------------------------------------------
    @tool(
        "suggest_breakpoints",
        "Suggest strategic breakpoints for debugging. Analyzes code to recommend breakpoint locations at function entries, conditionals, loops, exception handlers, and variable assignments. Provides confidence scores and categories. Use this when setting up debugging for a file.",
        {"file_path": str, "error_line": int},
    )
    async def suggest_breakpoints(args: dict[str, Any]) -> dict[str, Any]:
        """
        Suggest breakpoints for debugging.

        Analyzes code structure to recommend strategic breakpoint locations.
        """
        file_path = args.get("file_path", "")
        error_line = args.get("error_line")

        if not file_path:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: file_path parameter is required",
                    }
                ]
            }

        try:
            from analysis.breakpoint_suggester import suggest_breakpoints_for_file

            # Convert to Path object
            file_path_obj = Path(file_path)

            # Check if file exists
            if not file_path_obj.exists():
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: File not found: {file_path}",
                        }
                    ]
                }

            # Suggest breakpoints
            result = suggest_breakpoints_for_file(
                file_path=file_path_obj, error_line=error_line
            )
            suggestions = result.get("suggestions", [])

            # Format suggestions
            formatted = _format_breakpoint_suggestions(suggestions)

            return {
                "content": [
                    {
                        "type": "text",
                        "text": formatted,
                    }
                ]
            }

        except ImportError as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Breakpoint suggester module not available: {e}",
                    }
                ]
            }
        except Exception as e:
            logging.exception("Error during suggest_breakpoints tool execution")
            return {
                "content": [
                    {"type": "text", "text": f"Error suggesting breakpoints: {e}"}
                ]
            }

    tools.append(suggest_breakpoints)

    return tools


# =============================================================================
# FORMATTING HELPERS
# =============================================================================


def _format_debug_report(report: dict[str, Any]) -> str:
    """Format debug report for display."""
    lines = []
    lines.append("# 🐛 Debugging Report")
    lines.append("")

    # Error summary
    parsed = report.get("parsed_trace", {})
    lines.append("## 📋 Error Summary")
    lines.append(f"**Type:** {parsed.get('error_type', 'Unknown')}")
    lines.append(f"**Language:** {parsed.get('language', 'unknown')}")
    lines.append(f"**Failing File:** {parsed.get('failing_file', 'Unknown')}")
    lines.append(f"**Failing Line:** {parsed.get('failing_line', 'Unknown')}")
    lines.append("")

    # Pattern match
    pattern = report.get("pattern_match")
    if pattern:
        lines.append("## 🔍 Pattern Recognition")
        lines.append(f"**Category:** {pattern.get('category', 'Unknown')}")
        lines.append(f"**Pattern:** {pattern.get('name', 'Unknown')}")
        lines.append(f"**Confidence:** {pattern.get('confidence', 0):.2%}")
        lines.append("")

    # Historical errors
    historical_count = report.get("historical_errors_count", 0)
    if historical_count > 0:
        lines.append("## 📚 Historical Context")
        lines.append(f"Found **{historical_count}** similar error(s) in memory.")
        historical = report.get("historical_errors", [])
        for i, hist in enumerate(historical[:3], 1):
            lines.append(f"\n{i}. **{hist.get('error_type', 'Unknown')}**")
            if hist.get("solution"):
                lines.append(f"   - Solution: {hist['solution'][:100]}...")
        lines.append("")

    # Explanation
    explanation = report.get("explanation", "")
    if explanation:
        lines.append("## 💡 Explanation")
        lines.append(explanation)
        lines.append("")

    # Fix suggestions
    fix = report.get("fix_suggestion", {})
    if fix.get("suggested_fixes"):
        lines.append("## 🔧 Suggested Fixes")
        for i, suggestion in enumerate(fix["suggested_fixes"], 1):
            lines.append(f"{i}. {suggestion}")
        lines.append("")

    # Fix verification
    verification = report.get("fix_verification", {})
    if verification:
        lines.append("## ✅ Fix Verification")
        is_safe = verification.get("is_safe", False)
        lines.append(f"**Safe to Apply:** {'Yes ✅' if is_safe else 'No ⚠️'}")
        if verification.get("risk_level"):
            lines.append(f"**Risk Level:** {verification['risk_level']}")
        if verification.get("warnings"):
            lines.append("**Warnings:**")
            for warning in verification["warnings"]:
                lines.append(f"  - ⚠️ {warning}")
        lines.append("")

    # Log analysis
    log_analysis = report.get("log_analysis")
    if log_analysis:
        lines.append("## 📋 Log Analysis")
        if log_analysis.get("summary"):
            lines.append(f"**Summary:** {log_analysis['summary']}")
        if log_analysis.get("relevant_lines"):
            lines.append(
                f"**Relevant Lines:** {len(log_analysis['relevant_lines'])} found"
            )
        lines.append("")

    # Recommendations
    recommendations = report.get("recommendations", [])
    if recommendations:
        lines.append("## 📌 Recommendations")
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")
        lines.append("")

    # Confidence
    confidence = report.get("confidence", 0)
    lines.append(f"**Overall Confidence:** {confidence:.2%}")

    return "\n".join(lines)


def _format_error_explanation(explanation: dict[str, Any]) -> str:
    """Format error explanation for display."""
    lines = []
    lines.append("# 📖 Error Explanation")
    lines.append("")

    lines.append(f"**Error Type:** {explanation.get('error_type', 'Unknown')}")
    lines.append(f"**Language:** {explanation.get('language', 'unknown')}")
    lines.append("")

    # Plain language explanation
    plain = explanation.get("plain_language_explanation", "")
    if plain:
        lines.append("## 💬 What This Means (Plain Language)")
        lines.append(plain)
        lines.append("")

    # Likely causes
    causes = explanation.get("likely_causes", [])
    if causes:
        lines.append("## 🔍 Likely Causes")
        for i, cause in enumerate(causes, 1):
            lines.append(f"{i}. {cause}")
        lines.append("")

    # Affected code
    failing_file = explanation.get("failing_file")
    failing_line = explanation.get("failing_line")
    if failing_file or failing_line:
        lines.append("## 📍 Affected Code")
        if failing_file:
            lines.append(f"**File:** {failing_file}")
        if failing_line:
            lines.append(f"**Line:** {failing_line}")
        lines.append("")

    # Suggested actions
    actions = explanation.get("suggested_actions", [])
    if actions:
        lines.append("## ✅ Suggested Actions")
        for i, action in enumerate(actions, 1):
            lines.append(f"{i}. {action}")

    return "\n".join(lines)


def _format_breakpoint_suggestions(suggestions: list[dict[str, Any]]) -> str:
    """Format breakpoint suggestions for display."""
    if not suggestions:
        return "No breakpoint suggestions found for this file."

    lines = []
    lines.append("# 🎯 Breakpoint Suggestions")
    lines.append(f"Found **{len(suggestions)}** strategic breakpoint location(s)")
    lines.append("")

    # Group by category
    by_category: dict[str, list[dict]] = {}
    for suggestion in suggestions:
        category = suggestion.get("category", "other")
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(suggestion)

    # Display by category (priority order)
    priority_order = [
        "error_context",
        "pre_error",
        "error_line",
        "post_error",
        "function_entry",
        "conditional",
        "loop",
        "exception_handler",
        "assignment",
        "other",
    ]

    for category in priority_order:
        if category not in by_category:
            continue

        category_suggestions = by_category[category]

        # Format category name
        category_name = category.replace("_", " ").title()
        lines.append(f"## {category_name}")

        for suggestion in sorted(
            category_suggestions, key=lambda x: x.get("confidence", 0), reverse=True
        ):
            line = suggestion.get("line", "?")
            confidence = suggestion.get("confidence", 0)
            reason = suggestion.get("reason", "")

            # Confidence indicator
            if confidence >= 0.8:
                indicator = "🔴 High Priority"
            elif confidence >= 0.5:
                indicator = "🟡 Medium Priority"
            else:
                indicator = "🟢 Low Priority"

            lines.append(f"**Line {line}:** {indicator} ({confidence:.0%})")
            if reason:
                lines.append(f"  - {reason}")
        lines.append("")

    return "\n".join(lines)
