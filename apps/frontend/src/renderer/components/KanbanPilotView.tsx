/**
 * Kanban pilot on the shared design system (U1).
 *
 * Renders `libs/ui`'s KanbanBoard through the task-store AutoCodeClient
 * adapter — the first screen served by the shared UI in the desktop target.
 * Reachable via the "Kanban (new UI)" sidebar view next to the legacy board.
 */

import { useMemo, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AutoCodeClientProvider,
  KanbanBoard as UiKanbanBoard,
  useTasks,
} from '@auto-code/ui';
import type { KanbanColumn, UiTask } from '@auto-code/ui';
import type { Task } from '../../shared/types/task';
import { useTaskStore } from '../stores/task-store';
import { createTaskStoreAutoCodeClient } from '../lib/autoCodeClient';

export interface KanbanPilotViewProps {
  onTaskSelect?: (task: Task) => void;
}

function PilotBoard({ onTaskSelect }: Readonly<KanbanPilotViewProps>) {
  const { t } = useTranslation(['kanban']);
  const { tasks, loading, error, reload } = useTasks();

  const columns = useMemo<KanbanColumn[]>(
    () => [
      { status: 'draft', label: t('kanban:pilot.columns.draft') },
      { status: 'running', label: t('kanban:pilot.columns.running') },
      { status: 'review', label: t('kanban:pilot.columns.review') },
      { status: 'done', label: t('kanban:pilot.columns.done') },
    ],
    [t],
  );

  const handleSelect = (uiTask: UiTask) => {
    const task = useTaskStore
      .getState()
      .tasks.find((candidate) => candidate.id === uiTask.id);
    if (task) onTaskSelect?.(task);
  };

  return (
    <div className="h-full overflow-auto p-4">
      <h1 className="mb-4 text-lg font-semibold">{t('kanban:pilot.title')}</h1>
      {loading && <p>{t('kanban:pilot.loading')}</p>}
      {error && (
        <p role="alert">
          {t('kanban:pilot.error')}{' '}
          <button type="button" onClick={reload}>
            {t('kanban:pilot.retry')}
          </button>
        </p>
      )}
      {!loading && !error && (
        <UiKanbanBoard
          tasks={tasks}
          columns={columns}
          onSelectTask={handleSelect}
        />
      )}
    </div>
  );
}

export function KanbanPilotView({ onTaskSelect }: Readonly<KanbanPilotViewProps>) {
  const { t } = useTranslation(['kanban']);
  // Keep the client identity stable across locale switches (recreating it
  // would tear down and re-establish the store subscription): the labels are
  // read through a ref that always holds the current translations.
  const labelsRef = useRef({ error: '', prCreated: '' });
  labelsRef.current = {
    error: t('kanban:pilot.badges.error'),
    prCreated: t('kanban:pilot.badges.prCreated'),
  };
  const client = useMemo(
    () => createTaskStoreAutoCodeClient(useTaskStore, () => labelsRef.current),
    [],
  );
  return (
    <AutoCodeClientProvider client={client}>
      <PilotBoard onTaskSelect={onTaskSelect} />
    </AutoCodeClientProvider>
  );
}
