/**
 * Builds the TaskDetail right-rail meta cards (workspace, cost & tokens)
 * from the desktop data sources: the store Task, token_stats.json (over
 * getTokenStats) and cost_report.json (over getCostReport). Pure — labels
 * are injected so text goes through i18n.
 */

import type { UiMetaSection } from '@auto-code/ui';
import type { CostReport, Task, TaskTokenStats } from '../../shared/types';

export interface TaskMetaLabels {
  workspaceTitle: string;
  costTokensTitle: string;
  specId: string;
  location: string;
  updated: string;
  cost: string;
  inputTokens: string;
  outputTokens: string;
  sessions: string;
}

/** 112000 → "112k", 1200000 → "1.2M"; small counts stay verbatim. */
export function formatTokenCount(count: number): string {
  if (!Number.isFinite(count) || count < 0) return '0';
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${Math.round(count / 1_000)}k`;
  return String(count);
}

export function buildTaskMetaSections(
  task: Task,
  tokenStats: TaskTokenStats | null,
  costReport: CostReport | null,
  labels: TaskMetaLabels,
): UiMetaSection[] {
  const sections: UiMetaSection[] = [];

  const workspaceRows = [
    { label: labels.specId, value: task.specId },
    ...(task.location != null
      ? [{ label: labels.location, value: task.location }]
      : []),
    ...(task.updatedAt != null
      ? [
          {
            label: labels.updated,
            value: new Date(task.updatedAt).toLocaleString(),
          },
        ]
      : []),
  ];
  sections.push({ title: labels.workspaceTitle, rows: workspaceRows });

  const costRows = [];
  if (costReport != null) {
    costRows.push({
      label: labels.cost,
      value: `$${costReport.total_cost.toFixed(2)}`,
    });
  }
  if (tokenStats != null) {
    costRows.push({
      label: labels.inputTokens,
      value: formatTokenCount(tokenStats.total_input_tokens),
    });
    costRows.push({
      label: labels.outputTokens,
      value: formatTokenCount(tokenStats.total_output_tokens),
    });
    const sessions = Object.values(tokenStats.phases ?? {}).reduce(
      (total, phase) => total + (phase.session_count ?? 0),
      0,
    );
    if (sessions > 0) {
      costRows.push({ label: labels.sessions, value: String(sessions) });
    }
  }
  if (costRows.length > 0) {
    sections.push({ title: labels.costTokensTitle, rows: costRows });
  }

  return sections;
}
