"""
Security Commands
=================

CLI commands for security auditing (run security audit, generate reports)
"""

import sys
from pathlib import Path

# Ensure parent directory is in path for imports (before other imports)
_PARENT_DIR = Path(__file__).parent.parent
if str(_PARENT_DIR) not in sys.path:
    sys.path.insert(0, str(_PARENT_DIR))

from agents.security_auditor import SecurityAuditAgent
from ui import (
    Icons,
    divider,
    icon,
    info,
    muted,
    print_header,
    success,
    warning,
)

from .utils import print_banner


def handle_security_audit_command(
    project_dir: Path,
    spec_dir: Path | None = None,
    output_format: str = "both",
    verbose: bool = False,
) -> None:
    """
    Handle the --security-audit command.

    Runs a comprehensive security audit on the project, scanning for:
    - OWASP Top 10 vulnerabilities
    - Dependency vulnerabilities
    - Secrets in code
    - Authentication flow issues

    Args:
        project_dir: Project directory path
        spec_dir: Optional spec directory for context-aware scanning
        output_format: Output format - "json", "markdown", or "both" (default)
        verbose: Enable verbose output
    """
    print_banner()
    print(f"\n{icon(Icons.SECURITY)} Security Audit\n")

    if verbose:
        print(muted(f"Project: {project_dir}"))
        if spec_dir:
            print(muted(f"Spec: {spec_dir.name}"))
        print(muted(f"Output: {output_format}"))
        print()

    print(info(f"{icon(Icons.INFO)} Starting comprehensive security audit..."))
    print()

    # Create security auditor
    auditor = SecurityAuditAgent()

    # Run full audit
    try:
        print_header("Running Security Scans")
        print()

        print(f"{icon(Icons.SEARCH)} OWASP Top 10 vulnerability scanning...")
        print(f"{icon(Icons.SEARCH)} Dependency vulnerability checking...")
        print(f"{icon(Icons.SEARCH)} Secret detection...")
        print(f"{icon(Icons.SEARCH)} Authentication flow analysis...")
        print()

        # Run the audit
        report = auditor.run_full_audit(
            project_dir=project_dir,
            spec_dir=spec_dir,
        )

        # Display summary
        print(divider())
        print_header("Security Audit Summary")
        print()

        # Show findings by severity
        summary = report.summary_counts
        total_findings = sum(summary.values())

        if total_findings == 0:
            print(success(f"{icon(Icons.SUCCESS)} No security issues found!"))
            print()
        else:
            print(f"Total Findings: {total_findings}")
            print()

            if summary.get("critical", 0) > 0:
                print(warning(f"  Critical: {summary['critical']}"))
            if summary.get("high", 0) > 0:
                print(warning(f"  High:     {summary['high']}"))
            if summary.get("medium", 0) > 0:
                print(info(f"  Medium:   {summary['medium']}"))
            if summary.get("low", 0) > 0:
                print(muted(f"  Low:      {summary['low']}"))
            if summary.get("info", 0) > 0:
                print(muted(f"  Info:     {summary['info']}"))
            print()

        # Show OWASP coverage
        if report.owasp_coverage:
            print(divider())
            print_header("OWASP Top 10 Coverage")
            print()
            for category in report.owasp_coverage:
                print(f"  {icon(Icons.CHECK)} {category}")
            print()

        # Save report
        print(divider())
        print_header("Saving Report")
        print()

        # Determine output directory
        output_dir = spec_dir if spec_dir else project_dir / ".auto-claude"
        output_dir.mkdir(parents=True, exist_ok=True)

        # Save in requested format(s)
        if output_format in ("json", "both"):
            json_path = output_dir / "security_audit_report.json"
            report.to_json_file(json_path)
            print(success(f"{icon(Icons.SAVE)} JSON report saved: {json_path}"))

        if output_format in ("markdown", "both"):
            md_path = output_dir / "security_audit_report.md"
            report.to_markdown_file(md_path)
            print(success(f"{icon(Icons.SAVE)} Markdown report saved: {md_path}"))

        print()

        # Show critical findings
        critical_findings = report.get_critical_findings()
        if critical_findings:
            print(divider())
            print_header("Critical Findings")
            print()

            for finding in critical_findings[:5]:  # Show first 5
                print(warning(f"  {icon(Icons.WARNING)} {finding.title}"))
                if finding.file:
                    print(muted(f"    File: {finding.file}"))
                if finding.description:
                    desc_preview = finding.description[:80]
                    if len(finding.description) > 80:
                        desc_preview += "..."
                    print(muted(f"    {desc_preview}"))
                print()

            if len(critical_findings) > 5:
                print(muted(f"    ... and {len(critical_findings) - 5} more"))
                print()

        # Final summary
        print(divider())
        if report.has_blocking_issues():
            print(
                warning(f"{icon(Icons.WARNING)} Security audit found blocking issues.")
            )
            print(muted("Review the report for remediation guidance."))
        else:
            print(success(f"{icon(Icons.SUCCESS)} Security audit complete."))
            if total_findings > 0:
                print(muted("Review the report for recommendations."))

        print()

    except Exception as e:
        print()
        print(warning(f"{icon(Icons.WARNING)} Security audit failed: {e}"))
        if verbose:
            import traceback

            print()
            print(muted("Traceback:"))
            print(muted(traceback.format_exc()))
        print()
        sys.exit(1)
