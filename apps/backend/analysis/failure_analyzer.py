"""
Failure Analyzer
================

Analyzes failed builds, QA rejections, and recurring issues to extract root causes.
Provides structured failure analysis for learning from mistakes.

Uses the Claude Agent SDK (same as the rest of the system) for analysis.
Falls back to basic analysis if extraction fails (never blocks the build).
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    # Optional: claude_agent_sdk is checked at runtime for availability
    import claude_agent_sdk  # noqa: F401

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from core.auth import get_auth_token

# Default model for failure analysis (fast and cheap)
DEFAULT_ANALYSIS_MODEL = "claude-haiku-4-5-20251001"

# Maximum error message length to analyze
MAX_ERROR_CHARS = 10000

# Maximum diff size to send to the LLM
MAX_DIFF_CHARS = 15000

# Named pattern constants for heuristic root cause categorization
SYNTAX_ERROR_PATTERNS = ["syntaxerror", "unexpected token", "invalid syntax"]
MISSING_DEPENDENCY_PATTERNS = [
    "modulenotfounderror",
    "importerror",
    "cannot find module",
]
LOGIC_ERROR_PATTERNS = [
    "typeerror",
    "attributeerror",
    "referenceerror",
    "undefined is not",
]
TEST_ERROR_PATTERNS = [
    "test failed",
    "assertion",
    "expected",
    "actual",
    "test error",
    "mock error",
    "stub error",
    "beforeeach failed",
    "aftereach failed",
    "test setup failed",
    "test teardown failed",
    "coverage threshold",
]
BUILD_ERROR_PATTERNS = [
    "compilation error",
    "compile error",
    "typescript error",
    "type error:",
    "type mismatch",
    "build failed",
    "webpack error",
    "rollup error",
    "vite error",
    "bundler error",
    "eslint",
    "pylint",
    "linting error",
]
TIMEOUT_PATTERNS = ["timeout", "timed out", "deadline"]


def is_analysis_enabled() -> bool:
    """Check if failure analysis is enabled."""
    # Analysis requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("FAILURE_ANALYSIS_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_analysis_model() -> str:
    """Get the model to use for failure analysis."""
    return os.environ.get("FAILURE_ANALYZER_MODEL", DEFAULT_ANALYSIS_MODEL)


# =============================================================================
# Data Gathering Helpers
# =============================================================================


def get_recent_logs(project_dir: Path, lines: int = 100) -> str:
    """
    Get recent git commit logs.

    Args:
        project_dir: Project root directory
        lines: Number of recent commits to fetch

    Returns:
        Formatted log text
    """
    try:
        result = subprocess.run(
            ["git", "log", f"-{lines}", "--oneline"],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip() if result.stdout.strip() else "(No commits)"

    except Exception as e:
        logger.warning(f"Failed to get recent logs: {e}")
        return f"(Failed to get logs: {e})"


def get_recent_diff(project_dir: Path, commit_range: str = "HEAD~5..HEAD") -> str:
    """
    Get recent git diff.

    Args:
        project_dir: Project root directory
        commit_range: Git commit range to diff

    Returns:
        Diff text (truncated if too large)
    """
    try:
        result = subprocess.run(
            ["git", "diff", commit_range],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30,
        )
        diff = result.stdout

        if len(diff) > MAX_DIFF_CHARS:
            diff = (
                diff[:MAX_DIFF_CHARS] + f"\n\n... (truncated, {len(diff)} chars total)"
            )

        return diff if diff else "(Empty diff)"

    except Exception as e:
        logger.warning(f"Failed to get recent diff: {e}")
        return f"(Failed to get diff: {e})"


def load_qa_iteration_history(spec_dir: Path) -> list[dict[str, Any]]:
    """
    Load QA iteration history from implementation plan.

    Args:
        spec_dir: Spec directory

    Returns:
        List of QA iteration records
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return []

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)
        return plan.get("qa_iteration_history", [])

    except Exception as e:
        logger.warning(f"Failed to load QA iteration history: {e}")
        return []


def load_subtask_history(spec_dir: Path, subtask_id: str) -> dict[str, Any]:
    """
    Load subtask information from implementation plan.

    Args:
        spec_dir: Spec directory
        subtask_id: Subtask identifier

    Returns:
        Subtask data or empty dict
    """
    plan_file = spec_dir / "implementation_plan.json"
    if not plan_file.exists():
        return {}

    try:
        with open(plan_file, encoding="utf-8") as f:
            plan = json.load(f)

        # Search through phases for the subtask
        for phase in plan.get("phases", []):
            for subtask in phase.get("subtasks", []):
                if subtask.get("id") == subtask_id:
                    return subtask

        return {}

    except Exception as e:
        logger.warning(f"Failed to load subtask history: {e}")
        return {}


# =============================================================================
# Failure Analysis - Core Logic
# =============================================================================


def extract_root_cause(
    failure_data: dict[str, Any],
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Extract root cause from failure data.

    Args:
        failure_data: Dict with failure information (errors, issues, context)
        use_llm: Whether to use LLM for deeper analysis

    Returns:
        Dict with root cause analysis:
        {
            "category": str,  # e.g., "syntax_error", "logic_error", "missing_dependency"
            "description": str,  # Human-readable description
            "affected_files": list[str],
            "confidence": float,  # 0.0 - 1.0
            "recommendations": list[str],
            "is_recurring": bool,
        }
    """
    # Basic heuristic analysis (always runs)
    root_cause = _analyze_failure_heuristics(failure_data)

    # Enhanced LLM analysis (optional)
    if use_llm and is_analysis_enabled():
        try:
            llm_analysis = _analyze_failure_with_llm(failure_data)
            if llm_analysis:
                # Merge LLM insights with heuristic base
                root_cause.update(llm_analysis)
        except Exception as e:
            logger.warning(f"LLM analysis failed, using heuristics only: {e}")

    return root_cause


def _analyze_failure_heuristics(failure_data: dict[str, Any]) -> dict[str, Any]:
    """
    Perform heuristic-based failure analysis.

    Args:
        failure_data: Failure information

    Returns:
        Basic root cause dict
    """
    errors = failure_data.get("errors", [])
    issues = failure_data.get("issues", [])
    is_recurring = failure_data.get("is_recurring", False)

    # Default root cause
    root_cause = {
        "category": "unknown",
        "description": "Unable to determine root cause",
        "affected_files": [],
        "confidence": 0.3,
        "recommendations": [],
        "is_recurring": is_recurring,
    }

    # Extract affected files from issues
    affected_files = set()
    for issue in issues:
        if file := issue.get("file"):
            affected_files.add(file)

    root_cause["affected_files"] = list(affected_files)

    # Categorize based on error patterns
    error_text = " ".join(str(e) for e in errors).lower()

    if any(pattern in error_text for pattern in SYNTAX_ERROR_PATTERNS):
        root_cause["category"] = "syntax_error"
        root_cause["description"] = "Syntax error in code"
        root_cause["confidence"] = 0.9
        root_cause["recommendations"] = [
            "Check for missing brackets, quotes, or semicolons",
            "Verify code follows language syntax rules",
        ]

    elif any(pattern in error_text for pattern in MISSING_DEPENDENCY_PATTERNS):
        root_cause["category"] = "missing_dependency"
        root_cause["description"] = "Missing or misconfigured dependency"
        root_cause["confidence"] = 0.85
        root_cause["recommendations"] = [
            "Check if all dependencies are installed",
            "Verify import paths are correct",
            "Update package.json or requirements.txt",
        ]

    elif any(pattern in error_text for pattern in LOGIC_ERROR_PATTERNS):
        root_cause["category"] = "logic_error"
        root_cause["description"] = "Logic or type error in code"
        root_cause["confidence"] = 0.8
        root_cause["recommendations"] = [
            "Check variable types and null checks",
            "Verify object properties exist before access",
            "Review function signatures and return values",
        ]

    elif any(pattern in error_text for pattern in TEST_ERROR_PATTERNS):
        root_cause["category"] = "test_failure"
        root_cause["description"] = "Test assertion or setup failed"
        root_cause["confidence"] = 0.9
        root_cause["recommendations"] = [
            "Review test expectations vs actual behavior",
            "Check if implementation matches test requirements",
            "Verify test setup and mocks are correct",
            "Check test lifecycle hooks (setup/teardown)",
        ]

    elif any(pattern in error_text for pattern in BUILD_ERROR_PATTERNS):
        root_cause["category"] = "build_error"
        root_cause["description"] = "Build or compilation error"
        root_cause["confidence"] = 0.85
        root_cause["recommendations"] = [
            "Check for type errors and mismatches",
            "Review linting errors and code style issues",
            "Verify build configuration is correct",
            "Check for missing or incorrect imports",
        ]

    elif any(pattern in error_text for pattern in TIMEOUT_PATTERNS):
        root_cause["category"] = "timeout"
        root_cause["description"] = "Operation timed out"
        root_cause["confidence"] = 0.85
        root_cause["recommendations"] = [
            "Optimize slow operations",
            "Increase timeout limits if appropriate",
            "Check for infinite loops or blocking operations",
        ]

    # Adjust confidence based on recurring status
    if is_recurring:
        root_cause["recommendations"].insert(
            0, "⚠️ RECURRING ISSUE - This problem has occurred multiple times"
        )

    return root_cause


def _analyze_failure_with_llm(failure_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Perform LLM-based failure analysis.

    Args:
        failure_data: Failure information

    Returns:
        Enhanced root cause dict or None if analysis fails
    """
    if not SDK_AVAILABLE:
        logger.warning("Claude SDK not available, skipping LLM analysis")
        return None

    if not get_auth_token():
        logger.warning("No authentication token found, skipping LLM analysis")
        return None

    # Run async analysis synchronously
    import asyncio

    try:
        return asyncio.run(_run_llm_analysis(failure_data))
    except Exception as e:
        logger.warning(f"LLM analysis failed: {e}")
        return None


async def _run_llm_analysis(failure_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Run the LLM analysis asynchronously.

    Args:
        failure_data: Failure information

    Returns:
        Parsed root cause dict or None if analysis fails
    """
    from core.auth import ensure_claude_code_oauth_token
    from core.simple_client import create_simple_client

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = get_analysis_model()
    prompt = _build_analysis_prompt(failure_data)

    try:
        client = create_simple_client(
            agent_type="failure_analyzer",
            model=model,
            system_prompt=(
                "You are a failure analysis expert. You analyze build failures, QA rejections, and errors "
                "to identify root causes and provide specific, actionable recommendations. "
                "Always respond with valid JSON only, no markdown formatting or explanations."
            ),
            cwd=None,  # No specific directory needed for analysis
        )

        # Use async context manager
        async with client:
            await client.query(prompt)

            # Collect the response
            response_text = ""
            message_count = 0
            text_blocks_found = 0

            async for msg in client.receive_response():
                msg_type = type(msg).__name__
                message_count += 1

                if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                    for block in msg.content:
                        block_type = type(block).__name__
                        if block_type == "TextBlock" and hasattr(block, "text"):
                            text_blocks_found += 1
                            if block.text:
                                response_text += block.text

            logger.debug(
                f"Failure analysis response: {message_count} messages, "
                f"{text_blocks_found} text blocks, {len(response_text)} chars collected"
            )

            if not response_text.strip():
                logger.warning(
                    f"Failure analysis returned empty response. "
                    f"Messages received: {message_count}, TextBlocks found: {text_blocks_found}"
                )
                return None

        # Parse JSON from response
        return _parse_analysis_response(response_text)

    except Exception as e:
        logger.warning(f"LLM analysis execution failed: {e}")
        return None


def _build_analysis_prompt(failure_data: dict[str, Any]) -> str:
    """
    Build the prompt for failure analysis.

    Args:
        failure_data: Failure information

    Returns:
        Full prompt text
    """
    prompt_file = Path(__file__).parent / "prompts" / "failure_analysis.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        # Fallback if prompt file missing
        base_prompt = """Analyze this failure and provide root cause analysis.
Output ONLY valid JSON with: category, description, affected_files, confidence, recommendations"""

    # Truncate errors if too long
    errors = failure_data.get("errors", [])
    errors_text = "\n".join(str(e) for e in errors)
    if len(errors_text) > MAX_ERROR_CHARS:
        errors_text = (
            errors_text[:MAX_ERROR_CHARS]
            + f"\n\n... (truncated, {len(errors_text)} chars total)"
        )

    # Format issues
    issues = failure_data.get("issues", [])
    issues_text = "\n".join(
        f"- {issue.get('file', 'unknown')}:{issue.get('line', '?')} - {issue.get('description', 'No description')}"
        for issue in issues
    )

    # Format subtask info
    subtask = failure_data.get("subtask", {})
    subtask_text = ""
    if subtask:
        subtask_text = f"""
### Subtask Information
- **ID**: {subtask.get("id", "unknown")}
- **Description**: {subtask.get("description", "No description")}
- **Files to Modify**: {", ".join(subtask.get("files_to_modify", []))}
"""

    # Build failure context
    failure_context = f"""
---

## FAILURE DATA TO ANALYZE

### Failure Type
{failure_data.get("failure_type", "unknown")}

### Errors
{errors_text if errors_text else "(No errors)"}

### Issues
{issues_text if issues_text else "(No issues)"}

### Recurring Issue
{failure_data.get("is_recurring", False)}
{subtask_text}
---

Now analyze this failure and output ONLY the JSON object with your analysis.
"""

    return base_prompt + failure_context


def _parse_analysis_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the LLM response into structured root cause dict.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed root cause dict or None if parsing failed
    """
    text = response_text.strip()

    if not text:
        logger.warning("Cannot parse analysis: response text is empty")
        return None

    # Handle markdown code blocks
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()

        if not text:
            logger.warning(
                "Cannot parse analysis: response contained only markdown markers"
            )
            return None

    try:
        analysis = json.loads(text)

        if not isinstance(analysis, dict):
            logger.warning(
                f"Analysis is not a dict, got type: {type(analysis).__name__}"
            )
            return None

        # Validate required fields
        required_fields = [
            "category",
            "description",
            "affected_files",
            "confidence",
            "recommendations",
        ]
        for field in required_fields:
            if field not in analysis:
                logger.warning(f"Missing required field in analysis: {field}")
                return None

        return analysis

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse analysis JSON: {e}")
        preview_length = min(500, len(text))
        logger.warning(
            f"Response text preview (first {preview_length} chars): {text[:preview_length]}"
        )
        return None


def analyze_failure(
    spec_dir: Path,
    project_dir: Path,
    failure_type: str,
    failure_context: dict[str, Any],
) -> dict[str, Any]:
    """
    Analyze a failure and extract actionable insights.

    Args:
        spec_dir: Spec directory
        project_dir: Project root directory
        failure_type: Type of failure ("qa_rejection", "build_error", "test_failure")
        failure_context: Context about the failure (errors, issues, subtask_id, etc.)

    Returns:
        Dict with failure analysis:
        {
            "failure_type": str,
            "timestamp": str,
            "root_cause": dict,
            "qa_history": list,
            "recommendations": list[str],
        }
    """
    logger.info(f"Analyzing {failure_type} in {spec_dir.name}")

    # Gather failure data
    failure_data = {
        "failure_type": failure_type,
        "errors": failure_context.get("errors", []),
        "issues": failure_context.get("issues", []),
        "is_recurring": failure_context.get("is_recurring", False),
    }

    # Load QA history if available
    qa_history = load_qa_iteration_history(spec_dir)

    # Load subtask info if provided
    if subtask_id := failure_context.get("subtask_id"):
        subtask_info = load_subtask_history(spec_dir, subtask_id)
        failure_data["subtask"] = subtask_info

    # Extract root cause
    root_cause = extract_root_cause(failure_data, use_llm=True)

    # Build analysis result
    analysis = {
        "failure_type": failure_type,
        "timestamp": datetime.now(UTC).isoformat(),
        "root_cause": root_cause,
        "qa_history_length": len(qa_history),
        "recommendations": root_cause.get("recommendations", []),
    }

    # Add recurring issue warning if applicable
    if root_cause.get("is_recurring"):
        analysis["recurring_warning"] = (
            f"This issue has occurred {failure_context.get('occurrence_count', 'multiple')} times"
        )

    logger.info(
        f"Analysis complete: {root_cause['category']} (confidence: {root_cause['confidence']})"
    )

    return analysis


# =============================================================================
# Failure Storage (for Graphiti integration)
# =============================================================================


def format_for_graphiti(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Format failure analysis for storage in Graphiti memory.

    Args:
        analysis: Failure analysis result from analyze_failure()

    Returns:
        Dict formatted for Graphiti episode storage
    """
    root_cause = analysis.get("root_cause", {})

    return {
        "episode_type": "root_cause",
        "name": f"{analysis['failure_type']}: {root_cause.get('category', 'unknown')}",
        "content": root_cause.get("description", "Unknown failure"),
        "metadata": {
            "failure_type": analysis["failure_type"],
            "category": root_cause.get("category", "unknown"),
            "confidence": root_cause.get("confidence", 0.0),
            "affected_files": root_cause.get("affected_files", []),
            "is_recurring": root_cause.get("is_recurring", False),
            "recommendations": root_cause.get("recommendations", []),
            "timestamp": analysis["timestamp"],
        },
    }
