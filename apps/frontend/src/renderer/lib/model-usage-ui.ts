/**
 * Pure mapping helpers between the ModelUsageSummary/Trends IPC shapes and the
 * shared AnalyticsDashboard. Model Usage is line/sparkline + a per-model
 * distribution, so it exercises KPIs, trend charts, a BarList, and a rail card.
 */

import type {
  UiBarListCard,
  UiChartCard,
  UiKpi,
  UiMetaSection,
} from '@auto-code/ui';
import type {
  ModelMetrics,
  ModelUsageSummary,
  ModelUsageTrendPoint,
} from '../../shared/types';
import {
  formatCost,
  formatCount,
  sampleLabels,
  shortDate,
} from './analytics-ui';

/** Drop a provider prefix and date suffix so bars read as short model names. */
export function shortModelName(model: string): string {
  return model.replace(/^[^/]+\//, '').replace(/-\d{6,8}$/, '');
}

export interface ModelKpiLabels {
  calls: string;
  callsSub: string;
  tokens: string;
  cost: string;
  models: string;
  modelsSub: string;
}

export function buildModelKpis(
  summary: ModelUsageSummary,
  trends: readonly ModelUsageTrendPoint[],
  labels: ModelKpiLabels,
): UiKpi[] {
  const usageSeries = trends.map((point) => point.usage_count);
  const tokenSeries = trends.map((point) => point.total_tokens);
  const costSeries = trends.map((point) => point.total_cost);
  return [
    {
      value: String(summary.total_usage_count),
      label: labels.calls,
      sub: labels.callsSub,
      trend: usageSeries.length >= 2 ? usageSeries : undefined,
      trendTone: 'info',
    },
    {
      value: formatCount(summary.total_tokens),
      label: labels.tokens,
      trend: tokenSeries.length >= 2 ? tokenSeries : undefined,
      trendTone: 'info',
    },
    {
      value: formatCost(summary.total_cost),
      label: labels.cost,
      trend: costSeries.length >= 2 ? costSeries : undefined,
      trendTone: 'warn',
    },
    {
      value: String(summary.models.length),
      label: labels.models,
      sub: labels.modelsSub,
    },
  ];
}

export interface ModelChartLabels {
  tokensTitle: string;
  tokensAria: string;
  tokensSeries: string;
  costTitle: string;
  costAria: string;
  costSeries: string;
}

export function buildModelCharts(
  trends: readonly ModelUsageTrendPoint[],
  labels: ModelChartLabels,
  locale?: string,
): UiChartCard[] {
  if (trends.length < 2) return [];
  const xLabels = sampleLabels(trends.map((p) => shortDate(p.date, locale)));
  return [
    {
      title: labels.tokensTitle,
      ariaLabel: labels.tokensAria,
      xLabels,
      series: [
        {
          label: labels.tokensSeries,
          tone: 'info',
          values: trends.map((p) => p.total_tokens),
        },
      ],
    },
    {
      title: labels.costTitle,
      ariaLabel: labels.costAria,
      xLabels,
      series: [
        {
          label: labels.costSeries,
          tone: 'warn',
          values: trends.map((p) => p.total_cost),
        },
      ],
    },
  ];
}

/** Top models ranked by token usage, rendered as a BarList distribution. */
export function buildModelBarLists(
  models: readonly ModelMetrics[],
  title: string,
  ariaLabel: string,
  limit = 8,
): UiBarListCard[] {
  if (models.length === 0) return [];
  const top = [...models]
    .sort((a, b) => b.total_tokens - a.total_tokens)
    .slice(0, limit);
  return [
    {
      title,
      ariaLabel,
      items: top.map((model) => ({
        label: shortModelName(model.model),
        value: model.total_tokens,
        valueLabel: formatCount(model.total_tokens),
        tone: 'info',
      })),
    },
  ];
}

export interface ModelSectionLabels {
  splitTitle: string;
  inputTokens: string;
  outputTokens: string;
  providers: string;
}

export function buildModelSections(
  summary: ModelUsageSummary,
  labels: ModelSectionLabels,
): UiMetaSection[] {
  const input = summary.models.reduce((sum, m) => sum + m.total_input_tokens, 0);
  const output = summary.models.reduce((sum, m) => sum + m.total_output_tokens, 0);
  const providers = new Set(summary.models.map((m) => m.provider)).size;
  return [
    {
      title: labels.splitTitle,
      rows: [
        { label: labels.inputTokens, value: formatCount(input) },
        { label: labels.outputTokens, value: formatCount(output) },
        { label: labels.providers, value: String(providers) },
      ],
    },
  ];
}
