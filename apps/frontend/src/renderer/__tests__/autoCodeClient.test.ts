/**
 * Tests for the task-store AutoCodeClient adapter (U1): status/progress
 * mapping and the live-subscription bridge over a fake store.
 */

import { describe, expect, it } from 'vitest';
import {
  computeProgress,
  createTaskStoreAutoCodeClient,
  formatElapsed,
  mapStatus,
  mapTaskToUiTask,
  mapTaskToUiTaskDetail,
} from '../lib/autoCodeClient';
import type { TaskStoreLike, UiTaskBadgeLabels } from '../lib/autoCodeClient';
import type { ExecutionProgress, Subtask, Task } from '../../shared/types/task';

const CHIPS: UiTaskBadgeLabels['statusChips'] = {
  backlog: 'Backlog',
  queue: 'Queue',
  in_progress: 'Coding',
  ai_review: 'AI review',
  human_review: 'Human review',
  done: 'Done',
  pr_created: 'PR created',
  error: 'Error',
};

const PHASES: UiTaskBadgeLabels['phases'] = {
  idle: 'Idle',
  planning: 'Planning',
  coding: 'Coding',
  test_generation: 'Test generation',
  qa_review: 'QA review',
  qa_fixing: 'QA fixing',
  complete: 'Complete',
  failed: 'Failed',
};

const LABELS: UiTaskBadgeLabels = {
  error: 'Error',
  prCreated: 'PR',
  statusChips: CHIPS,
  phases: PHASES,
};

function makeExecutionProgress(
  overrides: Partial<ExecutionProgress> = {},
): ExecutionProgress {
  return {
    phase: 'coding',
    phaseProgress: 50,
    overallProgress: 40,
    ...overrides,
  };
}

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
    logs: [],
    createdAt: new Date('2026-01-01T00:00:00Z'),
    updatedAt: new Date('2026-01-01T00:00:00Z'),
    ...overrides,
  };
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
      statusChip: { label: 'Backlog', tone: 'neutral' },
      badges: undefined,
      progress: undefined,
      meta: undefined,
    });
  });
});

describe('formatElapsed', () => {
  it('renders minutes, sub-minute, and hour+minute forms', () => {
    expect(formatElapsed(30)).toBe('<1m');
    expect(formatElapsed(22 * 60)).toBe('22m');
    expect(formatElapsed(3900)).toBe('1h 05m');
  });

  it('returns an empty string for negative or non-finite input', () => {
    expect(formatElapsed(-5)).toBe('');
    expect(formatElapsed(Number.NaN)).toBe('');
    expect(formatElapsed(Number.POSITIVE_INFINITY)).toBe('');
  });
});

describe('card meta row', () => {
  it('combines the phase label and elapsed time for active tasks', () => {
    const task = makeTask({
      status: 'in_progress',
      executionProgress: makeExecutionProgress({ elapsed_seconds: 22 * 60 }),
    });
    expect(mapTaskToUiTask(task, LABELS).meta).toEqual(['Coding', '22m']);
  });

  it('renders phase-only meta when elapsed time is unknown', () => {
    const task = makeTask({
      status: 'ai_review',
      executionProgress: makeExecutionProgress({ phase: 'qa_review' }),
    });
    expect(mapTaskToUiTask(task, LABELS).meta).toEqual(['QA review']);
  });

  it('omits meta without execution progress or for the idle phase', () => {
    expect(mapTaskToUiTask(makeTask(), LABELS).meta).toBeUndefined();
    const idle = makeTask({
      executionProgress: makeExecutionProgress({ phase: 'idle', elapsed_seconds: 60 }),
    });
    expect(mapTaskToUiTask(idle, LABELS).meta).toBeUndefined();
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

  it('skips store updates that did not replace the tasks array', () => {
    const tasks = [makeTask()];
    const store = makeFakeStore(tasks);
    const client = createTaskStoreAutoCodeClient(store, LABELS);

    const seen: number[] = [];
    client.subscribeTasks?.((next) => seen.push(next.length));

    // Unrelated state change: same tasks reference -> no re-map, no onChange.
    store.push(tasks);
    expect(seen).toEqual([]);

    store.push([makeTask(), makeTask({ id: 't2' })]);
    expect(seen).toEqual([2]);
  });

  it('resolves labels lazily through a getter so the client can stay stable', () => {
    const store = makeFakeStore([makeTask({ status: 'error' })]);
    let labels: UiTaskBadgeLabels = {
      error: 'Error',
      prCreated: 'PR',
      statusChips: CHIPS,
      phases: PHASES,
    };
    const client = createTaskStoreAutoCodeClient(store, () => labels);

    const seen: string[] = [];
    client.subscribeTasks?.((tasks) => {
      seen.push(tasks[0].badges?.[0]?.label ?? '');
    });

    store.push([makeTask({ id: 'a', status: 'error' })]);
    // locale switch
    labels = { error: 'Erreur', prCreated: 'PR', statusChips: CHIPS, phases: PHASES };
    store.push([makeTask({ id: 'b', status: 'error' })]);
    expect(seen).toEqual(['Error', 'Erreur']);
  });
});

describe('mapTaskToUiTaskDetail', () => {
  it('adds a subtask breakdown on top of the card fields', () => {
    const task = makeTask({
      subtasks: [
        makeSubtask('completed'),
        makeSubtask('in_progress'),
        makeSubtask('pending'),
        makeSubtask('failed'),
      ],
    });
    const detail = mapTaskToUiTaskDetail(task, LABELS);
    expect(detail.id).toBe('t1');
    expect(detail.progressBreakdown).toEqual({
      completed: 1,
      inProgress: 1,
      pending: 1,
      failed: 1,
      total: 4,
    });
  });

  it('omits the breakdown without subtasks', () => {
    expect(mapTaskToUiTaskDetail(makeTask(), LABELS).progressBreakdown).toBeUndefined();
  });
});

describe('createTaskStoreAutoCodeClient.getTask', () => {
  const makeDetailStore = () => ({
    getState: () => ({ tasks: [makeTask({ id: 'known' })] }),
    subscribe: () => () => {},
  });

  it('resolves detail from the store and errors on unknown ids', async () => {
    const client = createTaskStoreAutoCodeClient(makeDetailStore(), LABELS);
    const detail = await client.getTask?.('known');
    expect(detail?.id).toBe('known');
    expect(detail?.specContent).toBeUndefined();
    await expect(client.getTask?.('missing')).rejects.toThrow('not found');
  });

  it('injects the spec body from the loadSpecContent option', async () => {
    const client = createTaskStoreAutoCodeClient(makeDetailStore(), LABELS, {
      loadSpecContent: async (task) => `# Spec for ${task.id}`,
    });
    const detail = await client.getTask?.('known');
    expect(detail?.specContent).toBe('# Spec for known');
  });

  it('leaves specContent undefined when the loader returns null', async () => {
    const client = createTaskStoreAutoCodeClient(makeDetailStore(), LABELS, {
      loadSpecContent: async () => null,
    });
    const detail = await client.getTask?.('known');
    expect(detail?.specContent).toBeUndefined();
  });

  it('still resolves the detail when the loader fails', async () => {
    const client = createTaskStoreAutoCodeClient(makeDetailStore(), LABELS, {
      loadSpecContent: async () => {
        throw new Error('IPC unavailable');
      },
    });
    const detail = await client.getTask?.('known');
    expect(detail?.id).toBe('known');
    expect(detail?.specContent).toBeUndefined();
  });
});

describe('statusChip', () => {
  it('labels the chip from the injected map with a status-matched tone', () => {
    const running = mapTaskToUiTask(makeTask({ status: 'in_progress' }), LABELS);
    expect(running.statusChip).toEqual({ label: 'Coding', tone: 'info' });
    const errored = mapTaskToUiTask(makeTask({ status: 'error' }), LABELS);
    expect(errored.statusChip).toEqual({ label: 'Error', tone: 'bad' });
  });
});
