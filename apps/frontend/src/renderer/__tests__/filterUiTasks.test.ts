/**
 * Tests for the shared board filtering (U3): the pure filter behind the
 * BoardToolbar search box and filter chips.
 */

import { describe, expect, it } from 'vitest';
import { filterUiTasks } from '@auto-code/ui';
import type { UiTask } from '@auto-code/ui';

const TASKS: UiTask[] = [
  { id: '001', title: 'Add user authentication', status: 'running', description: 'JWT + refresh flow' },
  { id: '002', title: 'Export usage report', status: 'draft' },
  { id: '003', title: 'Flaky e2e retry', status: 'review', description: 'uploads time out' },
  { id: '004', title: 'Spec index', status: 'done' },
];

describe('filterUiTasks', () => {
  it('returns everything for an empty or whitespace query', () => {
    expect(filterUiTasks(TASKS, {})).toHaveLength(4);
    expect(filterUiTasks(TASKS, { query: '   ' })).toHaveLength(4);
  });

  it('matches id, title, and description case-insensitively', () => {
    expect(filterUiTasks(TASKS, { query: '003' }).map((t) => t.id)).toEqual(['003']);
    expect(filterUiTasks(TASKS, { query: 'AUTHENTICATION' }).map((t) => t.id)).toEqual(['001']);
    expect(filterUiTasks(TASKS, { query: 'time out' }).map((t) => t.id)).toEqual(['003']);
  });

  it('narrows by status and combines it with the query', () => {
    expect(filterUiTasks(TASKS, { status: 'review' }).map((t) => t.id)).toEqual(['003']);
    expect(filterUiTasks(TASKS, { query: 'e', status: 'running' }).map((t) => t.id)).toEqual(['001']);
    expect(filterUiTasks(TASKS, { query: 'uploads', status: 'running' })).toHaveLength(0);
  });

  it('handles tasks without descriptions', () => {
    expect(filterUiTasks(TASKS, { query: 'export' }).map((t) => t.id)).toEqual(['002']);
  });
});
