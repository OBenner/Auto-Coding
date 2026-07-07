import { useMemo, useState } from 'react';
import { filterUiTasks } from './filtering';
import type { TaskStatus, UiTask } from './types';

/** Board filter chip ids (single-active). */
export type FilterId = 'all' | 'running' | 'review';

/** Ordered filter ids, shared by the toolbar wiring in both pilots. */
export const FILTER_IDS: readonly FilterId[] = ['all', 'running', 'review'];

/** Status behind each filter chip; 'all' clears the narrowing. */
const FILTER_STATUS: Record<FilterId, TaskStatus | undefined> = {
  all: undefined,
  running: 'running',
  review: 'review',
};

export interface UseBoardFilterResult {
  query: string;
  setQuery: (value: string) => void;
  filterId: FilterId;
  setFilterId: (id: FilterId) => void;
  /** True when a query or a non-'all' chip narrows the board. */
  filtering: boolean;
  visibleTasks: UiTask[];
}

/**
 * Board-narrowing state behind BoardToolbar (search box + single-active
 * chips), shared by the pilots so the wiring can't drift between apps.
 */
export function useBoardFilter(tasks: UiTask[]): UseBoardFilterResult {
  const [query, setQuery] = useState('');
  const [filterId, setFilterId] = useState<FilterId>('all');
  const visibleTasks = useMemo(
    () => filterUiTasks(tasks, { query, status: FILTER_STATUS[filterId] }),
    [tasks, query, filterId],
  );
  return {
    query,
    setQuery,
    filterId,
    setFilterId,
    filtering: query.trim() !== '' || filterId !== 'all',
    visibleTasks,
  };
}
