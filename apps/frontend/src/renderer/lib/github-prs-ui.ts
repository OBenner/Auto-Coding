/**
 * Pure mapping helpers between the preload GitHub PRData shape and the
 * shared PullRequestList screen. Localized strings (stat labels, row meta)
 * stay in the pilot; these helpers only produce locale-neutral values.
 */

import type { UiPullRequest } from '@auto-code/ui';
import type { PRData } from '../../preload/api/modules/github-api';

/** "auto-code" → "AC", "OM" → "OM", "renovate" → "RE". */
export function initialsOf(login: string): string {
  const parts = login.split(/[-_\s]+/).filter(Boolean);
  if (parts.length >= 2) {
    return (parts[0][0] + parts[1][0]).toUpperCase();
  }
  return login.slice(0, 2).toUpperCase();
}

/** Compact relative age: "22m", "4h", "2d"; "<1m" under a minute. */
export function relativeAge(iso: string, now: Date = new Date()): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return '';
  const minutes = Math.floor((now.getTime() - then) / 60_000);
  if (minutes < 1) return '<1m';
  if (minutes < 60) return `${minutes}m`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h`;
  return `${Math.floor(hours / 24)}d`;
}

/**
 * Map one GitHub PR onto the shared row shape. `listPRs` only returns open
 * PRs today, so the state tile is always "open"; draft/merged/conflict land
 * with the detail flow in part 2. `metaText` is left for the caller (i18n).
 */
export function mapPRToUi(pr: PRData, now: Date = new Date()): UiPullRequest {
  return {
    id: `pr#${pr.number}`,
    number: pr.number,
    title: pr.title,
    state: 'open',
    author: pr.author.login,
    headBranch: pr.headRefName,
    baseBranch: pr.baseRefName,
    additions: pr.additions,
    deletions: pr.deletions,
    reviewers:
      pr.assignees.length > 0
        ? pr.assignees.map((assignee) => ({
            initials: initialsOf(assignee.login),
            name: assignee.login,
          }))
        : undefined,
    timeLabel: relativeAge(pr.updatedAt, now),
  };
}

export interface PrStatValues {
  open: number;
  authors: number;
  additions: number;
  deletions: number;
}

export function computePrStatValues(prs: readonly PRData[]): PrStatValues {
  return {
    open: prs.length,
    authors: new Set(prs.map((pr) => pr.author.login)).size,
    additions: prs.reduce((total, pr) => total + (pr.additions || 0), 0),
    deletions: prs.reduce((total, pr) => total + (pr.deletions || 0), 0),
  };
}

/** Case-insensitive match over number, title, author, and branches. */
export function filterPullRequests(
  prs: readonly UiPullRequest[],
  query: string,
): UiPullRequest[] {
  const needle = query.trim().toLowerCase();
  if (needle === '') return [...prs];
  return prs.filter((pr) =>
    [`#${pr.number}`, pr.title, pr.author, pr.headBranch, pr.baseBranch]
      .filter((field): field is string => field != null)
      .some((field) => field.toLowerCase().includes(needle)),
  );
}
