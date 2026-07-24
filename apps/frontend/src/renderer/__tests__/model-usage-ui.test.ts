/**
 * Tests for the ModelUsage{Summary,Trends} → AnalyticsDashboard mappers.
 */

import { describe, expect, it } from 'vitest';
import {
  buildModelBarLists,
  buildModelCharts,
  buildModelKpis,
  buildModelSections,
  shortModelName,
} from '../lib/model-usage-ui';
import type {
  ModelMetrics,
  ModelUsageSummary,
  ModelUsageTrendPoint,
} from '../../shared/types';

function makeModel(overrides: Partial<ModelMetrics> = {}): ModelMetrics {
  return {
    model: 'anthropic/claude-sonnet-4-5-20250929',
    provider: 'anthropic',
    total_input_tokens: 800_000,
    total_output_tokens: 200_000,
    usage_by_agent: {},
    total_usage_count: 40,
    total_tokens: 1_000_000,
    total_cost: 12.5,
    first_used: null,
    last_used: null,
    ...overrides,
  };
}

function makeSummary(overrides: Partial<ModelUsageSummary> = {}): ModelUsageSummary {
  return {
    period_start: '2026-05-01T00:00:00Z',
    period_end: '2026-05-22T00:00:00Z',
    total_usage_count: 64,
    total_tokens: 1_680_000,
    total_cost: 18.7,
    models: [
      makeModel(),
      makeModel({
        model: 'anthropic/claude-haiku-4-5-20251001',
        total_tokens: 680_000,
        total_input_tokens: 500_000,
        total_output_tokens: 180_000,
        total_cost: 6.2,
      }),
    ],
    agents: [],
    top_models: [],
    ...overrides,
  } as ModelUsageSummary;
}

const TRENDS: ModelUsageTrendPoint[] = [
  { date: '2026-05-01', total_tokens: 400_000, total_cost: 4, usage_count: 12, unique_models: 2 },
  { date: '2026-05-08', total_tokens: 620_000, total_cost: 7, usage_count: 20, unique_models: 2 },
  { date: '2026-05-15', total_tokens: 660_000, total_cost: 8, usage_count: 22, unique_models: 3 },
];

describe('shortModelName', () => {
  it('drops the provider prefix and date suffix', () => {
    expect(shortModelName('anthropic/claude-sonnet-4-5-20250929')).toBe('claude-sonnet-4-5');
    expect(shortModelName('gpt-4o')).toBe('gpt-4o');
  });
});

describe('buildModelKpis', () => {
  const labels = {
    calls: 'calls',
    callsSub: 'all',
    tokens: 'tokens',
    cost: 'cost',
    models: 'models',
    modelsSub: 'distinct',
  };

  it('maps the summary + trend sparklines onto four tiles', () => {
    const kpis = buildModelKpis(makeSummary(), TRENDS, labels);
    expect(kpis.map((k) => k.value)).toEqual(['64', '1.7M', '$18.70', '2']);
    expect(kpis[0].trend).toEqual([12, 20, 22]);
    expect(kpis[2].trend).toEqual([4, 7, 8]);
  });

  it('omits sparklines when trends are too short', () => {
    const kpis = buildModelKpis(makeSummary(), [TRENDS[0]], labels);
    expect(kpis[0].trend).toBeUndefined();
  });
});

describe('buildModelCharts', () => {
  const labels = {
    tokensTitle: 'Tokens',
    tokensAria: 't',
    tokensSeries: 'Tokens',
    costTitle: 'Cost',
    costAria: 'c',
    costSeries: 'Cost',
  };

  it('builds token + cost trend charts with UTC labels', () => {
    const charts = buildModelCharts(TRENDS, labels, 'en-US');
    expect(charts.map((c) => c.title)).toEqual(['Tokens', 'Cost']);
    expect(charts[0].series[0].values).toEqual([400_000, 620_000, 660_000]);
    expect(charts[0].xLabels).toEqual(['May 1', 'May 8', 'May 15']);
  });

  it('returns no charts without at least two trend points', () => {
    expect(buildModelCharts([TRENDS[0]], labels)).toEqual([]);
  });
});

describe('buildModelBarLists', () => {
  it('ranks models by tokens with formatted value labels', () => {
    const lists = buildModelBarLists(makeSummary().models, 'Tokens by model', 'aria');
    expect(lists).toHaveLength(1);
    expect(lists[0].items).toEqual([
      { label: 'claude-sonnet-4-5', value: 1_000_000, valueLabel: '1.0M', tone: 'info' },
      { label: 'claude-haiku-4-5', value: 680_000, valueLabel: '680.0k', tone: 'info' },
    ]);
  });

  it('returns no card when there are no models', () => {
    expect(buildModelBarLists([], 't', 'a')).toEqual([]);
  });
});

describe('buildModelSections', () => {
  it('sums the input/output token split and counts providers', () => {
    const sections = buildModelSections(makeSummary(), {
      splitTitle: 'Split',
      inputTokens: 'Input',
      outputTokens: 'Output',
      providers: 'Providers',
    });
    expect(sections[0].rows).toEqual([
      { label: 'Input', value: '1.3M' },
      { label: 'Output', value: '380.0k' },
      { label: 'Providers', value: '1' },
    ]);
  });
});
