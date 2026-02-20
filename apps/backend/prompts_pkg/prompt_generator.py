"""
Prompt Generator
================

Generates minimal, focused prompts for each subtask.
Instead of a 900-line mega-prompt, each subtask gets a tailored ~100-line prompt
with only the context it needs.

This approach:
- Reduces token usage by ~80%
- Keeps the agent focused on ONE task
- Moves bookkeeping to Python orchestration

Context Optimization:
- Integrates with ContextSummarizer for intelligent file summarization
- Uses HistoryTracker to avoid redundant context
- Provides session coherence across multiple turns
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

from context.compressor import ContextCompressor
from context.token_estimator import TokenEstimator


def get_relative_spec_path(spec_dir: Path, project_dir: Path) -> str:
    """
    Get the spec directory path relative to the project/working directory.

    This ensures the AI gets a usable path regardless of absolute locations.

    Args:
        spec_dir: Absolute path to spec directory
        project_dir: Absolute path to project/working directory

    Returns:
        Relative path string (e.g., "./auto-claude/specs/003-new-spec")
    """
    try:
        # Try to make path relative to project_dir
        relative = spec_dir.relative_to(project_dir)
        return f"./{relative}"
    except ValueError:
        # If spec_dir is not under project_dir, return the name only
        # This shouldn't happen if workspace.py correctly copies spec files
        return f"./auto-claude/specs/{spec_dir.name}"


def generate_environment_context(project_dir: Path, spec_dir: Path) -> str:
    """
    Generate environment context header for prompts.

    This explicitly tells the AI where it is working, preventing path confusion.

    Args:
        project_dir: The working directory for the AI
        spec_dir: The spec directory (may be absolute or relative)

    Returns:
        Markdown string with environment context
    """
    relative_spec = get_relative_spec_path(spec_dir, project_dir)

    return f"""## YOUR ENVIRONMENT

**Working Directory:** `{project_dir}`
**Spec Location:** `{relative_spec}/`

Your filesystem is restricted to your working directory. All file paths should be
relative to this location. Do NOT use absolute paths.

**⚠️ CRITICAL:** Before ANY git command or file operation, run `pwd` to verify your current
directory. If you've used `cd` to change directories, you MUST use paths relative to your
NEW location, not the working directory. See the PATH CONFUSION PREVENTION section in the
coder prompt for detailed examples.

**Important Files:**
- Spec: `{relative_spec}/spec.md`
- Plan: `{relative_spec}/implementation_plan.json`
- Progress: `{relative_spec}/build-progress.txt`
- Context: `{relative_spec}/context.json`

---

"""


def generate_subtask_prompt(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
    phase: dict,
    attempt_count: int = 0,
    recovery_hints: list[str] | None = None,
    pattern_suggestions: str | None = None,
) -> str:
    """
    Generate a minimal, focused prompt for implementing a single subtask.

    Args:
        spec_dir: Directory containing spec files
        project_dir: Root project directory (working directory)
        subtask: The subtask to implement
        phase: The phase containing this subtask
        attempt_count: Number of previous attempts (for retry context)
        recovery_hints: Hints from previous failed attempts
        pattern_suggestions: Relevant code patterns from Graphiti memory
            (retrieved via get_pattern_suggestions from memory_manager)

    Returns:
        A focused prompt string (~100 lines instead of 900)
    """
    subtask_id = subtask.get("id", "unknown")
    description = subtask.get("description", "No description")
    service = subtask.get("service", "all")
    files_to_modify = subtask.get("files_to_modify", [])
    files_to_create = subtask.get("files_to_create", [])
    patterns_from = subtask.get("patterns_from", [])
    verification = subtask.get("verification", {})

    # Get relative spec path
    get_relative_spec_path(spec_dir, project_dir)

    # Build the prompt
    sections = []

    # Environment context first
    sections.append(generate_environment_context(project_dir, spec_dir))

    # Header
    sections.append(f"""# Subtask Implementation Task

**Subtask ID:** `{subtask_id}`
**Phase:** {phase.get("name", phase.get("id", "Unknown"))}
**Service:** {service}

## Description

{description}
""")

    # Recovery context if this is a retry
    if attempt_count > 0:
        sections.append(f"""
## ⚠️ RETRY ATTEMPT ({attempt_count + 1})

This subtask has been attempted {attempt_count} time(s) before without success.
You MUST use a DIFFERENT approach than previous attempts.
""")
        if recovery_hints:
            sections.append("**Previous attempt insights:**")
            for hint in recovery_hints:
                sections.append(f"- {hint}")
            sections.append("")

    # Files section
    sections.append("## Files\n")

    if files_to_modify:
        sections.append("**Files to Modify:**")
        for f in files_to_modify:
            sections.append(f"- `{f}`")
        sections.append("")

    if files_to_create:
        sections.append("**Files to Create:**")
        for f in files_to_create:
            sections.append(f"- `{f}`")
        sections.append("")

    if patterns_from:
        sections.append("**Pattern Files (study these first):**")
        for f in patterns_from:
            sections.append(f"- `{f}`")
        sections.append("")

    # Pattern suggestions from Graphiti memory (truncate to avoid bloating prompt)
    if pattern_suggestions:
        max_pattern_chars = 2000
        if len(pattern_suggestions) > max_pattern_chars:
            pattern_suggestions = (
                pattern_suggestions[:max_pattern_chars] + "\n...(truncated)"
            )
        sections.append(pattern_suggestions)
        sections.append("")

    # Verification
    sections.append("## Verification\n")
    v_type = verification.get("type", "manual")

    if v_type == "command":
        sections.append(f"""Run this command to verify:
```bash
{verification.get("command", 'echo "No command specified"')}
```
Expected: {verification.get("expected", "Success")}
""")
    elif v_type == "api":
        method = verification.get("method", "GET")
        url = verification.get("url", "http://localhost")
        body = verification.get("body", {})
        expected_status = verification.get("expected_status", 200)
        sections.append(f"""Test the API endpoint:
```bash
curl -X {method} {url} -H "Content-Type: application/json" {f"-d '{json.dumps(body)}'" if body else ""}
```
Expected status: {expected_status}
""")
    elif v_type == "browser":
        url = verification.get("url", "http://localhost:3000")
        checks = verification.get("checks", [])
        sections.append(f"""Open in browser: {url}

Verify:""")
        for check in checks:
            sections.append(f"- [ ] {check}")
        sections.append("")
    elif v_type == "e2e":
        steps = verification.get("steps", [])
        sections.append("End-to-end verification steps:")
        for i, step in enumerate(steps, 1):
            sections.append(f"{i}. {step}")
        sections.append("")
    else:
        instructions = verification.get("instructions", "Manual verification required")
        sections.append(f"**Manual Verification:**\n{instructions}\n")

    # Instructions
    sections.append(f"""## Instructions

1. **Read the pattern files** to understand code style and conventions
2. **Read the files to modify** (if any) to understand current implementation
3. **Implement the subtask** following the patterns exactly
4. **Run verification** and fix any issues
5. **Commit your changes:**
   ```bash
   git add .
   git commit -m "auto-claude: {subtask_id} - {description[:50]}"
   ```
6. **Update the plan** - set this subtask's status to "completed" in implementation_plan.json

## Quality Checklist

Before marking complete, verify:
- [ ] Follows patterns from reference files
- [ ] No console.log/print debugging statements
- [ ] Error handling in place
- [ ] Verification passes
- [ ] Clean commit with descriptive message

## Important

- Focus ONLY on this subtask - don't modify unrelated code
- If verification fails, FIX IT before committing
- If you encounter a blocker, document it in build-progress.txt
""")

    # Note: Linear updates are now handled by Python orchestrator via linear_updater.py
    # Agents no longer need to call Linear MCP tools directly

    return "\n".join(sections)


def generate_planner_prompt(spec_dir: Path, project_dir: Path | None = None) -> str:
    """
    Generate the planner prompt (used only once at start).
    This is a simplified version that focuses on plan creation.

    Args:
        spec_dir: Directory containing spec.md
        project_dir: Working directory (for relative paths)

    Returns:
        Planner prompt string
    """
    # Load the full planner prompt from file.
    candidate_dirs = [
        Path(__file__).parent.parent / "prompts",  # current layout
        Path(__file__).parent / "prompts",  # legacy fallback (if any)
    ]
    planner_file = next(
        (
            (candidate_dir / "planner.md")
            for candidate_dir in candidate_dirs
            if (candidate_dir / "planner.md").exists()
        ),
        None,
    )

    if planner_file:
        prompt = planner_file.read_text(encoding="utf-8")
    else:
        prompt = (
            "Read spec.md and create implementation_plan.json with phases and subtasks."
        )

    # Use project_dir for relative paths, or infer from spec_dir
    if project_dir is None:
        # Infer: spec_dir is typically project/auto-claude/specs/XXX
        project_dir = spec_dir.parent.parent.parent

    # Get relative path for spec directory
    relative_spec = get_relative_spec_path(spec_dir, project_dir)

    # Build header with environment context
    header = generate_environment_context(project_dir, spec_dir)

    # Add spec-specific instructions
    header += f"""## SPEC LOCATION

Your spec file is located at: `{relative_spec}/spec.md`

Store all build artifacts in this spec directory:
- `{relative_spec}/implementation_plan.json` - Subtask-based implementation plan
- `{relative_spec}/build-progress.txt` - Progress notes
- `{relative_spec}/init.sh` - Environment setup script

The project root is your current working directory. Implement code in the project root,
not in the spec directory.

---

"""
    # Note: Linear task creation and updates are now handled by Python orchestrator
    # via linear_updater.py - agents no longer need Linear instructions in prompts

    return header + prompt


def load_subtask_context(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
    max_file_lines: int = 200,
) -> dict:
    """
    Load minimal context needed for a subtask with smart compression.

    Uses ContextCompressor to intelligently compress large files instead of
    simple line truncation, preserving important information while reducing
    token usage.

    Args:
        spec_dir: Spec directory
        project_dir: Project root
        subtask: The subtask being implemented
        max_file_lines: Approximate maximum lines (converted to token threshold)

    Returns:
        Dict with file contents and relevant context
    """
    context = {
        "patterns": {},
        "files_to_modify": {},
        "spec_excerpt": None,
    }

    # Initialize compressor and token estimator
    # Convert max_file_lines to approximate token threshold
    # Average: ~10-15 tokens per line of code, so use 12.5 as middle ground
    token_threshold = max_file_lines * 12
    compressor = ContextCompressor(
        compression_threshold=token_threshold,
        target_ratio=0.5,  # Target 50% of original for subtask context
        token_estimator=TokenEstimator(),
    )

    # Load pattern files with smart compression
    for pattern_path in subtask.get("patterns_from", []):
        full_path = project_dir / pattern_path
        if full_path.exists():
            try:
                # Use smart compression instead of simple truncation
                result = compressor.compress_file(full_path, strategy="auto")
                content = result.compressed_content

                # Add compression metadata if applied
                if result.method != "none":
                    content += f"\n\n... (compressed from {result.original_tokens} to {result.compressed_tokens} tokens using {result.method})"

                context["patterns"][pattern_path] = content
            except Exception:
                # Fallback to simple truncation if compression fails
                try:
                    lines = full_path.read_text(encoding="utf-8").split("\n")
                    if len(lines) > max_file_lines:
                        content = "\n".join(lines[:max_file_lines])
                        content += f"\n\n... (truncated, {len(lines) - max_file_lines} more lines)"
                    else:
                        content = "\n".join(lines)
                    context["patterns"][pattern_path] = content
                except Exception:
                    context["patterns"][pattern_path] = "(Could not read file)"

    # Load files to modify with smart compression
    for file_path in subtask.get("files_to_modify", []):
        full_path = project_dir / file_path
        if full_path.exists():
            try:
                # Use smart compression instead of simple truncation
                result = compressor.compress_file(full_path, strategy="auto")
                content = result.compressed_content

                # Add compression metadata if applied
                if result.method != "none":
                    content += f"\n\n... (compressed from {result.original_tokens} to {result.compressed_tokens} tokens using {result.method})"

                context["files_to_modify"][file_path] = content
            except Exception:
                # Fallback to simple truncation if compression fails
                try:
                    lines = full_path.read_text(encoding="utf-8").split("\n")
                    if len(lines) > max_file_lines:
                        content = "\n".join(lines[:max_file_lines])
                        content += f"\n\n... (truncated, {len(lines) - max_file_lines} more lines)"
                    else:
                        content = "\n".join(lines)
                    context["files_to_modify"][file_path] = content
                except Exception:
                    context["files_to_modify"][file_path] = "(Could not read file)"

    return context


def get_recovery_context(
    spec_dir: Path, project_dir: Path, subtask_id: str
) -> tuple[int, list[str] | None]:
    """
    Get recovery context for a subtask.

    Retrieves attempt count and recovery hints from the recovery manager
    to support retry logic with different approaches.

    Args:
        spec_dir: Spec directory containing recovery state
        project_dir: Project root directory
        subtask_id: ID of the subtask to get recovery context for

    Returns:
        Tuple of (attempt_count, recovery_hints):
            - attempt_count: Number of previous attempts (0 if first attempt)
            - recovery_hints: List of hints from previous attempts, or None if first attempt
    """
    from services.recovery import RecoveryManager

    recovery_manager = RecoveryManager(spec_dir, project_dir)
    attempt_count = recovery_manager.get_attempt_count(subtask_id)
    recovery_hints = (
        recovery_manager.get_recovery_hints(subtask_id) if attempt_count > 0 else None
    )

    return attempt_count, recovery_hints


def format_context_for_prompt(context: dict) -> str:
    """
    Format loaded context into a prompt section.

    Args:
        context: Dict from load_subtask_context, may include:
            - patterns: Dict of reference file paths to contents
            - files_to_modify: Dict of file paths to current contents
            - pattern_suggestions: Pre-formatted string of pattern suggestions from Graphiti
            - selection_reasoning: List of strings explaining why files were selected
            - token_summary: Dict with token usage statistics (optional)

    Returns:
        Formatted string to append to prompt
    """
    sections = []

    # Add pattern suggestions from Graphiti (if available)
    if context.get("pattern_suggestions"):
        sections.append(context["pattern_suggestions"])
        sections.append("")  # Add spacing after pattern suggestions

    # Add selection reasoning for transparency
    if context.get("selection_reasoning"):
        sections.append("## Context Selection Reasoning\n")
        sections.append("The following files were selected for this task based on:\n")
        for reason in context["selection_reasoning"]:
            sections.append(f"- {reason}")
        sections.append("")  # Add spacing after reasoning

    # Add token summary if available
    if context.get("token_summary"):
        summary = context["token_summary"]
        sections.append("## Token Usage Summary\n")
        sections.append(
            f"- **Total Estimated Tokens:** {summary.get('total_tokens', 'N/A')}"
        )
        sections.append(f"- **Files Included:** {summary.get('file_count', 'N/A')}")
        sections.append(
            f"- **Compression Applied:** {summary.get('compression_method', 'None')}"
        )
        sections.append("")  # Add spacing after token summary

    if context.get("patterns"):
        sections.append("## Reference Files (Patterns to Follow)\n")
        for path, content in context["patterns"].items():
            sections.append(f"### `{path}`\n```\n{content}\n```\n")

    if context.get("files_to_modify"):
        sections.append("## Current File Contents (To Modify)\n")
        for path, content in context["files_to_modify"].items():
            sections.append(f"### `{path}`\n```\n{content}\n```\n")

    return "\n".join(sections)


def generate_context_summary_section(
    spec_dir: Path,
    project_dir: Path | None = None,
) -> str:
    """
    Generate a session context summary section for prompts.

    Uses HistoryTracker to provide information about what context has been
    sent to the agent, helping maintain session coherence and avoid redundancy.

    Args:
        spec_dir: Directory containing spec files
        project_dir: Project root directory (optional, inferred if not provided)

    Returns:
        Formatted markdown section with session summary

    Example:
        >>> section = generate_context_summary_section(
        ...     spec_dir=Path(".auto-claude/specs/120"),
        ...     project_dir=Path(".")
        ... )
        >>> # Returns markdown section with session stats
    """
    try:
        from context.history_tracker import get_history_tracker
    except ImportError:
        logger.warning("HistoryTracker not available, skipping session summary")
        return ""

    # Get history tracker for this spec
    tracker = get_history_tracker(spec_dir=spec_dir)

    # Get session summary
    summary = tracker.get_session_summary()

    # If no context has been sent yet, skip the section
    if summary.get("unique_files_sent", 0) == 0:
        return ""

    # Format the summary section
    sections = [
        "## Session Context Summary",
        "",
        f"**Turn:** {summary.get('current_turn', 0)}",
        f"**Files Sent:** {summary.get('unique_files_sent', 0)} unique files",
        f"**Total Tokens:** {summary.get('total_tokens_sent', 0)} tokens",
        "",
    ]

    # Add recently accessed files
    recent_files = summary.get("recent_files", [])
    if recent_files:
        sections.append("**Recently Accessed:**")
        for file_path in recent_files[:5]:  # Show top 5
            sections.append(f"- `{file_path}`")
        sections.append("")

    # Add most frequent files
    frequent = summary.get("most_frequent", [])
    if frequent:
        sections.append("**Most Referenced:**")
        for entry in frequent[:3]:  # Show top 3
            path = entry.get("path", "unknown")
            count = entry.get("sent_count", 0)
            sections.append(f"- `{path}` (sent {count}x)")
        sections.append("")

    sections.append("---")
    sections.append("")

    return "\n".join(sections)


async def generate_file_summary(
    file_path: str,
    content: str,
    summarization_level: str = "medium",
) -> str:
    """
    Generate a summary of file content using ContextSummarizer.

    This is useful for including condensed versions of large files in prompts
    to save tokens while preserving key information.

    Args:
        file_path: Path to the file (for context)
        content: File content to summarize
        summarization_level: Level of summarization (light/medium/aggressive)

    Returns:
        Summarized file content

    Example:
        >>> summary = await generate_file_summary(
        ...     file_path="apps/backend/core/client.py",
        ...     content=file_content,
        ...     summarization_level="medium"
        ... )
    """
    try:
        from context.summarizer import SummarizationLevel, get_context_summarizer
    except ImportError:
        logger.warning("ContextSummarizer not available, returning truncated content")
        # Fallback: return first 2000 chars
        if len(content) > 2000:
            return content[:2000] + "\n\n[... truncated ...]"
        return content

    # Map string level to enum
    level_map = {
        "light": SummarizationLevel.LIGHT,
        "medium": SummarizationLevel.MEDIUM,
        "aggressive": SummarizationLevel.AGGRESSIVE,
    }
    level = level_map.get(summarization_level.lower(), SummarizationLevel.MEDIUM)

    # Get summarizer
    summarizer = get_context_summarizer(default_level=level)

    try:
        # Generate summary
        summary = await summarizer.summarize_file_content(
            file_path=file_path,
            content=content,
            level=level,
            preserve_imports=True,
        )
        return summary
    except Exception as e:
        logger.warning(f"Failed to summarize {file_path}: {e}")
        # Fallback: return truncated content
        if len(content) > 2000:
            return (
                content[:2000] + f"\n\n[Summarization failed: {e}]\n[... truncated ...]"
            )
        return content


async def load_subtask_context_with_summaries(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
    enable_summarization: bool = True,
    summarization_level: str = "medium",
    max_file_lines: int = 200,
) -> dict[str, Any]:
    """
    Load subtask context with optional summarization for large files.

    This enhanced version of load_subtask_context can automatically
    summarize large files to save tokens while preserving key information.

    Args:
        spec_dir: Spec directory
        project_dir: Project root
        subtask: The subtask being implemented
        enable_summarization: Whether to summarize large files
        summarization_level: Level of summarization (light/medium/aggressive)
        max_file_lines: Maximum lines before triggering summarization

    Returns:
        Dict with file contents (possibly summarized) and context

    Example:
        >>> context = await load_subtask_context_with_summaries(
        ...     spec_dir=Path(".auto-claude/specs/120"),
        ...     project_dir=Path("."),
        ...     subtask=subtask_dict,
        ...     enable_summarization=True
        ... )
    """
    context: dict[str, Any] = {
        "patterns": {},
        "files_to_modify": {},
        "spec_excerpt": None,
        "summarization_used": False,
    }

    # Helper to load and optionally summarize a file
    async def load_file(file_path: str, is_pattern: bool = False) -> str:
        full_path = project_dir / file_path
        if not full_path.exists():
            return "(Could not read file)"

        try:
            content = full_path.read_text(encoding="utf-8")
            lines = content.split("\n")

            # Check if file is large enough to warrant summarization
            if enable_summarization and len(lines) > max_file_lines:
                logger.info(
                    f"Summarizing {file_path} ({len(lines)} lines > {max_file_lines})"
                )
                summary = await generate_file_summary(
                    file_path=file_path,
                    content=content,
                    summarization_level=summarization_level,
                )
                context["summarization_used"] = True
                return f"[Summarized to save tokens]\n\n{summary}"
            else:
                # Return full content (possibly truncated)
                if len(lines) > max_file_lines:
                    truncated = "\n".join(lines[:max_file_lines])
                    truncated += (
                        f"\n\n... (truncated, {len(lines) - max_file_lines} more lines)"
                    )
                    return truncated
                return content
        except Exception as e:
            logger.warning(f"Failed to load {file_path}: {e}")
            return f"(Could not read file: {e})"

    # Load pattern files
    for pattern_path in subtask.get("patterns_from", []):
        context["patterns"][pattern_path] = await load_file(
            pattern_path, is_pattern=True
        )

    # Load files to modify
    for file_path in subtask.get("files_to_modify", []):
        context["files_to_modify"][file_path] = await load_file(file_path)

    return context


def generate_subtask_prompt_with_context(
    spec_dir: Path,
    project_dir: Path,
    subtask: dict,
    phase: dict,
    include_session_summary: bool = True,
    attempt_count: int = 0,
    recovery_hints: list[str] | None = None,
) -> str:
    """
    Generate a subtask prompt with enhanced context awareness.

    This is an enhanced version of generate_subtask_prompt that includes:
    - Session summary from HistoryTracker
    - Context coherence information
    - Smart token optimization

    Args:
        spec_dir: Directory containing spec files
        project_dir: Root project directory (working directory)
        subtask: The subtask to implement
        phase: The phase containing this subtask
        include_session_summary: Whether to include session summary
        attempt_count: Number of previous attempts (for retry context)
        recovery_hints: Hints from previous failed attempts

    Returns:
        Context-optimized prompt string

    Example:
        >>> prompt = generate_subtask_prompt_with_context(
        ...     spec_dir=Path(".auto-claude/specs/120"),
        ...     project_dir=Path("."),
        ...     subtask=subtask_dict,
        ...     phase=phase_dict,
        ...     include_session_summary=True
        ... )
    """
    # Start with the base prompt
    base_prompt = generate_subtask_prompt(
        spec_dir=spec_dir,
        project_dir=project_dir,
        subtask=subtask,
        phase=phase,
        attempt_count=attempt_count,
        recovery_hints=recovery_hints,
    )

    # Add session summary if requested
    if include_session_summary:
        session_summary = generate_context_summary_section(
            spec_dir=spec_dir,
            project_dir=project_dir,
        )
        if session_summary:
            # Insert session summary after environment context
            parts = base_prompt.split("# Subtask Implementation Task", 1)
            if len(parts) == 2:
                return (
                    parts[0]
                    + session_summary
                    + "\n# Subtask Implementation Task"
                    + parts[1]
                )

    return base_prompt
