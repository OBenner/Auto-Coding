/**
 * Spec File Reader Utilities
 *
 * Provides utilities for reading task specification files from the worktree.
 * These files are read-only and provide task progress information:
 * - implementation_plan.json: Implementation stages and progress
 * - qa_report.md: QA testing results
 * - QA_ESCALATION.md: Escalated issues requiring attention
 */

import path from 'path';
import { readFileSync, existsSync } from 'fs';
import { AUTO_BUILD_PATHS, getSpecsDir } from '../../../shared/constants';
import type { Project, Task, ImplementationPlan, QAEscalation } from '../../../shared/types';

/**
 * Check if an error is a "file not found" error
 */
function isFileNotFoundError(err: unknown): boolean {
  return (err as NodeJS.ErrnoException).code === 'ENOENT';
}

/**
 * Get the spec directory path for a task
 */
export function getSpecDir(project: Project, task: Task): string {
  const specsBaseDir = getSpecsDir(project.autoBuildPath);
  return path.join(project.path, specsBaseDir, task.specId);
}

/**
 * Read the implementation plan from implementation_plan.json
 *
 * @param project - The project containing the task
 * @param task - The task to read the plan for
 * @returns The implementation plan, or null if file doesn't exist
 */
export function readImplementationPlan(
  project: Project,
  task: Task
): ImplementationPlan | null {
  try {
    const specDir = getSpecDir(project, task);
    const planPath = path.join(specDir, AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN);

    if (!existsSync(planPath)) {
      console.warn(`[spec-file-readers] Implementation plan not found at ${planPath}`);
      return null;
    }

    const planContent = readFileSync(planPath, 'utf-8');
    const plan = JSON.parse(planContent) as ImplementationPlan;

    return plan;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading implementation plan:`, err);
    throw err;
  }
}

/**
 * Read the QA report from qa_report.md
 *
 * @param project - The project containing the task
 * @param task - The task to read the QA report for
 * @returns The QA report content as markdown string, or null if file doesn't exist
 */
export function readQAReport(project: Project, task: Task): string | null {
  try {
    const specDir = getSpecDir(project, task);
    const qaReportPath = path.join(specDir, AUTO_BUILD_PATHS.QA_REPORT);

    if (!existsSync(qaReportPath)) {
      console.warn(`[spec-file-readers] QA report not found at ${qaReportPath}`);
      return null;
    }

    const qaReportContent = readFileSync(qaReportPath, 'utf-8');
    return qaReportContent;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading QA report:`, err);
    throw err;
  }
}

/**
 * Parse QA escalation metadata from QA_ESCALATION.md frontmatter
 *
 * The file format is:
 * ---
 * generated: "2024-01-15T10:30:00Z"
 * iteration: 5
 * maxIterations: 5
 * reason: "Max iterations reached"
 * ---
 * [Rest of markdown content]
 */
function parseQAEscalationFrontmatter(content: string): Partial<QAEscalation> | null {
  const frontmatterRegex = /^---\s*\n([\s\S]*?)\n---/;
  const match = content.match(frontmatterRegex);

  if (!match) {
    return null;
  }

  const frontmatter = match[1];
  const metadata: Partial<QAEscalation> = {};

  // Parse YAML-like frontmatter
  const lines = frontmatter.split('\n');
  for (const line of lines) {
    const [key, ...valueParts] = line.split(':');
    if (!key || valueParts.length === 0) continue;

    const value = valueParts.join(':').trim().replace(/^["']|["']$/g, '');
    const trimmedKey = key.trim();

    if (trimmedKey === 'generated') {
      metadata.generated = value;
    } else if (trimmedKey === 'iteration') {
      metadata.iteration = parseInt(value, 10);
    } else if (trimmedKey === 'maxIterations') {
      metadata.maxIterations = parseInt(value, 10);
    } else if (trimmedKey === 'reason') {
      metadata.reason = value;
    }
  }

  return metadata;
}

/**
 * Parse QA escalation summary section from markdown content
 */
function parseQAEscalationSummary(content: string): QAEscalation['summary'] | null {
  const summaryRegex = /## Summary\s*\n\s*-\s*Total iterations:\s*(\d+)\s*\n\s*-\s*Total issues found:\s*(\d+)\s*\n\s*-\s*Unique issues:\s*(\d+)\s*\n\s*-\s*Fix success rate:\s*([\d.]+)%/i;
  const match = content.match(summaryRegex);

  if (!match) {
    return null;
  }

  return {
    totalIterations: parseInt(match[1], 10),
    totalIssues: parseInt(match[2], 10),
    uniqueIssues: parseInt(match[3], 10),
    fixSuccessRate: parseFloat(match[4]) / 100 // Convert percentage to decimal
  };
}

/**
 * Parse recurring issues section from markdown content
 */
function parseRecurringIssues(content: string): QAEscalation['recurringIssues'] {
  const issues: QAEscalation['recurringIssues'] = [];
  const sectionRegex = /## Recurring Issues.*?\n([\s\S]*?)(?=\n## |\n---|\n$)/i;
  const sectionMatch = content.match(sectionRegex);

  if (!sectionMatch) {
    return issues;
  }

  const issuesContent = sectionMatch[1];
  const issueRegex = /###\s*(.+?)\s*\n\s*-\s*File:\s*`([^`]*)`\s*\n\s*-\s*Line:\s*(\d+)\s*\n\s*-\s*Type:\s*(.+?)\s*\n\s*-\s*Occurrences:\s*(\d+)\s*\n\s*-\s*Description:\s*(.+?)(?=\n###|\n##|\n---|\n$)/gs;

  let match;
  while ((match = issueRegex.exec(issuesContent)) !== null) {
    issues.push({
      title: match[1].trim(),
      file: match[2].trim() || undefined,
      line: parseInt(match[3], 10),
      type: match[4].trim(),
      occurrences: parseInt(match[5], 10),
      description: match[6].trim()
    });
  }

  return issues;
}

/**
 * Parse most common issues section from markdown content
 */
function parseMostCommonIssues(content: string): QAEscalation['mostCommonIssues'] {
  const issues: QAEscalation['mostCommonIssues'] = [];
  const sectionRegex = /## Most Common Issues.*?\n([\s\S]*?)(?=\n## |\n---|\n$)/i;
  const sectionMatch = content.match(sectionRegex);

  if (!sectionMatch) {
    return issues;
  }

  const issuesContent = sectionMatch[1];
  const issueRegex = /\d+\.\s*\*\*(.+?)\*\*\s*\((\d+)\s*occurrences?\)(?:\s*-\s*File:\s*`([^`]+)`)?/g;

  let match;
  while ((match = issueRegex.exec(issuesContent)) !== null) {
    issues.push({
      title: match[1].trim(),
      occurrences: parseInt(match[2], 10),
      file: match[3]?.trim() || undefined
    });
  }

  return issues;
}

/**
 * Read and parse QA escalation from QA_ESCALATION.md
 *
 * @param project - The project containing the task
 * @param task - The task to read the QA escalation for
 * @returns The parsed QA escalation data, or null if file doesn't exist
 */
export function readQAEscalation(project: Project, task: Task): QAEscalation | null {
  try {
    const specDir = getSpecDir(project, task);
    const escalationPath = path.join(specDir, 'QA_ESCALATION.md');

    if (!existsSync(escalationPath)) {
      console.warn(`[spec-file-readers] QA escalation not found at ${escalationPath}`);
      return null;
    }

    const escalationContent = readFileSync(escalationPath, 'utf-8');

    // Parse frontmatter
    const metadata = parseQAEscalationFrontmatter(escalationContent);
    if (!metadata) {
      console.warn(`[spec-file-readers] QA escalation missing frontmatter at ${escalationPath}`);
      return null;
    }

    // Parse summary section
    const summary = parseQAEscalationSummary(escalationContent);
    if (!summary) {
      console.warn(`[spec-file-readers] QA escalation missing summary section at ${escalationPath}`);
      return null;
    }

    // Parse recurring issues
    const recurringIssues = parseRecurringIssues(escalationContent);

    // Parse most common issues
    const mostCommonIssues = parseMostCommonIssues(escalationContent);

    // Construct the full QAEscalation object
    const escalation: QAEscalation = {
      generated: metadata.generated || new Date().toISOString(),
      iteration: metadata.iteration || 0,
      maxIterations: metadata.maxIterations || 0,
      reason: metadata.reason || '',
      summary,
      recurringIssues,
      mostCommonIssues
    };

    return escalation;
  } catch (err) {
    if (isFileNotFoundError(err)) {
      return null;
    }
    console.error(`[spec-file-readers] Error reading QA escalation:`, err);
    throw err;
  }
}
