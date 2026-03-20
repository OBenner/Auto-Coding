#!/usr/bin/env python3
"""
Dependency Update Runner
========================

Automated dependency management for Python and Node.js projects.
Scans for outdated packages, assesses update risk, batches compatible updates,
and optionally generates specs for automated dependency updates.

Features:
- Detects outdated Python (pip/uv) and Node.js (npm) dependencies
- CVE vulnerability detection via pip-audit and npm audit
- Risk classification (breaking vs patch vs minor updates)
- Intelligent batching of compatible updates
- JSON and Markdown report generation
- Optional spec generation for automated updates

Usage:
    # Basic scan
    python dependency_update_runner.py --project /path/to/project

    # Dry run with JSON output
    python dependency_update_runner.py --project . --dry-run --format json

    # Generate spec for updates
    python dependency_update_runner.py --project . --generate-spec

    # Scan specific ecosystems only
    python dependency_update_runner.py --project . --ecosystems python,node
"""

import asyncio
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# Add apps/backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Validate platform-specific dependencies BEFORE any imports that might
# trigger graphiti_core -> real_ladybug -> pywintypes import chain (ACS-253)
from core.dependency_validator import validate_platform_dependencies

validate_platform_dependencies()

# Load .env file with centralized error handling
from cli.utils import import_dotenv

load_dotenv = import_dotenv()

env_file = Path(__file__).parent.parent / ".env"
if env_file.exists():
    load_dotenv(env_file)

from phase_config import resolve_model_id

# Dependency update configuration file
DEPENDENCY_UPDATES_CONFIG = ".github/dependency-updates.config.json"


def load_config(project_dir: Path) -> dict[str, Any] | None:
    """
    Load dependency updates configuration from project directory.

    Args:
        project_dir: Project root directory

    Returns:
        Configuration dictionary, or None if not found
    """
    config_file = project_dir / DEPENDENCY_UPDATES_CONFIG

    if not config_file.exists():
        # Try example config
        example_config = project_dir / ".github" / "dependency-updates.config.json.example"
        if example_config.exists():
            try:
                with open(example_config, encoding="utf-8") as f:
                    return json.load(f)
            except (OSError, json.JSONDecodeError, UnicodeDecodeError):
                pass
        return None

    try:
        with open(config_file, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return None


def _generate_task_description(
    scan_result: any,
    batches: list,
    batch_id: str | None = None,
) -> str:
    """
    Generate a task description from scan results and batches.

    Args:
        scan_result: Scan result from DependencyScanner
        batches: List of UpdateBatch objects
        batch_id: Optional specific batch ID to generate spec for

    Returns:
        Formatted task description string
    """

    # Filter batches if specific batch_id requested
    if batch_id:
        target_batches = [b for b in batches if b.batch_id == batch_id]
        if not target_batches:
            raise ValueError(f"Batch {batch_id} not found")
        batches = target_batches

    # Build task description
    lines = ["Update dependencies for the following packages:", ""]

    # Security updates first
    if scan_result.security_updates:
        sec_updates_in_batches = []
        for batch in batches:
            for pkg_name in batch.packages:
                if any(
                    u.name == pkg_name and u.is_security
                    for u in scan_result.security_updates
                ):
                    sec_updates_in_batches.append(pkg_name)

        if sec_updates_in_batches:
            lines.append("**Security Updates (Priority)**:")
            for pkg_name in sec_updates_in_batches[:5]:
                update = next(
                    (u for u in scan_result.updates_available if u.name == pkg_name),
                    None,
                )
                if update:
                    cve_info = (
                        f" (CVEs: {', '.join(update.cve_ids)})"
                        if update.cve_ids
                        else ""
                    )
                    lines.append(
                        f"- {pkg_name}: {update.current_version} → {update.latest_version}{cve_info}"
                    )
            if len(sec_updates_in_batches) > 5:
                lines.append(
                    f"- ... and {len(sec_updates_in_batches) - 5} more security updates"
                )
            lines.append("")

    # All updates in batches
    lines.append("**Packages to Update**:")
    for i, batch in enumerate(batches, 1):
        lines.append(f"\nBatch {i}: {batch.batch_id}")
        lines.append(f"- Risk Level: {batch.risk_level}")
        lines.append(f"- Packages ({len(batch.packages)}):")

        for pkg_name in batch.packages[:5]:
            update = next(
                (u for u in scan_result.updates_available if u.name == pkg_name), None
            )
            if update:
                lines.append(
                    f"  - {pkg_name}: {update.current_version} → {update.latest_version} ({update.update_type})"
                )

        if len(batch.packages) > 5:
            lines.append(f"  - ... and {len(batch.packages) - 5} more packages")

    lines.append("")
    lines.append("**Requirements**:")
    lines.append("- Update specified packages to target versions")
    lines.append("- Run full test suite to verify no regressions")
    lines.append("- Check for breaking changes in updated APIs")
    lines.append("- Update documentation if needed")

    return "\n".join(lines)


def _generate_markdown_report(
    scan_result: any,
    batches: list,
    project_dir: Path,
    ecosystems_filter: list[str] | None = None,
) -> str:
    """
    Generate a markdown report for dependency scan results.

    Args:
        scan_result: Scan result from DependencyScanner
        batches: List of UpdateBatch objects
        project_dir: Project directory path
        ecosystems_filter: Optional list of ecosystems that were scanned

    Returns:
        Markdown formatted report string
    """

    lines = []

    # Header
    lines.append("# Dependency Update Report")
    lines.append("")
    lines.append(
        f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}"
    )
    lines.append(f"**Project**: `{project_dir}`")
    lines.append("")

    # Summary Section
    lines.append("## Summary")
    lines.append("")

    total_updates = len(scan_result.updates_available)
    security_updates = len(scan_result.security_updates)

    lines.append(f"- **Total Updates Available**: {total_updates}")
    lines.append(f"- **Security Updates**: {security_updates}")
    lines.append(f"- **Update Batches**: {len(batches)}")

    scanned_ecosystems = scan_result.scan_metadata.get("scanned_ecosystems", [])
    if scanned_ecosystems:
        lines.append(f"- **Ecosystems Scanned**: {', '.join(scanned_ecosystems)}")

    lines.append("")

    # Security Alerts Section
    if scan_result.security_updates:
        lines.append("## 🔒 Security Vulnerabilities")
        lines.append("")
        lines.append(
            f"Found **{security_updates}** package(s) with security vulnerabilities:"
        )
        lines.append("")

        # Render each severity group
        severity_levels = [
            ("critical", "🚨 Critical"),
            ("high", "🔴 High"),
            ("medium", "🟡 Medium"),
            ("low", "🟢 Low"),
        ]
        for severity_key, severity_heading in severity_levels:
            group = [
                u for u in scan_result.security_updates if u.severity == severity_key
            ]
            if group:
                lines.append(f"### {severity_heading}")
                for update in group:
                    lines.append(f"- **{update.name}** ({update.ecosystem})")
                    lines.append(
                        f"  - Current: `{update.current_version}` → Latest: `{update.latest_version}`"
                    )
                    if update.cve_ids:
                        lines.append(f"  - CVEs: {', '.join(update.cve_ids)}")
                    lines.append("")

    # Update Batches Section
    lines.append("## 📦 Recommended Update Batches")
    lines.append("")
    lines.append(
        "Updates are grouped by compatibility and risk level. "
        "Apply batches in order for smoothest updates."
    )
    lines.append("")

    for i, batch in enumerate(batches, 1):
        risk_icon = (
            "🔴"
            if batch.risk_level == "high"
            else "🟡"
            if batch.risk_level == "medium"
            else "🟢"
        )
        security_badge = " 🔒 **SECURITY**" if batch.is_security_batch else ""

        lines.append(f"### Batch {i}: `{batch.batch_id}` {security_badge}")
        lines.append("")
        lines.append(f"- **Risk Level**: {risk_icon} {batch.risk_level.title()}")
        lines.append(f"- **Priority**: {batch.priority}")
        lines.append(f"- **Ecosystem**: {batch.ecosystem}")
        lines.append(f"- **Packages**: {len(batch.packages)}")
        lines.append(f"- **Notes**: {batch.notes}")
        lines.append("")

        # List packages in batch (truncate if too many)
        lines.append("**Packages**:")
        for pkg in batch.packages[:10]:
            lines.append(f"  - {pkg}")
        if len(batch.packages) > 10:
            lines.append(f"  - ... and {len(batch.packages) - 10} more")
        lines.append("")

    # Detailed Package List Section
    lines.append("## 📋 All Available Updates")
    lines.append("")

    # Render update tables grouped by ecosystem
    ecosystem_groups = [
        (
            "Python Packages",
            [u for u in scan_result.updates_available if u.ecosystem == "python"],
        ),
        (
            "Node.js Packages",
            [
                u
                for u in scan_result.updates_available
                if u.ecosystem in ("node", "npm")
            ],
        ),
    ]

    for heading, updates in ecosystem_groups:
        if not updates:
            continue
        lines.append(f"### {heading}")
        lines.append("")
        lines.append("| Package | Current | Latest | Type | Security |")
        lines.append("|---------|---------|--------|------|----------|")
        for update in updates:
            security_badge = "🔒" if update.is_security else ""
            cve_list = ", ".join(update.cve_ids) if update.cve_ids else ""
            package_link = (
                f"[{update.name}]({update.changelog_url})"
                if update.changelog_url
                else update.name
            )
            lines.append(
                f"| {package_link} | "
                f"`{update.current_version}` | "
                f"`{update.latest_version}` | "
                f"{update.update_type} | "
                f"{security_badge} {cve_list} |"
            )
        lines.append("")

    # Scan Errors Section
    if scan_result.scan_errors:
        lines.append("## ⚠️ Scan Errors")
        lines.append("")
        lines.append("Some errors occurred during scanning:")
        lines.append("")
        for error in scan_result.scan_errors:
            lines.append(f"- {error}")
        lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append(
        "**Generated by**: [Auto-Claude Dependency Update Agent]"
        "(https://github.com/OBenner/Auto-Coding)"
    )
    lines.append("")

    return "\n".join(lines)


async def _create_pull_request_async(
    project_dir: Path,
    pr_title: str,
    pr_body: str,
) -> bool:
    """
    Create a pull request using GHClient with proper error handling and retries.

    Args:
        project_dir: Project directory
        pr_title: PR title
        pr_body: PR body content

    Returns:
        True if PR created successfully, False otherwise
    """
    try:
        # Detect default branch using git
        default_branch = "main"  # Default fallback
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "origin/HEAD"],
                cwd=project_dir,
                capture_output=True,
                text=True,
                timeout=5.0,
            )
            if result.returncode == 0:
                default_branch = result.stdout.strip().replace("origin/", "")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass  # Use fallback

        # Initialize GHClient
        client = GHClient(project_dir=project_dir)

        # Create PR
        pr_cmd = [
            "pr",
            "create",
            "--title",
            pr_title,
            "--body",
            pr_body,
            "--base",
            default_branch,
        ]

        print("🔧 Creating pull request...")
        result = await client.run(pr_cmd)

        print(f"\n✓ Pull request created successfully!")
        print(f"📝 {result.stdout.strip() if result.stdout else 'PR created'}")

        return True

    except GHTimeoutError as e:
        print(f"✗ GitHub CLI timed out: {e}")
        return False
    except GHCommandError as e:
        print(f"✗ Failed to create PR: {e}")
        print("\nNote: Branch has been pushed. You can create the PR manually via GitHub UI.")
        return False
    except Exception as e:
        print(f"✗ Unexpected error creating PR: {e}")
        print("\nNote: Branch has been pushed. You can create the PR manually via GitHub UI.")
        return False


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Automated dependency management and update orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current project for outdated dependencies
  %(prog)s --project .

  # Dry run with JSON output
  %(prog)s --project . --dry-run --format json

  # Generate update spec for security vulnerabilities
  %(prog)s --project . --generate-spec --security-only

  # Scan only Python dependencies
  %(prog)s --project . --ecosystems python
        """,
    )

    # Project configuration
    parser.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project directory to scan (default: current directory)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for reports (default: project/.auto-claude/dependency-reports)",
    )

    # Scan options
    parser.add_argument(
        "--ecosystems",
        type=str,
        help="Comma-separated list of ecosystems to scan (python, node)",
    )
    parser.add_argument(
        "--security-only",
        action="store_true",
        help="Only report dependencies with security vulnerabilities",
    )
    parser.add_argument(
        "--skip-dev",
        action="store_true",
        help="Skip development dependencies",
    )

    # Output options
    parser.add_argument(
        "--format",
        type=str,
        default="markdown",
        choices=["json", "markdown", "both"],
        help="Output format for reports (default: markdown)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run scan without making any changes",
    )

    # Spec generation
    parser.add_argument(
        "--generate-spec",
        action="store_true",
        help="Generate spec file for automated dependency updates",
    )
    parser.add_argument(
        "--batch",
        type=str,
        help="Generate spec for specific batch ID",
    )

    # PR creation
    parser.add_argument(
        "--create-pr",
        action="store_true",
        help="Create a pull request with dependency update proposals",
    )
    parser.add_argument(
        "--pr-title",
        type=str,
        default="Dependency Updates",
        help="Title for the PR (default: 'Dependency Updates')",
    )
    parser.add_argument(
        "--pr-branch",
        type=str,
        help="Branch name for the PR (default: auto-generated)",
    )

    # Advanced options
    parser.add_argument(
        "--model",
        type=str,
        default="sonnet",
        help="Model to use for AI analysis (haiku, sonnet, opus)",
    )
    parser.add_argument(
        "--thinking-level",
        type=str,
        default="medium",
        choices=["none", "low", "medium", "high", "ultrathink"],
        help="Thinking level for extended reasoning (default: medium)",
    )

    args = parser.parse_args()

    # Validate project directory
    project_dir = args.project.resolve()
    if not project_dir.exists():
        print(f"✗ Error: Project directory does not exist: {project_dir}")
        return 1

    # Load dependency updates configuration
    config = load_config(project_dir)
    if config:
        print("⚙️  Loaded dependency updates configuration")
    else:
        print("ℹ️  No dependency updates configuration found, using defaults")

    # Parse ecosystems filter
    ecosystems_filter = None
    if args.ecosystems:
        ecosystems_filter = [e.strip() for e in args.ecosystems.split(",")]
        valid_ecosystems = ["python", "node"]
        invalid = [e for e in ecosystems_filter if e not in valid_ecosystems]
        if invalid:
            print(f"✗ Error: Invalid ecosystems: {invalid}")
            print(f"Valid ecosystems: {valid_ecosystems}")
            return 1

    # Set output directory
    output_dir = args.output
    if not output_dir:
        output_dir = project_dir / ".auto-claude" / "dependency-reports"
    output_dir = output_dir.resolve()

    print("🔍 Dependency Update Scanner")
    print(f"📁 Project: {project_dir}")
    print(f"📊 Output: {output_dir}")
    if args.dry_run:
        print("🏃 Mode: Dry run (no changes)")
    if args.security_only:
        print("🔒 Filter: Security vulnerabilities only")
    if ecosystems_filter:
        print(f"🎯 Ecosystems: {', '.join(ecosystems_filter)}")
    print()

    # Import scanner and analyzer
    try:
        from analysis.analyzers.dependency_analyzer import DependencyAnalyzer
        from analysis.dependency_scanner import DependencyScanner
        from runners.github.gh_client import GHClient, GHCommandError, GHTimeoutError
    except ImportError as e:
        print(f"✗ Error: Failed to import dependency modules: {e}")
        return 1

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize scanner and analyzer
    print("⚙️  Initializing dependency scanner...")
    scanner = DependencyScanner()
    analyzer = DependencyAnalyzer(project_dir)

    # Determine which ecosystems to scan
    scan_python = ecosystems_filter is None or "python" in ecosystems_filter
    scan_node = ecosystems_filter is None or "node" in ecosystems_filter

    # Run dependency scan
    print("🔍 Scanning for outdated dependencies...")
    scan_result = scanner.scan(
        project_dir=project_dir,
        spec_dir=None,  # We'll save results manually
        scan_python=scan_python,
        scan_node=scan_node,
        check_security=True,
    )

    # Warn about --skip-dev (not yet implemented)
    if args.skip_dev:
        print(
            "⚠️  --skip-dev: Filtering dev dependencies is not yet implemented. "
            "All dependencies are included in the scan."
        )

    # Check for scan errors
    if scan_result.scan_errors:
        print(f"\n⚠️  Scan warnings ({len(scan_result.scan_errors)}):")
        for error in scan_result.scan_errors:
            print(f"  - {error}")
        print()

    # Filter security-only if requested
    updates_to_process = scan_result.updates_available
    if args.security_only:
        updates_to_process = scan_result.security_updates
        print("🔒 Filtered to security updates only")

    # Check if any updates were found
    if not updates_to_process:
        print("✓ No outdated dependencies found!")
        print()

        # Print OK for verification
        print("OK")
        return 0

    # Print summary
    print("\n📊 Scan Results:")
    print(f"  Total updates available: {len(scan_result.updates_available)}")
    print(f"  Security updates: {len(scan_result.security_updates)}")
    if scan_result.security_updates:
        critical = sum(
            1 for u in scan_result.security_updates if u.severity == "critical"
        )
        high = sum(1 for u in scan_result.security_updates if u.severity == "high")
        if critical > 0:
            print(f"    - Critical: {critical}")
        if high > 0:
            print(f"    - High: {high}")
    print(
        f"  Ecosystems scanned: {', '.join(scan_result.scan_metadata.get('scanned_ecosystems', []))}"
    )
    print()

    # Batch compatible updates (respect --security-only filter)
    print("🔄 Analyzing and batching compatible updates...")
    updates_as_dicts = [
        {
            "name": u.name,
            "current_version": u.current_version,
            "latest_version": u.latest_version,
            "update_type": u.update_type,
            "ecosystem": u.ecosystem,
            "is_security": u.is_security,
            "cve_ids": u.cve_ids,
            "severity": u.severity,
            "changelog_url": u.changelog_url,
        }
        for u in updates_to_process
    ]
    batches = analyzer.batch_updates(updates_as_dicts)

    print(f"\n📦 Update Batches ({len(batches)}):")
    for batch in batches:
        risk_icon = (
            "🔴"
            if batch.risk_level == "high"
            else "🟡"
            if batch.risk_level == "medium"
            else "🟢"
        )
        security_marker = " [SECURITY]" if batch.is_security_batch else ""
        print(
            f"  {risk_icon} {batch.batch_id}: {len(batch.packages)} package(s){security_marker}"
        )
        print(f"     Priority: {batch.priority} | Risk: {batch.risk_level}")
        print(f"     Packages: {', '.join(batch.packages[:5])}")
        if len(batch.packages) > 5:
            print(f"              ...and {len(batch.packages) - 5} more")
        print(f"     Notes: {batch.notes}")
        print()

    # Save results based on format
    if args.format in ["json", "both"]:
        print("💾 Saving JSON report...")
        json_file = output_dir / "dependency_report.json"
        report_data = scanner.to_dict(scan_result)
        report_data["batches"] = [
            {
                "batch_id": b.batch_id,
                "update_type": b.update_type,
                "ecosystem": b.ecosystem,
                "packages": b.packages,
                "risk_level": b.risk_level,
                "is_security_batch": b.is_security_batch,
                "priority": b.priority,
                "notes": b.notes,
            }
            for b in batches
        ]
        import json

        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        print(f"   Saved to: {json_file}")

    if args.format in ["markdown", "both"]:
        print("📝 Generating Markdown report...")
        markdown_file = output_dir / "dependency_report.md"
        markdown_content = _generate_markdown_report(
            scan_result=scan_result,
            batches=batches,
            project_dir=project_dir,
            ecosystems_filter=ecosystems_filter,
        )
        markdown_file.write_text(markdown_content, encoding="utf-8")
        print(f"   Saved to: {markdown_file}")

    # Spec generation
    if args.generate_spec:
        print("\n📝 Generating update spec...")

        # Import spec orchestrator
        from spec import SpecOrchestrator

        # Generate task description from scan results
        task_description = _generate_task_description(
            scan_result=scan_result,
            batches=batches,
            batch_id=args.batch,
        )

        # Resolve model shorthand to full model ID
        resolved_model = resolve_model_id(args.model)

        # Create spec orchestrator
        print("📋 Creating spec for dependency update...")
        orchestrator = SpecOrchestrator(
            project_dir=project_dir,
            task_description=task_description,
            model=resolved_model,
            thinking_level=args.thinking_level,
            complexity_override="simple",  # Dependency updates are typically simple
            use_ai_assessment=False,  # Skip AI assessment, use simple complexity
        )

        # Run spec creation
        try:
            success = asyncio.run(
                orchestrator.run(interactive=False, auto_approve=True)
            )

            if not success:
                print("✗ Spec creation failed")
                return 1

            print(f"\n✓ Spec created successfully: {orchestrator.spec_dir}")
            print("\nNext steps:")
            print(f"  1. Review the spec at: {orchestrator.spec_dir / 'spec.md'}")
            print(
                f"  2. Start the build: python run.py --spec {orchestrator.spec_dir.name}"
            )

        except KeyboardInterrupt:
            print("\n\nSpec creation interrupted.")
            return 1
        except Exception as e:
            print(f"\n\nError during spec creation: {e}")
            return 1

    # PR creation
    if args.create_pr:
        print("\n🔧 Creating pull request for dependency updates...")

        # Generate branch name if not provided
        if args.pr_branch:
            branch_name = args.pr_branch
        else:
            timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
            branch_name = f"dependency-updates-{timestamp}"

        # Create and checkout new branch
        try:
            print(f"📂 Creating branch: {branch_name}")
            subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=project_dir,
                check=True,
                capture_output=True,
                text=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to create branch: {e.stderr}")
            return 1

        # Create a commit with the report
        try:
            # Add the report files
            report_files = []
            if args.format in ["json", "both"]:
                json_file = output_dir / "dependency_report.json"
                if json_file.exists():
                    report_files.append(str(json_file))
            if args.format in ["markdown", "both"]:
                markdown_file = output_dir / "dependency_report.md"
                if markdown_file.exists():
                    report_files.append(str(markdown_file))

            if report_files:
                subprocess.run(
                    ["git", "add"] + report_files,
                    cwd=project_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                subprocess.run(
                    [
                        "git",
                        "commit",
                        "-m",
                        f"{args.pr_title}\n\nAutomated dependency update report generated by Auto-Claude.",
                    ],
                    cwd=project_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )

                # Push to remote
                print("📤 Pushing branch to remote...")
                subprocess.run(
                    ["git", "push", "-u", "origin", branch_name],
                    cwd=project_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                )
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to commit/push changes: {e.stderr}")
            return 1

        # Generate PR body
        pr_body_lines = [
            "## Automated Dependency Updates",
            "",
            f"**Generated**: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}",
            f"**Project**: `{project_dir}`",
            "",
        ]

        # Add summary
        total_updates = len(scan_result.updates_available)
        security_updates = len(scan_result.security_updates)
        pr_body_lines.extend([
            "### Summary",
            "",
            f"- **Total Updates**: {total_updates}",
            f"- **Security Updates**: {security_updates}",
            f"- **Update Batches**: {len(batches)}",
            "",
        ])

        # Add security alerts
        if scan_result.security_updates:
            pr_body_lines.extend([
                "### 🔒 Security Vulnerabilities",
                "",
                f"Found **{security_updates}** package(s) with security vulnerabilities:",
                "",
            ])
            for update in scan_result.security_updates[:5]:
                cve_info = f" (CVEs: {', '.join(update.cve_ids)})" if update.cve_ids else ""
                pr_body_lines.append(
                    f"- **{update.name}**: {update.current_version} → {update.latest_version}{cve_info}"
                )
            if len(scan_result.security_updates) > 5:
                pr_body_lines.append(
                    f"- ... and {len(scan_result.security_updates) - 5} more security updates"
                )
            pr_body_lines.append("")

        # Add batches
        pr_body_lines.extend([
            "### 📦 Update Batches",
            "",
        ])
        for i, batch in enumerate(batches, 1):
            risk_icon = (
                "🔴"
                if batch.risk_level == "high"
                else "🟡"
                if batch.risk_level == "medium"
                else "🟢"
            )
            security_badge = " 🔒 **SECURITY**" if batch.is_security_batch else ""
            pr_body_lines.extend([
                f"#### Batch {i}: `{batch.batch_id}` {security_badge}",
                f"- **Risk Level**: {risk_icon} {batch.risk_level.title()}",
                f"- **Priority**: {batch.priority}",
                f"- **Packages**: {len(batch.packages)}",
                "",
            ])

        # Add instructions
        pr_body_lines.extend([
            "### Next Steps",
            "",
            "1. Review the update batches and their risk levels",
            "2. Test the updates in a development environment",
            "3. Merge this PR to apply the updates",
            "",
            "---",
            "",
            "*Generated by [Auto-Claude Dependency Update Agent](https://github.com/OBenner/Auto-Coding)*",
        ])

        pr_body = "\n".join(pr_body_lines)

        # Create the PR using async GHClient
        pr_created = asyncio.run(
            _create_pull_request_async(
                project_dir=project_dir,
                pr_title=args.pr_title,
                pr_body=pr_body,
            )
        )

        if not pr_created:
            return 1

    print("\n✓ Dependency scan complete!")
    if not args.dry_run:
        print(f"📊 Report saved to: {output_dir}")

    # Print OK for verification
    print("OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
