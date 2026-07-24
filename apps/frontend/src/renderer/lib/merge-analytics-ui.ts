/**
 * Pure mapping helpers between the MergeAnalytics / ConflictPattern IPC shapes
 * and the shared AnalyticsDashboard. There is no time series in the merge
 * report, so the KPI tiles carry no sparklines; the conflict patterns map to a
 * BarList distribution and the rest to summary cards.
 */

import type { UiBarListCard, UiKpi, UiMetaSection } from '@auto-code/ui';
import type { ChartTone } from '@auto-code/ui';
import type {
  ConflictPattern,
  MergeAnalytics,
  MergeConflictSeverity,
} from '../../shared/types';
import { formatCount, formatPercent } from './analytics-ui';

const SEVERITY_TONES: Record<MergeConflictSeverity, ChartTone> = {
  none: 'neutral',
  low: 'info',
  medium: 'warn',
  high: 'bad',
  critical: 'bad',
};

/** Trailing path segment for a compact bar label; keeps a leading dir hint. */
export function shortenPath(path: string, maxSegments = 2): string {
  const parts = path.split('/').filter(Boolean);
  if (parts.length <= maxSegments) return path;
  return `…/${parts.slice(-maxSegments).join('/')}`;
}

export interface MergeKpiLabels {
  operations: string;
  operationsSub: string;
  successRate: string;
  autoMerge: string;
  conflicts: string;
  conflictsSub: string;
}

export function buildMergeKpis(
  analytics: MergeAnalytics,
  labels: MergeKpiLabels,
): UiKpi[] {
  // Backend rates are 0.0–1.0.
  const successPct = analytics.success_rate * 100;
  const autoPct = analytics.auto_merge_rate * 100;
  const successTone = successPct >= 80 ? 'good' : 'warn';
  return [
    {
      value: String(analytics.total_operations),
      label: labels.operations,
      sub: labels.operationsSub,
    },
    {
      value: formatPercent(successPct),
      label: labels.successRate,
      tone: successTone,
    },
    {
      value: formatPercent(autoPct),
      label: labels.autoMerge,
    },
    {
      value: String(analytics.total_conflicts),
      label: labels.conflicts,
      sub: labels.conflictsSub,
      tone: analytics.total_conflicts > 0 ? 'warn' : undefined,
    },
  ];
}

export function buildMergeBarLists(
  patterns: readonly ConflictPattern[],
  title: string,
  ariaLabel: string,
): UiBarListCard[] {
  if (patterns.length === 0) return [];
  return [
    {
      title,
      ariaLabel,
      items: patterns.map((pattern) => ({
        label: shortenPath(pattern.file_path),
        value: pattern.occurrence_count,
        tone: SEVERITY_TONES[pattern.severity] ?? 'info',
      })),
    },
  ];
}

export interface MergeSectionLabels {
  outcomesTitle: string;
  successful: string;
  failed: string;
  filesMerged: string;
  efficiencyTitle: string;
  avgDuration: string;
  aiCalls: string;
  tokens: string;
}

/** Seconds → "45s" or "2m 05s". */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '0s';
  const whole = Math.round(seconds);
  if (whole < 60) return `${whole}s`;
  const minutes = Math.floor(whole / 60);
  const rest = whole % 60;
  return `${minutes}m ${String(rest).padStart(2, '0')}s`;
}

export function buildMergeSections(
  analytics: MergeAnalytics,
  labels: MergeSectionLabels,
): UiMetaSection[] {
  return [
    {
      title: labels.outcomesTitle,
      rows: [
        { label: labels.successful, value: String(analytics.successful_operations) },
        { label: labels.failed, value: String(analytics.failed_operations) },
        { label: labels.filesMerged, value: String(analytics.total_files_merged) },
      ],
    },
    {
      title: labels.efficiencyTitle,
      rows: [
        {
          label: labels.avgDuration,
          value: formatDuration(analytics.average_duration_seconds),
        },
        { label: labels.aiCalls, value: String(analytics.total_ai_calls) },
        { label: labels.tokens, value: formatCount(analytics.total_tokens_used) },
      ],
    },
  ];
}
