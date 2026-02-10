/**
 * Hook for filtering and searching kanban tasks
 */

import { useMemo, useState, useCallback } from 'react';
import type { Task, TaskStatus, TaskCategory, TaskPriority } from '../../../../shared/types';

export interface TaskFilterState {
  searchQuery: string;
  statuses: TaskStatus[];
  categories: TaskCategory[];
  priorities: TaskPriority[];
}

const DEFAULT_FILTERS: TaskFilterState = {
  searchQuery: '',
  statuses: [],
  categories: [],
  priorities: [],
};

/**
 * Get unique categories from tasks
 */
function getUniqueCategories(tasks: Task[]): TaskCategory[] {
  const categorySet = new Set<TaskCategory>();
  tasks.forEach(task => {
    if (task.metadata?.category) {
      categorySet.add(task.metadata.category);
    }
  });
  return Array.from(categorySet).sort((a, b) =>
    a.localeCompare(b)
  );
}

/**
 * Get unique priorities from tasks
 */
function getUniquePriorities(tasks: Task[]): TaskPriority[] {
  const prioritySet = new Set<TaskPriority>();
  tasks.forEach(task => {
    if (task.metadata?.priority) {
      prioritySet.add(task.metadata.priority);
    }
  });
  return Array.from(prioritySet).sort((a, b) =>
    a.localeCompare(b)
  );
}

export function useTaskFiltering(tasks: Task[]) {
  const [filters, setFiltersState] = useState<TaskFilterState>(DEFAULT_FILTERS);

  // Derive unique categories and priorities from tasks
  const categories = useMemo(() => getUniqueCategories(tasks), [tasks]);
  const priorities = useMemo(() => getUniquePriorities(tasks), [tasks]);

  // Filter tasks based on current filters
  const filteredTasks = useMemo(() => {
    return tasks.filter(task => {
      // Search filter - matches title, description, or specId
      if (filters.searchQuery) {
        const query = filters.searchQuery.toLowerCase();
        const matchesTitle = task.title.toLowerCase().includes(query);
        const matchesDescription = task.description?.toLowerCase().includes(query);
        const matchesSpecId = task.specId.toLowerCase().includes(query);
        if (!matchesTitle && !matchesDescription && !matchesSpecId) {
          return false;
        }
      }

      // Status filter (multi-select)
      if (filters.statuses.length > 0) {
        if (!filters.statuses.includes(task.status)) {
          return false;
        }
      }

      // Category filter (multi-select)
      if (filters.categories.length > 0) {
        const category = task.metadata?.category;
        if (!category || !filters.categories.includes(category)) {
          return false;
        }
      }

      // Priority filter (multi-select)
      if (filters.priorities.length > 0) {
        const priority = task.metadata?.priority;
        if (!priority || !filters.priorities.includes(priority)) {
          return false;
        }
      }

      return true;
    });
  }, [tasks, filters]);

  // Filter setters
  const setSearchQuery = useCallback((query: string) => {
    setFiltersState(prev => ({ ...prev, searchQuery: query }));
  }, []);

  const setStatuses = useCallback((statuses: TaskStatus[]) => {
    setFiltersState(prev => ({ ...prev, statuses }));
  }, []);

  const setCategories = useCallback((categories: TaskCategory[]) => {
    setFiltersState(prev => ({ ...prev, categories }));
  }, []);

  const setPriorities = useCallback((priorities: TaskPriority[]) => {
    setFiltersState(prev => ({ ...prev, priorities }));
  }, []);

  const clearFilters = useCallback(() => {
    setFiltersState(DEFAULT_FILTERS);
  }, []);

  const hasActiveFilters = useMemo(() => {
    return (
      filters.searchQuery !== '' ||
      filters.statuses.length > 0 ||
      filters.categories.length > 0 ||
      filters.priorities.length > 0
    );
  }, [filters]);

  return {
    filteredTasks,
    categories,
    priorities,
    filters,
    setSearchQuery,
    setStatuses,
    setCategories,
    setPriorities,
    clearFilters,
    hasActiveFilters,
  };
}
