/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useTaskFiltering } from '../useTaskFiltering';
import type { Task } from '../../../shared/types';

function makeTask(overrides: Partial<Task> = {}): Task {
  return {
    id: 'task-1',
    specId: 'spec-001',
    title: 'Test Task',
    description: 'A test task',
    status: 'backlog',
    metadata: {
      category: 'feature',
      complexity: 'medium',
      impact: 'medium',
      priority: 'medium',
    },
    ...overrides,
  } as Task;
}

describe('useTaskFiltering', () => {
  const tasks: Task[] = [
    makeTask({
      id: 't1',
      specId: 'spec-001',
      title: 'Add Authentication',
      description: 'OAuth login flow',
      status: 'backlog',
      metadata: { category: 'feature', complexity: 'complex', impact: 'high', priority: 'high' },
    }),
    makeTask({
      id: 't2',
      specId: 'spec-002',
      title: 'Fix Button Bug',
      description: 'Submit button broken',
      status: 'in_progress',
      metadata: { category: 'bug_fix', complexity: 'small', impact: 'low', priority: 'low' },
    }),
    makeTask({
      id: 't3',
      specId: 'spec-003',
      title: 'Refactor Database',
      description: 'Move to PostgreSQL',
      status: 'done',
      metadata: { category: 'feature', complexity: 'complex', impact: 'high', priority: 'medium' },
    }),
  ];

  describe('initial state', () => {
    it('should return all tasks with no filters', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));
      expect(result.current.filteredTasks).toHaveLength(3);
      expect(result.current.isSearchActive).toBe(false);
      expect(result.current.hasActiveFilters).toBe(false);
    });

    it('should have default filter state', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));
      expect(result.current.filterState).toEqual({
        searchQuery: '',
        status: 'all',
        category: 'all',
        complexity: 'all',
        impact: 'all',
        priority: 'all',
      });
    });
  });

  describe('search filtering', () => {
    it('should filter by title', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setSearchQuery('auth'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t1');
      expect(result.current.isSearchActive).toBe(true);
    });

    it('should filter by description', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setSearchQuery('postgresql'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t3');
    });

    it('should filter by specId', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setSearchQuery('spec-002'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t2');
    });

    it('should filter by task id', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setSearchQuery('t3'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t3');
    });

    it('should be case insensitive', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setSearchQuery('AUTHENTICATION'));

      expect(result.current.filteredTasks).toHaveLength(1);
    });

    it('should return empty when no matches', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setSearchQuery('nonexistent'));

      expect(result.current.filteredTasks).toHaveLength(0);
    });
  });

  describe('status filtering', () => {
    it('should filter by status', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setStatusFilter('in_progress'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t2');
      expect(result.current.hasActiveFilters).toBe(true);
    });

    it('should show all when status is "all"', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setStatusFilter('backlog'));
      act(() => result.current.setStatusFilter('all'));

      expect(result.current.filteredTasks).toHaveLength(3);
    });
  });

  describe('category filtering', () => {
    it('should filter by category', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setCategoryFilter('bug_fix'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t2');
    });
  });

  describe('complexity filtering', () => {
    it('should filter by complexity', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setComplexityFilter('complex'));

      expect(result.current.filteredTasks).toHaveLength(2);
    });
  });

  describe('impact filtering', () => {
    it('should filter by impact', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setImpactFilter('high'));

      expect(result.current.filteredTasks).toHaveLength(2);
    });
  });

  describe('priority filtering', () => {
    it('should filter by priority', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => result.current.setPriorityFilter('high'));

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t1');
    });
  });

  describe('combined filters', () => {
    it('should apply multiple filters', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => {
        result.current.setAllFilters({
          category: 'feature',
          impact: 'high',
        });
      });

      expect(result.current.filteredTasks).toHaveLength(2);
      expect(result.current.hasActiveFilters).toBe(true);
    });

    it('should combine search with filters', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => {
        result.current.setSearchQuery('auth');
        result.current.setCategoryFilter('feature');
      });

      expect(result.current.filteredTasks).toHaveLength(1);
      expect(result.current.filteredTasks[0].id).toBe('t1');
    });
  });

  describe('clearFilters', () => {
    it('should reset all filters', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      act(() => {
        result.current.setSearchQuery('auth');
        result.current.setStatusFilter('backlog');
        result.current.setCategoryFilter('feature');
      });

      act(() => result.current.clearFilters());

      expect(result.current.filteredTasks).toHaveLength(3);
      expect(result.current.isSearchActive).toBe(false);
      expect(result.current.hasActiveFilters).toBe(false);
    });
  });

  describe('uniqueValues', () => {
    it('should extract unique filter values from tasks', () => {
      const { result } = renderHook(() => useTaskFiltering(tasks));

      const { uniqueValues } = result.current;
      expect(uniqueValues.categories).toContain('feature');
      expect(uniqueValues.categories).toContain('bug_fix');
      expect(uniqueValues.complexities).toContain('complex');
      expect(uniqueValues.complexities).toContain('small');
      expect(uniqueValues.impacts).toContain('high');
      expect(uniqueValues.impacts).toContain('low');
      expect(uniqueValues.priorities).toContain('high');
      expect(uniqueValues.priorities).toContain('low');
      expect(uniqueValues.priorities).toContain('medium');
    });
  });

  describe('callbacks', () => {
    it('should call onSearchStart when search becomes active', () => {
      const onSearchStart = vi.fn();
      const { result } = renderHook(() =>
        useTaskFiltering(tasks, { onSearchStart })
      );

      act(() => result.current.setSearchQuery('test'));

      expect(onSearchStart).toHaveBeenCalled();
    });

    it('should call onSearchClear when search is cleared', () => {
      const onSearchClear = vi.fn();
      const { result } = renderHook(() =>
        useTaskFiltering(tasks, { onSearchClear })
      );

      act(() => result.current.setSearchQuery('test'));
      act(() => result.current.setSearchQuery(''));

      expect(onSearchClear).toHaveBeenCalled();
    });
  });

  describe('empty tasks', () => {
    it('should handle empty task array', () => {
      const { result } = renderHook(() => useTaskFiltering([]));

      expect(result.current.filteredTasks).toHaveLength(0);
      expect(result.current.uniqueValues.categories).toEqual([]);
    });
  });
});
