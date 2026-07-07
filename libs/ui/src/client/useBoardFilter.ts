import { useMemo, useState } from 'react';
import { filterUiTasks } from './filtering';
import type { TaskStatus, UiTask } from './types';

/** Status behind each toolbar filter chip; 'all' clears the narrowing. */
const FILTER_STATUS: Record<string, TaskStatus | undefined> = {
  all: undefined,
  running: 'running',
  review: 'review',
};

export interface UseBoardFilterResult {
  query: string;
  setQuery: (value: string) => void;
  filterId: string;
  setFilterId: (id: string) => void;
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
  const [filterId, setFilterId] = useState('all');
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
