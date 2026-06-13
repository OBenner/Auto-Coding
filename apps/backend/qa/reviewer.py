"""
QA Reviewer Agent Session
==========================

Runs QA validation sessions to review implementation against
acceptance criteria.

Memory Integration:
- Retrieves past patterns, gotchas, and insights before QA session
- Saves QA findings (bugs, patterns, validation outcomes) after session

Coverage Integration:
- Runs coverage validation before QA session
- Includes coverage results in QA prompt
- Coverage results included in qa_signoff
"""

import json
import logging
from pathlib import Path

from agents.memory_manager import get_graphiti_context, save_session_memory
from agents.session import save_token_stats
from analysis.coverage_analyzer import CoverageAnalyzer, parse_coverage_json
from claude_agent_sdk import ClaudeSDKClient
from core.providers import create_engine_provider
from core.providers.base import SessionConfig
from core.providers.config import ProviderConfig
from debug import debug, debug_detailed, debug_error, debug_section, debug_success
from prompts_pkg import get_qa_reviewer_prompt
from security.tool_input_validator import get_safe_tool_input
from spec.coverage_config import load_coverage_config
from task_logger import (
    LogEntryType,
    LogPhase,
    get_task_logger,
)
from ui import print_status

# Import plugin system for agent lifecycle hooks
try:
    from plugins.base import PluginType
    from plugins.registry import PluginRegistry
    from plugins.sdk.agent import AgentContext

    PLUGINS_AVAILABLE = True
except ImportError:
    PLUGINS_AVAILABLE = False

from .coverage_validator import (
    format_coverage_report,
    format_validation_summary,
    validate_coverage,
)

logger = logging.getLogger(__name__)

# =============================================================================
# COVERAGE VALIDATION
# =============================================================================


def run_coverage_validation(
    project_dir: Path,
    spec_dir: Path,
) -> tuple[bool, str, dict | None]:
    """
    Run coverage analysis and validation.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory

    Returns:
        (success, summary_text, coverage_data) tuple where:
        - success: True if coverage validation passed or was skipped
        - summary_text: Human-readable summary of coverage results
        - coverage_data: Structured coverage data for qa_signoff (or None if skipped)
    """
    debug_section("coverage_validator", "Running coverage validation")

    # Load coverage configuration
    try:
        config = load_coverage_config(project_dir, spec_dir)
        debug(
            "coverage_validator",
            "Loaded coverage configuration",
            minimum_coverage=config.minimum_coverage,
            config_source=config.config_source,
            critical_paths=len(config.critical_paths),
        )
    except Exception as e:
        debug_error("coverage_validator", f"Failed to load coverage config: {e}")
        return True, f"⚠️  Coverage validation skipped (config load failed: {e})", None

    # Check if pytest-cov is available
    analyzer = CoverageAnalyzer(project_dir)
    installed, version_or_error = analyzer.check_pytest_cov_installed()

    if not installed:
        debug(
            "coverage_validator",
            "pytest-cov not available, skipping coverage validation",
            reason=version_or_error,
        )
        return (
            True,
            f"⚠️  Coverage validation skipped (pytest-cov not available: {version_or_error})",
            None,
        )

    debug_success("coverage_validator", f"pytest-cov is available: {version_or_error}")

    # Run coverage analysis
    print("\n📊 Running test coverage analysis...")

    try:
        coverage_result = analyzer.run_coverage(
            source_dir="apps/backend",
            test_dir="tests",
            output_format="json",
            min_coverage=None,  # Don't fail pytest run on coverage threshold
        )

        if not coverage_result.success:
            debug_error(
                "coverage_validator",
                "Coverage analysis failed",
                error=coverage_result.error_message,
            )
            return (
                False,
                f"❌ Coverage analysis failed: {coverage_result.error_message}",
                None,
            )

        debug_success(
            "coverage_validator",
            "Coverage analysis completed",
            total_coverage=coverage_result.total_coverage,
            files_covered=len(coverage_result.files),
        )

    except Exception as e:
        debug_error("coverage_validator", f"Exception during coverage analysis: {e}")
        return False, f"❌ Coverage analysis exception: {str(e)}", None

    # Parse coverage report if it was generated
    if coverage_result.report_path:
        try:
            coverage_result = parse_coverage_json(coverage_result.report_path)
            debug_success(
                "coverage_validator",
                "Parsed coverage report",
                report_path=coverage_result.report_path,
            )
        except Exception as e:
            debug_error(
                "coverage_validator",
                f"Failed to parse coverage report: {e}",
                report_path=coverage_result.report_path,
            )
            # Continue with existing result data

    # Validate coverage against thresholds
    try:
        validation_result = validate_coverage(coverage_result, config, project_dir)

        # Format results
        summary = format_validation_summary(validation_result)
        detailed_report = format_coverage_report(
            validation_result,
            coverage_result,
            show_all_files=False,
        )

        # Save detailed report to file
        report_file = spec_dir / "coverage_report.txt"
        report_file.parent.mkdir(parents=True, exist_ok=True)
        report_file.write_text(detailed_report, encoding="utf-8")
        debug_success(
            "coverage_validator",
            "Coverage report saved",
            report_file=str(report_file),
        )

        # Print summary
        print(f"\n{summary}\n")

        # Build structured coverage data for qa_signoff
        coverage_data = {
            "passed": validation_result.passed,
            "total_coverage": coverage_result.total_coverage,
            "files_analyzed": len(coverage_result.files),
            "issues_count": len(validation_result.issues),
            "critical_path_failures": validation_result.critical_path_failures,
            "minimum_required": config.minimum_coverage,
            "report_file": "coverage_report.txt",
        }

        if validation_result.passed:
            debug_success("coverage_validator", "Coverage validation PASSED")
            return True, summary, coverage_data
        else:
            debug_error(
                "coverage_validator",
                "Coverage validation FAILED",
                issues=len(validation_result.issues),
                critical_failures=validation_result.critical_path_failures,
            )
            return False, summary, coverage_data

    except Exception as e:
        debug_error("coverage_validator", f"Exception during coverage validation: {e}")
        return False, f"❌ Coverage validation exception: {str(e)}", None


def update_qa_signoff_with_coverage(
    spec_dir: Path,
    coverage_data: dict | None,
) -> bool:
    """
    Update qa_signoff in implementation_plan.json with coverage results.

    Automatically adds coverage_results field to qa_signoff if it exists,
    ensuring coverage data is always tracked.

    Args:
        spec_dir: Spec directory
        coverage_data: Coverage data from run_coverage_validation

    Returns:
        True if updated successfully, False otherwise
    """
    if coverage_data is None:
        debug(
            "coverage_validator",
            "No coverage data to add to qa_signoff",
        )
        return False

    # Lazy import to avoid cyclic import (qa.criteria -> ... -> qa.reviewer)
    from .criteria import load_implementation_plan, save_implementation_plan

    # Load implementation plan
    plan = load_implementation_plan(spec_dir)
    if not plan:
        debug_error(
            "coverage_validator",
            "Failed to load implementation plan for coverage signoff update",
        )
        return False

    # Get existing qa_signoff
    qa_signoff = plan.get("qa_signoff")
    if not qa_signoff:
        debug(
            "coverage_validator",
            "No qa_signoff found in implementation plan",
        )
        return False

    # Add coverage_results to qa_signoff
    qa_signoff["coverage_results"] = coverage_data
    debug_success(
        "coverage_validator",
        "Added coverage_results to qa_signoff",
        passed=coverage_data.get("passed"),
        total_coverage=coverage_data.get("total_coverage"),
    )

    # Save updated plan
    saved = save_implementation_plan(spec_dir, plan)
    if saved:
        debug_success(
            "coverage_validator",
            "Saved qa_signoff with coverage_results to implementation_plan.json",
        )
    else:
        debug_error(
            "coverage_validator",
            "Failed to save implementation plan with coverage results",
        )

    return saved


# =============================================================================
# QA REVIEWER SESSION
# =============================================================================


def build_qa_reviewer_prompt(
    *,
    base_prompt: str,
    qa_memory_context: str | None,
    coverage_summary: str,
    coverage_data: dict | None,
    coverage_passed: bool,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    previous_error: dict | None,
) -> str:
    """Assemble the QA reviewer prompt (pure, provider-neutral).

    Shared by the Claude Agent SDK path (:func:`run_qa_agent_session`) and
    the runtime-adapter path (:func:`run_qa_reviewer_via_runtime`) so both
    drive the reviewer with identical instructions. The verdict itself is
    file-based (``qa_signoff`` in ``implementation_plan.json``), so the
    same prompt yields the same contract on any provider.
    """
    prompt = base_prompt
    if qa_memory_context:
        prompt += "\n\n" + qa_memory_context

    # Add coverage validation results to prompt
    prompt += "\n\n---\n\n## Test Coverage Validation\n\n"
    prompt += coverage_summary
    prompt += "\n\n"

    if coverage_data:
        coverage_json = json.dumps(coverage_data, indent=2)
        prompt += f"""
### Coverage Results (Include in qa_signoff)

```json
{coverage_json}
```

"""

    if not coverage_passed:
        prompt += """
**⚠️ IMPORTANT**: Coverage validation failed. You MUST address coverage issues in your QA review.
- Include coverage_results in your qa_signoff (use the data above)
- Set status to "rejected" if critical paths lack coverage
- Reference the detailed coverage report at `coverage_report.txt` for specific missing lines

"""
    else:
        prompt += "✓ Coverage validation passed. Include coverage_results in your qa_signoff (use the data above).\n\n"

    # Add session context
    prompt += f"\n\n---\n\n**QA Session**: {qa_session}\n"
    prompt += f"**Max Iterations**: {max_iterations}\n"

    # Add error context for self-correction if previous iteration failed
    if previous_error:
        prompt += f"""

---

## ⚠️ CRITICAL: PREVIOUS ITERATION FAILED - SELF-CORRECTION REQUIRED

The previous QA session failed with the following error:

**Error**: {previous_error.get("error_message", "Unknown error")}
**Consecutive Failures**: {previous_error.get("consecutive_errors", 1)}

### What Went Wrong

You did NOT update the `implementation_plan.json` file with the required `qa_signoff` object.

### Required Action

After completing your QA review, you MUST:

1. **Read the current implementation_plan.json**:
   ```bash
   cat {spec_dir}/implementation_plan.json
   ```

2. **Update it with your qa_signoff** by editing the JSON file to add/update the `qa_signoff` field:

   If APPROVED:
   ```json
   {{
     "qa_signoff": {{
       "status": "approved",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "report_file": "qa_report.md",
       "tests_passed": {{"unit": "X/Y", "integration": "X/Y", "e2e": "X/Y"}},
       "coverage_results": {{
         "passed": true,
         "total_coverage": XX.X,
         "files_analyzed": N,
         "issues_count": 0,
         "critical_path_failures": 0,
         "minimum_required": YY.Y,
         "report_file": "coverage_report.txt"
       }},
       "verified_by": "qa_agent"
     }}
   }}
   ```

   If REJECTED:
   ```json
   {{
     "qa_signoff": {{
       "status": "rejected",
       "timestamp": "[current ISO timestamp]",
       "qa_session": {qa_session},
       "issues_found": [
         {{"type": "critical", "title": "[issue]", "location": "[file:line]", "fix_required": "[description]"}}
       ],
       "coverage_results": {{
         "passed": false,
         "total_coverage": XX.X,
         "files_analyzed": N,
         "issues_count": M,
         "critical_path_failures": K,
         "minimum_required": YY.Y,
         "report_file": "coverage_report.txt"
       }},
       "fix_request_file": "QA_FIX_REQUEST.md"
     }}
   }}
   ```

3. **Use the Edit tool or Write tool** to update the file. The file path is:
   `{spec_dir}/implementation_plan.json`

### FAILURE TO DO THIS WILL CAUSE ANOTHER ERROR

This is attempt {previous_error.get("consecutive_errors", 1) + 1}. If you fail to update implementation_plan.json again, the QA process will be escalated to human review.

---

"""

    return prompt


async def run_qa_reviewer_via_runtime(
    runtime_session: object,
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    verbose: bool = False,
    previous_error: dict | None = None,
) -> tuple[str, str]:
    """Run one QA reviewer pass through the provider-neutral runtime layer.

    Mirror of :func:`run_qa_agent_session` for direct-API providers: it
    drives a runtime adapter (generic_edit / direct_api_autonomous) via
    :func:`run_runtime_session` instead of a Claude SDK client, then reads
    the file-based verdict back from ``qa_signoff``. The reviewer is
    read-only with respect to the product — it validates and writes the
    signoff — so it is the safe first QA agent to port off the SDK.

    Returns ``(status, response_text)`` with the same ``"approved"`` /
    ``"rejected"`` / ``"error"`` contract as the Claude path.
    """
    # Lazy imports: keep the provider-neutral runtime layer off qa.reviewer's
    # module-import path so the SDK-path test harness (which mocks everything)
    # can import this module without wiring agents.runtime. ``get_qa_signoff_status``
    # is likewise lazy to avoid the qa.criteria -> ... -> qa.reviewer cycle.
    from agents.runtime import RuntimeRequirements, run_runtime_session

    from .criteria import get_qa_signoff_status

    coverage_passed, coverage_summary, coverage_data = run_coverage_validation(
        project_dir, spec_dir
    )
    base_prompt = get_qa_reviewer_prompt(spec_dir, project_dir)
    qa_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "QA validation and acceptance criteria review",
            "id": f"qa_reviewer_{qa_session}",
        },
    )
    prompt = build_qa_reviewer_prompt(
        base_prompt=base_prompt,
        qa_memory_context=qa_memory_context,
        coverage_summary=coverage_summary,
        coverage_data=coverage_data,
        coverage_passed=coverage_passed,
        spec_dir=spec_dir,
        qa_session=qa_session,
        max_iterations=max_iterations,
        previous_error=previous_error,
    )

    result = await run_runtime_session(
        runtime_session,
        message=prompt,
        spec_dir=spec_dir,
        verbose=verbose,
        requirements=RuntimeRequirements.generic_edit(),
    )
    response_text = result.response_text or ""

    status = get_qa_signoff_status(spec_dir)
    if status and coverage_data is not None:
        update_qa_signoff_with_coverage(spec_dir, coverage_data)
        status = get_qa_signoff_status(spec_dir)

    verdict = status.get("status") if status else None
    # Persist QA insights to memory exactly like the Claude path so opted-in
    # runtime reviewers keep contributing approved patterns / rejected gotchas
    # back into Graphiti for later QA and fixer sessions.
    qa_discoveries = {
        "files_understood": {},
        "patterns_found": [],
        "gotchas_encountered": [],
    }
    if verdict == "approved":
        debug_success("qa_reviewer", "QA APPROVED (runtime path)")
        qa_discoveries["patterns_found"].append(
            f"QA session {qa_session}: All acceptance criteria validated successfully"
        )
        await save_session_memory(
            spec_dir=spec_dir,
            project_dir=project_dir,
            subtask_id=f"qa_reviewer_{qa_session}",
            session_num=qa_session,
            success=True,
            subtasks_completed=[f"qa_reviewer_{qa_session}"],
            discoveries=qa_discoveries,
        )
        return "approved", response_text
    if verdict == "rejected":
        debug_error("qa_reviewer", "QA REJECTED (runtime path)")
        for issue in status.get("issues_found", []):
            qa_discoveries["gotchas_encountered"].append(
                f"QA Issue ({issue.get('type', 'unknown')}): "
                f"{issue.get('title', 'No title')} at {issue.get('location', 'unknown')}"
            )
        await save_session_memory(
            spec_dir=spec_dir,
            project_dir=project_dir,
            subtask_id=f"qa_reviewer_{qa_session}",
            session_num=qa_session,
            success=False,
            subtasks_completed=[],
            discoveries=qa_discoveries,
        )
        return "rejected", response_text
    return (
        "error",
        "QA agent did not update implementation_plan.json (runtime path)",
    )


async def run_qa_reviewer_runtime_session(
    *,
    provider_name: str,
    runtime_mode: str,
    model: str,
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    verbose: bool = False,
    previous_error: dict | None = None,
) -> tuple[str, str]:
    """Build a direct-provider runtime session and run the QA reviewer on it.

    Thin orchestration shim called by the QA loop when
    :func:`agents.runtime.qa_phase_routing.resolve_qa_runtime` permits the
    direct-API reviewer path: it constructs the provider session and the
    runtime adapter, then delegates to :func:`run_qa_reviewer_via_runtime`.
    """
    from agents.runtime import create_runtime_session

    config = ProviderConfig.from_env(agent_type="qa_reviewer")
    if config.provider != provider_name:
        # The routing decision and the env-resolved provider must agree, or
        # the runtime adapter and the underlying session would target
        # different backends. Fail fast instead of silently diverging.
        raise ValueError(
            "qa_reviewer runtime provider mismatch: "
            f"routed={provider_name}, env={config.provider}"
        )
    provider = create_engine_provider(config)
    # Keep a Claude-family QA phase default from 404ing a direct provider
    # (the QA-path analog of #337). See ProviderConfig.coherent_session_model.
    session = provider.create_session(
        SessionConfig(
            name=f"qa_reviewer-runtime-{qa_session}",
            model=config.coherent_session_model(model),
            extra={"agent_type": "qa_reviewer"},
        )
    )
    runtime_session = create_runtime_session(
        provider_name=provider_name,
        agent_session=session,
        runtime_mode=runtime_mode,
        project_dir=project_dir,
        agent_type="qa_reviewer",
    )
    return await run_qa_reviewer_via_runtime(
        runtime_session,
        project_dir,
        spec_dir,
        qa_session,
        max_iterations,
        verbose=verbose,
        previous_error=previous_error,
    )


async def run_qa_agent_session(
    client: ClaudeSDKClient,
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    verbose: bool = False,
    previous_error: dict | None = None,
) -> tuple[str, str]:
    """
    Run a QA reviewer agent session.

    Args:
        client: Claude SDK client
        project_dir: Project root directory (for capability detection)
        spec_dir: Spec directory
        qa_session: QA iteration number
        max_iterations: Maximum number of QA iterations
        verbose: Whether to show detailed output
        previous_error: Error context from previous iteration for self-correction

    Returns:
        (status, response_text) where status is:
        - "approved" if QA approves
        - "rejected" if QA finds issues
        - "error" if an error occurred
    """
    debug_section("qa_reviewer", f"QA Reviewer Session {qa_session}")
    debug(
        "qa_reviewer",
        "Starting QA reviewer session",
        spec_dir=str(spec_dir),
        qa_session=qa_session,
        max_iterations=max_iterations,
    )

    print(f"\n{'=' * 70}")
    print(f"  QA REVIEWER SESSION {qa_session}")
    print("  Validating all acceptance criteria...")
    print(f"{'=' * 70}\n")

    # Get task logger for streaming markers
    task_logger = get_task_logger(spec_dir)
    current_tool = None
    message_count = 0
    tool_count = 0

    # Run coverage validation before QA session
    coverage_passed, coverage_summary, coverage_data = run_coverage_validation(
        project_dir, spec_dir
    )
    debug(
        "qa_reviewer",
        "Coverage validation completed",
        passed=coverage_passed,
        summary_length=len(coverage_summary),
        has_data=coverage_data is not None,
    )

    # Load QA prompt with dynamically-injected project-specific MCP tools
    # This includes Electron validation for Electron apps, Puppeteer for web, etc.
    prompt = get_qa_reviewer_prompt(spec_dir, project_dir)
    debug_detailed(
        "qa_reviewer",
        "Loaded QA reviewer prompt with project-specific tools",
        prompt_length=len(prompt),
        project_dir=str(project_dir),
    )

    # Retrieve memory context for QA (past patterns, gotchas, validation insights)
    qa_memory_context = await get_graphiti_context(
        spec_dir,
        project_dir,
        {
            "description": "QA validation and acceptance criteria review",
            "id": f"qa_reviewer_{qa_session}",
        },
    )
    # Observability parity: keep the operator-facing notes the inline
    # assembly used to print; the prompt string itself is built by the
    # shared, provider-neutral ``build_qa_reviewer_prompt`` helper.
    if qa_memory_context:
        print("✓ Memory context loaded for QA reviewer")
        debug_success("qa_reviewer", "Graphiti memory context loaded for QA")
    if coverage_passed:
        debug_success("qa_reviewer", "Coverage passed - added success note to prompt")
    else:
        debug("qa_reviewer", "Coverage failed - added warning to prompt")
    if previous_error:
        debug(
            "qa_reviewer",
            "Adding error context for self-correction",
            error_type=previous_error.get("error_type"),
            consecutive_errors=previous_error.get("consecutive_errors"),
        )
        print(
            f"\n⚠️  Retry with self-correction context (attempt {previous_error.get('consecutive_errors', 1) + 1})"
        )

    prompt = build_qa_reviewer_prompt(
        base_prompt=prompt,
        qa_memory_context=qa_memory_context,
        coverage_summary=coverage_summary,
        coverage_data=coverage_data,
        coverage_passed=coverage_passed,
        spec_dir=spec_dir,
        qa_session=qa_session,
        max_iterations=max_iterations,
        previous_error=previous_error,
    )

    try:
        # Lazy import to avoid cyclic import (qa.criteria -> ... -> qa.reviewer)
        from .criteria import get_qa_signoff_status

        debug("qa_reviewer", "Sending query to Claude SDK...")
        await client.query(prompt)
        debug_success("qa_reviewer", "Query sent successfully")

        response_text = ""
        debug("qa_reviewer", "Starting to receive response stream...")
        async for msg in client.receive_response():
            msg_type = type(msg).__name__
            message_count += 1
            debug_detailed(
                "qa_reviewer",
                f"Received message #{message_count}",
                msg_type=msg_type,
            )

            if msg_type == "AssistantMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "TextBlock" and hasattr(block, "text"):
                        response_text += block.text
                        print(block.text, end="", flush=True)
                        # Log text to task logger (persist without double-printing)
                        if task_logger and block.text.strip():
                            task_logger.log(
                                block.text,
                                LogEntryType.TEXT,
                                LogPhase.VALIDATION,
                                print_to_console=False,
                            )
                    elif block_type == "ToolUseBlock" and hasattr(block, "name"):
                        tool_name = block.name
                        tool_input_display = None
                        tool_count += 1

                        # Safely extract tool input (handles None, non-dict, etc.)
                        inp = get_safe_tool_input(block)

                        # Extract tool input for display
                        if inp:
                            if "file_path" in inp:
                                fp = inp["file_path"]
                                if len(fp) > 50:
                                    fp = "..." + fp[-47:]
                                tool_input_display = fp
                            elif "pattern" in inp:
                                tool_input_display = f"pattern: {inp['pattern']}"

                        debug(
                            "qa_reviewer",
                            f"Tool call #{tool_count}: {tool_name}",
                            tool_input=tool_input_display,
                        )

                        # Log tool start (handles printing)
                        if task_logger:
                            task_logger.tool_start(
                                tool_name,
                                tool_input_display,
                                LogPhase.VALIDATION,
                                print_to_console=True,
                            )
                        else:
                            print(f"\n[QA Tool: {tool_name}]", flush=True)

                        if verbose and hasattr(block, "input"):
                            input_str = str(block.input)
                            if len(input_str) > 300:
                                print(f"   Input: {input_str[:300]}...", flush=True)
                            else:
                                print(f"   Input: {input_str}", flush=True)
                        current_tool = tool_name

            elif msg_type == "UserMessage" and hasattr(msg, "content"):
                for block in msg.content:
                    block_type = type(block).__name__

                    if block_type == "ToolResultBlock":
                        is_error = getattr(block, "is_error", False)
                        result_content = getattr(block, "content", "")

                        if is_error:
                            debug_error(
                                "qa_reviewer",
                                f"Tool error: {current_tool}",
                                error=str(result_content)[:200],
                            )
                            error_str = str(result_content)[:500]
                            print(f"   [Error] {error_str}", flush=True)
                            if task_logger and current_tool:
                                # Store full error in detail for expandable view
                                task_logger.tool_end(
                                    current_tool,
                                    success=False,
                                    result=error_str[:100],
                                    detail=str(result_content),
                                    phase=LogPhase.VALIDATION,
                                )
                        else:
                            debug_detailed(
                                "qa_reviewer",
                                f"Tool success: {current_tool}",
                                result_length=len(str(result_content)),
                            )
                            if verbose:
                                result_str = str(result_content)[:200]
                                print(f"   [Done] {result_str}", flush=True)
                            else:
                                print("   [Done]", flush=True)
                            if task_logger and current_tool:
                                # Store full result in detail for expandable view
                                detail_content = None
                                if current_tool in (
                                    "Read",
                                    "Grep",
                                    "Bash",
                                    "Edit",
                                    "Write",
                                ):
                                    result_str = str(result_content)
                                    if len(result_str) < 50000:
                                        detail_content = result_str
                                task_logger.tool_end(
                                    current_tool,
                                    success=True,
                                    detail=detail_content,
                                    phase=LogPhase.VALIDATION,
                                )

                        current_tool = None

        print("\n" + "-" * 70 + "\n")

        # Extract usage metadata from Claude SDK client
        usage_metadata = None
        try:
            # Try to get usage metadata from the client
            # The Claude SDK client may expose usage metadata after the session completes
            if hasattr(client, "usage_metadata"):
                metadata = client.usage_metadata
                if (
                    metadata
                    and hasattr(metadata, "input_tokens")
                    and hasattr(metadata, "output_tokens")
                ):
                    usage_metadata = {
                        "input_tokens": metadata.input_tokens,
                        "output_tokens": metadata.output_tokens,
                    }
                    debug_success(
                        "qa_reviewer",
                        "Extracted usage metadata",
                        input_tokens=metadata.input_tokens,
                        output_tokens=metadata.output_tokens,
                    )
            elif hasattr(client, "_usage"):
                # Alternative: some SDKs store usage in a _usage attribute
                usage = client._usage
                if (
                    isinstance(usage, dict)
                    and "input_tokens" in usage
                    and "output_tokens" in usage
                ):
                    usage_metadata = {
                        "input_tokens": usage["input_tokens"],
                        "output_tokens": usage["output_tokens"],
                    }
                    debug_success(
                        "qa_reviewer",
                        "Extracted usage metadata from _usage",
                        input_tokens=usage["input_tokens"],
                        output_tokens=usage["output_tokens"],
                    )
        except Exception as e:
            logger.debug(f"Could not extract usage metadata from client: {e}")

        # Persist usage metadata to token_stats.json if available
        if usage_metadata:
            try:
                saved = save_token_stats(
                    spec_dir,
                    "validation",
                    usage_metadata["input_tokens"],
                    usage_metadata["output_tokens"],
                )
                if saved:
                    print_status(
                        f"Token usage recorded: {usage_metadata['input_tokens']} in, {usage_metadata['output_tokens']} out",
                        "info",
                    )
                    debug_success(
                        "qa_reviewer",
                        "Validation phase token stats saved",
                        input_tokens=usage_metadata["input_tokens"],
                        output_tokens=usage_metadata["output_tokens"],
                    )
            except Exception as e:
                logger.warning(f"Failed to persist validation phase token stats: {e}")

        # Call after_session hook for enabled agent plugins
        if PLUGINS_AVAILABLE:
            try:
                registry = PluginRegistry.get_instance()
                agent_plugins = registry.list_plugins(
                    plugin_type=PluginType.AGENT, enabled_only=True
                )

                if agent_plugins:
                    # Create agent context for plugins
                    agent_context = AgentContext(
                        project_dir=project_dir,
                        spec_dir=spec_dir,
                        session_id=f"qa_reviewer_{qa_session}",
                        client=client,
                        phase="validation",
                        metadata={"qa_session": qa_session},
                    )

                    # Determine session success (will be updated after status check)
                    # For now, assume success - will be recalculated after status check
                    session_success = True

                    # Call after_session for each enabled agent plugin
                    for plugin in agent_plugins:
                        try:
                            plugin.after_session(agent_context, success=session_success)
                            logger.debug(
                                f"Called after_session for plugin: {plugin.name}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"Plugin {plugin.name} after_session hook failed: {e}"
                            )
            except Exception as e:
                logger.warning(f"Failed to call after_session hooks: {e}")

        # Check the QA result from implementation_plan.json
        status = get_qa_signoff_status(spec_dir)
        debug(
            "qa_reviewer",
            "QA session completed",
            message_count=message_count,
            tool_count=tool_count,
            response_length=len(response_text),
            qa_status=status.get("status") if status else "unknown",
        )

        # Automatically add coverage results to qa_signoff
        if status and coverage_data is not None:
            update_qa_signoff_with_coverage(spec_dir, coverage_data)
            # Reload status to get the updated qa_signoff with coverage_results
            status = get_qa_signoff_status(spec_dir)
            debug_success(
                "qa_reviewer",
                "Coverage results added to qa_signoff",
                coverage_passed=coverage_data.get("passed"),
                total_coverage=coverage_data.get("total_coverage"),
            )

        # Save QA session insights to memory
        qa_discoveries = {
            "files_understood": {},
            "patterns_found": [],
            "gotchas_encountered": [],
        }

        if status and status.get("status") == "approved":
            debug_success("qa_reviewer", "QA APPROVED")
            qa_discoveries["patterns_found"].append(
                f"QA session {qa_session}: All acceptance criteria validated successfully"
            )
            # Save successful QA session to memory
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=True,
                subtasks_completed=[f"qa_reviewer_{qa_session}"],
                discoveries=qa_discoveries,
            )
            return "approved", response_text
        elif status and status.get("status") == "rejected":
            debug_error("qa_reviewer", "QA REJECTED")
            # Extract issues found for memory
            issues = status.get("issues_found", [])
            for issue in issues:
                qa_discoveries["gotchas_encountered"].append(
                    f"QA Issue ({issue.get('type', 'unknown')}): {issue.get('title', 'No title')} at {issue.get('location', 'unknown')}"
                )
            # Save rejected QA session to memory (learning from failures)
            await save_session_memory(
                spec_dir=spec_dir,
                project_dir=project_dir,
                subtask_id=f"qa_reviewer_{qa_session}",
                session_num=qa_session,
                success=False,
                subtasks_completed=[],
                discoveries=qa_discoveries,
            )
            return "rejected", response_text
        else:
            # Agent didn't update the status properly - provide detailed error
            debug_error(
                "qa_reviewer",
                "QA agent did not update implementation_plan.json",
                message_count=message_count,
                tool_count=tool_count,
                response_preview=response_text[:500] if response_text else "empty",
            )

            # Build informative error message for feedback loop
            error_details = []
            if message_count == 0:
                error_details.append("No messages received from agent")
            if tool_count == 0:
                error_details.append("No tools were used by agent")
            if not response_text:
                error_details.append("Agent produced no output")

            error_msg = "QA agent did not update implementation_plan.json"
            if error_details:
                error_msg += f" ({'; '.join(error_details)})"

            return "error", error_msg

    except Exception as e:
        debug_error(
            "qa_reviewer",
            f"QA session exception: {e}",
            exception_type=type(e).__name__,
        )
        print(f"Error during QA session: {e}")
        if task_logger:
            task_logger.log_error(f"QA session error: {e}", LogPhase.VALIDATION)

        # Call after_session hook for enabled agent plugins (error case)
        if PLUGINS_AVAILABLE:
            try:
                registry = PluginRegistry.get_instance()
                agent_plugins = registry.list_plugins(
                    plugin_type=PluginType.AGENT, enabled_only=True
                )

                if agent_plugins:
                    # Create agent context for plugins
                    agent_context = AgentContext(
                        project_dir=project_dir,
                        spec_dir=spec_dir,
                        session_id=f"qa_reviewer_{qa_session}",
                        client=client,
                        phase="validation",
                        metadata={"qa_session": qa_session, "error": str(e)},
                    )

                    # Call after_session for each enabled agent plugin (error case)
                    for plugin in agent_plugins:
                        try:
                            plugin.after_session(agent_context, success=False)
                            logger.debug(
                                f"Called after_session for plugin: {plugin.name}"
                            )
                        except Exception as hook_error:
                            logger.warning(
                                f"Plugin {plugin.name} after_session hook failed: {hook_error}"
                            )
            except Exception as hook_error:
                logger.warning(f"Failed to call after_session hooks: {hook_error}")

        return "error", str(e)


# =============================================================================
# QA REVIEWER FACTORY FUNCTION (Provider Pattern)
# =============================================================================


def create_qa_reviewer_session(
    project_dir: Path,
    spec_dir: Path,
    model: str | None = None,
    max_thinking_tokens: int | None = None,
):
    """
    Create a QA reviewer agent session using the configured AI engine provider.

    This function is used by the QA validation loop to create reviewer sessions
    with the appropriate AI backend (Claude, LiteLLM, or OpenRouter).

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        model: Model to use (overrides provider config)
        max_thinking_tokens: Token budget for extended thinking

    Returns:
        AgentSession with a .client property containing the SDK client

    Raises:
        ProviderError: If provider creation or session creation fails
    """
    # Create provider from environment configuration (with per-agent overrides)
    config = ProviderConfig.from_env(agent_type="qa_reviewer")
    provider = create_engine_provider(config)

    # For Claude provider, pass provider-specific kwargs
    if provider.name == "claude":
        session = provider.create_session(
            config=SessionConfig(
                name="qa-reviewer-session",
                model=model,
            ),
            project_dir=project_dir,
            spec_dir=spec_dir,
            agent_type="qa_reviewer",
            max_thinking_tokens=max_thinking_tokens,
        )
    else:
        session = provider.create_session(
            SessionConfig(
                name="qa-reviewer-session",
                model=model,
            )
        )

    return session


async def run_qa_reviewer(
    project_dir: Path,
    spec_dir: Path,
    qa_session: int,
    max_iterations: int,
    model: str | None = None,
    verbose: bool = False,
    previous_error: dict | None = None,
    max_thinking_tokens: int | None = None,
) -> tuple[str, str]:
    """
    Run a QA reviewer session using the configured AI engine provider.

    This is the main entry point for running QA reviews with provider abstraction.
    Creates a session using the factory pattern and delegates to run_qa_agent_session.

    Args:
        project_dir: Project root directory
        spec_dir: Spec directory
        qa_session: QA iteration number
        max_iterations: Maximum number of QA iterations
        model: Model to use (overrides provider config)
        verbose: Whether to show detailed output
        previous_error: Error context from previous iteration for self-correction
        max_thinking_tokens: Token budget for extended thinking

    Returns:
        (status, response_text) where status is:
        - "approved" if QA approves
        - "rejected" if QA finds issues
        - "error" if an error occurred
    """
    # Create session using provider factory
    session = create_qa_reviewer_session(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        max_thinking_tokens=max_thinking_tokens,
    )

    # Get the underlying client from the session
    # For Claude provider, this is a ClaudeSDKClient
    client = session.client

    # Use async context manager for proper cleanup
    async with client:
        return await run_qa_agent_session(
            client=client,
            project_dir=project_dir,
            spec_dir=spec_dir,
            qa_session=qa_session,
            max_iterations=max_iterations,
            verbose=verbose,
            previous_error=previous_error,
        )
