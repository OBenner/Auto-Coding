/**
 * Tests for the MergeAnalytics / ConflictPattern → AnalyticsDashboard mappers.
 */

import { describe, expect, it } from 'vitest';
import {
  buildMergeBarLists,
  buildMergeKpis,
  buildMergeSections,
  formatDuration,
  shortenPath,
} from '../lib/merge-analytics-ui';
import type { ConflictPattern, MergeAnalytics } from '../../shared/types';

function makeAnalytics(overrides: Partial<MergeAnalytics> = {}): MergeAnalytics {
  return {
    total_operations: 84,
    total_files_merged: 312,
    total_conflicts: 12,
    successful_operations: 80,
    failed_operations: 4,
    total_ai_calls: 47,
    total_tokens_used: 1_240_000,
    average_duration_seconds: 125,
    success_rate: 0.95,
    auto_merge_rate: 0.72,
    conflict_patterns: [],
    ...overrides,
  };
}

function makePattern(overrides: Partial<ConflictPattern> = {}): ConflictPattern {
  return {
    file_path: 'apps/frontend/src/renderer/App.tsx',
    location: 'L120',
    occurrence_count: 6,
    severity: 'high',
    tasks_involved: ['001', '002'],
    last_seen: '2026-05-22T00:00:00Z',
    ...overrides,
  };
}

describe('shortenPath', () => {
  it('keeps short paths and truncates deep ones to the trailing segments', () => {
    expect(shortenPath('App.tsx')).toBe('App.tsx');
    expect(shortenPath('a/b')).toBe('a/b');
    expect(shortenPath('apps/frontend/src/App.tsx')).toBe('…/src/App.tsx');
  });
});

describe('formatDuration', () => {
  it('renders seconds and minute+second forms', () => {
    expect(formatDuration(45)).toBe('45s');
    expect(formatDuration(125)).toBe('2m 05s');
    expect(formatDuration(-1)).toBe('0s');
  });
});

describe('buildMergeKpis', () => {
  const labels = {
    operations: 'ops',
    operationsSub: 'all',
    successRate: 'success',
    autoMerge: 'auto',
    conflicts: 'conflicts',
    conflictsSub: 'total',
  };

  it('maps the analytics onto four tiles, converting 0-1 rates to percents', () => {
    const kpis = buildMergeKpis(makeAnalytics(), labels);
    expect(kpis.map((k) => k.value)).toEqual(['84', '95%', '72%', '12']);
    expect(kpis[1].tone).toBe('good');
    expect(kpis[3].tone).toBe('warn');
  });

  it('warns a low success rate and drops the conflict tone at zero', () => {
    const kpis = buildMergeKpis(
      makeAnalytics({ success_rate: 0.6, total_conflicts: 0 }),
      labels,
    );
    expect(kpis[1].tone).toBe('warn');
    expect(kpis[3].tone).toBeUndefined();
  });
});

describe('buildMergeBarLists', () => {
  it('maps conflict patterns to a distribution with severity-toned bars', () => {
    const lists = buildMergeBarLists(
      [
        makePattern({ occurrence_count: 6, severity: 'high' }),
        makePattern({ file_path: 'x/y/z/util.ts', occurrence_count: 3, severity: 'medium' }),
      ],
      'Top conflicts',
      'aria',
    );
    expect(lists).toHaveLength(1);
    expect(lists[0].items).toEqual([
      { label: '…/renderer/App.tsx', value: 6, tone: 'bad' },
      { label: '…/z/util.ts', value: 3, tone: 'warn' },
    ]);
  });

  it('returns no card when there are no patterns', () => {
    expect(buildMergeBarLists([], 't', 'a')).toEqual([]);
  });
});

describe('buildMergeSections', () => {
  it('builds outcome + efficiency cards', () => {
    const sections = buildMergeSections(makeAnalytics(), {
      outcomesTitle: 'Outcomes',
      successful: 'Successful',
      failed: 'Failed',
      filesMerged: 'Files merged',
      efficiencyTitle: 'Efficiency',
      avgDuration: 'Avg duration',
      aiCalls: 'AI calls',
      tokens: 'Tokens',
    });
    expect(sections[0].rows[0]).toEqual({ label: 'Successful', value: '80' });
    expect(sections[1].rows[0]).toEqual({ label: 'Avg duration', value: '2m 05s' });
    expect(sections[1].rows[2]).toEqual({ label: 'Tokens', value: '1.2M' });
  });
});
