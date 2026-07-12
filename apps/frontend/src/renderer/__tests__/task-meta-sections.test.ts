/**
 * Tests for the TaskDetail meta-rail builder: workspace + cost & tokens
 * cards assembled from the store Task, TaskTokenStats, and CostReport.
 */

import { describe, expect, it } from 'vitest';
import {
  buildTaskMetaSections,
  formatTokenCount,
} from '../lib/task-meta-sections';
import type { TaskMetaLabels } from '../lib/task-meta-sections';
import type {
  CostReport,
  Task,
  TaskTokenStats,
} from '../../shared/types';

const LABELS: TaskMetaLabels = {
  workspaceTitle: 'Workspace',
  costTokensTitle: 'Cost & tokens',
  specId: 'Spec',
  location: 'Location',
  updated: 'Updated',
  cost: 'Cost',
  inputTokens: 'Input',
  outputTokens: 'Output',
  sessions: 'Sessions',
};

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    specId: '004-auth',
    projectId: 'p1',
    title: 'Add user authentication',
    description: '',
    status: 'in_progress',
    subtasks: [],
    logs: [],
    createdAt: new Date('2026-01-01T00:00:00Z'),
    updatedAt: new Date('2026-01-02T00:00:00Z'),
    ...overrides,
  };
}

function makeTokenStats(overrides: Partial<TaskTokenStats> = {}): TaskTokenStats {
  return {
    phases: {
      planning: {
        phase: 'planning',
        input_tokens: 12_000,
        output_tokens: 3_000,
        total_tokens: 15_000,
        session_count: 2,
        updated_at: '2026-01-02T00:00:00Z',
      },
      coding: {
        phase: 'coding',
        input_tokens: 100_000,
        output_tokens: 25_000,
        total_tokens: 125_000,
        session_count: 7,
        updated_at: '2026-01-02T00:00:00Z',
      },
    },
    total_input_tokens: 112_000,
    total_output_tokens: 28_000,
    total_tokens: 140_000,
    created_at: '2026-01-01T00:00:00Z',
    updated_at: '2026-01-02T00:00:00Z',
    ...overrides,
  };
}

const COST_REPORT: CostReport = {
  spec_dir: '/x/specs/004-auth',
  total_cost: 4.867,
  records: [],
  last_updated: '2026-01-02T00:00:00Z',
};

describe('formatTokenCount', () => {
  it('renders verbatim, k, and M forms', () => {
    expect(formatTokenCount(950)).toBe('950');
    expect(formatTokenCount(112_000)).toBe('112k');
    expect(formatTokenCount(1_200_000)).toBe('1.2M');
  });

  it('clamps negative and non-finite input to 0', () => {
    expect(formatTokenCount(-5)).toBe('0');
    expect(formatTokenCount(Number.NaN)).toBe('0');
  });

  it('pins the k/M boundary behavior', () => {
    expect(formatTokenCount(999_999)).toBe('1000k');
    expect(formatTokenCount(1_234_000_000)).toBe('1234.0M');
  });
});

describe('buildTaskMetaSections', () => {
  it('builds workspace and cost cards from full data', () => {
    const task = makeTask({ location: 'worktree' });
    const sections = buildTaskMetaSections(task, makeTokenStats(), COST_REPORT, LABELS);
    expect(sections).toHaveLength(2);

    const [workspace, cost] = sections;
    expect(workspace.title).toBe('Workspace');
    expect(workspace.rows[0]).toEqual({ label: 'Spec', value: '004-auth' });
    expect(workspace.rows[1]).toEqual({ label: 'Location', value: 'worktree' });
    expect(workspace.rows[2].label).toBe('Updated');

    expect(cost.title).toBe('Cost & tokens');
    expect(cost.rows).toEqual([
      { label: 'Cost', value: '$4.87' },
      { label: 'Input', value: '112k' },
      { label: 'Output', value: '28k' },
      { label: 'Sessions', value: '9' },
    ]);
  });

  it('omits the cost card entirely without stats or report', () => {
    const sections = buildTaskMetaSections(makeTask(), null, null, LABELS);
    expect(sections).toHaveLength(1);
    expect(sections[0].title).toBe('Workspace');
  });

  it('renders a tokens-only cost card when the report is missing', () => {
    const sections = buildTaskMetaSections(makeTask(), makeTokenStats(), null, LABELS);
    const cost = sections[1];
    expect(cost.rows.map((row) => row.label)).toEqual([
      'Input',
      'Output',
      'Sessions',
    ]);
  });

  it('skips the sessions row when phase counts sum to zero', () => {
    const stats = makeTokenStats({ phases: {} });
    const sections = buildTaskMetaSections(makeTask(), stats, COST_REPORT, LABELS);
    const cost = sections[1];
    expect(cost.rows.map((row) => row.label)).toEqual(['Cost', 'Input', 'Output']);
  });

  it('omits the location row when the task has none', () => {
    const sections = buildTaskMetaSections(makeTask(), null, null, LABELS);
    expect(sections[0].rows.map((row) => row.label)).toEqual(['Spec', 'Updated']);
  });

  it('renders a cost-only card when token stats are missing', () => {
    const sections = buildTaskMetaSections(makeTask(), null, COST_REPORT, LABELS);
    expect(sections).toHaveLength(2);
    expect(sections[1].rows).toEqual([{ label: 'Cost', value: '$4.87' }]);
  });

  it('skips the cost row on malformed, negative, or non-finite total_cost', () => {
    const malformed = (total_cost: unknown): CostReport =>
      ({ ...COST_REPORT, total_cost }) as CostReport;
    for (const bad of ['4.87', null, undefined, -1, Number.POSITIVE_INFINITY]) {
      const sections = buildTaskMetaSections(
        makeTask(),
        makeTokenStats(),
        malformed(bad),
        LABELS,
      );
      // The rail must survive a bad cost_report.json: workspace card intact,
      // token rows intact, only the cost row dropped.
      expect(sections).toHaveLength(2);
      expect(sections[1].rows.map((row) => row.label)).toEqual([
        'Input',
        'Output',
        'Sessions',
      ]);
    }
  });
});
