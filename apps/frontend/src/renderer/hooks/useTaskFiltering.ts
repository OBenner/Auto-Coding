/**
 * Hook for filtering and searching tasks
 */

import { useState, useMemo, useCallback, useEffect } from 'react';
import type { Task, TaskStatus, TaskCategory, TaskComplexity, TaskImpact, TaskPriority } from '../../shared/types';

export interface TaskFilterState {
  searchQuery: string;
  status: TaskStatus | 'all';
  category: TaskCategory | 'all';
  complexity: TaskComplexity | 'all';
  impact: TaskImpact | 'all';
  priority: TaskPriority | 'all';
}

interface UseTaskFilteringOptions {
  onSearchStart?: () => void;
  onSearchClear?: () => void;
}

const DEFAULT_FILTER_STATE: TaskFilterState = {
  searchQuery: '',
  status: 'all',
  category: 'all',
  complexity: 'all',
  impact: 'all',
  priority: 'all'
};

export function useTaskFiltering(
  tasks: Task[],
  options: UseTaskFilteringOptions = {}
) {
  const { onSearchStart, onSearchClear } = options;

  const [filterState, setFilterState] = useState<TaskFilterState>(DEFAULT_FILTER_STATE);

  const filteredTasks = useMemo(() => {
    return tasks.filter(task => {
      // Search filter
      if (filterState.searchQuery) {
        const query = filterState.searchQuery.toLowerCase();
        const matchesId = task.id?.toLowerCase().includes(query) ?? false;
        const matchesTitle = task.title?.toLowerCase().includes(query) ?? false;
        const matchesDescription = task.description?.toLowerCase().includes(query) ?? false;
        const matchesSpecId = task.specId?.toLowerCase().includes(query) ?? false;

        if (!matchesId && !matchesTitle && !matchesDescription && !matchesSpecId) {
          return false;
        }
      }

      // Status filter
      if (filterState.status !== 'all' && task.status !== filterState.status) {
        return false;
      }

      // Category filter
      if (filterState.category !== 'all' && task.metadata?.category !== filterState.category) {
        return false;
      }

      // Complexity filter
      if (filterState.complexity !== 'all' && task.metadata?.complexity !== filterState.complexity) {
        return false;
      }

      // Impact filter
      if (filterState.impact !== 'all' && task.metadata?.impact !== filterState.impact) {
        return false;
      }

      // Priority filter
      if (filterState.priority !== 'all' && task.metadata?.priority !== filterState.priority) {
        return false;
      }

      return true;
    });
  }, [tasks, filterState]);

  // Notify when search becomes active or inactive
  useEffect(() => {
    if (filterState.searchQuery.length > 0) {
      onSearchStart?.();
    } else {
      onSearchClear?.();
    }
  }, [filterState.searchQuery, onSearchStart, onSearchClear]);

  // Get unique filter values from tasks
  const uniqueValues = useMemo(() => {
    const categories = new Set<TaskCategory>();
    const complexities = new Set<TaskComplexity>();
    const impacts = new Set<TaskImpact>();
    const priorities = new Set<TaskPriority>();

    tasks.forEach(task => {
      if (task.metadata?.category) categories.add(task.metadata.category);
      if (task.metadata?.complexity) complexities.add(task.metadata.complexity);
      if (task.metadata?.impact) impacts.add(task.metadata.impact);
      if (task.metadata?.priority) priorities.add(task.metadata.priority);
    });

    return {
      categories: Array.from(categories),
      complexities: Array.from(complexities),
      impacts: Array.from(impacts),
      priorities: Array.from(priorities)
    };
  }, [tasks]);

  // Individual filter setters
  const setSearchQuery = useCallback((query: string) => {
    setFilterState(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const setStatusFilter = useCallback((status: TaskStatus | 'all') => {
    setFilterState(prev => ({ ...prev, status }));
  }, []);

  const setCategoryFilter = useCallback((category: TaskCategory | 'all') => {
    setFilterState(prev => ({ ...prev, category }));
  }, []);

  const setComplexityFilter = useCallback((complexity: TaskComplexity | 'all') => {
    setFilterState(prev => ({ ...prev, complexity }));
  }, []);

  const setImpactFilter = useCallback((impact: TaskImpact | 'all') => {
    setFilterState(prev => ({ ...prev, impact }));
  }, []);

  const setPriorityFilter = useCallback((priority: TaskPriority | 'all') => {
    setFilterState(prev => ({ ...prev, priority }));
  }, []);

  const setAllFilters = useCallback((filters: Partial<TaskFilterState>) => {
    setFilterState(prev => ({ ...prev, ...filters }));
  }, []);

  const clearFilters = useCallback(() => {
    setFilterState(DEFAULT_FILTER_STATE);
  }, []);

  const isSearchActive = filterState.searchQuery.length > 0;
  const hasActiveFilters = filterState.searchQuery.length > 0 ||
    filterState.status !== 'all' ||
    filterState.category !== 'all' ||
    filterState.complexity !== 'all' ||
    filterState.impact !== 'all' ||
    filterState.priority !== 'all';

  return {
    filterState,
    filteredTasks,
    uniqueValues,
    isSearchActive,
    hasActiveFilters,
    setSearchQuery,
    setStatusFilter,
    setCategoryFilter,
    setComplexityFilter,
    setImpactFilter,
    setPriorityFilter,
    setAllFilters,
    clearFilters
  };
}
