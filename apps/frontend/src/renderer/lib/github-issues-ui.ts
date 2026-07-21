/**
 * Pure mapping helpers between the shared GitHubIssue shape and the
 * IssueList screen. Localized strings (row meta) stay in the pilot; these
 * helpers only produce locale-neutral values. Reuses the PR mappers'
 * initials/relative-age helpers so the two pilots stay consistent.
 */

import type { UiIssue, UiIssueLabel, UiIssueLabelTone } from '@auto-code/ui';
import type { GitHubIssue } from '../../shared/types';
import { initialsOf } from './github-prs-ui';

const LABEL_TONES: ReadonlyArray<[RegExp, UiIssueLabelTone]> = [
  [/bug|regression|crash/i, 'bug'],
  [/doc/i, 'docs'],
  [/good first/i, 'good-first'],
  [/help|question|discussion|repro/i, 'help'],
  [/enhancement|feature|priority/i, 'feat'],
];

/** Map a GitHub label name onto a semantic pill tone; unknown → area. */
export function labelToneOf(name: string): UiIssueLabelTone {
  for (const [pattern, tone] of LABEL_TONES) {
    if (pattern.test(name)) return tone;
  }
  return 'area';
}

export function mapIssueLabels(
  labels: GitHubIssue['labels'],
): UiIssueLabel[] | undefined {
  if (labels.length === 0) return undefined;
  return labels.map((label) => ({
    text: label.name,
    tone: labelToneOf(label.name),
  }));
}

/** Map one GitHub issue onto the shared row shape. `metaText` is the caller's. */
export function mapIssueToUi(issue: GitHubIssue): UiIssue {
  return {
    id: `issue#${issue.number}`,
    number: issue.number,
    title: issue.title,
    state: issue.state === 'closed' ? 'closed' : 'open',
    repo: issue.repoFullName || undefined,
    author: issue.author.login,
    labels: mapIssueLabels(issue.labels),
    assignees:
      issue.assignees.length > 0
        ? issue.assignees.map((assignee) => ({
            initials: initialsOf(assignee.login),
            name: assignee.login,
          }))
        : undefined,
    commentsCount: issue.commentsCount,
  };
}

/** Case-insensitive match over number, title, author, and label names. */
export function filterIssues(
  issues: readonly UiIssue[],
  query: string,
): UiIssue[] {
  const needle = query.trim().toLowerCase();
  if (needle === '') return [...issues];
  return issues.filter((issue) =>
    [
      `#${issue.number}`,
      issue.title,
      issue.repo,
      issue.author,
      ...(issue.labels ?? []).map((label) => label.text),
      ...(issue.assignees ?? []).map((assignee) => assignee.name),
    ]
      .filter((field): field is string => field != null)
      .some((field) => field.toLowerCase().includes(needle)),
  );
}
