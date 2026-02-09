"""
Documentation Generator Agent Module
=====================================

AI agent that generates comprehensive documentation based on code analysis results.
Uses the Documentation Generator Agent prompt to create API docs, README files,
architecture diagrams, and user guides.
"""

import json
import logging
from pathlib import Path
from typing import Any

from core.client import create_client
from phase_config import get_phase_model, get_phase_thinking_budget
from prompts_pkg.prompt_loader import get_agent_prompt
from task_logger import LogEntryType, LogPhase, get_task_logger
from ui import (
    Icons,
    bold,
    box,
    highlight,
    icon,
    muted,
    print_key_value,
    print_status,
)

logger = logging.getLogger(__name__)


def validate_generated_docs(doc_files: list[Path], project_dir: Path) -> bool:
    """
    Validate that generated documentation files exist and are well-formed.

    Checks that:
    - Files exist and are readable
    - Markdown files have valid structure
    - No empty documentation files

    Args:
        doc_files: List of generated documentation file paths
        project_dir: Project root directory

    Returns:
        True if all docs are valid, False otherwise
    """
    if not doc_files:
        logger.warning("No documentation files to validate")
        return False

    print()
    print_status("Validating generated documentation...", "progress")

    for doc_file in doc_files:
        file_path = project_dir / doc_file
        if not file_path.exists():
            print_status(f"Documentation file not found: {doc_file}", "error")
            return False

        # Check file is not empty
        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
            if not content.strip():
                print_status(f"Empty documentation file: {doc_file}", "error")
                return False

            # Basic markdown structure validation
            if file_path.suffix == ".md":
                # Check for at least one heading
                if not any(line.startswith("#") for line in content.split("\n")):
                    print_status(
                        f"Markdown file missing headings: {doc_file}", "warning"
                    )

            print_status(f"Valid documentation: {doc_file.name}", "success")
        except Exception as e:
            print_status(f"Error reading {doc_file}: {e}", "error")
            return False

    print_status("All generated documentation is valid", "success")
    return True


async def run_documentation_generator_session(
    project_dir: Path,
    spec_dir: Path,
    analysis_results: dict[str, Any],
    model: str | None = None,
    max_thinking_tokens: int | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """
    Run Documentation Generator Agent session to generate project documentation.

    Args:
        project_dir: Root directory for the project
        spec_dir: Directory containing the spec
        analysis_results: Code analysis results from CodeAnalyzer
        model: Claude model to use (defaults to phase config)
        max_thinking_tokens: Extended thinking token budget (optional)
        verbose: Whether to show detailed output

    Returns:
        Dictionary with:
        - generated_files: List of generated documentation file paths (relative to project_dir)
        - success: Whether generation succeeded
        - error: Error message if failed
    """
    # Initialize task logger
    task_logger = get_task_logger(spec_dir)

    # Print session header
    content = [
        bold(f"{icon(Icons.SPARKLES)} DOCUMENTATION GENERATOR SESSION"),
        "",
        f"Spec: {highlight(spec_dir.name)}",
        muted("Generating comprehensive documentation from code analysis..."),
    ]
    print()
    print(box(content, width=70, style="heavy"))
    print()

    # Determine model and thinking budget
    if model is None:
        model = get_phase_model("documentation_generation")
    if max_thinking_tokens is None:
        max_thinking_tokens = get_phase_thinking_budget("documentation_generation")

    print_key_value("Model", model)
    print_key_value(
        "Thinking budget",
        str(max_thinking_tokens) if max_thinking_tokens else "Default",
    )
    print()

    # Log session start
    if task_logger:
        task_logger.start_phase(LogPhase.CODING, "Starting documentation generation...")
        task_logger.log_entry(
            LogEntryType.INFO,
            f"Analyzing {len(analysis_results.get('functions', []))} functions, "
            f"{len(analysis_results.get('classes', []))} classes for documentation",
        )

    # Load the documentation generator prompt
    try:
        prompt = get_agent_prompt("documentation_generator")
    except Exception as e:
        error_msg = f"Failed to load documentation_generator prompt: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Create the starting message with analysis results
    starting_message = f"""You are the Documentation Generator Agent. Your task is to generate comprehensive documentation based on the code analysis results below.

## Code Analysis Results

{json.dumps(analysis_results, indent=2)}

## Your Task

1. Read the spec.md to understand what was implemented
2. Review the implementation_plan.json to see what features were built
3. Study existing documentation patterns in docs/ and guides/ directories
4. Generate documentation files for the functions and classes above:
   - API documentation for public functions and classes
   - README updates if needed
   - Architecture documentation for significant modules
   - User guides for new features
5. Follow the project's documentation style guide (docs/STYLE_GUIDE.md)
6. Use templates from docs/templates/ where applicable
7. Support multiple formats (Markdown, with consideration for HTML/PDF)

Generate documentation files in appropriate directories:
- API docs in docs/api/
- Architecture docs in docs/architecture/
- User guides in guides/
- README updates in project root

Begin by loading context (Phase 0 in your prompt).
"""

    # Create SDK client with documentation_generator agent type
    try:
        client = create_client(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            agent_type="documentation_generator",
            max_thinking_tokens=max_thinking_tokens,
        )
    except Exception as e:
        error_msg = f"Failed to create Claude SDK client: {e}"
        logger.error(error_msg)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)
        return {"generated_files": [], "success": False, "error": error_msg}

    # Run the agent session
    try:
        print_status("Starting documentation generation session...", "progress")

        response = await client.create_agent_session(
            name="documentation-generator-session",
            starting_message=starting_message,
        )

        if task_logger:
            task_logger.log_entry(
                LogEntryType.INFO, "Documentation generation session completed"
            )

        # Parse generated files from response
        # The agent should document which files it created
        generated_files = []

        # Check for common documentation locations
        doc_dirs = [
            project_dir / "docs" / "api",
            project_dir / "docs" / "architecture",
            project_dir / "guides",
            project_dir,
        ]

        for doc_dir in doc_dirs:
            if doc_dir.exists():
                # Look for recently modified markdown files
                for md_file in doc_dir.glob("*.md"):
                    # Consider files modified in the last minute as generated
                    import time

                    if time.time() - md_file.stat().st_mtime < 60:
                        generated_files.append(md_file.relative_to(project_dir))

        if verbose:
            print()
            print_status(f"Generated {len(generated_files)} documentation files", "info")
            for file in generated_files:
                print(f"  - {file}")

        # Validate generated documentation
        if generated_files:
            validation_success = validate_generated_docs(generated_files, project_dir)
            if not validation_success:
                logger.warning("Documentation validation failed")
                if task_logger:
                    task_logger.log_entry(
                        LogEntryType.WARNING,
                        "Some generated documentation files failed validation",
                    )

        print()
        print_status("Documentation generation complete", "success")

        return {
            "generated_files": [str(f) for f in generated_files],
            "success": True,
            "error": None,
        }

    except Exception as e:
        error_msg = f"Documentation generation failed: {e}"
        logger.error(error_msg, exc_info=True)
        if task_logger:
            task_logger.log_entry(LogEntryType.ERROR, error_msg)

        print()
        print_status(f"Documentation generation failed: {e}", "error")

        return {"generated_files": [], "success": False, "error": str(e)}
