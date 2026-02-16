#!/usr/bin/env python3
"""
Model Routing Analysis - Historical Task Distribution & Complexity
====================================================================

Analyzes historical spec runs to understand:
- Task complexity distribution (token counts, subtask counts, file counts)
- Agent type usage patterns (planner, coder, qa_reviewer, qa_fixer)
- Service type distribution (backend, frontend, web-backend)
- Phase type distribution (investigation, implementation, refactor)
- Token usage patterns per complexity tier

This data will inform 3-tier model routing strategy (Haiku/Sonnet/Opus).
"""

import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

# Add parent directory to path for imports
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from ui import bold, box, highlight, muted, print_key_value, print_status

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


# ============================================================================
# Data Structures
# ============================================================================


@dataclass
class SubtaskMetrics:
    """Metrics for a single subtask."""

    subtask_id: str
    description: str
    service: Literal["backend", "frontend", "web-backend"]
    phase_type: Literal["investigation", "implementation", "refactor"]
    status: Literal["pending", "in_progress", "completed", "failed"]
    files_to_modify: int
    files_to_create: int
    total_files: int = field(init=False)

    def __post_init__(self):
        self.total_files = self.files_to_modify + self.files_to_create


@dataclass
class SpecMetrics:
    """Aggregated metrics for a single spec."""

    spec_id: str
    feature: str
    workflow_type: Literal["investigation", "feature", "refactor", "bugfix"]
    total_subtasks: int
    completed_subtasks: int
    total_phases: int
    services: list[Literal["backend", "frontend", "web-backend"]]
    subtasks: list[SubtaskMetrics]
    completion_percentage: float = field(init=False)

    def __post_init__(self):
        self.completion_percentage = (
            (self.completed_subtasks / self.total_subtasks * 100)
            if self.total_subtasks > 0
            else 0
        )


@dataclass
class ComplexityTier:
    """Defines a complexity tier for model routing."""

    tier_name: str
    model: Literal["haiku", "sonnet", "opus"]
    description: str
    # Thresholds (inclusive)
    min_subtasks: int
    max_subtasks: int
    min_files: int
    max_files: int
    # Representative tasks
    examples: list[str] = field(default_factory=list)


# ============================================================================
# Analysis Functions
# ============================================================================


def parse_spec_directory(spec_dir: Path) -> SpecMetrics | None:
    """
    Parse a spec directory and extract metrics.

    Args:
        spec_dir: Path to spec directory containing implementation_plan.json

    Returns:
        SpecMetrics if parsing successful, None otherwise
    """
    plan_file = spec_dir / "implementation_plan.json"

    if not plan_file.exists():
        return None

    try:
        with open(plan_file, "r", encoding="utf-8") as f:
            plan_data = json.load(f)

        spec_id = spec_dir.name
        feature = plan_data.get("feature", "Unknown")
        workflow_type = plan_data.get("workflow_type", "feature")

        phases = plan_data.get("phases", [])
        total_subtasks = sum(len(p.get("subtasks", [])) for p in phases)
        total_phases = len(phases)

        services = set()
        subtasks = []
        completed_count = 0

        for phase in phases:
            phase_type = phase.get("type", "implementation")

            for subtask in phase.get("subtasks", []):
                subtask_id = subtask.get("id", "unknown")
                description = subtask.get("description", "")
                service = subtask.get("service", "backend")
                status = subtask.get("status", "pending")

                # Track completion
                if status == "completed":
                    completed_count += 1

                # File counts
                files_to_modify = subtask.get("files_to_modify", [])
                files_to_create = subtask.get("files_to_create", [])

                # Normalize to counts
                if isinstance(files_to_modify, list):
                    modify_count = len(files_to_modify)
                else:
                    modify_count = 0

                if isinstance(files_to_create, list):
                    create_count = len(files_to_create)
                else:
                    create_count = 0

                subtask_metrics = SubtaskMetrics(
                    subtask_id=subtask_id,
                    description=description,
                    service=service,
                    phase_type=phase_type,
                    status=status,
                    files_to_modify=modify_count,
                    files_to_create=create_count,
                )

                subtasks.append(subtask_metrics)
                services.add(service)

        return SpecMetrics(
            spec_id=spec_id,
            feature=feature,
            workflow_type=workflow_type,
            total_subtasks=total_subtasks,
            completed_subtasks=completed_count,
            total_phases=total_phases,
            services=list(services),
            subtasks=subtasks,
        )

    except Exception as e:
        logger.warning(f"Failed to parse {plan_file}: {e}")
        return None


def find_all_specs(root_dir: Path) -> list[Path]:
    """
    Find all spec directories with implementation_plan.json.

    Args:
        root_dir: Root directory to search

    Returns:
        List of spec directory paths
    """
    spec_dirs = []

    # Search in .auto-claude/specs
    specs_root = root_dir / ".auto-claude" / "specs"
    if specs_root.exists():
        for spec_dir in specs_root.iterdir():
            if spec_dir.is_dir() and (spec_dir / "implementation_plan.json").exists():
                spec_dirs.append(spec_dir)

    # Sort by spec ID (numeric prefix)
    spec_dirs.sort(key=lambda p: int(p.name.split("-")[0]) if p.name.split("-")[0].isdigit() else 0)

    return spec_dirs


def analyze_complexity_distribution(specs: list[SpecMetrics]) -> dict[str, Any]:
    """
    Analyze task complexity distribution across all specs.

    Args:
        specs: List of spec metrics

    Returns:
        Dictionary with complexity distribution statistics
    """
    # Subtask count distribution
    subtask_counts = [s.total_subtasks for s in specs if s.total_subtasks > 0]

    # File count distribution (per subtask)
    file_counts = []
    for spec in specs:
        for subtask in spec.subtasks:
            file_counts.append(subtask.total_files)

    # Service distribution
    service_counts: dict[str, int] = {}
    for spec in specs:
        for subtask in spec.subtasks:
            service_counts[subtask.service] = service_counts.get(subtask.service, 0) + 1

    # Workflow type distribution
    workflow_counts: dict[str, int] = {}
    for spec in specs:
        workflow_counts[spec.workflow_type] = workflow_counts.get(spec.workflow_type, 0) + 1

    # Phase type distribution
    phase_counts: dict[str, int] = {}
    for spec in specs:
        for subtask in spec.subtasks:
            phase_counts[subtask.phase_type] = phase_counts.get(subtask.phase_type, 0) + 1

    # Calculate percentiles
    def percentile(data: list[int], p: float) -> float:
        """Calculate percentile of sorted data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = int(len(sorted_data) * p / 100)
        return float(sorted_data[min(index, len(sorted_data) - 1)])

    return {
        "total_specs": len(specs),
        "total_subtasks": sum(s.total_subtasks for s in specs),
        "subtask_distribution": {
            "min": min(subtask_counts) if subtask_counts else 0,
            "max": max(subtask_counts) if subtask_counts else 0,
            "mean": sum(subtask_counts) / len(subtask_counts) if subtask_counts else 0.0,
            "median": percentile(subtask_counts, 50),
            "p25": percentile(subtask_counts, 25),
            "p75": percentile(subtask_counts, 75),
            "p90": percentile(subtask_counts, 90),
        },
        "file_distribution": {
            "min": min(file_counts) if file_counts else 0,
            "max": max(file_counts) if file_counts else 0,
            "mean": sum(file_counts) / len(file_counts) if file_counts else 0.0,
            "median": percentile(file_counts, 50),
            "p25": percentile(file_counts, 25),
            "p75": percentile(file_counts, 75),
            "p90": percentile(file_counts, 90),
        },
        "service_distribution": service_counts,
        "workflow_distribution": workflow_counts,
        "phase_distribution": phase_counts,
    }


def define_complexity_tiers(stats: dict[str, Any]) -> list[ComplexityTier]:
    """
    Define complexity tiers based on statistical analysis.

    Uses subtask count as the primary metric (more reliable) with file count
    as a secondary signal for tiebreaking when subtask counts are similar.

    Args:
        stats: Statistics from analyze_complexity_distribution()

    Returns:
        List of ComplexityTier definitions
    """
    subtask_dist = stats["subtask_distribution"]
    file_dist = stats["file_distribution"]

    # Simple tier: Bottom 33% of subtasks (1/3 of tasks)
    # Use min to ensure at least some room for simple tasks
    simple_max_subtasks = max(int(subtask_dist["median"]), 10)
    simple_max_files = int(file_dist["median"])

    # Complex tier: Top 33% of subtasks (1/3 of tasks)
    complex_min_subtasks = int(subtask_dist["p75"])
    complex_min_files = max(int(file_dist["median"]), 1)

    # Standard tier: Middle 33% of subtasks
    standard_min_subtasks = simple_max_subtasks + 1
    standard_max_subtasks = complex_min_subtasks - 1

    # Standard file threshold (>= median files)
    standard_min_files = 0  # Can be 0 files
    standard_max_files = max(int(file_dist["p75"]), 2)

    return [
        ComplexityTier(
            tier_name="Simple",
            model="haiku",
            description=(
                f"Low-complexity tasks with minimal scope. "
                f"≤{simple_max_subtasks} subtasks, ≤{simple_max_files} files per subtask on average."
            ),
            min_subtasks=0,
            max_subtasks=simple_max_subtasks,
            min_files=0,
            max_files=simple_max_files,
            examples=[
                "Bug fixes with clear reproduction steps",
                "Documentation updates",
                "Simple configuration changes",
                "Single-component refactors",
                "Investigation tasks with narrow scope",
            ],
        ),
        ComplexityTier(
            tier_name="Standard",
            model="sonnet",
            description=(
                f"Medium-complexity tasks requiring moderate coordination. "
                f"{standard_min_subtasks}-{standard_max_subtasks} subtasks, "
                f"{standard_min_files}-{standard_max_files} files per subtask on average."
            ),
            min_subtasks=standard_min_subtasks,
            max_subtasks=standard_max_subtasks,
            min_files=standard_min_files,
            max_files=standard_max_files,
            examples=[
                "Feature implementation across 2-3 components",
                "API endpoint additions",
                "Multi-file refactors",
                "Integration with external services",
                "Medium-scale investigation tasks",
            ],
        ),
        ComplexityTier(
            tier_name="Complex",
            model="opus",
            description=(
                f"High-complexity tasks requiring extensive coordination. "
                f"≥{complex_min_subtasks} subtasks, ≥{complex_min_files} files per subtask on average."
            ),
            min_subtasks=complex_min_subtasks,
            max_subtasks=9999,
            min_files=complex_min_files,
            max_files=9999,
            examples=[
                "Architecture redesigns",
                "Cross-platform feature development",
                "Major refactors with >10 files",
                "Complex state management changes",
                "Multi-service integrations",
            ],
        ),
    ]


def classify_spec(spec: SpecMetrics, tiers: list[ComplexityTier]) -> ComplexityTier:
    """
    Classify a spec into a complexity tier.

    Uses subtask count as the primary metric. File count is used as a secondary
    signal when subtask counts are at tier boundaries.

    Args:
        spec: Spec metrics
        tiers: List of complexity tiers (ordered simple -> complex)

    Returns:
        The matching ComplexityTier
    """
    # Primary classification by subtask count
    for tier in tiers:
        if tier.min_subtasks <= spec.total_subtasks <= tier.max_subtasks:
            return tier

    # Edge case: very high subtask count
    if spec.total_subtasks > tiers[-1].max_subtasks:
        return tiers[-1]

    # Default to standard if no match
    return tiers[1]


def generate_markdown_report(
    specs: list[SpecMetrics],
    stats: dict[str, Any],
    tiers: list[ComplexityTier],
    output_path: Path,
) -> None:
    """
    Generate a comprehensive markdown analysis report.

    Args:
        specs: List of spec metrics
        stats: Statistics dictionary
        tiers: List of complexity tiers
        output_path: Path to write markdown report
    """
    lines = []

    # Header
    lines.append("# Model Routing Analysis - Historical Task Distribution")
    lines.append("")
    lines.append(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    lines.append("## Executive Summary")
    lines.append("")
    lines.append(
        f"This analysis examines **{stats['total_specs']} completed specs** "
        f"with **{stats['total_subtasks']} total subtasks** to inform "
        f"3-tier model routing (Haiku/Sonnet/Opus) for API cost reduction."
    )
    lines.append("")

    # Overall Statistics
    lines.append("## Overall Statistics")
    lines.append("")
    lines.append("### Subtask Distribution")
    lines.append("")
    subtask_dist = stats["subtask_distribution"]
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Specs | {stats['total_specs']} |")
    lines.append(f"| Total Subtasks | {stats['total_subtasks']} |")
    lines.append(f"| Min Subtasks/Spec | {subtask_dist['min']} |")
    lines.append(f"| Max Subtasks/Spec | {subtask_dist['max']} |")
    lines.append(f"| Mean Subtasks/Spec | {subtask_dist['mean']:.1f} |")
    lines.append(f"| Median Subtasks/Spec | {subtask_dist['median']:.0f} |")
    lines.append(f"| 25th Percentile | {subtask_dist['p25']:.0f} |")
    lines.append(f"| 75th Percentile | {subtask_dist['p75']:.0f} |")
    lines.append(f"| 90th Percentile | {subtask_dist['p90']:.0f} |")
    lines.append("")

    # File Distribution
    lines.append("### File Distribution (Per Subtask)")
    lines.append("")
    file_dist = stats["file_distribution"]
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Min Files/Subtask | {file_dist['min']} |")
    lines.append(f"| Max Files/Subtask | {file_dist['max']} |")
    lines.append(f"| Mean Files/Subtask | {file_dist['mean']:.1f} |")
    lines.append(f"| Median Files/Subtask | {file_dist['median']:.0f} |")
    lines.append(f"| 25th Percentile | {file_dist['p25']:.0f} |")
    lines.append(f"| 75th Percentile | {file_dist['p75']:.0f} |")
    lines.append(f"| 90th Percentile | {file_dist['p90']:.0f} |")
    lines.append("")

    # Service Distribution
    lines.append("### Service Distribution")
    lines.append("")
    service_dist = stats["service_distribution"]
    total_subtasks = sum(service_dist.values())
    lines.append(f"| Service | Subtasks | Percentage |")
    lines.append(f"|---------|----------|------------|")
    for service, count in sorted(service_dist.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_subtasks * 100) if total_subtasks > 0 else 0
        lines.append(f"| {service} | {count} | {percentage:.1f}% |")
    lines.append("")

    # Workflow Distribution
    lines.append("### Workflow Type Distribution")
    lines.append("")
    workflow_dist = stats["workflow_distribution"]
    total_specs = sum(workflow_dist.values())
    lines.append(f"| Workflow Type | Specs | Percentage |")
    lines.append(f"|---------------|-------|------------|")
    for workflow, count in sorted(workflow_dist.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_specs * 100) if total_specs > 0 else 0
        lines.append(f"| {workflow} | {count} | {percentage:.1f}% |")
    lines.append("")

    # Phase Distribution
    lines.append("### Phase Type Distribution")
    lines.append("")
    phase_dist = stats["phase_distribution"]
    total_phase_subtasks = sum(phase_dist.values())
    lines.append(f"| Phase Type | Subtasks | Percentage |")
    lines.append(f"|------------|----------|------------|")
    for phase, count in sorted(phase_dist.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / total_phase_subtasks * 100) if total_phase_subtasks > 0 else 0
        lines.append(f"| {phase} | {count} | {percentage:.1f}% |")
    lines.append("")

    # Complexity Tier Definitions
    lines.append("## Complexity Tier Definitions")
    lines.append("")
    lines.append(
        "Based on statistical analysis of historical data, we define three complexity tiers:"
    )
    lines.append("")

    for tier in tiers:
        lines.append(f"### {tier.tier_name} Tier → `{tier.model}`")
        lines.append("")
        lines.append(f"**Model:** Claude {tier.model.title()}")
        lines.append("")
        lines.append(f"**Description:** {tier.description}")
        lines.append("")
        lines.append("**Thresholds:**")
        lines.append(f"- Subtasks: {tier.min_subtasks}-{tier.max_subtasks}")
        lines.append(f"- Files: {tier.min_files}-{tier.max_files}")
        lines.append("")
        lines.append("**Example Tasks:**")
        for example in tier.examples:
            lines.append(f"- {example}")
        lines.append("")

    # Spec Classification
    lines.append("## Spec Classification by Tier")
    lines.append("")

    tier_counts: dict[str, int] = {}
    tier_specs: dict[str, list[SpecMetrics]] = {}

    for spec in specs:
        tier = classify_spec(spec, tiers)
        tier_counts[tier.tier_name] = tier_counts.get(tier.tier_name, 0) + 1
        tier_specs.setdefault(tier.tier_name, []).append(spec)

    lines.append(f"| Tier | Specs | Percentage |")
    lines.append(f"|------|-------|------------|")
    total_classified = sum(tier_counts.values())
    for tier_name in ["Simple", "Standard", "Complex"]:
        count = tier_counts.get(tier_name, 0)
        percentage = (count / total_classified * 100) if total_classified > 0 else 0
        lines.append(f"| {tier_name} | {count} | {percentage:.1f}% |")
    lines.append("")

    # Detailed Spec Breakdown
    lines.append("## Detailed Spec Breakdown")
    lines.append("")

    for tier in tiers:
        tier_name = tier.tier_name
        if tier_name not in tier_specs:
            continue

        lines.append(f"### {tier_name} Tier Specs (→ {tier.model})")
        lines.append("")
        lines.append(f"| Spec ID | Feature | Subtasks | Files | Services |")
        lines.append(f"|---------|---------|----------|-------|----------|")

        for spec in sorted(tier_specs[tier_name], key=lambda s: s.total_subtasks):
            total_files = sum(s.total_files for s in spec.subtasks)
            services_str = ", ".join(spec.services)
            lines.append(
                f"| {spec.spec_id} | {spec.feature[:50]} | {spec.total_subtasks} | {total_files} | {services_str} |"
            )
        lines.append("")

    # Key Findings
    lines.append("## Key Findings")
    lines.append("")

    findings = []

    # Finding 1: Complexity distribution
    simple_pct = (tier_counts.get("Simple", 0) / total_classified * 100) if total_classified > 0 else 0
    standard_pct = (tier_counts.get("Standard", 0) / total_classified * 100) if total_classified > 0 else 0
    complex_pct = (tier_counts.get("Complex", 0) / total_classified * 100) if total_classified > 0 else 0

    findings.append(
        f"**Complexity Distribution:** {simple_pct:.0f}% simple, {standard_pct:.0f}% standard, {complex_pct:.0f}% complex tasks"
    )

    # Finding 2: Service concentration
    backend_pct = (service_dist.get("backend", 0) / total_subtasks * 100) if total_subtasks > 0 else 0
    findings.append(
        f"**Service Concentration:** {backend_pct:.0f}% of subtasks target backend service"
    )

    # Finding 3: Workflow patterns
    if workflow_dist.get("feature", 0) > 0:
        feature_pct = (workflow_dist.get("feature", 0) / total_specs * 100) if total_specs > 0 else 0
        findings.append(
            f"**Workflow Pattern:** {feature_pct:.0f}% of specs are feature development tasks"
        )

    # Finding 4: Median complexity
    findings.append(
        f"**Median Complexity:** {subtask_dist['median']:.0f} subtasks, {file_dist['median']:.0f} files per spec"
    )

    for i, finding in enumerate(findings, 1):
        lines.append(f"{i}. {finding}")
    lines.append("")

    # Next Steps
    lines.append("## Next Steps")
    lines.append("")
    lines.append("1. **Validate Complexity Metrics** - Review if subtask/file counts accurately reflect task complexity")
    lines.append("2. **Calculate Cost Savings** - Run cost simulation based on tier distribution and model pricing")
    lines.append("3. **Define Routing Logic** - Implement complexity-based model selection in `core/client.py`")
    lines.append("4. **Quality Validation** - Test Haiku on simple tasks to ensure quality is maintained")
    lines.append("")

    # Appendices
    lines.append("---")
    lines.append("")
    lines.append("## Appendix: Raw Data")
    lines.append("")
    lines.append("### All Spec Metrics")
    lines.append("")
    lines.append(f"| Spec ID | Feature | Workflow | Subtasks | Phases | Services | Complete |")
    lines.append(f"|---------|---------|----------|----------|--------|----------|----------|")

    for spec in specs:
        services_str = ", ".join(spec.services)
        lines.append(
            f"| {spec.spec_id} | {spec.feature[:40]} | {spec.workflow_type} | {spec.total_subtasks} | {spec.total_phases} | {services_str} | {spec.completion_percentage:.0f}% |"
        )
    lines.append("")

    # Write to file
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    logger.info(f"Report generated: {output_path}")


# ============================================================================
# Main Analysis
# ============================================================================


def main() -> int:
    """Run the complete analysis pipeline."""
    print()
    print_status("Starting Model Routing Analysis...", "progress")
    print()

    # Find all spec directories
    # When run from apps/backend, cwd is the worktree root
    # If run from elsewhere, resolve from script location
    cwd = Path.cwd()
    if (cwd / ".auto-claude" / "specs").exists():
        root_dir = cwd
    else:
        # Script is in apps/backend/experiments/, go up to worktree root
        root_dir = Path(__file__).parent.parent.parent.parent

    spec_dirs = find_all_specs(root_dir)

    if not spec_dirs:
        print_status("No spec directories found", "error")
        return 1

    print_key_value("Specs found", len(spec_dirs))
    print()

    # Parse all specs
    print_status("Parsing spec data...", "progress")
    specs = []
    for spec_dir in spec_dirs:
        metrics = parse_spec_directory(spec_dir)
        if metrics:
            specs.append(metrics)

    if not specs:
        print_status("No valid specs found", "error")
        return 1

    print_key_value("Valid specs", len(specs))
    print_key_value("Total subtasks", sum(s.total_subtasks for s in specs))
    print()

    # Analyze complexity distribution
    print_status("Analyzing complexity distribution...", "progress")
    stats = analyze_complexity_distribution(specs)
    print()

    # Define complexity tiers
    print_status("Defining complexity tiers...", "progress")
    tiers = define_complexity_tiers(stats)
    print()

    for tier in tiers:
        print_key_value(f"{tier.tier_name} Tier → {tier.model}", tier.description)

    print()

    # Generate report
    print_status("Generating analysis report...", "progress")
    output_path = root_dir / ".auto-claude" / "specs" / "173-integrate-claude-flow-into-project" / "MODEL_ROUTING_ANALYSIS.md"
    generate_markdown_report(specs, stats, tiers, output_path)

    print()
    content = [
        bold(f"{'✓' if (spec_count := len(specs)) > 0 else '✗'} ANALYSIS COMPLETE"),
        "",
        f"Specs analyzed: {highlight(str(spec_count))}",
        f"Subtasks analyzed: {highlight(str(stats['total_subtasks']))}",
        "",
        muted(f"Report: {output_path.relative_to(root_dir)}"),
    ]
    print(box(content, width=70, style="heavy"))
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
