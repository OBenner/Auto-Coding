"""
Debug Assistant
===============

Main orchestrator for intelligent debugging assistance. Coordinates stack trace parsing,
error pattern matching, fix suggestions, fix verification, and log analysis
to provide comprehensive debugging support.

Uses the Claude Agent SDK (same as the rest of the system) for analysis.
Falls back to heuristic analysis if SDK fails (never blocks debugging).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
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

from .error_pattern_matcher import match_error_pattern
from .fix_suggester import suggest_fix
from .fix_verifier import FixVerifier
from .log_analyzer import analyze_logs

# Import all analyzer modules
from .stack_trace_parser import (
    get_failing_file,
    get_failing_line,
    parse_stack_trace,
)

# Default model for debug assistant (fast and accurate)
DEFAULT_ASSISTANT_MODEL = "claude-haiku-4-5-20251001"

# Maximum trace size to process
MAX_TRACE_CHARS = 15000


def is_assistant_enabled() -> bool:
    """Check if debug assistant is enabled."""
    # Assistant requires Claude SDK and authentication token
    if not SDK_AVAILABLE:
        return False
    if not get_auth_token():
        return False
    enabled_str = os.environ.get("DEBUG_ASSISTANT_ENABLED", "true").lower()
    return enabled_str in ("true", "1", "yes")


def get_assistant_model() -> str:
    """Get the model to use for debug assistant."""
    return os.environ.get("DEBUG_ASSISTANT_MODEL", DEFAULT_ASSISTANT_MODEL)


# =============================================================================
# DEBUG ASSISTANT ORCHESTRATOR
# =============================================================================


class DebugAssistant:
    """
    Main orchestrator for debugging assistance.

    Coordinates all analysis modules:
    - Stack trace parsing
    - Error pattern matching
    - Fix suggestion
    - Fix verification
    - Log analysis
    - Historical error lookup

    Provides unified interface for debugging errors with AI-powered insights.
    """

    def __init__(self, project_dir: Path | None = None, spec_dir: Path | None = None):
        """
        Initialize debug assistant.

        Args:
            project_dir: Project root directory
            spec_dir: Spec directory (for memory integration)
        """
        self.project_dir = Path(project_dir) if project_dir else Path.cwd()
        self.spec_dir = Path(spec_dir) if spec_dir else self.project_dir
        self._fix_verifier = FixVerifier()
        self._cache: dict[str, Any] = {}

    def debug_error(
        self,
        error_trace: str,
        code_context: dict | None = None,
        log_content: str | None = None,
        use_historical: bool = True,
    ) -> dict[str, Any]:
        """
        Debug an error with comprehensive analysis.

        This is the main entry point for debugging. It orchestrates all
        analyzers to provide a complete debugging report.

        Args:
            error_trace: Raw stack trace string
            code_context: Context about failing code (file, lines, etc.)
            log_content: Optional log content for context
            use_historical: Whether to look up historical errors

        Returns:
            Comprehensive debug report:
            {
                "parsed_trace": dict,
                "pattern_match": dict | None,
                "fix_suggestion": dict,
                "fix_verification": dict,
                "log_analysis": dict | None,
                "historical_errors": list,
                "explanation": str,  # Plain language explanation
                "recommendations": list[str],
                "confidence": float,
                "timestamp": str,
            }
        """
        logger.info("Starting comprehensive error debugging")

        # Step 1: Parse stack trace
        parsed_trace = self._parse_trace(error_trace)

        # Step 2: Match error pattern
        pattern_match = self._match_pattern(parsed_trace)

        # Step 3: Get historical errors (if enabled)
        historical_errors = []
        if use_historical:
            historical_errors = self._get_historical_errors(parsed_trace, pattern_match)

        # Step 4: Suggest fixes
        fix_suggestion = self._suggest_fixes(
            parsed_trace, pattern_match, code_context, historical_errors
        )

        # Step 5: Verify fixes
        fix_verification = self._verify_fix(fix_suggestion, parsed_trace)

        # Step 6: Analyze logs (if provided)
        log_analysis = None
        if log_content:
            log_analysis = self._analyze_logs(log_content, parsed_trace)

        # Step 7: Generate explanation
        explanation = self._generate_explanation(
            parsed_trace, pattern_match, fix_suggestion
        )

        # Compile comprehensive report
        report = {
            "parsed_trace": self._serialize_trace(parsed_trace),
            "pattern_match": self._serialize_pattern_match(pattern_match),
            "fix_suggestion": fix_suggestion,
            "fix_verification": self._serialize_verification(fix_verification),
            "log_analysis": log_analysis,
            "historical_errors_count": len(historical_errors),
            "historical_errors": historical_errors[:3],  # Top 3 most relevant
            "explanation": explanation,
            "recommendations": self._generate_recommendations(
                fix_suggestion, fix_verification, log_analysis
            ),
            "confidence": self._calculate_confidence(
                pattern_match, fix_suggestion, fix_verification
            ),
            "timestamp": datetime.now(UTC).isoformat(),
        }

        logger.info(
            f"Debugging complete: {parsed_trace.get('error_type', 'Unknown')} "
            f"(confidence: {report['confidence']})"
        )

        return report

    def explain_error(
        self,
        error_trace: str,
        detail_level: str = "basic",
    ) -> dict[str, Any]:
        """
        Explain an error in plain language.

        Args:
            error_trace: Raw stack trace string
            detail_level: Level of detail ("basic", "detailed", "comprehensive")

        Returns:
            Explanation dict:
            {
                "error_type": str,
                "error_message": str,
                "plain_language_explanation": str,
                "likely_causes": list[str],
                "affected_code": str | None,
                "suggested_actions": list[str],
            }
        """
        # Parse trace
        parsed = parse_stack_trace(error_trace)

        if not parsed:
            return {
                "error_type": "UnknownError",
                "error_message": "Could not parse error trace",
                "plain_language_explanation": "The error trace could not be parsed. "
                "Please check the format and try again.",
                "likely_causes": [],
                "affected_code": None,
                "suggested_actions": ["Review error trace format"],
            }

        # Match pattern for explanation
        pattern_match = match_error_pattern(parsed)

        explanation = {
            "error_type": parsed.error_type,
            "error_message": parsed.error_message,
            "language": parsed.language,
            "failing_file": get_failing_file(parsed),
            "failing_line": get_failing_line(parsed),
        }

        # Build plain language explanation
        if pattern_match and hasattr(pattern_match, "pattern"):
            pattern = pattern_match.pattern
            explanation["plain_language_explanation"] = pattern.description
            explanation["likely_causes"] = pattern.common_causes
        else:
            explanation["plain_language_explanation"] = (
                f"A {parsed.error_type} occurred in {parsed.language} code. "
                f"This means: {parsed.error_message}"
            )
            explanation["likely_causes"] = [
                "Code syntax error or typo",
                "Incorrect type usage",
                "Missing or invalid data",
            ]

        # Add detail-level information
        if detail_level in ["detailed", "comprehensive"]:
            explanation["stack_frames"] = [
                {
                    "file": f.file_path,
                    "line": f.line_number,
                    "function": f.function_name,
                }
                for f in parsed.frames
            ]

            if pattern_match:
                explanation["pattern_suggestion"] = pattern_match.pattern.suggestion

        # Generate suggested actions
        explanation["suggested_actions"] = [
            "Review the failing code for obvious issues",
            "Check for common error patterns",
            "Consider adding error handling or validation",
            "Run tests to verify fix",
        ]

        return explanation

    # -------------------------------------------------------------------------
    # Internal helper methods
    # -------------------------------------------------------------------------

    def _parse_trace(self, error_trace: str) -> dict[str, Any]:
        """Parse stack trace into structured dict."""
        # Check cache first
        cache_key = f"trace:{hash(error_trace)}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Parse trace
        parsed = parse_stack_trace(error_trace)

        if not parsed:
            result = {
                "error_type": "UnknownError",
                "error_message": error_trace[:200] if error_trace else "",
                "language": "unknown",
                "failing_file": None,
                "failing_line": None,
                "frame_count": 0,
            }
        else:
            result = {
                "error_type": parsed.error_type,
                "error_message": parsed.error_message,
                "language": parsed.language,
                "failing_file": get_failing_file(parsed),
                "failing_line": get_failing_line(parsed),
                "frame_count": len(parsed.frames),
            }

        # Cache and return
        self._cache[cache_key] = result
        return result

    def _match_pattern(self, parsed_trace: dict) -> dict | None:
        """Match error against known patterns."""
        # Reconstruct ParsedStackTrace for matching
        if not parsed_trace.get("error_type"):
            return None

        from .stack_trace_parser import ParsedStackTrace

        trace_obj = ParsedStackTrace(
            error_type=parsed_trace["error_type"],
            error_message=parsed_trace["error_message"],
            language=parsed_trace["language"],
            frames=[],  # Frames not needed for pattern matching
            raw_trace="",
        )

        # Match pattern
        pattern_match = match_error_pattern(trace_obj)

        if not pattern_match:
            return None

        # Serialize pattern match
        return {
            "category": pattern_match.pattern.category,
            "name": pattern_match.pattern.name,
            "description": pattern_match.pattern.description,
            "suggestion": pattern_match.pattern.suggestion,
            "common_causes": pattern_match.pattern.common_causes,
            "confidence": pattern_match.confidence,
        }

    def _get_historical_errors(
        self, parsed_trace: dict, pattern_match: dict | None
    ) -> list[dict]:
        """Get historical errors from memory (Graphiti)."""
        try:
            from integrations.graphiti.memory import get_graphiti_memory

            memory = get_graphiti_memory(self.spec_dir, self.project_dir)

            # Search for similar errors
            error_type = parsed_trace.get("error_type", "UnknownError")
            error_message = parsed_trace.get("error_message", "")

            # Use Graphiti search for similar errors
            from integrations.graphiti.queries_pkg.search import GraphitiSearch

            search = GraphitiSearch(
                client=memory.client,
                group_id=memory.group_id,
                spec_context_id=memory.spec_context_id,
                group_id_mode=memory.group_id_mode,
                project_dir=memory.project_dir,
            )

            # search_similar_errors is async - run it
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                # Already in async context - create task
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    similar_errors = executor.submit(
                        asyncio.run,
                        search.search_similar_errors(
                            error_type=error_type,
                            error_message=error_message,
                            min_score=0.5,
                            limit=5,
                        ),
                    ).result()
            else:
                similar_errors = asyncio.run(
                    search.search_similar_errors(
                        error_type=error_type,
                        error_message=error_message,
                        min_score=0.5,
                        limit=5,
                    )
                )

            return similar_errors

        except ImportError as e:
            logger.warning(f"Graphiti not available for historical errors: {e}")
            return []
        except Exception as e:
            logger.warning(f"Failed to retrieve historical errors: {e}")
            return []

    def _suggest_fixes(
        self,
        parsed_trace: dict,
        pattern_match: dict | None,
        code_context: dict | None,
        historical_errors: list[dict],
    ) -> dict:
        """Suggest fixes using AI or patterns."""
        # Run async fix suggestion
        try:
            coro = suggest_fix(
                parsed_trace=parsed_trace,
                pattern_match=pattern_match,
                code_context=code_context,
                historical_errors=historical_errors,
                project_dir=self.project_dir,
            )

            try:
                asyncio.get_running_loop()
                # Already in async context - run in thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    suggestion = executor.submit(asyncio.run, coro).result()
            except RuntimeError:
                # No running loop - safe to use asyncio.run
                suggestion = asyncio.run(coro)

            return suggestion or {
                "root_cause": "Unable to generate suggestion",
                "fix_category": "unknown",
                "suggested_fixes": ["Review error and code manually"],
                "verification_steps": [],
                "confidence": 0.3,
                "pattern_based": True,
            }

        except Exception as e:
            logger.warning(f"Fix suggestion failed: {e}")
            return {
                "root_cause": f"Error during suggestion: {e}",
                "fix_category": "unknown",
                "suggested_fixes": ["Manual review required"],
                "verification_steps": [],
                "confidence": 0.2,
                "pattern_based": True,
            }

    def _verify_fix(self, fix_suggestion: dict, parsed_trace: dict) -> dict:
        """Verify a fix suggestion."""
        try:
            verification = self._fix_verifier.verify(
                fix_suggestion, self.project_dir, parsed_trace
            )
            return self._serialize_verification(verification)
        except Exception as e:
            logger.warning(f"Fix verification failed: {e}")
            return {
                "is_safe": False,
                "risk_level": "unknown",
                "test_command": "",
                "warnings": [f"Verification failed: {e}"],
                "recommendations": ["Manual review required"],
            }

    def _analyze_logs(self, log_content: str, parsed_trace: dict) -> dict | None:
        """Analyze log content for error context."""
        try:
            error_type = parsed_trace.get("error_type", "")
            return analyze_logs(
                log_content=log_content,
                error_pattern=error_type if error_type else None,
                context_lines=5,
                use_llm=is_assistant_enabled(),
            )
        except Exception as e:
            logger.warning(f"Log analysis failed: {e}")
            return None

    def _generate_explanation(
        self, parsed_trace: dict, pattern_match: dict | None, fix_suggestion: dict
    ) -> str:
        """Generate plain language explanation of error."""
        error_type = parsed_trace.get("error_type", "UnknownError")
        error_message = parsed_trace.get("error_message", "")
        language = parsed_trace.get("language", "unknown")

        explanation_parts = [
            f"**Error Type:** {error_type}",
            f"**Language:** {language}",
            f"**What Happened:** {error_message}",
        ]

        if pattern_match:
            explanation_parts.append(
                f"**Why It Happened:** {pattern_match.get('description', 'Unknown cause')}"
            )

        if fix_suggestion.get("suggested_fixes"):
            explanation_parts.append("\n**Suggested Fixes:**")
            for i, fix in enumerate(fix_suggestion["suggested_fixes"][:3], 1):
                explanation_parts.append(f"{i}. {fix}")

        return "\n".join(explanation_parts)

    def _generate_recommendations(
        self,
        fix_suggestion: dict,
        fix_verification: dict,
        log_analysis: dict | None,
    ) -> list[str]:
        """Generate comprehensive recommendations."""
        recommendations = []

        # From fix suggestion
        if fix_suggestion.get("verification_steps"):
            recommendations.extend(fix_suggestion["verification_steps"])

        # From fix verification
        if fix_verification.get("recommendations"):
            recommendations.extend(fix_verification["recommendations"])

        # From log analysis
        if log_analysis and log_analysis.get("recommendations"):
            recommendations.extend(log_analysis["recommendations"])

        # Safety recommendations
        if not fix_verification.get("is_safe", True):
            recommendations.insert(
                0, "⚠️ CAUTION: This fix has risks - review carefully before applying"
            )

        # Remove duplicates while preserving order
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec not in seen:
                seen.add(rec)
                unique_recommendations.append(rec)

        return unique_recommendations

    def _calculate_confidence(
        self, pattern_match: dict | None, fix_suggestion: dict, fix_verification: dict
    ) -> float:
        """Calculate overall confidence in the analysis."""
        confidence_scores = []

        # Pattern match confidence
        if pattern_match:
            confidence_scores.append(pattern_match.get("confidence", 0.5))

        # Fix suggestion confidence
        if fix_suggestion:
            confidence_scores.append(fix_suggestion.get("confidence", 0.5))

        # Fix verification impact
        if fix_verification.get("is_safe"):
            confidence_scores.append(0.8)
        else:
            confidence_scores.append(0.4)

        # Average confidence scores
        if confidence_scores:
            return sum(confidence_scores) / len(confidence_scores)

        return 0.5

    def _serialize_trace(self, parsed: dict) -> dict[str, Any]:
        """Serialize parsed trace (already a dict, just validate)."""
        return parsed

    def _serialize_pattern_match(self, pattern_match: dict | None) -> dict | None:
        """Serialize pattern match (already a dict if not None)."""
        return pattern_match

    def _serialize_verification(self, verification: Any) -> dict[str, Any]:
        """Serialize verification result."""
        if isinstance(verification, dict):
            return verification

        # If it's a VerificationResult dataclass
        return {
            "is_safe": verification.is_safe,
            "test_command": verification.test_command,
            "test_results": verification.test_results,
            "risk_level": verification.risk_level,
            "warnings": verification.warnings,
            "recommendations": verification.recommendations,
        }


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================


def debug_error(
    error_trace: str,
    project_dir: Path | None = None,
    code_context: dict | None = None,
    log_content: str | None = None,
) -> dict[str, Any]:
    """
    Debug an error with comprehensive analysis.

    Convenience function that creates a DebugAssistant and runs debugging.

    Args:
        error_trace: Raw stack trace string
        project_dir: Project root directory
        code_context: Context about failing code
        log_content: Optional log content for context

    Returns:
        Comprehensive debug report from DebugAssistant.debug_error()
    """
    assistant = DebugAssistant(project_dir=project_dir)
    return assistant.debug_error(error_trace, code_context, log_content)


def explain_error(
    error_trace: str,
    detail_level: str = "basic",
) -> dict[str, Any]:
    """
    Explain an error in plain language.

    Convenience function for quick error explanations.

    Args:
        error_trace: Raw stack trace string
        detail_level: Level of detail ("basic", "detailed", "comprehensive")

    Returns:
        Explanation dict from DebugAssistant.explain_error()
    """
    assistant = DebugAssistant()
    return assistant.explain_error(error_trace, detail_level)


# =============================================================================
# AI-POWERED DEBUGGING (Optional Enhancement)
# =============================================================================


async def debug_with_ai(
    error_trace: str,
    project_dir: Path | None = None,
    code_context: dict | None = None,
    historical_context: str = "",
) -> dict[str, Any] | None:
    """
    Debug an error using AI-powered analysis.

    This is an enhanced version that uses LLM for deeper analysis
    when the debug assistant is enabled.

    Args:
        error_trace: Raw stack trace string
        project_dir: Project root directory
        code_context: Context about failing code
        historical_context: Historical error context as text

    Returns:
        Enhanced debug report with AI insights, or None if AI unavailable
    """
    if not SDK_AVAILABLE:
        logger.warning("Claude SDK not available for AI debugging")
        return None

    if not get_auth_token():
        logger.warning("No authentication token found for AI debugging")
        return None

    from core.auth import ensure_claude_code_oauth_token
    from core.simple_client import create_simple_client

    # Ensure SDK can find the token
    ensure_claude_code_oauth_token()

    model = get_assistant_model()
    prompt = _build_ai_debug_prompt(error_trace, code_context, historical_context)

    try:
        client = create_simple_client(
            agent_type="debug_assistant",
            model=model,
            system_prompt=(
                "You are an expert debugging assistant. You analyze errors, identify root causes, "
                "and provide specific, actionable fixes with code examples. "
                "Always respond with valid JSON only, no markdown formatting."
            ),
            cwd=project_dir,
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
                f"AI debug response: {message_count} messages, "
                f"{text_blocks_found} text blocks, {len(response_text)} chars collected"
            )

            if not response_text.strip():
                logger.warning(
                    f"AI debug returned empty response. "
                    f"Messages received: {message_count}, TextBlocks found: {text_blocks_found}"
                )
                return None

        # Parse JSON from response
        return _parse_ai_debug_response(response_text)

    except Exception as e:
        logger.warning(f"AI debug execution failed: {e}")
        return None


def _build_ai_debug_prompt(
    error_trace: str, code_context: dict | None, historical_context: str
) -> str:
    """Build the prompt for AI-powered debugging."""
    prompt_file = Path(__file__).parent / "prompts" / "debug_assistant.md"

    if prompt_file.exists():
        base_prompt = prompt_file.read_text(encoding="utf-8")
    else:
        # Fallback if prompt file missing
        base_prompt = """Analyze this error and provide comprehensive debugging assistance.
Output ONLY valid JSON with: root_cause, explanation, suggested_fixes, verification_steps"""

    # Build error context
    error_section = f"""
---

## ERROR TRACE TO DEBUG

```
{error_trace[:MAX_TRACE_CHARS]}
```
"""

    # Build code context
    code_section = ""
    if code_context:
        failing_code = code_context.get("failing_code", "(Code not available)")
        code_section = f"""

### FAILING CODE
```{code_context.get("language", "unknown")}
{failing_code}
```
"""

    # Build historical context
    history_section = ""
    if historical_context:
        history_section = f"""

### HISTORICAL CONTEXT
{historical_context}
"""

    session_context = f"""{error_section}{code_section}{history_section}

---

Now analyze this error comprehensively and output ONLY the JSON object with your analysis.
"""

    return base_prompt + session_context


def _parse_ai_debug_response(response_text: str) -> dict[str, Any] | None:
    """
    Parse the AI debug response into structured dict.

    Args:
        response_text: Raw LLM response

    Returns:
        Parsed debug dict or None if parsing failed
    """
    text = response_text.strip()

    if not text:
        logger.warning("Cannot parse AI debug: response text is empty")
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
                "Cannot parse AI debug: response contained only markdown markers"
            )
            return None

    try:
        debug_result = json.loads(text)

        if not isinstance(debug_result, dict):
            logger.warning(
                f"AI debug is not a dict, got type: {type(debug_result).__name__}"
            )
            return None

        # Ensure required keys exist
        debug_result.setdefault("root_cause", "Unknown root cause")
        debug_result.setdefault("explanation", "No explanation available")
        debug_result.setdefault("suggested_fixes", [])
        debug_result.setdefault("verification_steps", [])
        debug_result.setdefault("confidence", 0.5)

        return debug_result

    except json.JSONDecodeError as e:
        logger.warning(f"Failed to parse AI debug JSON: {e}")
        preview_length = min(500, len(text))
        logger.warning(
            f"Response text preview (first {preview_length} chars): {text[:preview_length]}"
        )
        return None
