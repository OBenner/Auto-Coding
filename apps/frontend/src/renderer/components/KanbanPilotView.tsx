/**
 * Kanban pilot on the shared design system (U1/U2).
 *
 * Renders `libs/ui`'s KanbanBoard through the task-store AutoCodeClient
 * adapter; selecting a card opens the shared TaskDetail inline (U2), so the
 * whole flow — board → detail → back — runs on the new UI end to end.
 * Reachable via the "Kanban (new UI)" sidebar view next to the legacy board.
 */

import { useMemo, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AutoCodeClientProvider,
  KanbanBoard as UiKanbanBoard,
  TaskDetail as UiTaskDetail,
  useTask,
  useTasks,
} from '@auto-code/ui';
import type { KanbanColumn, TaskStatus } from '@auto-code/ui';
import { useTaskStore } from '../stores/task-store';
import { createTaskStoreAutoCodeClient } from '../lib/autoCodeClient';

function usePilotColumns(): KanbanColumn[] {
  const { t } = useTranslation(['kanban']);
  return useMemo<KanbanColumn[]>(
    () => [
      { status: 'draft', label: t('kanban:pilot.columns.draft') },
      { status: 'running', label: t('kanban:pilot.columns.running') },
      { status: 'review', label: t('kanban:pilot.columns.review') },
      { status: 'done', label: t('kanban:pilot.columns.done') },
    ],
    [t],
  );
}

function PilotBoard({ onOpen }: Readonly<{ onOpen: (id: string) => void }>) {
  const { t } = useTranslation(['kanban']);
  const { tasks, loading, error, reload } = useTasks();
  const columns = usePilotColumns();

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
          onSelectTask={(task) => onOpen(task.id)}
        />
      )}
    </div>
  );
}

function PilotDetail({
  id,
  onBack,
}: Readonly<{ id: string; onBack: () => void }>) {
  const columns = usePilotColumns();
  const { task, loading, error, reload } = useTask(id);

  const statusLabels = useMemo<Partial<Record<TaskStatus, string>>>(
    () =>
      Object.fromEntries(columns.map((column) => [column.status, column.label])),
    [columns],
  );

  return (
    <div className="h-full overflow-auto">
      <UiTaskDetail
        task={task}
        loading={loading}
        error={error}
        onBack={onBack}
        onRetry={reload}
        statusLabels={statusLabels}
      />
    </div>
  );
}

export function KanbanPilotView() {
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
  const [openId, setOpenId] = useState<string | null>(null);

  return (
    <AutoCodeClientProvider client={client}>
      {openId == null ? (
        <PilotBoard onOpen={setOpenId} />
      ) : (
        <PilotDetail id={openId} onBack={() => setOpenId(null)} />
      )}
    </AutoCodeClientProvider>
  );
}
