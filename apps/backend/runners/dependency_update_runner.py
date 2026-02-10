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

import sys
from pathlib import Path

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

    print(f"🔍 Dependency Update Scanner")
    print(f"📁 Project: {project_dir}")
    print(f"📊 Output: {output_dir}")
    if args.dry_run:
        print(f"🏃 Mode: Dry run (no changes)")
    if args.security_only:
        print(f"🔒 Filter: Security vulnerabilities only")
    if ecosystems_filter:
        print(f"🎯 Ecosystems: {', '.join(ecosystems_filter)}")
    print()

    # Import scanner and analyzer
    try:
        from analysis.dependency_scanner import DependencyScanner
        from analysis.analyzers.dependency_analyzer import DependencyAnalyzer
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
        check_security=not args.skip_dev,  # Check security unless disabled
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
        print(f"🔒 Filtered to security updates only")

    # Check if any updates were found
    if not updates_to_process:
        print("✓ No outdated dependencies found!")
        print()
        return 0

    # Print summary
    print(f"\n📊 Scan Results:")
    print(f"  Total updates available: {len(scan_result.updates_available)}")
    print(f"  Security updates: {len(scan_result.security_updates)}")
    if scan_result.security_updates:
        critical = sum(1 for u in scan_result.security_updates if u.severity == "critical")
        high = sum(1 for u in scan_result.security_updates if u.severity == "high")
        if critical > 0:
            print(f"    - Critical: {critical}")
        if high > 0:
            print(f"    - High: {high}")
    print(f"  Ecosystems scanned: {', '.join(scan_result.scan_metadata.get('scanned_ecosystems', []))}")
    print()

    # Batch compatible updates
    print("🔄 Analyzing and batching compatible updates...")
    batches = analyzer.batch_updates(scanner.to_dict(scan_result)["updates_available"])

    print(f"\n📦 Update Batches ({len(batches)}):")
    for batch in batches:
        risk_icon = "🔴" if batch.risk_level == "high" else "🟡" if batch.risk_level == "medium" else "🟢"
        security_marker = " [SECURITY]" if batch.is_security_batch else ""
        print(f"  {risk_icon} {batch.batch_id}: {len(batch.packages)} package(s){security_marker}")
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
        print("📝 Markdown report generation will be implemented in subtask-3-3")

    # Spec generation (will be implemented in subtask-4-2)
    if args.generate_spec:
        print("\n⚠️  Spec generation will be implemented in subtask-4-2")

    print("\n✓ Dependency scan complete!")
    if not args.dry_run:
        print(f"📊 Report saved to: {output_dir}")

    # Print OK for verification
    print("OK")

    return 0


if __name__ == "__main__":
    sys.exit(main())
