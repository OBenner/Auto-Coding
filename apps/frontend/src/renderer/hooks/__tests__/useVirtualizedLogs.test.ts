/**
 * @vitest-environment jsdom
 */

/**
 * Unit tests for useVirtualizedLogs hook
 * Tests flattenLogs function and visible items computation
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  flattenLogs,
  useVirtualizedLogs,
  estimateLogItemHeight,
  ESTIMATED_HEIGHTS,
  type FlattenedLogItem,
} from '../useVirtualizedLogs';
import type { TaskLogs, TaskLogPhase, TaskLogEntry, TaskPhaseLog } from '../../../shared/types';

// Helper to create test TaskLogEntry
function createTestLogEntry(overrides: Partial<TaskLogEntry> = {}): TaskLogEntry {
  return {
    timestamp: '2024-01-01T00:00:00Z',
    type: 'info',
    content: 'Test log entry',
    phase: 'coding',
    ...overrides,
  };
}

// Helper to create a TaskPhaseLog
function createTestPhaseLog(
  phase: TaskLogPhase,
  entries: TaskLogEntry[] = [],
  overrides: Partial<TaskPhaseLog> = {}
): TaskPhaseLog {
  return {
    phase,
    status: 'active',
    started_at: '2024-01-01T00:00:00Z',
    completed_at: null,
    entries,
    ...overrides,
  };
}

// Helper to create TaskLogs
function createTestTaskLogs(overrides: Partial<TaskLogs> = {}): TaskLogs {
  return {
    spec_id: 'test-spec',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    phases: {
      planning: createTestPhaseLog('planning', []),
      coding: createTestPhaseLog('coding', []),
      validation: createTestPhaseLog('validation', []),
    },
    ...overrides,
  };
}

describe('flattenLogs', () => {
  describe('basic functionality', () => {
    it('should return empty array for null input', () => {
      const result = flattenLogs(null, new Set(), new Map());
      expect(result).toHaveLength(0);
    });

    it('should return phase headers only when no phases are expanded', () => {
      const logs = createTestTaskLogs();
      const result = flattenLogs(logs, new Set(), new Map());

      // Should have 3 phase headers (planning, coding, validation)
      expect(result).toHaveLength(3);
      expect(result[0].type).toBe('phase-header');
      expect(result[0].phase).toBe('planning');
      expect(result[1].type).toBe('phase-header');
      expect(result[1].phase).toBe('coding');
      expect(result[2].type).toBe('phase-header');
      expect(result[2].phase).toBe('validation');
    });

    it('should include entries when phase is expanded', () => {
      const entry1 = createTestLogEntry({ content: 'Entry 1', phase: 'coding' });
      const entry2 = createTestLogEntry({ content: 'Entry 2', phase: 'coding' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry1, entry2]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['coding']);
      const result = flattenLogs(logs, expandedPhases, new Map());

      // Should have 3 headers + 2 entries = 5 items
      expect(result).toHaveLength(5);

      // Find coding phase header
      const codingHeader = result.find(item => item.phase === 'coding' && item.type === 'phase-header');
      expect(codingHeader).toBeDefined();
      expect(codingHeader?.isPhaseExpanded).toBe(true);

      // Find coding entries
      const codingEntries = result.filter(item => item.phase === 'coding' && item.type === 'log-entry');
      expect(codingEntries).toHaveLength(2);
      expect(codingEntries[0].entry?.content).toBe('Entry 1');
      expect(codingEntries[1].entry?.content).toBe('Entry 2');
    });

    it('should not include entries when phase is collapsed', () => {
      const entry = createTestLogEntry({ content: 'Hidden entry', phase: 'coding' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>([]); // No phases expanded
      const result = flattenLogs(logs, expandedPhases, new Map());

      // Should only have 3 headers
      expect(result).toHaveLength(3);
      expect(result.every(item => item.type === 'phase-header')).toBe(true);
    });
  });

  describe('expansion state', () => {
    it('should mark expanded phases correctly', () => {
      const logs = createTestTaskLogs();
      const expandedPhases = new Set<TaskLogPhase>(['planning', 'validation']);
      const result = flattenLogs(logs, expandedPhases, new Map());

      const planningHeader = result.find(item => item.phase === 'planning' && item.type === 'phase-header');
      const codingHeader = result.find(item => item.phase === 'coding' && item.type === 'phase-header');
      const validationHeader = result.find(item => item.phase === 'validation' && item.type === 'phase-header');

      expect(planningHeader?.isPhaseExpanded).toBe(true);
      expect(codingHeader?.isPhaseExpanded).toBe(false);
      expect(validationHeader?.isPhaseExpanded).toBe(true);
    });

    it('should mark detail-expanded entries correctly', () => {
      const entry1 = createTestLogEntry({ content: 'Entry 1', phase: 'coding', detail: 'Detail 1' });
      const entry2 = createTestLogEntry({ content: 'Entry 2', phase: 'coding', detail: 'Detail 2' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry1, entry2]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['coding']);
      const expandedDetails = new Map<string, boolean>([
        ['coding:0', true],   // First entry expanded
        ['coding:1', false],  // Second entry collapsed
      ]);
      const result = flattenLogs(logs, expandedPhases, expandedDetails);

      const entries = result.filter(item => item.type === 'log-entry');
      expect(entries).toHaveLength(2);
      expect(entries[0].isDetailExpanded).toBe(true);
      expect(entries[1].isDetailExpanded).toBe(false);
    });

    it('should default to collapsed for details not in map', () => {
      const entry = createTestLogEntry({ content: 'Entry', phase: 'coding', detail: 'Detail' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['coding']);
      const result = flattenLogs(logs, expandedPhases, new Map());

      const entries = result.filter(item => item.type === 'log-entry');
      expect(entries).toHaveLength(1);
      expect(entries[0].isDetailExpanded).toBe(false);
    });
  });

  describe('multiple phases', () => {
    it('should flatten multiple expanded phases correctly', () => {
      const planningEntry = createTestLogEntry({ content: 'Planning entry', phase: 'planning' });
      const codingEntry1 = createTestLogEntry({ content: 'Coding entry 1', phase: 'coding' });
      const codingEntry2 = createTestLogEntry({ content: 'Coding entry 2', phase: 'coding' });
      const validationEntry = createTestLogEntry({ content: 'Validation entry', phase: 'validation' });

      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', [planningEntry]),
          coding: createTestPhaseLog('coding', [codingEntry1, codingEntry2]),
          validation: createTestPhaseLog('validation', [validationEntry]),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['planning', 'coding', 'validation']);
      const result = flattenLogs(logs, expandedPhases, new Map());

      // 3 headers + 1 planning entry + 2 coding entries + 1 validation entry = 7 items
      expect(result).toHaveLength(7);

      // Verify order: planning header, planning entry, coding header, coding entries, validation header, validation entry
      expect(result[0]).toMatchObject({ type: 'phase-header', phase: 'planning' });
      expect(result[1]).toMatchObject({ type: 'log-entry', phase: 'planning' });
      expect(result[2]).toMatchObject({ type: 'phase-header', phase: 'coding' });
      expect(result[3]).toMatchObject({ type: 'log-entry', phase: 'coding' });
      expect(result[4]).toMatchObject({ type: 'log-entry', phase: 'coding' });
      expect(result[5]).toMatchObject({ type: 'phase-header', phase: 'validation' });
      expect(result[6]).toMatchObject({ type: 'log-entry', phase: 'validation' });
    });

    it('should handle mixed expanded/collapsed phases', () => {
      const planningEntry = createTestLogEntry({ content: 'Planning entry', phase: 'planning' });
      const codingEntry = createTestLogEntry({ content: 'Coding entry', phase: 'coding' });
      const validationEntry = createTestLogEntry({ content: 'Validation entry', phase: 'validation' });

      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', [planningEntry]),
          coding: createTestPhaseLog('coding', [codingEntry]),
          validation: createTestPhaseLog('validation', [validationEntry]),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['coding']); // Only coding expanded
      const result = flattenLogs(logs, expandedPhases, new Map());

      // 3 headers + 1 coding entry = 4 items
      expect(result).toHaveLength(4);

      const planningItems = result.filter(item => item.phase === 'planning');
      const codingItems = result.filter(item => item.phase === 'coding');
      const validationItems = result.filter(item => item.phase === 'validation');

      expect(planningItems).toHaveLength(1); // Only header
      expect(codingItems).toHaveLength(2); // Header + entry
      expect(validationItems).toHaveLength(1); // Only header
    });
  });

  describe('key generation', () => {
    it('should generate unique keys for all items', () => {
      const entry1 = createTestLogEntry({ content: 'Entry 1', phase: 'coding' });
      const entry2 = createTestLogEntry({ content: 'Entry 2', phase: 'coding' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry1, entry2]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['coding']);
      const result = flattenLogs(logs, expandedPhases, new Map());

      const keys = result.map(item => item.key);
      const uniqueKeys = new Set(keys);

      expect(keys).toHaveLength(uniqueKeys.size); // All keys are unique
    });

    it('should use consistent key format', () => {
      const entry = createTestLogEntry({ content: 'Entry', phase: 'coding' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const expandedPhases = new Set<TaskLogPhase>(['coding']);
      const result = flattenLogs(logs, expandedPhases, new Map());

      // Phase headers should use "phase-{phase}" format
      const headers = result.filter(item => item.type === 'phase-header');
      headers.forEach(header => {
        expect(header.key).toMatch(/^phase-\w+$/);
      });

      // Log entries should use "{phase}-entry-{index}" format
      const entries = result.filter(item => item.type === 'log-entry');
      entries.forEach(entry => {
        expect(entry.key).toMatch(/^\w+-entry-\d+$/);
      });
    });
  });
});

describe('estimateLogItemHeight', () => {
  describe('phase headers', () => {
    it('should return phase header height for phase headers', () => {
      const item: FlattenedLogItem = {
        key: 'phase-coding',
        type: 'phase-header',
        phase: 'coding',
        phaseLog: createTestPhaseLog('coding'),
        isPhaseExpanded: false,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.PHASE_HEADER);
    });
  });

  describe('log entries', () => {
    it('should return simple height for basic entries', () => {
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'info' }),
        entryIndex: 0,
        isDetailExpanded: false,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });

    it('should return tool height for tool entries', () => {
      const toolStartItem: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'tool_start' }),
        entryIndex: 0,
        isDetailExpanded: false,
      };

      const toolEndItem: FlattenedLogItem = {
        key: 'coding-entry-1',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'tool_end' }),
        entryIndex: 1,
        isDetailExpanded: false,
      };

      expect(estimateLogItemHeight(toolStartItem)).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_TOOL);
      expect(estimateLogItemHeight(toolEndItem)).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_TOOL);
    });

    it('should return error height for error entries', () => {
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'error' }),
        entryIndex: 0,
        isDetailExpanded: false,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_ERROR);
    });

    it('should return simple height for success entries', () => {
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'success' }),
        entryIndex: 0,
        isDetailExpanded: false,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });

    it('should add detail height when detail is expanded', () => {
      const shortDetail = 'Short detail';
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'info', detail: shortDetail }),
        entryIndex: 0,
        isDetailExpanded: true,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBeGreaterThan(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });

    it('should not add detail height when detail is collapsed', () => {
      const detail = 'Some detail content';
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'info', detail }),
        entryIndex: 0,
        isDetailExpanded: false,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });

    it('should scale detail height based on content length', () => {
      const shortDetail = 'One line';
      // Need enough lines to exceed the minimum detail height (150)
      // detailLines * 14 + 20 > 150, so need at least 10 lines
      const longDetail = Array.from({ length: 15 }, (_, i) => `Line ${i + 1}`).join('\n');

      const shortItem: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'info', detail: shortDetail }),
        entryIndex: 0,
        isDetailExpanded: true,
      };

      const longItem: FlattenedLogItem = {
        key: 'coding-entry-1',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'info', detail: longDetail }),
        entryIndex: 1,
        isDetailExpanded: true,
      };

      const shortHeight = estimateLogItemHeight(shortItem);
      const longHeight = estimateLogItemHeight(longItem);

      expect(longHeight).toBeGreaterThan(shortHeight);
    });

    it('should not add detail height when entry has no detail', () => {
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: createTestLogEntry({ type: 'info', detail: undefined }),
        entryIndex: 0,
        isDetailExpanded: true, // Even though expanded, no detail to show
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });

    it('should handle missing entry gracefully', () => {
      const item: FlattenedLogItem = {
        key: 'coding-entry-0',
        type: 'log-entry',
        phase: 'coding',
        entry: undefined,
        entryIndex: 0,
        isDetailExpanded: false,
      };

      const height = estimateLogItemHeight(item);
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });
  });
});

describe('useVirtualizedLogs', () => {
  describe('basic usage', () => {
    it('should return empty flattened items for null logs', () => {
      const { result } = renderHook(() => useVirtualizedLogs(null, new Set()));

      expect(result.current.flattenedItems).toHaveLength(0);
      expect(result.current.count).toBe(0);
      expect(result.current.hasLogs).toBe(false);
    });

    it('should return flattened items for logs with no expanded phases', () => {
      const logs = createTestTaskLogs();
      const { result } = renderHook(() => useVirtualizedLogs(logs, new Set()));

      // Should have 3 phase headers
      expect(result.current.flattenedItems).toHaveLength(3);
      expect(result.current.count).toBe(3);
      expect(result.current.hasLogs).toBe(true);
    });

    it('should return flattened items with entries when phase is expanded', () => {
      const entry = createTestLogEntry({ content: 'Test entry', phase: 'coding' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });
      const expandedPhases = new Set<TaskLogPhase>(['coding']);

      const { result } = renderHook(() => useVirtualizedLogs(logs, expandedPhases));

      // 3 headers + 1 entry = 4 items
      expect(result.current.flattenedItems).toHaveLength(4);
      expect(result.current.count).toBe(4);
    });
  });

  describe('toggleDetail', () => {
    it('should toggle detail expansion state', () => {
      const entry = createTestLogEntry({ content: 'Test entry', phase: 'coding', detail: 'Detail content' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });
      const expandedPhases = new Set<TaskLogPhase>(['coding']);

      const { result } = renderHook(() => useVirtualizedLogs(logs, expandedPhases));

      // Initially, detail should be collapsed
      const initialEntry = result.current.flattenedItems.find(item => item.type === 'log-entry');
      expect(initialEntry?.isDetailExpanded).toBe(false);

      // Toggle detail
      act(() => {
        result.current.toggleDetail('coding', 0);
      });

      // Now detail should be expanded
      const expandedEntry = result.current.flattenedItems.find(item => item.type === 'log-entry');
      expect(expandedEntry?.isDetailExpanded).toBe(true);

      // Toggle again
      act(() => {
        result.current.toggleDetail('coding', 0);
      });

      // Detail should be collapsed again
      const collapsedEntry = result.current.flattenedItems.find(item => item.type === 'log-entry');
      expect(collapsedEntry?.isDetailExpanded).toBe(false);
    });

    it('should handle multiple entries with independent expansion states', () => {
      const entry1 = createTestLogEntry({ content: 'Entry 1', phase: 'coding', detail: 'Detail 1' });
      const entry2 = createTestLogEntry({ content: 'Entry 2', phase: 'coding', detail: 'Detail 2' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry1, entry2]),
          validation: createTestPhaseLog('validation', []),
        },
      });
      const expandedPhases = new Set<TaskLogPhase>(['coding']);

      const { result } = renderHook(() => useVirtualizedLogs(logs, expandedPhases));

      // Expand first entry
      act(() => {
        result.current.toggleDetail('coding', 0);
      });

      const entries1 = result.current.flattenedItems.filter(item => item.type === 'log-entry');
      expect(entries1[0].isDetailExpanded).toBe(true);
      expect(entries1[1].isDetailExpanded).toBe(false);

      // Expand second entry
      act(() => {
        result.current.toggleDetail('coding', 1);
      });

      const entries2 = result.current.flattenedItems.filter(item => item.type === 'log-entry');
      expect(entries2[0].isDetailExpanded).toBe(true);
      expect(entries2[1].isDetailExpanded).toBe(true);
    });
  });

  describe('collapseAllDetails', () => {
    it('should collapse all expanded details', () => {
      const entry1 = createTestLogEntry({ content: 'Entry 1', phase: 'coding', detail: 'Detail 1' });
      const entry2 = createTestLogEntry({ content: 'Entry 2', phase: 'coding', detail: 'Detail 2' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry1, entry2]),
          validation: createTestPhaseLog('validation', []),
        },
      });
      const expandedPhases = new Set<TaskLogPhase>(['coding']);

      const { result } = renderHook(() => useVirtualizedLogs(logs, expandedPhases));

      // Expand both entries
      act(() => {
        result.current.toggleDetail('coding', 0);
        result.current.toggleDetail('coding', 1);
      });

      const expandedEntries = result.current.flattenedItems.filter(item => item.type === 'log-entry');
      expect(expandedEntries[0].isDetailExpanded).toBe(true);
      expect(expandedEntries[1].isDetailExpanded).toBe(true);

      // Collapse all
      act(() => {
        result.current.collapseAllDetails();
      });

      const collapsedEntries = result.current.flattenedItems.filter(item => item.type === 'log-entry');
      expect(collapsedEntries[0].isDetailExpanded).toBe(false);
      expect(collapsedEntries[1].isDetailExpanded).toBe(false);
    });
  });

  describe('estimateSize', () => {
    it('should return estimated height for valid index', () => {
      const logs = createTestTaskLogs();
      const { result } = renderHook(() => useVirtualizedLogs(logs, new Set()));

      // First item is planning phase header
      const height = result.current.estimateSize(0);
      expect(height).toBe(ESTIMATED_HEIGHTS.PHASE_HEADER);
    });

    it('should return default height for invalid index', () => {
      const logs = createTestTaskLogs();
      const { result } = renderHook(() => useVirtualizedLogs(logs, new Set()));

      const height = result.current.estimateSize(999); // Out of bounds
      expect(height).toBe(ESTIMATED_HEIGHTS.LOG_ENTRY_SIMPLE);
    });

    it('should update when detail expansion changes', () => {
      const entry = createTestLogEntry({
        content: 'Test entry',
        phase: 'coding',
        detail: 'Some detail content\nWith multiple lines\nOf text'
      });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });
      const expandedPhases = new Set<TaskLogPhase>(['coding']);

      const { result } = renderHook(() => useVirtualizedLogs(logs, expandedPhases));

      // Index 2 is the coding entry (0: planning header, 1: coding header, 2: coding entry)
      const collapsedHeight = result.current.estimateSize(2);

      // Expand detail
      act(() => {
        result.current.toggleDetail('coding', 0);
      });

      const expandedHeight = result.current.estimateSize(2);
      expect(expandedHeight).toBeGreaterThan(collapsedHeight);
    });
  });

  describe('reactivity', () => {
    it('should update flattened items when logs change', () => {
      const logs1 = createTestTaskLogs();
      const { result, rerender } = renderHook(
        ({ logs, expanded }) => useVirtualizedLogs(logs, expanded),
        { initialProps: { logs: logs1, expanded: new Set<TaskLogPhase>() } }
      );

      expect(result.current.flattenedItems).toHaveLength(3);

      // Add entries to coding phase
      const entry = createTestLogEntry({ content: 'New entry', phase: 'coding' });
      const logs2 = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      rerender({ logs: logs2, expanded: new Set<TaskLogPhase>(['coding']) });

      // Should now have 3 headers + 1 entry = 4 items
      expect(result.current.flattenedItems).toHaveLength(4);
    });

    it('should update flattened items when expanded phases change', () => {
      const entry = createTestLogEntry({ content: 'Test entry', phase: 'coding' });
      const logs = createTestTaskLogs({
        phases: {
          planning: createTestPhaseLog('planning', []),
          coding: createTestPhaseLog('coding', [entry]),
          validation: createTestPhaseLog('validation', []),
        },
      });

      const { result, rerender } = renderHook(
        ({ logs, expanded }) => useVirtualizedLogs(logs, expanded),
        { initialProps: { logs, expanded: new Set<TaskLogPhase>() } }
      );

      // Initially, only 3 headers
      expect(result.current.flattenedItems).toHaveLength(3);

      // Expand coding phase
      rerender({ logs, expanded: new Set<TaskLogPhase>(['coding']) });

      // Now should have 3 headers + 1 entry = 4 items
      expect(result.current.flattenedItems).toHaveLength(4);
    });
  });
});
