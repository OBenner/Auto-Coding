"""
Auto-Code CLI - Main Entry Point
==================================

Command-line interface for the Auto-Code autonomous coding framework.
"""

import argparse
import os
import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))


from .analysis_commands import handle_analysis_command
from .analytics_commands import handle_analytics_command
from .batch_commands import (
    handle_batch_cleanup_command,
    handle_batch_create_command,
    handle_batch_status_command,
)
from .build_commands import handle_build_command
from .followup_commands import handle_followup_command
from .migration_commands import (
    handle_migration_command,
    handle_migration_status_command,
)
from .pattern_commands import (
    handle_pattern_analyze_command,
    handle_pattern_query_command,
    handle_pattern_stats_command,
)
from .predictive_scan_commands import (
    handle_predictive_scan_check_command,
    handle_predictive_scan_command,
    handle_predictive_scan_status_command,
)
from .provider_smoke_commands import (
    DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS,
    handle_provider_smoke_command,
)
from .qa_commands import (
    handle_qa_command,
    handle_qa_status_command,
    handle_review_status_command,
)
from .runtime_commands import handle_runtime_modes_command
from .scheduler_commands import (
    handle_schedule_cancel_command,
    handle_schedule_command,
    handle_schedule_start_command,
    handle_schedule_status_command,
    handle_schedule_stop_command,
)
from .security_commands import handle_security_audit_command
from .setup_commands import handle_setup_command
from .spec_commands import print_specs_list
from .utils import (
    DEFAULT_MODEL,
    find_spec,
    get_project_dir,
    print_banner,
    setup_environment,
)
from .workspace_commands import (
    handle_cleanup_worktrees_command,
    handle_create_pr_command,
    handle_discard_command,
    handle_list_worktrees_command,
    handle_merge_analytics_export_command,
    handle_merge_analytics_list_command,
    handle_merge_analytics_summary_command,
    handle_merge_command,
    handle_review_command,
)


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Auto-Code Framework - Autonomous multi-session coding agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all specs
  python auto-claude/run.py --list

  # Run a specific spec (by number or full name)
  python auto-claude/run.py --spec 001
  python auto-claude/run.py --spec 001-initial-app

  # Workspace management (after build completes)
  python auto-claude/run.py --spec 001 --merge     # Add build to your project
  python auto-claude/run.py --spec 001 --review    # See what was built
  python auto-claude/run.py --spec 001 --discard   # Delete build (with confirmation)

  # Advanced options
  python auto-claude/run.py --spec 001 --direct       # Skip workspace isolation
  python auto-claude/run.py --spec 001 --isolated     # Force workspace isolation

  # Status checks
  python auto-claude/run.py --spec 001 --review-status  # Check human review status
  python auto-claude/run.py --spec 001 --qa-status      # Check QA validation status

Prerequisites:
  1. Authenticate: Run 'claude' and type '/login'
  2. Create a spec first: claude /spec

Environment Variables:
  CLAUDE_CODE_OAUTH_TOKEN  Your Claude Code OAuth token (auto-detected from Keychain)
                           Or authenticate via: claude → /login
  AUTO_BUILD_MODEL         Override default model (optional)
        """,
    )

    parser.add_argument(
        "--list",
        action="store_true",
        help="List all available specs and their status",
    )

    parser.add_argument(
        "--spec",
        type=str,
        default=None,
        help="Spec to run (e.g., '001' or '001-feature-name')",
    )

    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Project directory (default: current working directory)",
    )

    parser.add_argument(
        "--max-iterations",
        type=int,
        default=None,
        help="Maximum number of agent sessions (default: unlimited)",
    )

    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help=f"Model to use (default: {DEFAULT_MODEL})",
    )

    parser.add_argument(
        "--provider",
        type=str,
        default=None,
        choices=[
            "claude",
            "openai",
            "google",
            "litellm",
            "openrouter",
            "zhipuai",
            "ollama",
        ],
        help="AI provider to use (default: from env or claude)",
    )

    parser.add_argument(
        "--runtime-mode",
        type=str,
        default=None,
        choices=[
            "full-autonomous",
            "full_autonomous",
            "patch-proposal",
            "patch_proposal",
            "analysis-only",
            "analysis_only",
        ],
        help="Agent runtime mode (default: full_autonomous)",
    )

    parser.add_argument(
        "--runtime-modes",
        action="store_true",
        help="Show provider/runtime compatibility and exit",
    )

    parser.add_argument(
        "--provider-smoke",
        action="store_true",
        help="Run an opt-in text-only smoke check for the configured provider",
    )

    parser.add_argument(
        "--provider-smoke-prompt",
        type=str,
        default=None,
        help="With --provider-smoke: custom prompt for the smoke request",
    )

    parser.add_argument(
        "--provider-smoke-timeout",
        type=float,
        default=DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS,
        help=(
            "With --provider-smoke: timeout in seconds "
            f"(default: {DEFAULT_PROVIDER_SMOKE_TIMEOUT_SECONDS:g})"
        ),
    )

    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Run a non-mutating analysis-only pass for a spec",
    )

    parser.add_argument(
        "--analysis-prompt",
        type=str,
        default=None,
        help="With --analyze: custom analysis question or focus",
    )

    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )

    parser.add_argument(
        "--ci",
        action="store_true",
        help="Enable CI/CD pipeline mode (non-interactive, structured output)",
    )

    parser.add_argument(
        "--json",
        action="store_true",
        help="Enable JSON output mode for structured machine-readable output",
    )

    # Workspace options
    workspace_group = parser.add_mutually_exclusive_group()
    workspace_group.add_argument(
        "--isolated",
        action="store_true",
        help="Force building in isolated workspace (safer)",
    )
    workspace_group.add_argument(
        "--direct",
        action="store_true",
        help="Build directly in your project (no isolation)",
    )

    # Build management commands
    build_group = parser.add_mutually_exclusive_group()
    build_group.add_argument(
        "--merge",
        action="store_true",
        help="Merge an existing build into your project",
    )
    build_group.add_argument(
        "--review",
        action="store_true",
        help="Review what an existing build contains",
    )
    build_group.add_argument(
        "--discard",
        action="store_true",
        help="Discard an existing build (requires confirmation)",
    )
    build_group.add_argument(
        "--create-pr",
        action="store_true",
        help="Push branch and create a GitHub Pull Request",
    )

    # PR options
    parser.add_argument(
        "--pr-target",
        type=str,
        metavar="BRANCH",
        help="With --create-pr: target branch for PR (default: auto-detect)",
    )
    parser.add_argument(
        "--pr-title",
        type=str,
        metavar="TITLE",
        help="With --create-pr: custom PR title (default: generated from spec name)",
    )
    parser.add_argument(
        "--pr-draft",
        action="store_true",
        help="With --create-pr: create as draft PR",
    )

    # Merge options
    parser.add_argument(
        "--no-commit",
        action="store_true",
        help="With --merge: stage changes but don't commit (review in IDE first)",
    )
    parser.add_argument(
        "--merge-preview",
        action="store_true",
        help="Preview merge conflicts without actually merging (returns JSON)",
    )

    # QA options
    parser.add_argument(
        "--qa",
        action="store_true",
        help="Run QA validation loop on a completed build",
    )
    parser.add_argument(
        "--qa-status",
        action="store_true",
        help="Show QA validation status for a spec",
    )
    parser.add_argument(
        "--skip-qa",
        action="store_true",
        help="Skip automatic QA validation after build completes",
    )

    # Follow-up options
    parser.add_argument(
        "--followup",
        action="store_true",
        help="Add follow-up tasks to a completed spec (extends existing implementation plan)",
    )

    # Migration options
    parser.add_argument(
        "--migrate",
        action="store_true",
        help="Run migration assistant agent for framework/library migrations",
    )
    parser.add_argument(
        "--migration-status",
        action="store_true",
        help="Show migration checkpoint status and validation results",
    )

    # Review options
    parser.add_argument(
        "--review-status",
        action="store_true",
        help="Show human review/approval status for a spec",
    )

    # Non-interactive mode (for UI/automation)
    parser.add_argument(
        "--auto-continue",
        action="store_true",
        help="Non-interactive mode: auto-continue existing builds, skip prompts (for UI integration)",
    )

    # Worktree management
    parser.add_argument(
        "--list-worktrees",
        action="store_true",
        help="List all spec worktrees and their status",
    )
    parser.add_argument(
        "--cleanup-worktrees",
        action="store_true",
        help="Remove all spec worktrees and their branches (with confirmation)",
    )

    # Force bypass
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip approval check and start build anyway (for debugging)",
    )

    # Task restart
    parser.add_argument(
        "--restart-from",
        type=str,
        default=None,
        metavar="SUBTASK_ID",
        help="Restart build from a specific subtask ID (preserves provider/model config)",
    )

    # Base branch for worktree creation
    parser.add_argument(
        "--base-branch",
        type=str,
        default=None,
        help="Base branch for creating worktrees (default: auto-detect or current branch)",
    )

    # Batch task management
    parser.add_argument(
        "--batch-create",
        type=str,
        default=None,
        metavar="FILE",
        help="Create multiple tasks from a batch JSON file",
    )
    parser.add_argument(
        "--batch-status",
        action="store_true",
        help="Show status of all specs in the project",
    )
    parser.add_argument(
        "--batch-cleanup",
        action="store_true",
        help="Clean up completed specs (dry-run by default)",
    )
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Actually delete files in cleanup (not just preview)",
    )

    # Scheduler commands
    parser.add_argument(
        "--schedule",
        type=str,
        default=None,
        metavar="SPEC",
        help="Schedule a build for a specific spec",
    )
    parser.add_argument(
        "--schedule-at",
        type=str,
        default=None,
        metavar="TIME",
        help="With --schedule: when to run (ISO format or 'tonight 10pm')",
    )
    parser.add_argument(
        "--schedule-priority",
        type=str,
        default="normal",
        choices=["low", "normal", "high", "urgent"],
        help="With --schedule: build priority (default: normal)",
    )
    parser.add_argument(
        "--schedule-deps",
        type=str,
        default=None,
        metavar="SPECS",
        help="With --schedule: comma-separated spec IDs this build depends on",
    )
    parser.add_argument(
        "--schedule-status",
        action="store_true",
        help="Show status of scheduled builds",
    )
    parser.add_argument(
        "--schedule-cancel",
        type=str,
        default=None,
        metavar="BUILD_ID",
        help="Cancel a scheduled build",
    )
    parser.add_argument(
        "--schedule-start",
        action="store_true",
        help="Start the scheduler service",
    )
    parser.add_argument(
        "--schedule-stop",
        action="store_true",
        help="Stop the scheduler service",
    )

    # Merge analytics commands
    parser.add_argument(
        "--merge-analytics-list",
        action="store_true",
        help="Show merge operation history",
    )
    parser.add_argument(
        "--merge-analytics-summary",
        action="store_true",
        help="Show aggregated merge analytics and statistics",
    )
    parser.add_argument(
        "--merge-analytics-export",
        action="store_true",
        help="Export merge analytics to a file (JSON or CSV)",
    )
    parser.add_argument(
        "--analytics-format",
        type=str,
        default="json",
        choices=["json", "csv"],
        help="Format for analytics export (default: json)",
    )
    parser.add_argument(
        "--analytics-output",
        type=str,
        default=None,
        metavar="FILE",
        help="Output file for analytics export",
    )
    parser.add_argument(
        "--analytics-limit",
        type=int,
        default=100,
        help="Limit number of operations in list view (default: 100)",
    )
    parser.add_argument(
        "--analytics-task",
        type=str,
        default=None,
        metavar="TASK_ID",
        help="Filter analytics by task ID",
    )

    # Productivity analytics commands
    parser.add_argument(
        "--analytics",
        action="store_true",
        help="Show productivity analytics across all specs",
    )
    parser.add_argument(
        "--analytics-trends",
        action="store_true",
        help="Show productivity trends over time",
    )
    parser.add_argument(
        "--analytics-days",
        type=int,
        default=30,
        help="Number of days for trends analysis (default: 30)",
    )
    parser.add_argument(
        "--analytics-granularity",
        type=str,
        default="daily",
        choices=["daily", "weekly", "monthly"],
        help="Time granularity for trends (default: daily)",
    )
    parser.add_argument(
        "--analytics-export-path",
        type=str,
        default=None,
        metavar="FILE",
        help="Export analytics to file (with --analytics)",
    )

    # Predictive scan commands
    parser.add_argument(
        "--predictive-scan",
        action="store_true",
        help="Run predictive issue scan on project",
    )
    parser.add_argument(
        "--predictive-status",
        action="store_true",
        help="Show predictive scan status and trends",
    )
    parser.add_argument(
        "--predictive-check",
        action="store_true",
        help="CI/CD blocking check (exits 1 if critical issues found)",
    )
    parser.add_argument(
        "--scan-file-patterns",
        nargs="+",
        metavar="PATTERN",
        help="Glob patterns to scan (e.g., '**/*.py')",
    )
    parser.add_argument(
        "--no-scan-llm",
        action="store_true",
        help="Disable LLM analysis for faster scan",
    )
    parser.add_argument(
        "--scan-json",
        action="store_true",
        help="Output scan results as JSON",
    )
    parser.add_argument(
        "--scan-no-bug",
        action="store_true",
        help="Disable bug detection",
    )
    parser.add_argument(
        "--scan-no-performance",
        action="store_true",
        help="Disable performance analysis",
    )
    parser.add_argument(
        "--scan-no-code-smell",
        action="store_true",
        help="Disable code smell detection",
    )
    parser.add_argument(
        "--scan-days",
        type=int,
        default=30,
        help="Number of days for trend analysis (default: 30)",
    )
    parser.add_argument(
        "--scan-fail-on-high",
        action="store_true",
        help="Fail CI/CD check on high severity (default: critical only)",
    )

    # Security audit commands
    parser.add_argument(
        "--security-audit",
        action="store_true",
        help="Run comprehensive security audit on the project",
    )
    parser.add_argument(
        "--security-output-format",
        type=str,
        default="both",
        choices=["json", "markdown", "both"],
        help="Output format for security audit report (default: both)",
    )

    # Failure pattern analysis commands
    parser.add_argument(
        "--failure-pattern-analyze",
        action="store_true",
        help="Analyze failure patterns from attempt history",
    )
    parser.add_argument(
        "--failure-pattern-query",
        type=str,
        default=None,
        metavar="QUERY",
        help="Query stored failure patterns from Graphiti memory",
    )
    parser.add_argument(
        "--failure-pattern-stats",
        action="store_true",
        help="Show failure pattern statistics",
    )
    parser.add_argument(
        "--pattern-type",
        type=str,
        default=None,
        choices=[
            "recurring_error",
            "escalating_complexity",
            "model_limitation",
            "circular_fix",
            "context_exhaustion",
        ],
        help="Filter failure patterns by type (with --failure-pattern-query)",
    )
    parser.add_argument(
        "--min-confidence",
        type=float,
        default=0.0,
        help="Minimum confidence score for pattern queries (default: 0.0)",
    )
    parser.add_argument(
        "--pattern-num-results",
        type=int,
        default=10,
        help="Maximum number of pattern results (default: 10)",
    )

    # Environment setup commands
    parser.add_argument(
        "--setup",
        action="store_true",
        help="One-command environment sync: detect stack, install dependencies, configure .env, validate setup",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview mode: with --setup shows planned changes without executing; "
        "with --batch-cleanup previews deletions (opposite of --no-dry-run)",
    )
    parser.add_argument(
        "--skip-install",
        action="store_true",
        help="With --setup: skip dependency installation",
    )
    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="With --setup: skip environment configuration (.env setup)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="With --setup: skip Graphiti and LLM provider validation",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="With --setup: non-interactive mode (use default values, no prompts)",
    )

    return parser.parse_args()


def main() -> None:
    """Main CLI entry point."""
    # Set up environment first
    setup_environment()

    # Initialize Sentry early to capture any startup errors
    from core.sentry import capture_exception, init_sentry

    init_sentry(component="cli")

    try:
        _run_cli()
    except KeyboardInterrupt:
        # Clean exit on Ctrl+C
        sys.exit(130)
    except Exception as e:
        # Capture unexpected errors to Sentry
        capture_exception(e)
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


def _run_cli() -> None:
    """Run the CLI logic (extracted for error handling)."""
    # Import here to avoid import errors during startup
    from core.sentry import set_context

    # Parse arguments
    args = parse_args()

    # Wire --ci flag into CI mode env var so is_ci_mode() picks it up
    if args.ci:
        os.environ["AUTO_CLAUDE_CI"] = "1"

    # Import debug functions after environment setup
    from debug import debug, debug_error, debug_section, debug_success

    debug_section("run.py", "Starting Auto-Build Framework")
    debug("run.py", "Arguments parsed", args=vars(args))

    # Determine project directory
    project_dir = get_project_dir(args.project_dir)
    debug("run.py", f"Using project directory: {project_dir}")

    # Get model from CLI arg or env var (None if not explicitly set)
    # This allows get_phase_model() to fall back to task_metadata.json
    model = args.model or os.environ.get("AUTO_BUILD_MODEL")

    # Get provider from CLI arg (default: from env or claude)
    provider = args.provider
    if provider:
        os.environ["AI_ENGINE_PROVIDER"] = provider

    if args.runtime_mode:
        from agents.runtime import normalize_runtime_mode

        os.environ["AUTO_CODE_RUNTIME_MODE"] = normalize_runtime_mode(args.runtime_mode)

    # Handle --runtime-modes command before requiring a spec.
    if args.runtime_modes:
        handle_runtime_modes_command(output_json=args.json)
        return

    # Handle --provider-smoke command before requiring a spec.
    if args.provider_smoke:
        result = handle_provider_smoke_command(
            project_dir=project_dir,
            model=model,
            prompt=args.provider_smoke_prompt,
            timeout_seconds=args.provider_smoke_timeout,
            output_json=args.json,
        )
        if not result.success:
            sys.exit(1)
        return

    # Handle --list command
    if args.list:
        print_banner()
        print_specs_list(project_dir)
        return

    # Handle --list-worktrees command
    if args.list_worktrees:
        handle_list_worktrees_command(project_dir)
        return

    # Handle --cleanup-worktrees command
    if args.cleanup_worktrees:
        handle_cleanup_worktrees_command(project_dir)
        return

    # Handle --setup command
    if args.setup:
        result = handle_setup_command(
            project_dir=project_dir,
            dry_run=args.dry_run,
            skip_install=args.skip_install,
            skip_config=args.skip_config,
            skip_validation=args.skip_validation,
            interactive=not args.non_interactive,
            verbose=args.verbose or not args.json,
        )
        # Output JSON if --json flag is set
        if args.json:
            import json

            print(json.dumps(result, indent=2, default=str))
        # Exit with appropriate code
        sys.exit(0 if result["success"] else 1)

    # Handle batch commands
    if args.batch_create:
        handle_batch_create_command(args.batch_create, str(project_dir))
        return

    if args.batch_status:
        handle_batch_status_command(str(project_dir))
        return

    if args.batch_cleanup:
        handle_batch_cleanup_command(str(project_dir), dry_run=not args.no_dry_run)
        return

    # Handle scheduler commands
    if args.schedule:
        deps = (
            [d.strip() for d in args.schedule_deps.split(",") if d.strip()]
            if args.schedule_deps
            else None
        )
        handle_schedule_command(
            args.schedule,
            str(project_dir),
            scheduled_time=args.schedule_at,
            priority=args.schedule_priority,
            dependencies=deps,
        )
        return

    if args.schedule_status:
        handle_schedule_status_command(str(project_dir))
        return

    if args.schedule_cancel:
        handle_schedule_cancel_command(args.schedule_cancel, str(project_dir))
        return

    if args.schedule_start:
        handle_schedule_start_command(str(project_dir))
        return

    if args.schedule_stop:
        handle_schedule_stop_command(str(project_dir))
        return

    # Handle merge analytics commands
    if args.merge_analytics_list:
        handle_merge_analytics_list_command(
            project_dir, limit=args.analytics_limit, task_id=args.analytics_task
        )
        return

    if args.merge_analytics_summary:
        handle_merge_analytics_summary_command(project_dir)
        return

    if args.merge_analytics_export:
        handle_merge_analytics_export_command(
            project_dir,
            output_path=args.analytics_output,
            format=args.analytics_format,
        )
        return

    # Handle productivity analytics command
    if args.analytics:
        export_path = (
            Path(args.analytics_export_path) if args.analytics_export_path else None
        )
        handle_analytics_command(
            project_dir=project_dir,
            trends=args.analytics_trends,
            days=args.analytics_days,
            granularity=args.analytics_granularity,
            export_path=export_path,
            export_format=args.analytics_format,
        )
        return

    # Handle predictive scan commands
    if args.predictive_scan:
        scan_spec_dir = None
        if args.spec:
            scan_spec_dir = find_spec(project_dir, args.spec)
        exit_code = handle_predictive_scan_command(
            project_dir=project_dir,
            spec_dir=scan_spec_dir,
            file_patterns=args.scan_file_patterns,
            run_llm=not args.no_scan_llm,
            output_json=args.scan_json,
            detect_bug=not args.scan_no_bug,
            detect_performance=not args.scan_no_performance,
            detect_code_smell=not args.scan_no_code_smell,
        )
        sys.exit(exit_code)

    if args.predictive_status:
        if not args.spec:
            print("Warning: --spec required for --predictive-status")
            sys.exit(1)

        spec_dir = find_spec(project_dir, args.spec)
        if not spec_dir:
            print_banner()
            print(f"\nError: Spec '{args.spec}' not found")
            print("\nAvailable specs:")
            print_specs_list(project_dir)
            sys.exit(1)

        handle_predictive_scan_status_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            days=args.scan_days,
        )
        return

    if args.predictive_check:
        spec_dir = None
        if args.spec:
            spec_dir = find_spec(project_dir, args.spec)
            if not spec_dir:
                print_banner()
                print(f"\nError: Spec '{args.spec}' not found")
                print("\nAvailable specs:")
                print_specs_list(project_dir)
                sys.exit(1)

        exit_code = handle_predictive_scan_check_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            fail_on_high=args.scan_fail_on_high,
        )
        sys.exit(exit_code)

    # Handle security audit command
    if args.security_audit:
        # Security audit can run with or without a spec
        spec_dir = None
        if args.spec:
            spec_dir = find_spec(project_dir, args.spec)
            if not spec_dir:
                print_banner()
                print(f"\nError: Spec '{args.spec}' not found")
                print("\nAvailable specs:")
                print_specs_list(project_dir)
                sys.exit(1)

        handle_security_audit_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            output_format=args.security_output_format,
            verbose=args.verbose,
        )
        return

    # Handle failure pattern analyze command
    if args.failure_pattern_analyze:
        handle_pattern_analyze_command(
            project_dir=project_dir,
            spec_id=args.spec,
            output_json=args.json,
        )
        return

    # Handle failure pattern query command
    if args.failure_pattern_query is not None:
        # Requires --spec for context
        if not args.spec:
            print_banner()
            print("\nError: --spec is required for --failure-pattern-query")
            print("\nUsage:")
            print(
                "  python auto-claude/run.py --spec 001 --failure-pattern-query 'error type'"
            )
            sys.exit(1)

        spec_dir = find_spec(project_dir, args.spec)
        if not spec_dir:
            print_banner()
            print(f"\nError: Spec '{args.spec}' not found")
            print("\nAvailable specs:")
            print_specs_list(project_dir)
            sys.exit(1)

        handle_pattern_query_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            query=args.failure_pattern_query,
            pattern_type=args.pattern_type,
            min_confidence=args.min_confidence,
            num_results=args.pattern_num_results,
            output_json=args.json,
        )
        return

    # Handle failure pattern statistics command
    if args.failure_pattern_stats:
        # Requires --spec for context
        if not args.spec:
            print_banner()
            print("\nError: --spec is required for --failure-pattern-stats")
            print("\nUsage:")
            print("  python auto-claude/run.py --spec 001 --failure-pattern-stats")
            sys.exit(1)

        spec_dir = find_spec(project_dir, args.spec)
        if not spec_dir:
            print_banner()
            print(f"\nError: Spec '{args.spec}' not found")
            print("\nAvailable specs:")
            print_specs_list(project_dir)
            sys.exit(1)

        handle_pattern_stats_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            output_json=args.json,
        )
        return

    # Require --spec if not listing
    if not args.spec:
        print_banner()
        print("\nError: --spec is required")
        print("\nUsage:")
        print("  python auto-claude/run.py --list           # See all specs")
        print("  python auto-claude/run.py --spec 001       # Run a spec")
        print("\nCreate a new spec with:")
        print("  claude /spec")
        sys.exit(1)

    # Find the spec
    debug("run.py", "Finding spec", spec_identifier=args.spec)
    spec_dir = find_spec(project_dir, args.spec)
    if not spec_dir:
        debug_error("run.py", "Spec not found", spec=args.spec)
        print_banner()
        print(f"\nError: Spec '{args.spec}' not found")
        print("\nAvailable specs:")
        print_specs_list(project_dir)
        sys.exit(1)

    debug_success("run.py", "Spec found", spec_dir=str(spec_dir))

    # Set Sentry context for error tracking
    set_context(
        "spec",
        {
            "name": spec_dir.name,
            "project": str(project_dir),
        },
    )

    # Handle build management commands
    if args.merge_preview:
        from cli.workspace_commands import handle_merge_preview_command

        result = handle_merge_preview_command(
            project_dir, spec_dir.name, base_branch=args.base_branch
        )
        # Output as JSON for the UI to parse
        import json

        print(json.dumps(result))
        return

    if args.merge:
        success = handle_merge_command(
            project_dir,
            spec_dir.name,
            no_commit=args.no_commit,
            base_branch=args.base_branch,
        )
        if not success:
            sys.exit(1)
        return

    if args.review:
        handle_review_command(project_dir, spec_dir.name)
        return

    if args.discard:
        handle_discard_command(project_dir, spec_dir.name)
        return

    if args.create_pr:
        # Pass args.pr_target directly - WorktreeManager._detect_base_branch
        # handles base branch detection internally when target_branch is None
        result = handle_create_pr_command(
            project_dir=project_dir,
            spec_name=spec_dir.name,
            target_branch=args.pr_target,
            title=args.pr_title,
            draft=args.pr_draft,
        )
        # JSON output is already printed by handle_create_pr_command
        if not result.get("success"):
            sys.exit(1)
        return

    # Handle QA commands
    if args.qa_status:
        handle_qa_status_command(spec_dir)
        return

    if args.review_status:
        handle_review_status_command(spec_dir)
        return

    if args.analyze:
        handle_analysis_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            user_prompt=args.analysis_prompt,
            verbose=args.verbose,
            output_json=args.json,
        )
        return

    if args.qa:
        handle_qa_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            verbose=args.verbose,
        )
        return

    # Handle --followup command
    if args.followup:
        handle_followup_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            verbose=args.verbose,
        )
        return

    # Handle migration commands
    if args.migration_status:
        handle_migration_status_command(project_dir, spec_dir)
        return

    if args.migrate:
        handle_migration_command(
            project_dir=project_dir,
            spec_dir=spec_dir,
            model=model,
            verbose=args.verbose,
        )
        return

    # Normal build flow
    handle_build_command(
        project_dir=project_dir,
        spec_dir=spec_dir,
        model=model,
        provider=provider,
        max_iterations=args.max_iterations,
        verbose=args.verbose,
        force_isolated=args.isolated,
        force_direct=args.direct,
        auto_continue=args.auto_continue,
        skip_qa=args.skip_qa,
        force_bypass_approval=args.force,
        base_branch=args.base_branch,
        json_mode=args.json,
        restart_from=args.restart_from,
    )


if __name__ == "__main__":
    main()
