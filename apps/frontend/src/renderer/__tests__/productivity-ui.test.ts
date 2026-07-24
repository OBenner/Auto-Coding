/**
 * Tests for the Productivity{Summary,Trends} → AnalyticsDashboard mappers.
 */

import { describe, expect, it } from 'vitest';
import {
  buildProductivityCharts,
  buildProductivityKpis,
  buildProductivitySections,
  formatHours,
} from '../lib/productivity-ui';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
} from '../../shared/types';

function makeSummary(overrides: Partial<ProductivitySummary> = {}): ProductivitySummary {
  return {
    period_start: '2026-05-01T00:00:00Z',
    period_end: '2026-05-22T00:00:00Z',
    total_specs: 60,
    completed_specs: 52,
    in_progress_specs: 5,
    failed_specs: 3,
    total_time_saved_hours: 142.4,
    total_build_time_hours: 38.7,
    average_success_rate: 0.87,
    first_attempt_success_rate: 0.71,
    specs_by_type: {},
    specs_by_complexity: {},
    average_subtasks_per_spec: 4.33,
    average_qa_iterations: 1.2,
    total_subtasks_completed: 225,
    specs: [],
    ...overrides,
  } as ProductivitySummary;
}

const TRENDS: ProductivityTrendPoint[] = [
  { date: '2026-05-01', total_specs: 5, completed_specs: 4, time_saved_hours: 8, success_rate: 0.8 },
  { date: '2026-05-08', total_specs: 7, completed_specs: 6, time_saved_hours: 12, success_rate: 0.85 },
  { date: '2026-05-15', total_specs: 8, completed_specs: 7, time_saved_hours: 14, success_rate: 0.9 },
];

const KPI_LABELS = {
  specs: 'specs',
  specsSub: 'period',
  timeSaved: 'saved',
  timeSavedSub: 'est',
  successRate: 'success',
  buildTime: 'build',
  buildTimeSub: 'total',
};

describe('formatHours', () => {
  it('rounds to whole hours with an h unit', () => {
    expect(formatHours(52.4)).toBe('52h');
    expect(formatHours(0)).toBe('0h');
    expect(formatHours(-5)).toBe('0h');
  });
});

describe('buildProductivityKpis', () => {
  it('maps the summary onto four tiles, converting the 0-1 rate to a percent', () => {
    const kpis = buildProductivityKpis(makeSummary(), TRENDS, KPI_LABELS);
    expect(kpis).toHaveLength(4);
    expect(kpis[0]).toMatchObject({ value: '52', label: 'specs' });
    expect(kpis[1].value).toBe('142h');
    expect(kpis[2]).toMatchObject({ value: '87%', tone: 'good' });
    expect(kpis[3].value).toBe('39h');
    // sparkline series come from the trends.
    expect(kpis[0].trend).toEqual([4, 6, 7]);
    expect(kpis[2].trend).toEqual([80, 85, 90]);
  });

  it('omits sparklines when trends are too short', () => {
    const kpis = buildProductivityKpis(makeSummary(), [TRENDS[0]], KPI_LABELS);
    expect(kpis[0].trend).toBeUndefined();
  });

  it('tones a low success rate red', () => {
    const kpis = buildProductivityKpis(
      makeSummary({ average_success_rate: 0.4 }),
      TRENDS,
      KPI_LABELS,
    );
    expect(kpis[2].tone).toBe('bad');
  });
});

describe('buildProductivityCharts', () => {
  const labels = {
    velocityTitle: 'Completed',
    velocityAria: 'v',
    velocitySeries: 'Completed',
    timeSavedTitle: 'Time saved',
    timeSavedAria: 't',
    timeSavedSeries: 'Hours',
  };

  it('builds velocity + time-saved charts with UTC date labels', () => {
    const charts = buildProductivityCharts(TRENDS, labels, 'en-US');
    expect(charts.map((c) => c.title)).toEqual(['Completed', 'Time saved']);
    expect(charts[0].series[0].values).toEqual([4, 6, 7]);
    expect(charts[1].series[0].values).toEqual([8, 12, 14]);
    expect(charts[0].xLabels).toEqual(['May 1', 'May 8', 'May 15']);
  });

  it('returns no charts without at least two trend points', () => {
    expect(buildProductivityCharts([TRENDS[0]], labels)).toEqual([]);
  });
});

describe('buildProductivitySections', () => {
  it('builds outcome + effort cards with one-decimal effort figures', () => {
    const sections = buildProductivitySections(makeSummary(), {
      outcomesTitle: 'Outcomes',
      completed: 'Completed',
      inProgress: 'In progress',
      failed: 'Failed',
      effortTitle: 'Effort',
      subtasksPerSpec: 'Subtasks / spec',
      qaIterations: 'QA iterations',
      firstAttempt: 'First-attempt rate',
    });
    expect(sections[0].rows[0]).toEqual({ label: 'Completed', value: '52' });
    expect(sections[1].rows[0]).toEqual({ label: 'Subtasks / spec', value: '4.3' });
    expect(sections[1].rows[2]).toEqual({ label: 'First-attempt rate', value: '71%' });
  });
});
