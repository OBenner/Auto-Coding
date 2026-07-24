/**
 * Pure mapping helpers between the ProductivitySummary/Trends IPC shapes and
 * the shared AnalyticsDashboard screen. The mockup's categorical bar panels
 * ("when you ship", "where the time went") have no backing data, so — like
 * the other pilots — this maps only what the backend actually provides: KPI
 * summary figures plus the daily trend series as line charts.
 */

import type { UiChartCard, UiKpi, UiMetaSection } from '@auto-code/ui';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
} from '../../shared/types';
import {
  formatPercent,
  sampleLabels,
  shortDate,
  successRateTone,
} from './analytics-ui';

/** Whole hours with an "h" unit, e.g. 52.4 → "52h". */
export function formatHours(hours: number): string {
  if (!Number.isFinite(hours) || hours < 0) return '0h';
  return `${Math.round(hours)}h`;
}

export interface ProductivityKpiLabels {
  specs: string;
  specsSub: string;
  timeSaved: string;
  timeSavedSub: string;
  successRate: string;
  buildTime: string;
  buildTimeSub: string;
}

export function buildProductivityKpis(
  summary: ProductivitySummary,
  trends: readonly ProductivityTrendPoint[],
  labels: ProductivityKpiLabels,
): UiKpi[] {
  // Backend success rates are 0.0–1.0; the tile shows a whole percent.
  const ratePct = summary.average_success_rate * 100;
  const specSeries = trends.map((point) => point.completed_specs);
  const savedSeries = trends.map((point) => point.time_saved_hours);
  const rateSeries = trends.map((point) => point.success_rate * 100);
  const rateTone = successRateTone(ratePct);
  return [
    {
      value: String(summary.completed_specs),
      label: labels.specs,
      sub: labels.specsSub,
      trend: specSeries.length >= 2 ? specSeries : undefined,
      trendTone: 'info',
    },
    {
      value: formatHours(summary.total_time_saved_hours),
      label: labels.timeSaved,
      sub: labels.timeSavedSub,
      trend: savedSeries.length >= 2 ? savedSeries : undefined,
      trendTone: 'good',
    },
    {
      value: formatPercent(ratePct),
      label: labels.successRate,
      tone: rateTone,
      trend: rateSeries.length >= 2 ? rateSeries : undefined,
      trendTone: rateTone === 'bad' ? 'bad' : 'good',
    },
    {
      value: formatHours(summary.total_build_time_hours),
      label: labels.buildTime,
      sub: labels.buildTimeSub,
    },
  ];
}

export interface ProductivityChartLabels {
  velocityTitle: string;
  velocityAria: string;
  velocitySeries: string;
  timeSavedTitle: string;
  timeSavedAria: string;
  timeSavedSeries: string;
}

export function buildProductivityCharts(
  trends: readonly ProductivityTrendPoint[],
  labels: ProductivityChartLabels,
  locale?: string,
): UiChartCard[] {
  if (trends.length < 2) return [];
  const xLabels = sampleLabels(trends.map((p) => shortDate(p.date, locale)));
  return [
    {
      title: labels.velocityTitle,
      ariaLabel: labels.velocityAria,
      xLabels,
      series: [
        {
          label: labels.velocitySeries,
          tone: 'info',
          values: trends.map((p) => p.completed_specs),
        },
      ],
    },
    {
      title: labels.timeSavedTitle,
      ariaLabel: labels.timeSavedAria,
      xLabels,
      series: [
        {
          label: labels.timeSavedSeries,
          tone: 'good',
          values: trends.map((p) => p.time_saved_hours),
        },
      ],
    },
  ];
}

export interface ProductivitySectionLabels {
  outcomesTitle: string;
  completed: string;
  inProgress: string;
  failed: string;
  effortTitle: string;
  subtasksPerSpec: string;
  qaIterations: string;
  firstAttempt: string;
}

/** Round to at most one decimal, dropping a trailing ".0". */
function oneDecimal(value: number): string {
  if (!Number.isFinite(value)) return '0';
  return String(Math.round(value * 10) / 10);
}

export function buildProductivitySections(
  summary: ProductivitySummary,
  labels: ProductivitySectionLabels,
): UiMetaSection[] {
  return [
    {
      title: labels.outcomesTitle,
      rows: [
        { label: labels.completed, value: String(summary.completed_specs) },
        { label: labels.inProgress, value: String(summary.in_progress_specs) },
        { label: labels.failed, value: String(summary.failed_specs) },
      ],
    },
    {
      title: labels.effortTitle,
      rows: [
        {
          label: labels.subtasksPerSpec,
          value: oneDecimal(summary.average_subtasks_per_spec),
        },
        {
          label: labels.qaIterations,
          value: oneDecimal(summary.average_qa_iterations),
        },
        {
          label: labels.firstAttempt,
          value: formatPercent(summary.first_attempt_success_rate * 100),
        },
      ],
    },
  ];
}
