/**
 * Pure mapping helpers between the AnalyticsReport IPC shape and the shared
 * AnalyticsDashboard screen. Localized strings (KPI/section/chart labels)
 * stay in the pilot; these helpers produce locale-neutral values + series.
 */

import type { UiChartCard, UiKpi, UiMetaSection } from '@auto-code/ui';
import type { AnalyticsReport } from '../../shared/types';

/** 4200000 → "4.2M", 4200 → "4.2k", 420 → "420". */
export function formatCount(count: number): string {
  if (!Number.isFinite(count) || count < 0) return '0';
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}k`;
  return String(Math.round(count));
}

/** Whole-number percent with a trailing sign, e.g. 87.4 → "87%". */
export function formatPercent(pct: number): string {
  if (!Number.isFinite(pct)) return '0%';
  return `${Math.round(pct)}%`;
}

/** USD with two decimals, e.g. 142.1 → "$142.10". */
export function formatCost(usd: number): string {
  if (!Number.isFinite(usd) || usd < 0) return '$0.00';
  return `$${usd.toFixed(2)}`;
}

/** Bucket a 0–100 success rate into a tile tone. */
export function successRateTone(pct: number): 'good' | 'warn' | 'bad' {
  if (pct >= 80) return 'good';
  if (pct >= 50) return 'warn';
  return 'bad';
}

export interface AnalyticsKpiLabels {
  specs: string;
  successRate: string;
  cost: string;
  tokens: string;
  specsSub: string;
  tokensSub: string;
}

/** Build the KPI tiles from the report summary + trend sparklines. */
export function buildKpis(
  report: AnalyticsReport,
  labels: AnalyticsKpiLabels,
): UiKpi[] {
  const { summary, trends } = report;
  const taskSeries = trends.map((point) => point.total_tasks);
  const rateSeries = trends.map((point) => point.success_rate);
  const costSeries = trends.map((point) => point.total_cost);
  const successTone = successRateTone(summary.overall_success_rate);
  return [
    {
      value: String(summary.total_specs),
      label: labels.specs,
      sub: labels.specsSub,
      trend: taskSeries.length >= 2 ? taskSeries : undefined,
      trendTone: 'info',
    },
    {
      value: formatPercent(summary.overall_success_rate),
      label: labels.successRate,
      tone: successTone,
      trend: rateSeries.length >= 2 ? rateSeries : undefined,
      trendTone: successTone === 'bad' ? 'bad' : 'good',
    },
    {
      value: formatCost(summary.total_cost),
      label: labels.cost,
      trend: costSeries.length >= 2 ? costSeries : undefined,
      trendTone: 'warn',
    },
    {
      value: formatCount(summary.total_tokens),
      label: labels.tokens,
      sub: labels.tokensSub,
    },
  ];
}

export interface AnalyticsChartLabels {
  velocityTitle: string;
  velocityAria: string;
  tasksSeries: string;
  rateTitle: string;
  rateAria: string;
  rateSeries: string;
}

/** "2026-05-22" → "May 22" (UTC); non-ISO input passes through verbatim. */
export function shortDate(iso: string, locale?: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
  if (match == null) return iso;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return iso;
  return parsed.toLocaleDateString(locale, {
    month: 'short',
    day: 'numeric',
    timeZone: 'UTC',
  });
}

/** Evenly sample up to `max` labels from a series so the axis stays legible. */
export function sampleLabels(labels: readonly string[], max = 6): string[] {
  if (labels.length <= max) return [...labels];
  const step = (labels.length - 1) / (max - 1);
  return Array.from({ length: max }, (_, i) => labels[Math.round(i * step)]);
}

export function buildCharts(
  report: AnalyticsReport,
  labels: AnalyticsChartLabels,
  locale?: string,
): UiChartCard[] {
  const { trends } = report;
  if (trends.length < 2) return [];
  const xLabels = sampleLabels(trends.map((p) => shortDate(p.date, locale)));
  return [
    {
      title: labels.velocityTitle,
      ariaLabel: labels.velocityAria,
      showLegend: false,
      xLabels,
      series: [
        {
          label: labels.tasksSeries,
          tone: 'info',
          values: trends.map((p) => p.total_tasks),
        },
      ],
    },
    {
      title: labels.rateTitle,
      ariaLabel: labels.rateAria,
      xLabels,
      series: [
        {
          label: labels.rateSeries,
          tone: 'good',
          values: trends.map((p) => p.success_rate),
        },
      ],
    },
  ];
}

export interface AnalyticsSectionLabels {
  outcomesTitle: string;
  completed: string;
  failed: string;
  inProgress: string;
  qaTitle: string;
  reviews: string;
  approved: string;
  rejectionRate: string;
}

export function buildSections(
  report: AnalyticsReport,
  labels: AnalyticsSectionLabels,
): UiMetaSection[] {
  const { summary } = report;
  const qa = summary.qa_stats;
  return [
    {
      title: labels.outcomesTitle,
      rows: [
        { label: labels.completed, value: String(summary.completed_specs) },
        { label: labels.failed, value: String(summary.failed_specs) },
        { label: labels.inProgress, value: String(summary.in_progress_specs) },
      ],
    },
    {
      title: labels.qaTitle,
      rows: [
        { label: labels.reviews, value: String(qa.total_reviews) },
        { label: labels.approved, value: String(qa.approved) },
        {
          label: labels.rejectionRate,
          value: formatPercent(qa.rejection_rate),
        },
      ],
    },
  ];
}
