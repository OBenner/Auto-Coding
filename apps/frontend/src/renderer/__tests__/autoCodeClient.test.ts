/**
 * Tests for the task-store AutoCodeClient adapter (U1): status/progress
 * mapping and the live-subscription bridge over a fake store.
 */

import { describe, expect, it } from 'vitest';
import {
  computeProgress,
  createTaskStoreAutoCodeClient,
  mapStatus,
  mapTaskToUiTask,
} from '../lib/autoCodeClient';
import type { TaskStoreLike, UiTaskBadgeLabels } from '../lib/autoCodeClient';
import type { Subtask, Task } from '../../shared/types/task';

const LABELS: UiTaskBadgeLabels = { error: 'Error', prCreated: 'PR' };

let subtaskSeq = 0;

function makeSubtask(status: Subtask['status']): Subtask {
  subtaskSeq += 1;
  return {
    id: `s-${subtaskSeq}`,
    title: `Subtask ${subtaskSeq}`,
    description: 'x',
    status,
    files: [],
  };
}

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 't1',
    specId: '001-x',
    projectId: 'p1',
    title: 'Do the thing',
    description: '',
    status: 'backlog',
    subtasks: [],
    ...overrides,
  } as Task;
}

describe('mapStatus', () => {
  it('maps every desktop status onto the shared closed set', () => {
    expect(mapStatus('backlog')).toBe('draft');
    expect(mapStatus('queue')).toBe('draft');
    expect(mapStatus('in_progress')).toBe('running');
    expect(mapStatus('ai_review')).toBe('review');
    expect(mapStatus('human_review')).toBe('review');
    expect(mapStatus('error')).toBe('review');
    expect(mapStatus('done')).toBe('done');
    expect(mapStatus('pr_created')).toBe('done');
  });
});

describe('computeProgress', () => {
  it('is undefined without subtasks and a rounded percent with them', () => {
    expect(computeProgress(makeTask())).toBeUndefined();
    const task = makeTask({
      subtasks: [
        makeSubtask('completed'),
        makeSubtask('completed'),
        makeSubtask('pending'),
      ],
    });
    expect(computeProgress(task)).toBe(67);
  });
});

describe('mapTaskToUiTask', () => {
  it('adds an Error badge for errored tasks (surfaced in Review)', () => {
    const ui = mapTaskToUiTask(makeTask({ status: 'error' }), LABELS);
    expect(ui.status).toBe('review');
    expect(ui.badges).toEqual([{ label: 'Error', tone: 'bad' }]);
  });

  it('adds a PR badge for pr_created tasks', () => {
    const ui = mapTaskToUiTask(makeTask({ status: 'pr_created' }), LABELS);
    expect(ui.status).toBe('done');
    expect(ui.badges).toEqual([{ label: 'PR', tone: 'good' }]);
  });

  it('omits badges and empty descriptions otherwise', () => {
    const ui = mapTaskToUiTask(makeTask(), LABELS);
    expect(ui).toEqual({
      id: 't1',
      title: 'Do the thing',
      status: 'draft',
      description: undefined,
      badges: undefined,
      progress: undefined,
    });
  });
});

describe('createTaskStoreAutoCodeClient', () => {
  function makeFakeStore(initial: Task[]): TaskStoreLike & {
    push(tasks: Task[]): void;
  } {
    let state = { tasks: initial };
    const listeners = new Set<(s: { tasks: Task[] }) => void>();
    return {
      getState: () => state,
      subscribe(listener) {
        listeners.add(listener);
        return () => listeners.delete(listener);
      },
      push(tasks: Task[]) {
        state = { tasks };
        listeners.forEach((listener) => listener(state));
      },
    };
  }

  it('lists mapped tasks and pushes live updates until unsubscribed', async () => {
    const store = makeFakeStore([makeTask()]);
    const client = createTaskStoreAutoCodeClient(store, LABELS);

    const initial = await client.listTasks();
    expect(initial.map((task) => task.id)).toEqual(['t1']);

    const seen: string[][] = [];
    const unsubscribe = client.subscribeTasks?.((tasks) =>
      seen.push(tasks.map((task) => task.id)),
    );
    store.push([makeTask(), makeTask({ id: 't2', status: 'in_progress' })]);
    expect(seen).toEqual([['t1', 't2']]);

    unsubscribe?.();
    store.push([makeTask({ id: 't3' })]);
    expect(seen).toEqual([['t1', 't2']]);
  });
});
