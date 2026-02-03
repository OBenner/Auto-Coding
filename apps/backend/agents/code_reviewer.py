"""
Code Review Agent Session
==========================

Runs code review sessions to analyze code changes for security issues,
performance anti-patterns, and style violations.

Memory Integration:
- Retrieves past security patterns, gotchas, and review insights before session
- Saves code review findings (vulnerabilities, patterns, recommendations) after session
"""

from pathlib import Path

# Memory integration for cross-session learning
from agents.memory_manager import get_graphiti_context, save_session_memory
from claude_agent_sdk import ClaudeSDKClient
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from security.tool_input_validator import get_safe_tool_input
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)

from .session import run_agent_session

# =============================================================================
# CODE REVIEW SESSION
# =============================================================================


async def run_code_review_session(
    client: ClaudeSDKClient,
    project_dir: Path,
    spec_dir: Path,
    target_files: list[str] | None = None,
    pr_number: int | None = None,
    review_session: int = 1,
    verbose: bool = False,
    previous_error: dict | None = None,
) -> tuple[str, str]:
    """
    Run a code review agent session.

    Args:
        client: Claude SDK client
        project_dir: Project root directory (for capability detection)
        spec_dir: Spec directory
        target_files: Optional list of specific files to review
        pr_number: Optional PR number for GitHub integration
        review_session: Review iteration number
        verbose: Whether to show detailed output
        previous_error: Error context from previous iteration for self-correction

    Returns:
        (status, response_text) where status is:
        - "approved" if review approves
        - "issues_found" if review finds problems
        - "error" if an error occurred
    """
    debug_section("code_reviewer", f"Code Review Session {review_session}")
    debug(
        "code_reviewer",
        "Starting code review session",
        spec_dir=str(spec_dir),
        review_session=review_session,
        target_files=target_files,
        pr_number=pr_number,
    )

    print(f"\n{'=' * 70}")
    print(f"  CODE REVIEW SESSION {review_session}")
    print("  Analyzing code for security, performance, and style issues...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Load code review prompt with dynamically-injected project-specific MCP tools
    # For now, we'll use a placeholder until subtask-1-2 creates the prompt
    try:
        from prompts_pkg import get_code_review_prompt

        prompt = get_code_review_prompt(spec_dir, project_dir)
        debug_detailed(
            "code_reviewer",
            "Loaded code review prompt with project-specific tools",
            prompt_length=len(prompt),
            project_dir=str(project_dir),
        )
    except ImportError:
        # Fallback prompt for initial development
        debug(
            "code_reviewer",
            "Code review prompt not yet available, using placeholder",
        )
        prompt = f"""
You are a code review specialist agent. Your role is to analyze code changes and provide:

1. **Security Analysis**: Identify vulnerabilities, injection risks, and unsafe patterns
2. **Performance Review**: Detect anti-patterns, inefficient algorithms, memory leaks
3. **Style & Best Practices**: Check code conventions, readability, maintainability
4. **Actionable Feedback**: Provide clear, specific recommendations for improvement

Review the code changes in: {project_dir}
Spec directory: {spec_dir}
"""

    # Retrieve memory context for code review (past patterns, gotchas, security insights)
    review_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "Code review for security, performance, and style",
            "id": f"code_reviewer_{review_session}",
        },
    )
    if review_memory_context:
        prompt += "\n\n" + review_memory_context
        print("✓ Memory context loaded for code reviewer")
        debug_success("code_reviewer", "Graphiti memory context loaded for review")

    # Add session context
    prompt += f"\n\n---\n\n**Review Session**: {review_session}\n"
    if target_files:
        prompt += f"**Target Files**: {', '.join(target_files)}\n"
    if pr_number:
        prompt += f"**PR Number**: {pr_number}\n"

    # Add error context for self-correction if previous iteration failed
    if previous_error:
        debug(
            "code_reviewer",
            "Adding error context for self-correction",
            error_type=previous_error.get("error_type"),
            consecutive_errors=previous_error.get("consecutive_errors"),
        )
        prompt += f"""

---

## ⚠️ CRITICAL: PREVIOUS ITERATION FAILED - SELF-CORRECTION REQUIRED

The previous code review session failed with the following error:

**Error**: {previous_error.get("error_message", "Unknown error")}
**Consecutive Failures**: {previous_error.get("consecutive_errors", 1)}

### Required Action

After completing your code review, you MUST create a review report file at:
`{spec_dir}/code_review_report.md`

This is attempt {previous_error.get("consecutive_errors", 1) + 1}. If you fail to create the report again, the review process will be escalated to human review.

---

"""
        print(
            f"\n⚠️  Retry with self-correction context (attempt {previous_error.get('consecutive_errors', 1) + 1})"
        )

    try:
        debug("code_reviewer", "Starting code review agent session...")

        # Run the agent session
        status, response_text = await run_agent_session(
            client=client,
            message=prompt,
            spec_dir=spec_dir,
            verbose=verbose,
            phase=LogPhase.CODING,  # Use CODING phase for now
        )

        debug_success(
            "code_reviewer",
            f"Code review session completed with status: {status}",
        )

        # Analyze response to determine if issues were found
        if status == "error":
            debug_error("code_reviewer", "Code review session failed")
            return ("error", response_text)

        # Check if review report was created
        review_report = spec_dir / "code_review_report.md"
        if review_report.exists():
            # Parse report to determine approval status
            content = review_report.read_text()
            if "APPROVED" in content.upper() or "NO ISSUES" in content.upper():
                debug_success("code_reviewer", "Code review approved")
                return ("approved", response_text)
            else:
                debug("code_reviewer", "Code review found issues")
                return ("issues_found", response_text)
        else:
            # No report created - assume issues found if session completed
            debug(
                "code_reviewer",
                "No review report found, assuming issues for follow-up",
            )
            return ("issues_found", response_text)

    except Exception as e:
        debug_error("code_reviewer", f"Code review session error: {e}")
        if task_logger:
            task_logger.log_error(
                f"Code review session error: {e}",
                LogPhase.CODING,
            )
        return ("error", str(e))
