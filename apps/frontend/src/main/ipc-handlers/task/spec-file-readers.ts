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
import fs from 'fs/promises';
import { AUTO_BUILD_PATHS, getSpecsDir } from '../../../shared/constants';
import type { Project, Task, ImplementationPlan, QAEscalation } from '../../../shared/types';

/**
 * Check if an error is a "file not found" error
 */
function isFileNotFoundError(err: unknown): boolean {
  return (err as NodeJS.ErrnoException).code === 'ENOENT';
}

/**
 * Validate specId to prevent path traversal attacks
 */
function isValidSpecId(specId: string): boolean {
  return /^[\w-]+$/.test(specId);
}

/**
 * Get the spec directory path for a task.
 * Validates specId to prevent path traversal.
 */
export function getSpecDir(project: Project, task: Task): string {
  if (!isValidSpecId(task.specId)) {
    throw new Error(`Invalid specId: ${task.specId}`);
  }
  const specsBaseDir = getSpecsDir(project.autoBuildPath);
  const specDir = path.join(project.path, specsBaseDir, task.specId);
  const resolvedSpecDir = path.resolve(specDir);
  const resolvedProjectDir = path.resolve(project.path);
  if (!resolvedSpecDir.startsWith(resolvedProjectDir + path.sep) && resolvedSpecDir !== resolvedProjectDir) {
    throw new Error(`Path traversal detected: specDir escapes project root`);
  }
  return specDir;
}

/**
 * Read the implementation plan from implementation_plan.json
 *
 * @param project - The project containing the task
 * @param task - The task to read the plan for
 * @returns The implementation plan, or null if file doesn't exist
 */
export async function readImplementationPlan(
  project: Project,
  task: Task
): Promise<ImplementationPlan | null> {
  try {
    const specDir = getSpecDir(project, task);
    const planPath = path.join(specDir, AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN);

    const planContent = await fs.readFile(planPath, 'utf-8');
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
export async function readQAReport(project: Project, task: Task): Promise<string | null> {
  try {
    const specDir = getSpecDir(project, task);
    const qaReportPath = path.join(specDir, AUTO_BUILD_PATHS.QA_REPORT);

    const qaReportContent = await fs.readFile(qaReportPath, 'utf-8');
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
  // Extract frontmatter between --- delimiters using indexOf (avoids ReDoS)
  const firstDelim = content.indexOf('---');
  if (firstDelim === -1) return null;

  const afterFirst = content.indexOf('\n', firstDelim);
  if (afterFirst === -1) return null;

  const secondDelim = content.indexOf('\n---', afterFirst);
  if (secondDelim === -1) return null;

  const frontmatter = content.slice(afterFirst + 1, secondDelim);
  const metadata: Partial<QAEscalation> = {};

  // Parse YAML-like frontmatter line by line
  const lines = frontmatter.split('\n');
  for (const line of lines) {
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;

    const trimmedKey = line.slice(0, colonIdx).trim();
    const value = line.slice(colonIdx + 1).trim().replace(/(^["'])|(['"]$)/g, '');

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
  // Find "## Summary" section and parse bullet points (avoids ReDoS)
  const summaryIdx = content.search(/## Summary/i);
  if (summaryIdx === -1) return null;

  const sectionEnd = content.indexOf('\n## ', summaryIdx + 1);
  const section = sectionEnd === -1
    ? content.slice(summaryIdx)
    : content.slice(summaryIdx, sectionEnd);

  const lines = section.split('\n');
  let totalIterations = 0;
  let totalIssues = 0;
  let uniqueIssues = 0;
  let fixSuccessRate = 0;
  let found = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('- Total iterations:')) {
      totalIterations = parseInt(trimmed.split(':')[1].trim(), 10);
      found++;
    } else if (trimmed.startsWith('- Total issues found:')) {
      totalIssues = parseInt(trimmed.split(':')[1].trim(), 10);
      found++;
    } else if (trimmed.startsWith('- Unique issues:')) {
      uniqueIssues = parseInt(trimmed.split(':')[1].trim(), 10);
      found++;
    } else if (trimmed.startsWith('- Fix success rate:')) {
      fixSuccessRate = parseFloat(trimmed.split(':')[1].trim()) / 100;
      found++;
    }
  }

  if (found < 4) return null;

  return { totalIterations, totalIssues, uniqueIssues, fixSuccessRate };
}

/**
 * Parse recurring issues section from markdown content
 */
function parseRecurringIssues(content: string): QAEscalation['recurringIssues'] {
  const issues: QAEscalation['recurringIssues'] = [];

  // Find "## Recurring Issues" section using indexOf (avoids ReDoS)
  const sectionIdx = content.search(/## Recurring Issues/i);
  if (sectionIdx === -1) return issues;

  const sectionEnd = content.indexOf('\n## ', sectionIdx + 1);
  const section = sectionEnd === -1
    ? content.slice(sectionIdx)
    : content.slice(sectionIdx, sectionEnd);

  const lines = section.split('\n');
  let currentTitle = '';
  let currentFile = '';
  let currentLine = 0;
  let currentType = '';
  let currentOccurrences = 0;
  let currentDescription = '';
  let inIssue = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith('### ')) {
      if (inIssue && currentTitle) {
        issues.push({
          title: currentTitle,
          file: currentFile || undefined,
          line: currentLine,
          type: currentType,
          occurrences: currentOccurrences,
          description: currentDescription
        });
      }
      currentTitle = trimmed.slice(4).trim();
      currentFile = '';
      currentLine = 0;
      currentType = '';
      currentOccurrences = 0;
      currentDescription = '';
      inIssue = true;
    } else if (inIssue) {
      if (trimmed.startsWith('- File:')) {
        const backtickStart = trimmed.indexOf('`');
        const backtickEnd = trimmed.lastIndexOf('`');
        currentFile = backtickStart >= 0 && backtickEnd > backtickStart
          ? trimmed.slice(backtickStart + 1, backtickEnd)
          : '';
      } else if (trimmed.startsWith('- Line:')) {
        currentLine = parseInt(trimmed.split(':')[1].trim(), 10);
      } else if (trimmed.startsWith('- Type:')) {
        currentType = trimmed.slice(trimmed.indexOf(':') + 1).trim();
      } else if (trimmed.startsWith('- Occurrences:')) {
        currentOccurrences = parseInt(trimmed.split(':')[1].trim(), 10);
      } else if (trimmed.startsWith('- Description:')) {
        currentDescription = trimmed.slice(trimmed.indexOf(':') + 1).trim();
      }
    }
  }

  // Push last issue
  if (inIssue && currentTitle) {
    issues.push({
      title: currentTitle,
      file: currentFile || undefined,
      line: currentLine,
      type: currentType,
      occurrences: currentOccurrences,
      description: currentDescription
    });
  }

  return issues;
}

/**
 * Parse most common issues section from markdown content
 */
function parseMostCommonIssues(content: string): QAEscalation['mostCommonIssues'] {
  const issues: QAEscalation['mostCommonIssues'] = [];

  // Find "## Most Common Issues" section using indexOf (avoids ReDoS)
  const sectionIdx = content.search(/## Most Common Issues/i);
  if (sectionIdx === -1) return issues;

  const sectionEnd = content.indexOf('\n## ', sectionIdx + 1);
  const section = sectionEnd === -1
    ? content.slice(sectionIdx)
    : content.slice(sectionIdx, sectionEnd);

  // Parse numbered list items: "1. **Title** (N occurrences) - File: `path`"
  const lines = section.split('\n');
  for (const line of lines) {
    const trimmed = line.trim();
    // Match lines starting with a number and dot
    if (!/^\d+\./.test(trimmed)) continue;

    const boldStart = trimmed.indexOf('**');
    const boldEnd = trimmed.indexOf('**', boldStart + 2);
    if (boldStart === -1 || boldEnd === -1) continue;

    const title = trimmed.slice(boldStart + 2, boldEnd).trim();

    const parenStart = trimmed.indexOf('(', boldEnd);
    const parenEnd = trimmed.indexOf(')', parenStart);
    let occurrences = 0;
    if (parenStart >= 0 && parenEnd >= 0) {
      occurrences = parseInt(trimmed.slice(parenStart + 1, parenEnd), 10);
    }

    let file: string | undefined;
    const backtickStart = trimmed.indexOf('`', parenEnd);
    const backtickEnd = trimmed.indexOf('`', backtickStart + 1);
    if (backtickStart >= 0 && backtickEnd > backtickStart) {
      file = trimmed.slice(backtickStart + 1, backtickEnd).trim() || undefined;
    }

    issues.push({ title, occurrences, file });
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
export async function readQAEscalation(project: Project, task: Task): Promise<QAEscalation | null> {
  try {
    const specDir = getSpecDir(project, task);
    const escalationPath = path.join(specDir, 'QA_ESCALATION.md');

    const escalationContent = await fs.readFile(escalationPath, 'utf-8');

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
