"""
Log Analyzer
============

Analyzes application logs to extract relevant information, identify error patterns,
and provide contextual insights for debugging. Works with various log formats
and extracts the most relevant log lines for error context.

Uses the Claude Agent SDK (same as the rest of the system) for analysis.
Falls back to basic analysis if extraction fails (never blocks the build).
"""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Check for Claude SDK availability
try:
    import claude_agent_sdk  # noqa: F401

    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

from core.auth import get_auth_token

# Default model for log analysis (fast and cheap)
DEFAULT_ANALYSIS_MODEL = "claude-haiku-4-5-20251001"

# Maximum log content to analyze
MAX_LOG_CHARS = 20000

# Maximum number of lines to extract
MAX_EXTRACTED_LINES = 50


def is_analysis_enabled() -> bool:
    """Check if log analysis is enabled."""
    # Analysis requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("LOG_ANALYSIS_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_analysis_model() -> str:
    """Get the model to use for log analysis."""
    return os.environ.get("LOG_ANALYZER_MODEL", DEFAULT_ANALYSIS_MODEL)


# =============================================================================
# Log Parsing Helpers
# =============================================================================


def parse_log_entry(line: str) -> dict[str, Any] | None:
    """
    Parse a single log entry into structured components.

    Args:
        line: Raw log line

    Returns:
        Dict with timestamp, level, message, or None if not a valid log entry
    """
    # Common log patterns
    patterns = [
        # Python logging: 2024-01-15 10:30:45,123 INFO logger_name Message
        r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,\.]\d{3})\s+(\w+)\s+(\S+)\s+(.+)$",
        # ISO format: [2024-01-15T10:30:45.123Z] INFO: Message
        r"^\[?(\d{4}-\d{2}-\d{2}T[\d:\.]+Z?)\]?\s*(\w+):\s*(.+)$",
        # Simple format: [INFO] Message or INFO: Message
        r"^[(\[]?(\w+)[)\]]?:?\s*(.+)$",
        # Nginx/Apache style: 127.0.0.1 - - [15/Jan/2024:10:30:45 +0000] "GET /path HTTP/1.1" 200
        r"^[\d\.]+\s+-\s+-\s+\[([^\]]+)\]\s+\"(\w+)\s+([^\"]+)\".+\s+(\d+)\s*$",
    ]

    for pattern in patterns:
        match = re.match(pattern, line.strip())
        if match:
            groups = match.groups()

            # Return structured data based on pattern
            if len(groups) >= 4:
                return {
                    "timestamp": groups[0],
                    "level": groups[1] if groups[1].upper() in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO",
                    "logger": groups[2] if len(groups) > 3 else None,
                    "message": groups[-2] if len(groups) > 3 else groups[-1],
                    "status": groups[-1] if groups[-1].isdigit() else None,
                }
            elif len(groups) == 3:
                return {
                    "timestamp": groups[0],
                    "level": groups[1],
                    "message": groups[2],
                }
            elif len(groups) == 2:
                level = groups[0].upper()
                return {
                    "level": level if level in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] else "INFO",
                    "message": groups[1],
                }

    # If no pattern matches, treat as plain message
    if line.strip():
        return {"message": line.strip()}

    return None


def load_log_file(log_path: Path, max_lines: int = 1000) -> list[str]:
    """
    Load log lines from a file.

    Args:
        log_path: Path to log file
        max_lines: Maximum number of lines to read from end of file

    Returns:
        List of log lines
    """
    if not log_path.exists():
        logger.warning(f"Log file not found: {log_path}")
        return []

    try:
        with open(log_path, encoding="utf-8", errors="replace") as f:
            # Read all lines and take the last max_lines
            all_lines = f.readlines()
            return all_lines[-max_lines:] if len(all_lines) > max_lines else all_lines

    except Exception as e:
        logger.warning(f"Failed to read log file {log_path}: {e}")
        return []


def find_log_files(project_dir: Path, log_names: list[str] | None = None) -> list[Path]:
    """
    Find log files in the project directory.

    Args:
        project_dir: Project root directory
        log_names: Specific log file names to look for (optional)

    Returns:
        List of log file paths
    """
    log_files = []
    common_log_paths = [
        "logs",
        "log",
        ".logs",
        "var/log",
        "storage/logs",
        "app/logs",
    ]

    # If specific log names provided, search for them
    if log_names:
        for log_name in log_names:
            # Check direct path
            direct_path = project_dir / log_name
            if direct_path.exists():
                log_files.append(direct_path)
                continue

            # Check in common log directories
            for log_dir in common_log_paths:
                log_path = project_dir / log_dir / log_name
                if log_path.exists():
                    log_files.append(log_path)
    else:
        # Search for common log file patterns
        common_patterns = [
            "*.log",
            "log.txt",
            "error.log",
            "debug.log",
            "application.log",
            "app.log",
            "server.log",
        ]

        for log_dir_str in common_log_paths:
            log_dir = project_dir / log_dir_str
            if not log_dir.exists():
                continue

            for pattern in common_patterns:
                matches = list(log_dir.glob(pattern))
                log_files.extend(matches)

    return log_files


# =============================================================================
# Log Analysis - Core Logic
# =============================================================================


def extract_relevant_lines(
    log_content: str,
    error_pattern: str | None = None,
    context_lines: int = 5,
) -> list[dict[str, Any]]:
    """
    Extract relevant log lines based on error patterns or keywords.

    Args:
        log_content: Full log content
        error_pattern: Optional regex pattern to match error lines
        context_lines: Number of lines before/after matched lines to include

    Returns:
        List of relevant log entries with metadata
    """
    lines = log_content.splitlines()
    relevant_entries = []

    # Default error patterns if none provided
    if not error_pattern:
        error_keywords = [
            "error",
            "exception",
            "failed",
            "failure",
            "timeout",
            "critical",
            "fatal",
            "traceback",
            "stack trace",
            "warning",
        ]
    else:
        error_keywords = [error_pattern]

    # Find matching lines and their context
    for i, line in enumerate(lines):
        parsed = parse_log_entry(line)
        if not parsed:
            continue

        message = parsed.get("message", "").lower()
        level = parsed.get("level", "").upper()

        # Check if line matches error criteria
        is_error_line = (
            level in ["ERROR", "CRITICAL", "FATAL"]
            or any(keyword in message for keyword in error_keywords)
        )

        if is_error_line:
            # Add context lines
            start_idx = max(0, i - context_lines)
            end_idx = min(len(lines), i + context_lines + 1)

            for j in range(start_idx, end_idx):
                context_line = lines[j]
                context_parsed = parse_log_entry(context_line)

                if context_parsed:
                    entry = {
                        **context_parsed,
                        "line_number": j + 1,
                        "is_match": j == i,
                        "relevance": "high" if j == i else "context",
                    }

                    # Avoid duplicates
                    if entry not in relevant_entries:
                        relevant_entries.append(entry)

            # Limit total entries
            if len(relevant_entries) >= MAX_EXTRACTED_LINES:
                break

    return relevant_entries


def _analyze_logs_heuristics(
    log_content: str,
    relevant_lines: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Perform heuristic-based log analysis.

    Args:
        log_content: Full log content
        relevant_lines: Extracted relevant log entries

    Returns:
        Basic analysis dict
    """
    analysis = {
        "summary": "No significant issues found in logs",
        "error_count": 0,
        "warning_count": 0,
        "critical_issues": [],
        "patterns_found": [],
        "affected_components": [],
        "recommendations": [],
        "confidence": 0.5,
    }

    # Count error levels
    error_keywords = {"error", "exception", "failed", "failure", "critical", "fatal"}
    warning_keywords = {"warning", "warn", "deprecated"}

    for entry in relevant_lines:
        level = entry.get("level", "").upper()
        message = entry.get("message", "").lower()

        if level in ["ERROR", "CRITICAL", "FATAL"] or any(
            kw in message for kw in error_keywords
        ):
            analysis["error_count"] += 1

            # Add critical issue if high relevance
            if entry.get("relevance") == "high":
                analysis["critical_issues"].append(
                    {
                        "message": entry.get("message", ""),
                        "line_number": entry.get("line_number"),
                        "timestamp": entry.get("timestamp"),
                    }
                )

        elif level == "WARNING" or any(kw in message for kw in warning_keywords):
            analysis["warning_count"] += 1

    # Identify patterns
    error_messages = [
        entry.get("message", "")
        for entry in relevant_lines
        if entry.get("relevance") == "high"
    ]

    # Common error patterns
    if any("connection" in msg.lower() for msg in error_messages):
        analysis["patterns_found"].append("connection_issues")
        analysis["affected_components"].append("database/network")
        analysis["recommendations"].append(
            "Check database/network connectivity and configuration"
        )

    if any("timeout" in msg.lower() for msg in error_messages):
        analysis["patterns_found"].append("timeout_issues")
        analysis["affected_components"].append("external_services")
        analysis["recommendations"].append(
            "Review timeout settings and external service availability"
        )

    if any("permission" in msg.lower() or "access denied" in msg.lower() for msg in error_messages):
        analysis["patterns_found"].append("permission_issues")
        analysis["affected_components"].append("authentication/authorization")
        analysis["recommendations"].append(
            "Verify user permissions and access control settings"
        )

    if any("memory" in msg.lower() or "out of memory" in msg.lower() for msg in error_messages):
        analysis["patterns_found"].append("memory_issues")
        analysis["affected_components"].append("application_runtime")
        analysis["recommendations"].append(
            "Investigate memory usage patterns and potential leaks"
        )

    # Update summary based on findings
    if analysis["error_count"] > 0:
        analysis["summary"] = (
            f"Found {analysis['error_count']} error(s) and {analysis['warning_count']} warning(s) in logs"
        )
        analysis["confidence"] = 0.7

        if analysis["critical_issues"]:
            analysis["summary"] += f" with {len(analysis['critical_issues'])} critical issues"
            analysis["confidence"] = 0.8

    return analysis


def _analyze_logs_with_llm(
    log_content: str,
    relevant_lines: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Perform LLM-based log analysis.

    Args:
        log_content: Full log content
        relevant_lines: Extracted relevant log entries

    Returns:
        Enhanced analysis dict or None if analysis fails
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
        return asyncio.run(_run_llm_log_analysis(log_content, relevant_lines))
    except Exception as e:
        logger.warning(f"LLM log analysis failed: {e}")
        return None


async def _run_llm_log_analysis(
    log_content: str,
    relevant_lines: list[dict[str, Any]],
) -> dict[str, Any] | None:
    """
    Run the LLM log analysis asynchronously.

    Args:
        log_content: Full log content
        relevant_lines: Extracted relevant log entries

    Returns:
        Parsed analysis dict or None if analysis fails
    """
    from core.auth import ensure_claude_code_oauth_token
    from core.simple_client import create_simple_client

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = get_analysis_model()
    prompt = _build_log_analysis_prompt(log_content, relevant_lines)

    try:
        client = create_simple_client(
            agent_type="log_analyzer",
            model=model,
            system_prompt=(
                "You are a log analysis expert. You analyze application logs to identify error patterns, "
                "root causes, and provide actionable insights. Always respond with valid JSON only, "
                "no markdown formatting or explanations."
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
                f"Log analysis response: {message_count} messages, "
                f"{text_blocks_found} text blocks, {len(response_text)} chars collected"
            )

            if not response_text.strip():
                logger.warning(
                    f"Log analysis returned empty response. "
                    f"Messages received: {message_count}, TextBlocks found: {text_blocks_found}"
                )
                return None

        # Parse JSON from response
        return _parse_log_analysis_response(response_text)

    except Exception as e:
        logger.warning(f"LLM log analysis execution failed: {e}")
        return None


def _build_log_analysis_prompt(
    log_content: str,
    relevant_lines: list[dict[str, Any]],
) -> str:
    """
    Build the prompt for log analysis.

    Args:
        log_content: Full log content
        relevant_lines: Extracted relevant log entries

    Returns:
        Full prompt text
    """
    prompt_file = Path(__file__).parent / "prompts" / "log_analysis.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        # Fallback if prompt file missing
        base_prompt = """Analyze these log entries and provide insights.
Output ONLY valid JSON with: summary, error_count, warning_count, patterns_found, recommendations"""

    # Truncate log content if too long
    truncated_content = log_content
    if len(log_content) > MAX_LOG_CHARS:
        truncated_content = (
            log_content[:MAX_LOG_CHARS]
            + f"\n\n... (truncated, {len(log_content)} chars total)"
        )

    # Format relevant lines
    relevant_lines_text = "\n".join(
        f"Line {entry.get('line_number', '?')} [{entry.get('level', 'INFO')}]: {entry.get('message', '')}"
        for entry in relevant_lines[:20]  # Limit to 20 entries for prompt
    )

    # Build log context
    log_context = f"""
---

## LOG DATA TO ANALYZE

### Full Log Content (truncated if needed)
{truncated_content if truncated_content else "(Empty logs)"}

### Relevant Extracted Lines
{relevant_lines_text if relevant_lines_text else "(No relevant lines extracted)"}

---

Now analyze these logs and output ONLY the JSON object with your analysis.
"""

    return base_prompt + log_context


def _parse_log_analysis_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the LLM response into structured analysis dict.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed analysis dict or None if parsing failed
    """
    text = response_text.strip()

    if not text:
        logger.warning("Cannot parse log analysis: response text is empty")
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
                "Cannot parse log analysis: response contained only markdown markers"
            )
            return None

    try:
        analysis = json.loads(text)

        if not isinstance(analysis, dict):
            logger.warning(
                f"Log analysis is not a dict, got type: {type(analysis).__name__}"
            )
            return None

        # Validate required fields
        required_fields = [
            "summary",
            "error_count",
            "warning_count",
            "recommendations",
        ]
        for field in required_fields:
            if field not in analysis:
                logger.warning(f"Missing required field in log analysis: {field}")
                return None

        return analysis

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse log analysis JSON: {e}")
        preview_length = min(500, len(text))
        logger.warning(
            f"Response text preview (first {preview_length} chars): {text[:preview_length]}"
        )
        return None


def analyze_logs(
    log_content: str,
    error_pattern: str | None = None,
    context_lines: int = 5,
    use_llm: bool = True,
) -> dict[str, Any]:
    """
    Analyze log content and extract actionable insights.

    Args:
        log_content: Full log content to analyze
        error_pattern: Optional regex pattern to match error lines
        context_lines: Number of lines before/after matched lines to include
        use_llm: Whether to use LLM for deeper analysis

    Returns:
        Dict with log analysis:
        {
            "summary": str,
            "error_count": int,
            "warning_count": int,
            "critical_issues": list[dict],
            "patterns_found": list[str],
            "affected_components": list[str],
            "recommendations": list[str],
            "confidence": float,
            "timestamp": str,
            "relevant_lines": list[dict],
        }
    """
    logger.info("Analyzing log content")

    # Extract relevant lines
    relevant_lines = extract_relevant_lines(log_content, error_pattern, context_lines)

    # Basic heuristic analysis (always runs)
    analysis = _analyze_logs_heuristics(log_content, relevant_lines)

    # Add metadata
    analysis["timestamp"] = datetime.now(UTC).isoformat()
    analysis["relevant_lines_count"] = len(relevant_lines)
    analysis["relevant_lines"] = relevant_lines[:20]  # Include top 20 in result

    # Enhanced LLM analysis (optional)
    if use_llm and is_analysis_enabled():
        try:
            llm_analysis = _analyze_logs_with_llm(log_content, relevant_lines)
            if llm_analysis:
                # Merge LLM insights with heuristic base
                analysis.update(llm_analysis)
        except Exception as e:
            logger.warning(f"LLM analysis failed, using heuristics only: {e}")

    logger.info(
        f"Log analysis complete: {analysis['error_count']} errors, "
        f"{analysis['warning_count']} warnings (confidence: {analysis['confidence']})"
    )

    return analysis


# =============================================================================
# Log Storage (for Graphiti integration)
# =============================================================================


def format_for_graphiti(analysis: dict[str, Any]) -> dict[str, Any]:
    """
    Format log analysis for storage in Graphiti memory.

    Args:
        analysis: Log analysis result from analyze_logs()

    Returns:
        Dict formatted for Graphiti episode storage
    """
    return {
        "episode_type": "log_analysis",
        "name": f"Log Analysis: {analysis.get('summary', 'unknown')[:50]}",
        "content": analysis.get("summary", "Unknown log pattern"),
        "metadata": {
            "error_count": analysis.get("error_count", 0),
            "warning_count": analysis.get("warning_count", 0),
            "patterns_found": analysis.get("patterns_found", []),
            "affected_components": analysis.get("affected_components", []),
            "confidence": analysis.get("confidence", 0.0),
            "timestamp": analysis["timestamp"],
        },
    }
