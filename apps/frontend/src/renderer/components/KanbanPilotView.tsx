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
  BoardSkeleton,
  BoardView,
  TaskDetail as UiTaskDetail,
  buildBoardViewLabels,
  useTask,
  useTasks,
} from '@auto-code/ui';
import type {
  KanbanColumn,
  TaskDetailTabId,
  TaskStatus,
  UiSubtaskStatus,
} from '@auto-code/ui';
import { useTaskStore } from '../stores/task-store';
import { useProjectStore } from '../stores/project-store';
import { createTaskStoreAutoCodeClient } from '../lib/autoCodeClient';
import type { UiTaskBadgeLabels } from '../lib/autoCodeClient';
import { buildTaskMetaSections } from '../lib/task-meta-sections';
import type { TaskMetaLabels } from '../lib/task-meta-sections';

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
  const labels = useMemo(
    () => buildBoardViewLabels(t, 'kanban:pilot.toolbar'),
    [t],
  );

  return (
    <div className="h-full overflow-auto p-4">
      <h1 className="mb-4 text-lg font-semibold">{t('kanban:pilot.title')}</h1>
      {loading && <BoardSkeleton label={t('kanban:pilot.loading')} />}
      {error && (
        <p role="alert">
          {t('kanban:pilot.error')}{' '}
          <button type="button" onClick={reload}>
            {t('kanban:pilot.retry')}
          </button>
        </p>
      )}
      {!loading && !error && (
        <BoardView
          tasks={tasks}
          columns={columns}
          labels={labels}
          onSelectTask={(task) => onOpen(task.id)}
          emptyTitle={t('kanban:pilot.empty.title')}
          emptyDescription={t('kanban:pilot.empty.description')}
        />
      )}
    </div>
  );
}

function PilotDetail({
  id,
  onBack,
}: Readonly<{ id: string; onBack: () => void }>) {
  const { t } = useTranslation(['kanban']);
  const columns = usePilotColumns();
  const { task, loading, error, reload } = useTask(id);

  const statusLabels = useMemo<Partial<Record<TaskStatus, string>>>(
    () =>
      Object.fromEntries(columns.map((column) => [column.status, column.label])),
    [columns],
  );
  const tabLabels = useMemo<Partial<Record<TaskDetailTabId, string>>>(
    () => ({
      overview: t('kanban:pilot.detail.tabs.overview'),
      subtasks: t('kanban:pilot.detail.tabs.subtasks'),
      logs: t('kanban:pilot.detail.tabs.logs'),
      files: t('kanban:pilot.detail.tabs.files'),
      timeline: t('kanban:pilot.detail.tabs.timeline'),
    }),
    [t],
  );
  const subtaskStatusLabels = useMemo<
    Partial<Record<UiSubtaskStatus, string>>
  >(
    () => ({
      pending: t('kanban:pilot.detail.subtaskStatus.pending'),
      in_progress: t('kanban:pilot.detail.subtaskStatus.in_progress'),
      completed: t('kanban:pilot.detail.subtaskStatus.completed'),
      failed: t('kanban:pilot.detail.subtaskStatus.failed'),
    }),
    [t],
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
        tabLabels={tabLabels}
        subtaskStatusLabels={subtaskStatusLabels}
      />
    </div>
  );
}

export function KanbanPilotView() {
  const { t } = useTranslation(['kanban']);
  // Keep the client identity stable across locale switches (recreating it
  // would tear down and re-establish the store subscription): the labels are
  // read through a ref that always holds the current translations.
  const labelsRef = useRef<UiTaskBadgeLabels>({
    error: '',
    prCreated: '',
    statusChips: {} as UiTaskBadgeLabels['statusChips'],
    phases: {} as UiTaskBadgeLabels['phases'],
  });
  labelsRef.current = {
    error: t('kanban:pilot.badges.error'),
    prCreated: t('kanban:pilot.badges.prCreated'),
    statusChips: {
      backlog: t('kanban:pilot.statusChips.backlog'),
      queue: t('kanban:pilot.statusChips.queue'),
      in_progress: t('kanban:pilot.statusChips.in_progress'),
      ai_review: t('kanban:pilot.statusChips.ai_review'),
      human_review: t('kanban:pilot.statusChips.human_review'),
      done: t('kanban:pilot.statusChips.done'),
      pr_created: t('kanban:pilot.statusChips.pr_created'),
      error: t('kanban:pilot.statusChips.error'),
    },
    phases: {
      idle: t('kanban:pilot.phases.idle'),
      planning: t('kanban:pilot.phases.planning'),
      coding: t('kanban:pilot.phases.coding'),
      test_generation: t('kanban:pilot.phases.test_generation'),
      qa_review: t('kanban:pilot.phases.qa_review'),
      qa_fixing: t('kanban:pilot.phases.qa_fixing'),
      complete: t('kanban:pilot.phases.complete'),
      failed: t('kanban:pilot.phases.failed'),
    },
  };
  const metaLabelsRef = useRef<TaskMetaLabels>({} as TaskMetaLabels);
  metaLabelsRef.current = {
    workspaceTitle: t('kanban:pilot.detail.meta.workspaceTitle'),
    costTokensTitle: t('kanban:pilot.detail.meta.costTokensTitle'),
    specId: t('kanban:pilot.detail.meta.specId'),
    location: t('kanban:pilot.detail.meta.location'),
    updated: t('kanban:pilot.detail.meta.updated'),
    cost: t('kanban:pilot.detail.meta.cost'),
    inputTokens: t('kanban:pilot.detail.meta.inputTokens'),
    outputTokens: t('kanban:pilot.detail.meta.outputTokens'),
    sessions: t('kanban:pilot.detail.meta.sessions'),
  };
  const client = useMemo(
    () =>
      createTaskStoreAutoCodeClient(useTaskStore, () => labelsRef.current, {
        loadSpecContent: async (task) => {
          const result = await window.electronAPI.getSpecContent(task.id);
          return result.success ? (result.data ?? null) : null;
        },
        loadMetaSections: async (task) => {
          const project = useProjectStore
            .getState()
            .projects.find((p) => p.id === task.projectId);
          const [tokensResult, costResult] = await Promise.all([
            project
              ? window.electronAPI.getTokenStats(project.path, task.specId)
              : Promise.resolve(null),
            window.electronAPI.getCostReport(task.projectId, task.specId),
          ]);
          const tokenStats =
            tokensResult?.success && tokensResult.data != null
              ? tokensResult.data
              : (task.tokenStats ?? null);
          const costReport =
            costResult.success && costResult.data != null
              ? costResult.data
              : null;
          const sections = buildTaskMetaSections(
            task,
            tokenStats,
            costReport,
            metaLabelsRef.current,
          );
          return sections.length > 0 ? sections : null;
        },
      }),
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
