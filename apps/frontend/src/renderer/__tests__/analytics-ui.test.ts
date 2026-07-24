/**
 * Tests for the AnalyticsReport → AnalyticsDashboard mapping helpers.
 */

import { describe, expect, it } from 'vitest';
import {
  buildCharts,
  buildKpis,
  buildSections,
  formatCost,
  formatCount,
  formatPercent,
  sampleLabels,
  shortDate,
  successRateTone,
} from '../lib/analytics-ui';
import type { AnalyticsReport } from '../../shared/types';

function makeReport(overrides: Partial<AnalyticsReport> = {}): AnalyticsReport {
  return {
    summary: {
      total_specs: 112,
      completed_specs: 98,
      failed_specs: 9,
      in_progress_specs: 5,
      overall_success_rate: 87.4,
      total_cost: 142.1,
      total_tokens: 4_200_000,
      agent_stats: {},
      complexity_stats: {},
      qa_stats: {
        total_reviews: 204,
        approved: 181,
        rejected: 23,
        rejection_rate: 11.3,
        common_issues: {},
      },
      last_updated: '2026-05-22T00:00:00Z',
    },
    trends: [
      { date: '2026-05-01', success_rate: 80, total_tasks: 10, total_cost: 12 },
      { date: '2026-05-08', success_rate: 84, total_tasks: 14, total_cost: 16 },
      { date: '2026-05-15', success_rate: 87, total_tasks: 16, total_cost: 18 },
    ],
    generated_at: '2026-05-22T00:00:00Z',
    ...overrides,
  };
}

const KPI_LABELS = {
  specs: 'specs',
  successRate: 'success',
  cost: 'cost',
  tokens: 'tokens',
  specsSub: 'all time',
  tokensSub: 'in+out',
};

describe('formatters', () => {
  it('formatCount uses k/M with one decimal', () => {
    expect(formatCount(420)).toBe('420');
    expect(formatCount(4_200)).toBe('4.2k');
    expect(formatCount(4_200_000)).toBe('4.2M');
    expect(formatCount(-5)).toBe('0');
  });

  it('formatPercent rounds to a whole percent', () => {
    expect(formatPercent(87.4)).toBe('87%');
    expect(formatPercent(Number.NaN)).toBe('0%');
  });

  it('formatCost renders two-decimal USD, clamping bad input', () => {
    expect(formatCost(142.1)).toBe('$142.10');
    expect(formatCost(-1)).toBe('$0.00');
  });
});

describe('successRateTone', () => {
  it('buckets the rate into a tone', () => {
    expect(successRateTone(90)).toBe('good');
    expect(successRateTone(80)).toBe('good');
    expect(successRateTone(60)).toBe('warn');
    expect(successRateTone(40)).toBe('bad');
  });
});

describe('shortDate', () => {
  it('formats ISO calendar dates in UTC', () => {
    expect(shortDate('2026-05-22', 'en-US')).toBe('May 22');
  });

  it('passes non-ISO strings through verbatim', () => {
    expect(shortDate('week 5', 'en-US')).toBe('week 5');
  });
});

describe('sampleLabels', () => {
  it('keeps short label lists intact', () => {
    expect(sampleLabels(['a', 'b', 'c'], 6)).toEqual(['a', 'b', 'c']);
  });

  it('evenly samples down to max, keeping first and last', () => {
    const labels = Array.from({ length: 12 }, (_, i) => String(i));
    const sampled = sampleLabels(labels, 4);
    expect(sampled).toHaveLength(4);
    expect(sampled[0]).toBe('0');
    expect(sampled[3]).toBe('11');
  });
});

describe('buildKpis', () => {
  it('maps summary + trend sparklines onto four tiles', () => {
    const kpis = buildKpis(makeReport(), KPI_LABELS);
    expect(kpis).toHaveLength(4);
    expect(kpis[0]).toMatchObject({ value: '112', label: 'specs', trendTone: 'info' });
    expect(kpis[1]).toMatchObject({ value: '87%', tone: 'good', trendTone: 'good' });
    expect(kpis[2].value).toBe('$142.10');
    expect(kpis[3].value).toBe('4.2M');
    // trend series come from the report trends.
    expect(kpis[0].trend).toEqual([10, 14, 16]);
  });

  it('omits sparklines when there are fewer than two trend points', () => {
    const kpis = buildKpis(
      makeReport({ trends: [{ date: '2026-05-01', success_rate: 80, total_tasks: 10, total_cost: 12 }] }),
      KPI_LABELS,
    );
    expect(kpis[0].trend).toBeUndefined();
  });

  it('tones a failing success rate red', () => {
    const kpis = buildKpis(
      makeReport({ summary: { ...makeReport().summary, overall_success_rate: 40 } }),
      KPI_LABELS,
    );
    expect(kpis[1].tone).toBe('bad');
    expect(kpis[1].trendTone).toBe('bad');
  });
});

describe('buildCharts', () => {
  const labels = {
    velocityTitle: 'Velocity',
    velocityAria: 'velocity',
    tasksSeries: 'Tasks',
    rateTitle: 'Rate',
    rateAria: 'rate',
    rateSeries: 'Success rate',
  };

  it('builds velocity + rate charts with sampled UTC date labels', () => {
    const charts = buildCharts(makeReport(), labels, 'en-US');
    expect(charts.map((c) => c.title)).toEqual(['Velocity', 'Rate']);
    expect(charts[0].series[0].values).toEqual([10, 14, 16]);
    expect(charts[0].xLabels).toEqual(['May 1', 'May 8', 'May 15']);
    expect(charts[1].series[0].values).toEqual([80, 84, 87]);
  });

  it('returns no charts without at least two trend points', () => {
    expect(buildCharts(makeReport({ trends: [] }), labels)).toEqual([]);
  });
});

describe('buildSections', () => {
  it('builds outcome + QA summary cards', () => {
    const sections = buildSections(makeReport(), {
      outcomesTitle: 'Outcomes',
      completed: 'Completed',
      failed: 'Failed',
      inProgress: 'In progress',
      qaTitle: 'QA',
      reviews: 'Reviews',
      approved: 'Approved',
      rejectionRate: 'Rejection rate',
    });
    expect(sections[0].rows).toEqual([
      { label: 'Completed', value: '98' },
      { label: 'Failed', value: '9' },
      { label: 'In progress', value: '5' },
    ]);
    expect(sections[1].rows[2]).toEqual({ label: 'Rejection rate', value: '11%' });
  });
});
