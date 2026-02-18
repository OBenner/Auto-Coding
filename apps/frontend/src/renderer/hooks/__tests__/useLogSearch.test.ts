/**
 * @vitest-environment jsdom
 */
import { describe, it, expect } from 'vitest';
import type {
  TaskLogs,
  TaskLogEntry,
  TaskLogPhase,
  LogFilterState,
} from '../../../shared/types';

// The pure functions are not exported, so we test them through the module internals.
// We'll re-implement the key logic tests using the hook indirectly, but since the
// pure functions (searchLogEntry, passesFilter, performSearch) are private,
// we test them by importing the module and testing observable behavior.

// To test pure functions, we extract them. Since they are not exported,
// we'll create our own identical implementations to verify the logic,
// then verify the hook integrates correctly via renderHook.

// Actually, let's test the pure logic directly by re-exporting or by
// testing the hook output. Let's focus on testing through the hook.

import { renderHook, act } from '@testing-library/react';
import { useLogSearch } from '../useLogSearch';

function makeEntry(overrides: Partial<TaskLogEntry> = {}): TaskLogEntry {
  return {
    timestamp: '2025-01-01T00:00:00Z',
    type: 'text',
    content: 'Default content',
    phase: 'coding',
    ...overrides,
  } as TaskLogEntry;
}

function makeLogs(entries: {
  planning?: TaskLogEntry[];
  coding?: TaskLogEntry[];
  validation?: TaskLogEntry[];
}): TaskLogs {
  return {
    spec_id: 'spec-1',
    created_at: '2025-01-01T00:00:00Z',
    updated_at: '2025-01-01T00:00:00Z',
    phases: {
      planning: {
        status: 'completed',
        entries: entries.planning ?? [],
        started_at: '',
        completed_at: '',
      },
      coding: {
        status: 'completed',
        entries: entries.coding ?? [],
        started_at: '',
        completed_at: '',
      },
      validation: {
        status: 'completed',
        entries: entries.validation ?? [],
        started_at: '',
        completed_at: '',
      },
    },
  } as TaskLogs;
}

const defaultFilter: LogFilterState = {
  searchQuery: '',
  phases: [],
  entryTypes: [],
  tools: [],
  showToolOutput: true,
};

describe('useLogSearch', () => {
  describe('basic search', () => {
    it('should return empty results when no search query', () => {
      const logs = makeLogs({
        coding: [makeEntry({ content: 'hello world' })],
      });

      const { result } = renderHook(() =>
        useLogSearch(logs, { ...defaultFilter, searchQuery: '' }, 0)
      );

      expect(result.current.results).toEqual([]);
    });

    it('should return empty results when logs are null', () => {
      const { result } = renderHook(() =>
        useLogSearch(null, { ...defaultFilter, searchQuery: 'test' }, 0)
      );

      expect(result.current.results).toEqual([]);
    });

    it('should find matches in content', async () => {
      const logs = makeLogs({
        coding: [
          makeEntry({ content: 'Hello World' }),
          makeEntry({ content: 'Goodbye' }),
        ],
      });

      const { result, rerender } = renderHook(
        ({ filter }) => useLogSearch(logs, filter, 0),
        { initialProps: { filter: { ...defaultFilter, searchQuery: 'hello' } } }
      );

      // With 0 debounce, results should appear after the effect runs
      // Wait for debounce effect
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ filter: { ...defaultFilter, searchQuery: 'hello' } });

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.results.length).toBeGreaterThanOrEqual(1);
      expect(result.current.results[0].matchType).toBe('content');
      expect(result.current.results[0].phase).toBe('coding');
    });

    it('should find matches in tool_name', async () => {
      const logs = makeLogs({
        planning: [makeEntry({ content: 'x', tool_name: 'ReadFile' })],
      });

      const { result, rerender } = renderHook(
        ({ filter }) => useLogSearch(logs, filter, 0),
        { initialProps: { filter: { ...defaultFilter, searchQuery: 'readfile' } } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ filter: { ...defaultFilter, searchQuery: 'readfile' } });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.results.length).toBeGreaterThanOrEqual(1);
      expect(result.current.results[0].matchType).toBe('tool_name');
    });

    it('should find matches in tool_input', async () => {
      const logs = makeLogs({
        coding: [makeEntry({ content: 'x', tool_input: '/path/to/file.ts' })],
      });

      const { result, rerender } = renderHook(
        ({ filter }) => useLogSearch(logs, filter, 0),
        {
          initialProps: {
            filter: { ...defaultFilter, searchQuery: 'file.ts' },
          },
        }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ filter: { ...defaultFilter, searchQuery: 'file.ts' } });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.results.length).toBeGreaterThanOrEqual(1);
      expect(result.current.results[0].matchType).toBe('tool_input');
    });

    it('should find matches in detail', async () => {
      const logs = makeLogs({
        validation: [makeEntry({ content: 'x', detail: 'Detailed error info' })],
      });

      const { result, rerender } = renderHook(
        ({ filter }) => useLogSearch(logs, filter, 0),
        {
          initialProps: {
            filter: { ...defaultFilter, searchQuery: 'detailed' },
          },
        }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ filter: { ...defaultFilter, searchQuery: 'detailed' } });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.results.length).toBeGreaterThanOrEqual(1);
      expect(result.current.results[0].matchType).toBe('detail');
    });
  });

  describe('filtering', () => {
    it('should exclude tool_start/tool_end when showToolOutput is false', async () => {
      const logs = makeLogs({
        coding: [
          makeEntry({ content: 'match text', type: 'text' }),
          makeEntry({ content: 'match tool start', type: 'tool_start' }),
          makeEntry({ content: 'match tool end', type: 'tool_end' }),
        ],
      });

      const filter: LogFilterState = {
        ...defaultFilter,
        searchQuery: 'match',
        showToolOutput: false,
      };

      const { result, rerender } = renderHook(
        ({ f }) => useLogSearch(logs, f, 0),
        { initialProps: { f: filter } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ f: filter });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      // Only the 'text' type entry should match
      expect(result.current.results.length).toBe(1);
      expect(result.current.results[0].matchType).toBe('content');
    });

    it('should filter by entry type', async () => {
      const logs = makeLogs({
        coding: [
          makeEntry({ content: 'match text', type: 'text' }),
          makeEntry({ content: 'match error', type: 'error' }),
        ],
      });

      const filter: LogFilterState = {
        ...defaultFilter,
        searchQuery: 'match',
        entryTypes: ['error'],
      };

      const { result, rerender } = renderHook(
        ({ f }) => useLogSearch(logs, f, 0),
        { initialProps: { f: filter } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ f: filter });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.results.length).toBe(1);
      expect(result.current.results[0].matchText).toBe('match error');
    });
  });

  describe('navigation', () => {
    it('should navigate through results with next/previous', async () => {
      const logs = makeLogs({
        coding: [
          makeEntry({ content: 'match A' }),
          makeEntry({ content: 'match B' }),
          makeEntry({ content: 'match C' }),
        ],
      });

      const filter: LogFilterState = {
        ...defaultFilter,
        searchQuery: 'match',
      };

      const { result, rerender } = renderHook(
        ({ f }) => useLogSearch(logs, f, 0),
        { initialProps: { f: filter } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ f: filter });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.currentResultIndex).toBe(0);

      act(() => result.current.nextResult());
      expect(result.current.currentResultIndex).toBe(1);

      act(() => result.current.nextResult());
      expect(result.current.currentResultIndex).toBe(2);

      // Wraps around
      act(() => result.current.nextResult());
      expect(result.current.currentResultIndex).toBe(0);

      // Previous wraps backwards
      act(() => result.current.previousResult());
      expect(result.current.currentResultIndex).toBe(2);
    });

    it('should navigate to specific result with goToResult', async () => {
      const logs = makeLogs({
        coding: [
          makeEntry({ content: 'match A' }),
          makeEntry({ content: 'match B' }),
        ],
      });

      const filter: LogFilterState = {
        ...defaultFilter,
        searchQuery: 'match',
      };

      const { result, rerender } = renderHook(
        ({ f }) => useLogSearch(logs, f, 0),
        { initialProps: { f: filter } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ f: filter });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      act(() => result.current.goToResult(1));
      expect(result.current.currentResultIndex).toBe(1);

      // Out of bounds should be ignored
      act(() => result.current.goToResult(99));
      expect(result.current.currentResultIndex).toBe(1);
    });

    it('should handle next/previous with no results', () => {
      const { result } = renderHook(() =>
        useLogSearch(null, defaultFilter, 0)
      );

      act(() => result.current.nextResult());
      expect(result.current.currentResultIndex).toBe(0);

      act(() => result.current.previousResult());
      expect(result.current.currentResultIndex).toBe(0);
    });
  });

  describe('clearSearch', () => {
    it('should reset query and index', async () => {
      const logs = makeLogs({
        coding: [makeEntry({ content: 'match' })],
      });

      const filter: LogFilterState = {
        ...defaultFilter,
        searchQuery: 'match',
      };

      const { result, rerender } = renderHook(
        ({ f }) => useLogSearch(logs, f, 0),
        { initialProps: { f: filter } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ f: filter });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      act(() => result.current.clearSearch());

      expect(result.current.query).toBe('');
      expect(result.current.currentResultIndex).toBe(0);
    });
  });

  describe('search across phases', () => {
    it('should search all three phases', async () => {
      const logs = makeLogs({
        planning: [makeEntry({ content: 'match in planning', phase: 'planning' })],
        coding: [makeEntry({ content: 'match in coding', phase: 'coding' })],
        validation: [makeEntry({ content: 'match in validation', phase: 'validation' })],
      });

      const filter: LogFilterState = {
        ...defaultFilter,
        searchQuery: 'match',
      };

      const { result, rerender } = renderHook(
        ({ f }) => useLogSearch(logs, f, 0),
        { initialProps: { f: filter } }
      );

      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });
      rerender({ f: filter });
      await act(async () => {
        await new Promise((r) => setTimeout(r, 10));
      });

      expect(result.current.results.length).toBe(3);
      const phases = result.current.results.map((r) => r.phase);
      expect(phases).toContain('planning');
      expect(phases).toContain('coding');
      expect(phases).toContain('validation');
    });
  });
});
