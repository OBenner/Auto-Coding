"""
CLI Utilities
==============

Shared utility functions for the Auto-Code CLI.
"""

import os
import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from core.auth import get_auth_token, get_auth_token_source
from core.dependency_validator import validate_platform_dependencies


def import_dotenv():
    """
    Import and return load_dotenv with helpful error message if not installed.

    This centralized function ensures consistent error messaging across all
    runner scripts when python-dotenv is not available.

    Returns:
        The load_dotenv function

    Raises:
        SystemExit: If dotenv cannot be imported, with helpful installation instructions.
    """
    try:
        from dotenv import load_dotenv as _load_dotenv

        return _load_dotenv
    except ImportError:
        sys.exit(
            "Error: Required Python package 'python-dotenv' is not installed.\n"
            "\n"
            "This usually means you're not using the virtual environment.\n"
            "\n"
            "To fix this:\n"
            "1. From the 'apps/backend/' directory, activate the venv:\n"
            "   source .venv/bin/activate  # Linux/macOS\n"
            "   .venv\\Scripts\\activate   # Windows\n"
            "\n"
            "2. Or install dependencies directly:\n"
            "   pip install python-dotenv\n"
            "   pip install -r requirements.txt\n"
            "\n"
            f"Current Python: {sys.executable}\n"
        )


# Load .env with helpful error if dependencies not installed
load_dotenv = import_dotenv()
# NOTE: graphiti_config is imported lazily in validate_environment() to avoid
# triggering graphiti_core -> real_ladybug -> pywintypes import chain before
# platform dependency validation can run. See ACS-253.
from ui import (
    Icons,
    bold,
    box,
    icon,
    muted,
)

# Configuration - uses shorthand that resolves via API Profile if configured
DEFAULT_MODEL = "sonnet"  # Changed from "opus" (fix #433)

# Agent roles a build/QA run spawns directly. Auth validation resolves each
# role's provider the same way the runtime factory does, so the Claude OAuth
# requirement only applies when one of these roles actually runs on claude.
# Utility agents (insights, commit_message, merge_resolver) are best-effort
# and degrade gracefully without Claude auth.
CORE_AGENT_ROLES: tuple[str, ...] = ("planner", "coder", "qa_reviewer", "qa_fixer")


def resolve_agent_providers(
    roles: tuple[str, ...] = CORE_AGENT_ROLES,
) -> dict[str, str]:
    """
    Map each agent role to the AI provider it resolves to at runtime.

    Mirrors core.providers.factory.create_agent_session, which resolves via
    ProviderConfig.from_env: AGENT_PROVIDER_<ROLE> > AI_ENGINE_PROVIDER >
    claude default (invalid names fall back to claude).

    Returns:
        Dict of role -> provider name, in the order roles were given
    """
    # Lazy import: core.providers pulls in the full adapter registry
    from core.providers.config import ProviderConfig

    return {role: ProviderConfig.from_env(agent_type=role).provider for role in roles}


def is_ci_mode() -> bool:
    """
    Check if running in CI/CD mode.

    CI mode is enabled when the AUTO_CLAUDE_CI environment variable is set to
    'true', '1', 'yes', or 'on'. This enables headless operation with exit codes
    and JSON output.

    Returns:
        True if in CI mode, False otherwise
    """
    ci_value = os.environ.get("AUTO_CLAUDE_CI", "").lower()
    return ci_value in ("true", "1", "yes", "on")


def is_json_output_enabled() -> bool:
    """
    Check if JSON output mode is enabled.

    JSON output mode is enabled when the AUTO_CLAUDE_JSON_OUTPUT environment variable
    is set to 'true', '1', 'yes', or 'on'. This enables structured JSON output for
    programmatic consumption.

    Returns:
        True if JSON output is enabled, False otherwise
    """
    json_value = os.environ.get("AUTO_CLAUDE_JSON_OUTPUT", "").lower()
    return json_value in ("true", "1", "yes", "on")


def setup_environment() -> Path:
    """
    Set up the environment and return the script directory.

    Returns:
        Path to the auto-claude directory
    """
    # Add auto-claude directory to path for imports
    script_dir = Path(__file__).parent.parent.resolve()
    sys.path.insert(0, str(script_dir))

    # Load .env file - check both auto-claude/ and dev/auto-claude/ locations
    env_file = script_dir / ".env"
    dev_env_file = script_dir.parent / "dev" / "auto-claude" / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    elif dev_env_file.exists():
        load_dotenv(dev_env_file)

    return script_dir


def find_spec(project_dir: Path, spec_identifier: str) -> Path | None:
    """
    Find a spec by number or full name.

    Args:
        project_dir: Project root directory
        spec_identifier: Either "001" or "001-feature-name"

    Returns:
        Path to spec folder, or None if not found
    """
    from spec.pipeline import get_specs_dir

    specs_dir = get_specs_dir(project_dir)

    if specs_dir.exists():
        # Try exact match first
        exact_path = specs_dir / spec_identifier
        if exact_path.exists() and (exact_path / "spec.md").exists():
            return exact_path

        # Try matching by number prefix
        for spec_folder in specs_dir.iterdir():
            if (
                spec_folder.is_dir()
                and spec_folder.name.startswith(spec_identifier + "-")
                and (spec_folder / "spec.md").exists()
            ):
                return spec_folder

    # Check worktree specs (for merge-preview, merge, review, discard operations)
    worktree_base = project_dir / ".auto-claude" / "worktrees" / "tasks"
    if worktree_base.exists():
        # Try exact match in worktree
        worktree_spec = (
            worktree_base / spec_identifier / ".auto-claude" / "specs" / spec_identifier
        )
        if worktree_spec.exists() and (worktree_spec / "spec.md").exists():
            return worktree_spec

        # Try matching by prefix in worktrees
        for worktree_dir in worktree_base.iterdir():
            if worktree_dir.is_dir() and worktree_dir.name.startswith(
                spec_identifier + "-"
            ):
                spec_in_worktree = (
                    worktree_dir / ".auto-claude" / "specs" / worktree_dir.name
                )
                if (
                    spec_in_worktree.exists()
                    and (spec_in_worktree / "spec.md").exists()
                ):
                    return spec_in_worktree

    return None


def validate_environment(spec_dir: Path) -> bool:
    """
    Validate that the environment is set up correctly.

    Returns:
        True if valid, False otherwise (with error messages printed)
    """
    # Validate platform-specific dependencies first (exits if missing)
    validate_platform_dependencies()

    valid = True

    # Resolve which provider each agent role runs on. The Claude OAuth token
    # is only required when at least one role resolves to the claude provider;
    # codex and the direct-API providers carry their own credentials.
    agent_providers = resolve_agent_providers()
    claude_roles = [
        role for role, provider in agent_providers.items() if provider == "claude"
    ]
    non_claude_providers = sorted(set(agent_providers.values()) - {"claude"})

    if non_claude_providers:
        summary = ", ".join(
            f"{role}={provider}" for role, provider in agent_providers.items()
        )
        print(f"AI providers: {summary}")

    # Check for OAuth token (API keys are not supported)
    if not claude_roles:
        print("Claude auth: not required (no agent role uses the claude provider)")
    elif not get_auth_token():
        print("Error: No OAuth token found")
        print("\nAuto-Code requires Claude Code OAuth authentication because")
        print(f"these agent roles use the claude provider: {', '.join(claude_roles)}.")
        print("Direct API keys (ANTHROPIC_API_KEY) are not supported.")
        print("\nTo authenticate, run:")
        print("  claude setup-token")
        print("\nOr configure every agent role to use a non-Claude provider via")
        print(
            "AI_ENGINE_PROVIDER or AGENT_PROVIDER_<ROLE> (e.g. AGENT_PROVIDER_CODER=openai)."
        )
        valid = False
    else:
        # Show which auth source is being used
        source = get_auth_token_source()
        if source:
            print(f"Auth: {source}")

        # Show custom base URL if set
        base_url = os.environ.get("ANTHROPIC_BASE_URL")
        if base_url:
            print(f"API Endpoint: {base_url}")

    # Surface missing credentials for non-claude providers without blocking:
    # the task router can still fall back to another available provider.
    if non_claude_providers:
        from dataclasses import replace

        from core.providers.config import ProviderConfig

        env_config = ProviderConfig.from_env()
        for provider_name in non_claude_providers:
            if env_config.is_provider_available(provider_name):
                continue
            errors = replace(env_config, provider=provider_name).get_validation_errors()
            detail = (
                errors[0]
                if errors
                else f"{provider_name} provider is missing required configuration"
            )
            print(f"Warning: {detail}")

    # Check for spec.md in spec directory
    spec_file = spec_dir / "spec.md"
    if not spec_file.exists():
        print(f"\nError: spec.md not found in {spec_dir}")
        valid = False

    # Check Linear integration (optional but show status)
    from linear_integration import LinearManager
    from linear_updater import is_linear_enabled

    if is_linear_enabled():
        print("Linear integration: ENABLED")
        # Show Linear project status if initialized
        project_dir = (
            spec_dir.parent.parent
        )  # auto-claude/specs/001-name -> project root
        linear_manager = LinearManager(spec_dir, project_dir)
        if linear_manager.is_initialized:
            summary = linear_manager.get_progress_summary()
            print(f"  Project: {summary.get('project_name', 'Unknown')}")
            print(
                f"  Issues: {summary.get('mapped_subtasks', 0)}/{summary.get('total_subtasks', 0)} mapped"
            )
        else:
            print("  Status: Will be initialized during planner session")
    else:
        print("Linear integration: DISABLED (set LINEAR_API_KEY to enable)")

    # Check CI mode — write to stderr so CI mode status never corrupts JSON stdout output
    if is_ci_mode():
        print("CI/CD mode: ENABLED (AUTO_CLAUDE_CI=true)", file=sys.stderr)
    else:
        print(
            "CI/CD mode: DISABLED (set AUTO_CLAUDE_CI=true to enable)", file=sys.stderr
        )

    # Check Graphiti integration (optional but show status)
    # Lazy import to avoid triggering pywintypes import before validation (ACS-253)
    from integrations.graphiti.config import get_graphiti_status

    graphiti_status = get_graphiti_status()
    if graphiti_status["available"]:
        print("Graphiti memory: ENABLED")
        print(f"  Database: {graphiti_status['database']}")
        if graphiti_status.get("db_path"):
            print(f"  Path: {graphiti_status['db_path']}")
    elif graphiti_status["enabled"]:
        print(
            f"Graphiti memory: CONFIGURED but unavailable ({graphiti_status['reason']})"
        )
    else:
        print("Graphiti memory: DISABLED (set GRAPHITI_ENABLED=true to enable)")

    print()
    return valid


def print_banner() -> None:
    """Print the Auto-Build banner."""
    content = [
        bold(f"{icon(Icons.LIGHTNING)} AUTO-BUILD FRAMEWORK"),
        "",
        "Autonomous Multi-Session Coding Agent",
        muted("Subtask-Based Implementation with Phase Dependencies"),
    ]
    print()
    print(box(content, width=70, style="heavy"))


def get_project_dir(provided_dir: Path | None) -> Path:
    """
    Determine the project directory.

    Args:
        provided_dir: User-provided project directory (or None)

    Returns:
        Resolved project directory path
    """
    if provided_dir:
        return provided_dir.resolve()

    project_dir = Path.cwd()

    # Auto-detect if running from within apps/backend directory (the source code)
    if project_dir.name == "backend" and (project_dir / "run.py").exists():
        # Running from within apps/backend/ source directory, go up 2 levels
        project_dir = project_dir.parent.parent

    return project_dir


def find_specs_dir(project_dir: Path) -> Path:
    """
    Find the specs directory for a project.

    Returns the '.auto-claude/specs' directory path.
    The directory is guaranteed to exist (get_specs_dir calls init_auto_claude_dir).

    Args:
        project_dir: Project root directory

    Returns:
        Path to specs directory (always returns a valid Path)
    """
    from spec.pipeline import get_specs_dir

    return get_specs_dir(project_dir)
