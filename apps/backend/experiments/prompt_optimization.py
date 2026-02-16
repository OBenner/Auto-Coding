#!/usr/bin/env python3
"""
Prompt Optimization Prototype

This script prototypes Phase 1 prompt optimizations for Auto-Claude agent prompts.
It measures token reduction and validates that optimizations preserve quality.

Phase 1 Optimizations (Quick Wins):
1. Extract shared content to reference documents
2. Simplify bash command examples
3. Reduce meta-instructions
4. Condense validation phases

Based on research from:
- PROMPT_ANALYSIS.md - Token inventory and optimization opportunities
- PROMPT_RESEARCH.md - Optimization strategies and API compatibility

Usage:
    cd apps/backend
    python experiments/prompt_optimization.py

Expected output:
    Token reduction: 10-15% without quality loss
"""

import os
import re
import json
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass, asdict


@dataclass
class PromptMetrics:
    """Metrics for a prompt before/after optimization."""
    path: str
    original_tokens: int
    optimized_tokens: int
    reduction_pct: float
    techniques: List[str]


class PromptOptimizer:
    """Applies Phase 1 optimizations to agent prompts."""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self.optimization_log = []

    def estimate_tokens(self, text: str) -> int:
        """
        Estimate token count using 4 chars/token heuristic.

        For more accurate counting, use claudetic library:
        pip install claudetic
        from claudetic import count_tokens
        """
        return len(text) // 4

    def optimize_prompt(self, prompt_path: str) -> PromptMetrics:
        """
        Optimize a single prompt file and return metrics.

        Args:
            prompt_path: Relative path to prompt file (e.g., "prompts/coder.md")

        Returns:
            PromptMetrics with before/after token counts and reduction percentage
        """
        full_path = self.prompts_dir / prompt_path

        if not full_path.exists():
            raise FileNotFoundError(f"Prompt not found: {full_path}")

        # Read original prompt
        with open(full_path, 'r', encoding='utf-8') as f:
            original_content = f.read()

        original_tokens = self.estimate_tokens(original_content)

        # Apply optimizations
        optimized_content = self._apply_phase1_optimizations(original_content, prompt_path)

        optimized_tokens = self.estimate_tokens(optimized_content)

        # Calculate metrics
        reduction_pct = ((original_tokens - optimized_tokens) / original_tokens) * 100

        # Track techniques used
        techniques = self._get_techniques_used(original_content, optimized_content)

        metrics = PromptMetrics(
            path=prompt_path,
            original_tokens=original_tokens,
            optimized_tokens=optimized_tokens,
            reduction_pct=round(reduction_pct, 1),
            techniques=techniques
        )

        # Log the optimization
        self.optimization_log.append(metrics)

        return metrics

    def _apply_phase1_optimizations(self, content: str, prompt_path: str) -> str:
        """
        Apply Phase 1 optimization techniques to prompt content.

        Techniques:
        1. Extract shared content (replace with brief summaries + references)
        2. Simplify bash command examples
        3. Reduce meta-instructions
        4. Condense validation phases (for qa_reviewer)
        5. Remove verbose examples and demonstrations
        """
        optimized = content

        # Technique 1: Extract shared content
        optimized = self._extract_shared_content(optimized)

        # Technique 2: Simplify bash examples
        optimized = self._simplify_bash_examples(optimized)

        # Technique 3: Reduce meta-instructions
        optimized = self._reduce_meta_instructions(optimized)

        # Technique 4: Condense validation phases (qa_reviewer specific)
        if "qa_reviewer" in prompt_path:
            optimized = self._condense_validation_phases(optimized)

        # Technique 5: Remove verbose examples
        optimized = self._remove_verbose_examples(optimized)

        return optimized

    def _extract_shared_content(self, content: str) -> str:
        """
        Extract duplicated sections and replace with brief summaries + references.

        Sections to extract:
        - PATH CONFUSION PREVENTION (appears in coder, planner, qa_fixer)
        - Workflow type documentation (appears in coder, planner)
        - TOKEN EFFICIENCY sections (appears in coder, qa_reviewer)
        """
        optimized = content

        # Replace PATH CONFUSION PREVENTION with brief summary
        # This section is very long in coder.md (~800 lines)
        if "## 🚨 CRITICAL: PATH CONFUSION PREVENTION" in optimized:
            # Find the section and replace it
            start = optimized.find("## 🚨 CRITICAL: PATH CONFUSION PREVENTION")
            if start != -1:
                # Find the next major section
                end = optimized.find("\n## ", start + 100)
                if end != -1:
                    before = optimized[:start]
                    after = optimized[end:]
                    replacement = '''## 🚨 CRITICAL: Path Confusion Prevention

**Always check `pwd` before git operations in monorepos.**
See: `docs/prompts/shared/path_management.md`

**Quick check:**
1. Run `pwd` to verify location
2. Use paths relative to current directory
3. Never use absolute paths in monorepos

'''
                    optimized = before + replacement + after

        # Replace TOKEN EFFICIENCY with brief summary
        if "## TOKEN EFFICIENCY" in optimized:
            start = optimized.find("## TOKEN EFFICIENCY")
            if start != -1:
                end = optimized.find("\n## ", start + 100)
                if end != -1:
                    before = optimized[:start]
                    after = optimized[end:]
                    replacement = '''## OUTPUT GUIDELINES

- Lead with action, not explanation
- Bullet points over paragraphs
- One verification line, not verbose confirmations

'''
                    optimized = before + replacement + after

        return optimized

    def _simplify_bash_examples(self, content: str) -> str:
        """
        Simplify verbose bash command examples.

        Strategy:
        - Replace multi-line examples with concise templates
        - Use placeholders like [test_command], [build_command]
        - Keep essential commands, remove verbose output
        """
        optimized = content

        # Remove verbose expected output from code blocks
        # Pattern: ```bash...``` followed by Expected output: ```...```
        lines = optimized.split('\n')
        i = 0
        while i < len(lines):
            line = lines[i]
            # Look for expected output sections
            if 'Expected output:' in line or 'Expected:' in line:
                # Skip this line and the code block that follows
                j = i + 1
                while j < len(lines) and not lines[j].strip().startswith('```'):
                    j += 1
                if j < len(lines):
                    # Remove lines from i to j (inclusive of the closing ```)
                    lines = lines[:i] + lines[j+1:]
                    # Don't increment i, recheck current line
                    continue
            i += 1

        optimized = '\n'.join(lines)

        # Condense multi-line code blocks with repeated patterns
        # Replace verbose cd + activate patterns
        verbose_pattern = "cd apps/backend\nsource .venv/bin/activate"
        if verbose_pattern in optimized:
            optimized = optimized.replace(verbose_pattern, "[activate_and_cd]")

        # Simplify verbose examples that show command + output
        # Keep only the essential commands
        optimized = re.sub(
            r'(```bash\n)(.*?)(```)\n\n(Expected|Output):?\n\n```.*?```',
            r'\1\2\3',
            optimized,
            flags=re.DOTALL
        )

        return optimized

    def _reduce_meta_instructions(self, content: str) -> str:
        """
        Reduce verbose meta-instructions about instructions.

        Meta-instructions ironically consume tokens while telling agents to be concise.
        """
        optimized = content

        # Remove "WHY X EXISTS" sections entirely
        lines = optimized.split('\n')
        filtered_lines = []
        skip = False

        for i, line in enumerate(lines):
            # Check if this line starts a "Why..." section
            if '**Why' in line and ('exists:' in line.lower() or 'important' in line.lower()):
                skip = True
                continue

            # Check if we should stop skipping
            if skip and line.strip().startswith('##'):
                skip = False

            # Keep the line if we're not skipping
            if not skip:
                filtered_lines.append(line)

        optimized = '\n'.join(filtered_lines)

        # Condense verbose "KEY REMINDERS" sections
        # If the section is very long (> 15 lines), condense it
        if '## KEY REMINDERS' in optimized or '## CRITICAL REMINDERS' in optimized:
            for section_name in ['## KEY REMINDERS', '## CRITICAL REMINDERS']:
                if section_name in optimized:
                    start = optimized.find(section_name)
                    if start != -1:
                        end = optimized.find("\n## ", start + 50)
                        if end == -1:
                            end = len(optimized)

                        section = optimized[start:end]
                        lines_in_section = section.count('\n')

                        # If section is very long (> 15 lines), condense
                        if lines_in_section > 15:
                            # Extract just the bullet points, skip verbose explanations
                            condensed = section_name + "\n\n"
                            for line in section.split('\n'):
                                if line.strip().startswith('- ') or line.strip().startswith('*'):
                                    condensed += line + "\n"
                                elif line.strip().startswith('##'):
                                    continue
                                elif not line.strip():
                                    condensed += "\n"

                            optimized = optimized[:start] + condensed + optimized[end:]

        return optimized

    def _condense_validation_phases(self, content: str) -> str:
        """
        Condense qa_reviewer validation phases.

        Strategy:
        - Merge generated test validation subsections
        - Simplify coverage validation to checklist
        - Keep critical path requirements (100% coverage mandatory)
        """
        optimized = content

        # Condense generated test validation (6 subsections -> 1 checklist)
        if "### **Generated Test Validation**" in optimized:
            start = optimized.find("### **Generated Test Validation**")
            if start != -1:
                end = optimized.find("\n###", start + 50)
                if end == -1:
                    end = optimized.find("\n## ", start + 50)
                if end != -1:
                    before = optimized[:start]
                    after = optimized[end:]
                    replacement = '''### **Generated Test Validation**

- [ ] Test type matches requirements (unit/integration/e2e)
- [ ] Tests cover happy path and edge cases
- [ ] Test data includes valid/invalid inputs
- [ ] Assertions verify behavior, not implementation
- [ ] Test names clearly describe what is tested
- [ ] No test duplication

'''
                    optimized = before + replacement + after

        # Condense coverage validation (8 subsections -> checklist)
        if "### **Coverage Validation**" in optimized:
            start = optimized.find("### **Coverage Validation**")
            if start != -1:
                end = optimized.find("\n###", start + 50)
                if end == -1:
                    end = optimized.find("\n## ", start + 50)
                if end != -1:
                    before = optimized[:start]
                    after = optimized[end:]
                    replacement = '''### **Coverage Validation**

- [ ] New code: 100% coverage mandatory
- [ ] Modified code: Maintain or improve coverage
- [ ] Critical paths: Full branch coverage
- [ ] Edge cases: Valid/invalid inputs tested
- [ ] Error paths: Exception handling verified

**Thresholds:** <80% reject | 80-99% accept w/ improvements | 100% commend

Use: `pytest --cov=app --cov-report=term-missing`

'''
                    optimized = before + replacement + after

        return optimized

    def _remove_verbose_examples(self, content: str) -> str:
        """
        Remove verbose examples and demonstrations while keeping core instructions.

        Strategy:
        - Keep one example per concept (not 3-4 similar examples)
        - Remove lengthy code demonstrations
        - Condense multi-step examples to summaries
        """
        optimized = content

        # Remove lengthy "Good vs Bad" pattern comparisons
        # Keep just the "Good" pattern, skip verbose "Bad" examples
        optimized = re.sub(
            r'❌ DON\'T:.*?(?=\n\n\*|```|##)',
            '',
            optimized,
            flags=re.DOTALL
        )

        # Remove ❌ WRONG sections
        optimized = re.sub(
            r'❌ WRONG.*?(?=\n\n\*|✅)',
            '',
            optimized,
            flags=re.DOTALL
        )

        # Condense Example sections that are overly verbose
        lines = optimized.split('\n')
        filtered_lines = []
        skip_example = False
        example_lines_count = 0
        max_example_lines = 30

        for line in lines:
            # Check if we're entering a verbose example section
            if line.strip().startswith('**Example') or line.strip().startswith('*Example'):
                example_lines_count = 0
                skip_example = False

            # Count lines in example section
            if not line.strip().startswith('##') and not line.strip().startswith('###'):
                example_lines_count += 1
            else:
                example_lines_count = 0

            # Skip if example is too long
            if example_lines_count > max_example_lines:
                skip_example = True

            # Skip verbose "Wrong" or "Bad" examples
            if '❌' in line or 'WRONG' in line or 'BAD' in line:
                skip_example = True
                continue

            # Reset skip at new sections
            if line.strip().startswith('##') or line.strip().startswith('###'):
                skip_example = False

            # Keep the line if not skipping
            if not skip_example:
                filtered_lines.append(line)

        optimized = '\n'.join(filtered_lines)

        return optimized

    def _get_techniques_used(self, original: str, optimized: str) -> List[str]:
        """Determine which optimization techniques were applied."""
        techniques = []

        # Check if shared content was extracted (replacement text added)
        if "docs/prompts/shared/" in optimized:
            techniques.append("Shared content extraction")

        # Check if content was reduced (significantly fewer characters)
        if len(optimized) < len(original) * 0.95:  # More than 5% reduction
            # Check which specific reductions occurred
            if "path_management.md" in optimized:
                if not techniques.count("Shared content extraction"):
                    techniques.append("Shared content extraction")

            if "[activate_and_cd]" in optimized:
                techniques.append("Bash command simplification")

        # Check if meta-instructions were reduced
        if "**Why" in original and "**Why" not in optimized:
            techniques.append("Meta-instruction reduction")

        # Check if validation phases were condensed
        if "Coverage Validation" in optimized:
            original_coverage = original[original.find("Coverage Validation"):original.find("Coverage Validation")+500]
            optimized_coverage = optimized[optimized.find("Coverage Validation"):optimized.find("Coverage Validation")+500]
            if "- [ ] New code: 100%" in optimized_coverage and len(optimized_coverage) < len(original_coverage):
                techniques.append("Validation phase condensation")

        # If no specific technique detected but content is smaller
        if not techniques and len(optimized) < len(original):
            techniques.append("Content reduction")

        return techniques

    def generate_report(self) -> Dict:
        """Generate optimization report with metrics."""
        if not self.optimization_log:
            return {"error": "No optimizations performed yet"}

        total_original = sum(m.original_tokens for m in self.optimization_log)
        total_optimized = sum(m.optimized_tokens for m in self.optimization_log)
        overall_reduction = ((total_original - total_optimized) / total_original) * 100

        report = {
            "summary": {
                "total_prompts_optimized": len(self.optimization_log),
                "total_original_tokens": total_original,
                "total_optimized_tokens": total_optimized,
                "tokens_saved": total_original - total_optimized,
                "overall_reduction_pct": round(overall_reduction, 1)
            },
            "by_prompt": [asdict(m) for m in self.optimization_log],
            "phase1_techniques": {
                "shared_content_extraction": "Extract duplicated sections to references",
                "bash_command_simplification": "Replace verbose examples with placeholders",
                "meta_instruction_reduction": "Simplify TOKEN EFFICIENCY sections",
                "validation_condensation": "Merge qa_reviewer validation subsections"
            },
            "recommendation": self._get_recommendation(overall_reduction)
        }

        return report

    def _get_recommendation(self, reduction_pct: float) -> str:
        """Generate recommendation based on measured reduction."""
        if reduction_pct >= 15:
            return f"EXCELLENT: {reduction_pct:.1f}% reduction exceeds Phase 1 target (10-15%). Proceed to implementation."
        elif reduction_pct >= 10:
            return f"GOOD: {reduction_pct:.1f}% reduction meets Phase 1 target (10-15%). Proceed to implementation."
        elif reduction_pct >= 5:
            return f"MODERATE: {reduction_pct:.1f}% reduction below target. Review optimizations and consider additional techniques."
        else:
            return f"LOW: {reduction_pct:.1f}% reduction insufficient. Re-evaluate optimization strategy."


def main():
    """Main entry point for prompt optimization prototype."""
    print("=" * 80)
    print("PROMPT OPTIMIZATION PROTOTYPE - PHASE 1")
    print("=" * 80)
    print()

    # Determine prompts directory
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    prompts_dir = project_root / "prompts"

    if not prompts_dir.exists():
        print(f"ERROR: Prompts directory not found: {prompts_dir}")
        print("Run this script from apps/backend/")
        return 1

    # Initialize optimizer
    optimizer = PromptOptimizer(prompts_dir)

    # Define prompts to optimize (top 4 agent prompts from PROMPT_ANALYSIS.md)
    prompts_to_optimize = [
        "coder.md",
        "planner.md",
        "qa_reviewer.md",
        "qa_fixer.md"
    ]

    print(f"Optimizing {len(prompts_to_optimize)} agent prompts...")
    print()

    # Optimize each prompt
    results = []
    for prompt_path in prompts_to_optimize:
        print(f"Processing: {prompt_path}")

        try:
            metrics = optimizer.optimize_prompt(prompt_path)
            results.append(metrics)

            # Print immediate results
            print(f"  Original: {metrics.original_tokens:,} tokens")
            print(f"  Optimized: {metrics.optimized_tokens:,} tokens")
            print(f"  Reduction: {metrics.reduction_pct}%")
            print(f"  Techniques: {', '.join(metrics.techniques)}")
            print()

        except FileNotFoundError as e:
            print(f"  ERROR: {e}")
            print()
            continue

    # Generate and print report
    print("=" * 80)
    print("OPTIMIZATION REPORT")
    print("=" * 80)
    print()

    report = optimizer.generate_report()

    # Print summary
    summary = report["summary"]
    print(f"Total prompts optimized: {summary['total_prompts_optimized']}")
    print(f"Total original tokens: {summary['total_original_tokens']:,}")
    print(f"Total optimized tokens: {summary['total_optimized_tokens']:,}")
    print(f"Tokens saved: {summary['tokens_saved']:,}")
    print(f"Overall reduction: {summary['overall_reduction_pct']}%")
    print()

    # Print recommendation
    print("RECOMMENDATION:")
    print(f"  {report['recommendation']}")
    print()

    # Print techniques used
    print("PHASE 1 TECHNIQUES APPLIED:")
    for technique, description in report["phase1_techniques"].items():
        print(f"  - {technique}: {description}")
    print()

    # Print detailed breakdown
    print("DETAILED BREAKDOWN:")
    print("-" * 80)
    for metrics in results:
        print(f"\n{metrics.path}:")
        print(f"  Reduction: {metrics.reduction_pct}% ({metrics.original_tokens:,} → {metrics.optimized_tokens:,})")
        print(f"  Saved: {metrics.original_tokens - metrics.optimized_tokens:,} tokens")
        print(f"  Techniques: {', '.join(metrics.techniques)}")
    print()

    # Save report to JSON
    report_path = script_dir / "prompt_optimization_report.json"
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2)

    print(f"Report saved to: {report_path}")
    print()

    # Quality validation reminder
    print("=" * 80)
    print("QUALITY VALIDATION REQUIRED")
    print("=" * 80)
    print()
    print("Next steps to validate quality preservation:")
    print()
    print("1. Run 5 existing specs with optimized prompts:")
    print("   python run.py --spec <spec-id>")
    print()
    print("2. Compare test pass rates to baseline:")
    print("   - Baseline: Run same specs with original prompts")
    print("   - Optimized: Run with optimized prompts")
    print("   - Accept if: pass rate >= baseline (no regression)")
    print()
    print("3. Monitor agent feedback:")
    print("   - Look for confusion or missed context")
    print("   - Check for increased iteration counts")
    print("   - Verify QA acceptance rates remain stable")
    print()
    print("4. Rollback threshold:")
    print("   - If test pass rate drops > 5%: Revert to original prompts")
    print("   - If agent confusion increases: Review optimization strategy")
    print()
    print("5. If validation passes:")
    print("   - Proceed to Phase 1 implementation (1-2 weeks)")
    print("   - Create docs/prompts/shared/ for reference documents")
    print("   - Update agent initialization to load optimized prompts")
    print()

    # Expected outcome
    print("EXPECTED OUTCOME:")
    print(f"  Target: 10-15% token reduction")
    print(f"  Actual: {summary['overall_reduction_pct']}% token reduction")
    print()

    if summary['overall_reduction_pct'] >= 10:
        print("✓ MEETS EXPECTATIONS - Proceed to quality validation")
        return 0
    else:
        print("⚠ BELOW EXPECTATIONS - Review optimization strategy")
        return 1


if __name__ == "__main__":
    exit(main())
