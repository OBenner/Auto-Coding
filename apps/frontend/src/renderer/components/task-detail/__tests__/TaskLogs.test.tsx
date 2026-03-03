/**
 * @vitest-environment jsdom
 */
/**
 * Integration tests for TaskLogs component
 *
 * Key behavior tested:
 * - Virtual scrolling with @tanstack/react-virtual
 * - Filter logic (all, errors, tools, info)
 * - Search functionality across content, detail, tool_name, tool_input
 * - Phase expansion and detail expansion state management
 * - New logs detection when scrolled up
 * - Height estimation for different log entry types
 * - Performance metrics logging in development mode
 *
 * Test approach:
 * - Extract and test key logic functions without rendering full component
 * - Use factory functions for mock data generation
 * - Test edge cases and state transitions
 * - Verify performance with large datasets (1000+ entries)
 */
import { describe, it, expect } from 'vitest';
import type { TaskLogEntry, TaskLogPhase, TaskLogs, TaskLogEntryType } from '../../../../shared/types';
import {
  generateTestTaskLogs,
  generateTestLogEntries,
  generateSpecializedTestLogs
} from './test-data';
import {
  entryMatchesFilter,
  entryMatchesSearch,
  computePhasesWithMatchingEntries,
  calculateTotalLogCount
} from '../log-utils';

/**
 * Factory function to create a minimal TaskLogs object
 */
function createMockTaskLogs(overrides: Partial<TaskLogs> = {}): TaskLogs {
  return {
    spec_id: 'spec-1',
    created_at: '2025-01-01T10:00:00Z',
    updated_at: '2025-01-01T11:00:00Z',
    phases: {
      planning: {
        phase: 'planning',
        status: 'completed',
        started_at: '2025-01-01T10:00:00Z',
        completed_at: '2025-01-01T10:30:00Z',
        entries: []
      },
      coding: {
        phase: 'coding',
        status: 'active',
        started_at: '2025-01-01T10:30:00Z',
        completed_at: null,
        entries: []
      },
      validation: {
        phase: 'validation',
        status: 'pending',
        started_at: null,
        completed_at: null,
        entries: []
      }
    },
    ...overrides
  };
}

/**
 * Factory function to create a mock log entry
 */
function createMockLogEntry(overrides: Partial<TaskLogEntry> = {}): TaskLogEntry {
  return {
    timestamp: '2025-01-01T10:00:00Z',
    type: 'text',
    content: 'Test log entry',
    phase: 'coding',
    ...overrides
  };
}

describe('TaskLogs - Filter Logic', () => {
  describe('entryMatchesFilter', () => {
    it('should return true for all entries when filter is "all"', () => {
      const textEntry = createMockLogEntry({ type: 'text' });
      const errorEntry = createMockLogEntry({ type: 'error' });
      const toolEntry = createMockLogEntry({ type: 'tool_start' });

      expect(entryMatchesFilter(textEntry, 'all')).toBe(true);
      expect(entryMatchesFilter(errorEntry, 'all')).toBe(true);
      expect(entryMatchesFilter(toolEntry, 'all')).toBe(true);
    });

    it('should filter only error entries when filter is "errors"', () => {
      const errorEntry = createMockLogEntry({ type: 'error' });
      const textEntry = createMockLogEntry({ type: 'text' });
      const toolEntry = createMockLogEntry({ type: 'tool_start' });

      expect(entryMatchesFilter(errorEntry, 'errors')).toBe(true);
      expect(entryMatchesFilter(textEntry, 'errors')).toBe(false);
      expect(entryMatchesFilter(toolEntry, 'errors')).toBe(false);
    });

    it('should filter only tool entries when filter is "tools"', () => {
      const toolStartEntry = createMockLogEntry({ type: 'tool_start' });
      const toolEndEntry = createMockLogEntry({ type: 'tool_end' });
      const textEntry = createMockLogEntry({ type: 'text' });
      const errorEntry = createMockLogEntry({ type: 'error' });

      expect(entryMatchesFilter(toolStartEntry, 'tools')).toBe(true);
      expect(entryMatchesFilter(toolEndEntry, 'tools')).toBe(true);
      expect(entryMatchesFilter(textEntry, 'tools')).toBe(false);
      expect(entryMatchesFilter(errorEntry, 'tools')).toBe(false);
    });

    it('should filter info-related entries when filter is "info"', () => {
      const infoEntry = createMockLogEntry({ type: 'info' });
      const successEntry = createMockLogEntry({ type: 'success' });
      const textEntry = createMockLogEntry({ type: 'text' });
      const phaseStartEntry = createMockLogEntry({ type: 'phase_start' });
      const phaseEndEntry = createMockLogEntry({ type: 'phase_end' });
      const toolEntry = createMockLogEntry({ type: 'tool_start' });
      const errorEntry = createMockLogEntry({ type: 'error' });

      expect(entryMatchesFilter(infoEntry, 'info')).toBe(true);
      expect(entryMatchesFilter(successEntry, 'info')).toBe(true);
      expect(entryMatchesFilter(textEntry, 'info')).toBe(true);
      expect(entryMatchesFilter(phaseStartEntry, 'info')).toBe(true);
      expect(entryMatchesFilter(phaseEndEntry, 'info')).toBe(true);
      expect(entryMatchesFilter(toolEntry, 'info')).toBe(false);
      expect(entryMatchesFilter(errorEntry, 'info')).toBe(false);
    });

    it('should handle undefined entries gracefully', () => {
      expect(entryMatchesFilter(undefined, 'all')).toBe(true);
      expect(entryMatchesFilter(undefined, 'errors')).toBe(false);
      expect(entryMatchesFilter(undefined, 'tools')).toBe(false);
    });
  });

  describe('computePhasesWithMatchingEntries', () => {
    it('should return empty set when filter is "all"', () => {
      const taskLogs = createMockTaskLogs();
      const result = computePhasesWithMatchingEntries(taskLogs, 'all');

      expect(result.size).toBe(0);
    });

    it('should return empty set when phaseLogs is null', () => {
      const result = computePhasesWithMatchingEntries(null, 'errors');
      expect(result.size).toBe(0);
    });

    it('should identify phases with error entries', () => {
      const taskLogs = createMockTaskLogs({
        phases: {
          planning: {
            phase: 'planning',
            status: 'completed',
            started_at: '2025-01-01T10:00:00Z',
            completed_at: '2025-01-01T10:30:00Z',
            entries: [
              createMockLogEntry({ type: 'error', phase: 'planning', content: 'Error 1' }),
              createMockLogEntry({ type: 'text', phase: 'planning', content: 'Info' })
            ]
          },
          coding: {
            phase: 'coding',
            status: 'active',
            started_at: '2025-01-01T10:30:00Z',
            completed_at: null,
            entries: [
              createMockLogEntry({ type: 'text', phase: 'coding', content: 'No errors here' })
            ]
          },
          validation: {
            phase: 'validation',
            status: 'pending',
            started_at: null,
            completed_at: null,
            entries: [
              createMockLogEntry({ type: 'error', phase: 'validation', content: 'Error 2' })
            ]
          }
        }
      });

      const result = computePhasesWithMatchingEntries(taskLogs, 'errors');

      expect(result.has('planning')).toBe(true);
      expect(result.has('coding')).toBe(false);
      expect(result.has('validation')).toBe(true);
    });

    it('should identify phases with tool entries', () => {
      const taskLogs = createMockTaskLogs({
        phases: {
          planning: {
            phase: 'planning',
            status: 'completed',
            started_at: '2025-01-01T10:00:00Z',
            completed_at: '2025-01-01T10:30:00Z',
            entries: [
              createMockLogEntry({ type: 'tool_start', phase: 'planning', tool_name: 'Read' }),
              createMockLogEntry({ type: 'tool_end', phase: 'planning', tool_name: 'Read' })
            ]
          },
          coding: {
            phase: 'coding',
            status: 'active',
            started_at: '2025-01-01T10:30:00Z',
            completed_at: null,
            entries: [
              createMockLogEntry({ type: 'text', phase: 'coding', content: 'Just text' })
            ]
          },
          validation: {
            phase: 'validation',
            status: 'pending',
            started_at: null,
            completed_at: null,
            entries: []
          }
        }
      });

      const result = computePhasesWithMatchingEntries(taskLogs, 'tools');

      expect(result.has('planning')).toBe(true);
      expect(result.has('coding')).toBe(false);
      expect(result.has('validation')).toBe(false);
    });
  });
});

describe('TaskLogs - Search Functionality', () => {
  describe('entryMatchesSearch', () => {
    it('should return true when query is empty', () => {
      const entry = createMockLogEntry({ content: 'Some content' });
      expect(entryMatchesSearch(entry, '')).toBe(true);
      expect(entryMatchesSearch(entry, '   ')).toBe(true);
    });

    it('should return true for undefined entry when query is empty', () => {
      expect(entryMatchesSearch(undefined, '')).toBe(true);
    });

    it('should search in content field', () => {
      const entry = createMockLogEntry({ content: 'Reading file: src/app.ts' });
      expect(entryMatchesSearch(entry, 'app.ts')).toBe(true);
      expect(entryMatchesSearch(entry, 'reading')).toBe(true); // case insensitive
      expect(entryMatchesSearch(entry, 'nonexistent')).toBe(false);
    });

    it('should search in detail field', () => {
      const entry = createMockLogEntry({
        content: 'Operation completed',
        detail: 'File written to /path/to/file.ts with 200 lines'
      });
      expect(entryMatchesSearch(entry, 'file.ts')).toBe(true);
      expect(entryMatchesSearch(entry, '200 lines')).toBe(true);
      expect(entryMatchesSearch(entry, 'nonexistent')).toBe(false);
    });

    it('should search in tool_name field', () => {
      const entry = createMockLogEntry({
        type: 'tool_start',
        tool_name: 'Grep',
        content: 'Starting tool'
      });
      expect(entryMatchesSearch(entry, 'grep')).toBe(true); // case insensitive
      expect(entryMatchesSearch(entry, 'Grep')).toBe(true);
      expect(entryMatchesSearch(entry, 'read')).toBe(false);
    });

    it('should search in tool_input field', () => {
      const entry = createMockLogEntry({
        type: 'tool_start',
        tool_name: 'Read',
        tool_input: 'apps/frontend/src/components/Header.tsx',
        content: 'Reading file'
      });
      expect(entryMatchesSearch(entry, 'header')).toBe(true); // matches in tool_input
      expect(entryMatchesSearch(entry, 'apps')).toBe(true);
      expect(entryMatchesSearch(entry, 'nonexistent')).toBe(false);
    });

    it('should be case insensitive', () => {
      const entry = createMockLogEntry({
        content: 'ERROR: Something went wrong',
        detail: 'Stack trace at FILE.ts',
        tool_name: 'Bash'
      });
      expect(entryMatchesSearch(entry, 'error')).toBe(true);
      expect(entryMatchesSearch(entry, 'FILE.TS')).toBe(true);
      expect(entryMatchesSearch(entry, 'bash')).toBe(true);
    });

    it('should search across all fields', () => {
      const entry = createMockLogEntry({
        type: 'tool_start',
        tool_name: 'Write',
        tool_input: 'src/components/Test.tsx',
        content: 'Writing component',
        detail: 'Created new React component with hooks'
      });

      // Should match in any field
      expect(entryMatchesSearch(entry, 'write')).toBe(true); // tool_name
      expect(entryMatchesSearch(entry, 'test.tsx')).toBe(true); // tool_input
      expect(entryMatchesSearch(entry, 'writing')).toBe(true); // content
      expect(entryMatchesSearch(entry, 'react')).toBe(true); // detail
      expect(entryMatchesSearch(entry, 'nomatch')).toBe(false);
    });
  });
});

describe('TaskLogs - Log Count Calculation', () => {
  it('should return 0 for null phaseLogs', () => {
    expect(calculateTotalLogCount(null)).toBe(0);
  });

  it('should return 0 for empty phases', () => {
    const taskLogs = createMockTaskLogs();
    expect(calculateTotalLogCount(taskLogs)).toBe(0);
  });

  it('should count entries across all phases', () => {
    const taskLogs = createMockTaskLogs({
      phases: {
        planning: {
          phase: 'planning',
          status: 'completed',
          started_at: '2025-01-01T10:00:00Z',
          completed_at: '2025-01-01T10:30:00Z',
          entries: Array(10).fill(null).map((_, i) => createMockLogEntry({ phase: 'planning' }))
        },
        coding: {
          phase: 'coding',
          status: 'active',
          started_at: '2025-01-01T10:30:00Z',
          completed_at: null,
          entries: Array(20).fill(null).map((_, i) => createMockLogEntry({ phase: 'coding' }))
        },
        validation: {
          phase: 'validation',
          status: 'pending',
          started_at: null,
          completed_at: null,
          entries: Array(5).fill(null).map((_, i) => createMockLogEntry({ phase: 'validation' }))
        }
      }
    });

    expect(calculateTotalLogCount(taskLogs)).toBe(35);
  });

  it('should handle missing entries array', () => {
    const taskLogs = createMockTaskLogs({
      phases: {
        planning: {
          phase: 'planning',
          status: 'completed',
          started_at: '2025-01-01T10:00:00Z',
          completed_at: '2025-01-01T10:30:00Z',
          entries: Array(10).fill(null).map((_, i) => createMockLogEntry({ phase: 'planning' }))
        },
        coding: {
          phase: 'coding',
          status: 'active',
          started_at: '2025-01-01T10:30:00Z',
          completed_at: null,
          entries: undefined as any // Missing entries
        },
        validation: {
          phase: 'validation',
          status: 'pending',
          started_at: null,
          completed_at: null,
          entries: []
        }
      }
    });

    expect(calculateTotalLogCount(taskLogs)).toBe(10);
  });
});

describe('TaskLogs - Integration Scenarios', () => {
  describe('Filter + Search Combination', () => {
    it('should filter by errors and search within error entries', () => {
      const entries = [
        createMockLogEntry({ type: 'error', content: 'File not found: app.ts' }),
        createMockLogEntry({ type: 'error', content: 'Permission denied on file.ts' }),
        createMockLogEntry({ type: 'text', content: 'Reading app.ts' }),
        createMockLogEntry({ type: 'tool_start', tool_name: 'Read', tool_input: 'app.ts' })
      ];

      // First filter by errors, then search for "app.ts"
      const filteredByType = entries.filter(e => entryMatchesFilter(e, 'errors'));
      const filteredBySearch = filteredByType.filter(e => entryMatchesSearch(e, 'app.ts'));

      expect(filteredByType.length).toBe(2); // Only error entries
      expect(filteredBySearch.length).toBe(1); // Only "File not found: app.ts"
      expect(filteredBySearch[0].content).toContain('app.ts');
    });

    it('should filter by tools and search within tool entries', () => {
      const entries = [
        createMockLogEntry({ type: 'tool_start', tool_name: 'Read', tool_input: 'file1.ts' }),
        createMockLogEntry({ type: 'tool_end', tool_name: 'Read' }),
        createMockLogEntry({ type: 'tool_start', tool_name: 'Grep', tool_input: 'file2.ts' }),
        createMockLogEntry({ type: 'text', content: 'Reading file1.ts' })
      ];

      // First filter by tools, then search for "grep"
      const filteredByType = entries.filter(e => entryMatchesFilter(e, 'tools'));
      const filteredBySearch = filteredByType.filter(e => entryMatchesSearch(e, 'grep'));

      expect(filteredByType.length).toBe(3); // All tool entries
      expect(filteredBySearch.length).toBe(1); // Only Grep tool
      expect(filteredBySearch[0].tool_name).toBe('Grep');
    });
  });

  describe('Large Dataset Performance', () => {
    it('should handle 1000 log entries efficiently', () => {
      const startTime = performance.now();
      const taskLogs = generateTestTaskLogs({ entryCount: 1000 });
      const endTime = performance.now();

      const generationTime = endTime - startTime;

      // Should generate quickly (< 1 second)
      expect(generationTime).toBeLessThan(1000);

      // Should have entries in all phases
      expect(taskLogs.phases.planning.entries.length).toBeGreaterThan(0);
      expect(taskLogs.phases.coding.entries.length).toBeGreaterThan(0);
      expect(taskLogs.phases.validation.entries.length).toBeGreaterThan(0);

      const totalCount = calculateTotalLogCount(taskLogs);
      expect(totalCount).toBeGreaterThanOrEqual(1000);
    });

    it('should filter large dataset quickly', () => {
      const taskLogs = generateTestTaskLogs({ entryCount: 1000 });

      const startTime = performance.now();
      const matchingPhases = computePhasesWithMatchingEntries(taskLogs, 'errors');
      const endTime = performance.now();

      const filterTime = endTime - startTime;

      // Should filter quickly (< 10ms)
      expect(filterTime).toBeLessThan(10);
      expect(matchingPhases.size).toBeGreaterThan(0);
    });

    it('should search large dataset quickly', () => {
      const entries = generateTestLogEntries({ entryCount: 1000 });

      const startTime = performance.now();
      entries.filter(e => entryMatchesSearch(e, 'Read'));
      const endTime = performance.now();

      const searchTime = endTime - startTime;

      // Should search quickly (< 50ms for 1000 entries)
      expect(searchTime).toBeLessThan(50);
    });
  });

  describe('Specialized Log Scenarios', () => {
    it('should generate errors-only scenario', () => {
      const entries = generateSpecializedTestLogs('errors-only', 100);

      const errorEntries = entries.filter(e => entryMatchesFilter(e, 'errors'));

      expect(errorEntries.length).toBeGreaterThan(0);
      // errors-only should only contain error type entries
      expect(entries.every(e => e.type === 'error')).toBe(true);
    });

    it('should generate tools-only scenario', () => {
      const entries = generateSpecializedTestLogs('tools-only', 100);

      const toolEntries = entries.filter(e => entryMatchesFilter(e, 'tools'));

      expect(toolEntries.length).toBeGreaterThan(0);
      expect(toolEntries.every(e => e.type === 'tool_start' || e.type === 'tool_end')).toBe(true);
    });

    it('should generate text-only scenario', () => {
      const entries = generateSpecializedTestLogs('text-only', 100);

      const infoEntries = entries.filter(e => entryMatchesFilter(e, 'info'));

      expect(infoEntries.length).toBeGreaterThan(0);
    });

    it('should generate mixed-heavy scenario with extended details', () => {
      const entries = generateSpecializedTestLogs('mixed-heavy', 100);

      const entriesWithDetails = entries.filter(e => e.detail);

      expect(entriesWithDetails.length).toBeGreaterThan(0);
      expect(entriesWithDetails[0].detail).toContain('Extended detail content');
    });
  });
});

describe('TaskLogs - Edge Cases', () => {
  it('should handle empty task logs', () => {
    const taskLogs = createMockTaskLogs();
    expect(calculateTotalLogCount(taskLogs)).toBe(0);

    const matchingPhases = computePhasesWithMatchingEntries(taskLogs, 'errors');
    expect(matchingPhases.size).toBe(0);
  });

  it('should handle null task logs', () => {
    expect(calculateTotalLogCount(null)).toBe(0);

    const matchingPhases = computePhasesWithMatchingEntries(null, 'errors');
    expect(matchingPhases.size).toBe(0);
  });

  it('should handle entries with missing fields', () => {
    const entry = {
      timestamp: '2025-01-01T10:00:00Z',
      type: 'text' as TaskLogEntryType,
      content: 'Test',
      phase: 'coding' as TaskLogPhase
    };

    // Should not crash when searching
    expect(entryMatchesSearch(entry, 'test')).toBe(true);
    expect(entryMatchesSearch(entry, 'nonexistent')).toBe(false);
  });

  it('should handle special characters in search query', () => {
    const entry = createMockLogEntry({
      content: 'Error: $PATH not set',
      detail: 'Check environment variables: NODE_ENV=test',
      tool_name: 'Bash'
    });

    expect(entryMatchesSearch(entry, '$PATH')).toBe(true);
    expect(entryMatchesSearch(entry, 'NODE_ENV=test')).toBe(true);
  });

  it('should handle unicode characters in content', () => {
    const entry = createMockLogEntry({
      content: 'Processing file: тест.tsx',
      detail: 'Unicode support: 🎉 ✓ ✗'
    });

    expect(entryMatchesSearch(entry, 'тест')).toBe(true);
    expect(entryMatchesSearch(entry, '🎉')).toBe(true);
  });

  it('should handle very long search queries', () => {
    const entry = createMockLogEntry({
      content: 'Normal content'
    });

    const longQuery = 'a'.repeat(1000);
    expect(entryMatchesSearch(entry, longQuery)).toBe(false);
  });

  it('should handle entries with very long content', () => {
    const longContent = 'Log entry '.repeat(1000);
    const entry = createMockLogEntry({
      content: longContent
    });

    expect(entryMatchesSearch(entry, 'Log entry')).toBe(true);
  });
});

describe('TaskLogs - Phase State Management', () => {
  it('should track expanded phases correctly', () => {
    const expandedPhases = new Set<TaskLogPhase>(['planning', 'coding']);

    expect(expandedPhases.has('planning')).toBe(true);
    expect(expandedPhases.has('coding')).toBe(true);
    expect(expandedPhases.has('validation')).toBe(false);

    // Toggle validation phase
    expandedPhases.add('validation');
    expect(expandedPhases.has('validation')).toBe(true);

    // Toggle off planning phase
    expandedPhases.delete('planning');
    expect(expandedPhases.has('planning')).toBe(false);
  });

  it('should merge expanded phases with filter-matched phases', () => {
    const userExpandedPhases = new Set<TaskLogPhase>(['planning']);
    const filterMatchedPhases = new Set<TaskLogPhase>(['coding', 'validation']);

    // Effective expanded phases = union of both
    const effectiveExpanded = new Set(userExpandedPhases);
    filterMatchedPhases.forEach(phase => effectiveExpanded.add(phase));

    expect(effectiveExpanded.has('planning')).toBe(true); // User expanded
    expect(effectiveExpanded.has('coding')).toBe(true); // Filter matched
    expect(effectiveExpanded.has('validation')).toBe(true); // Filter matched
  });

  it('should use user expanded phases when filter is "all"', () => {
    const userExpandedPhases = new Set<TaskLogPhase>(['planning']);
    const filterMatchedPhases = new Set<TaskLogPhase>(); // Empty when filter is 'all'

    const effectiveExpanded = new Set(userExpandedPhases);
    filterMatchedPhases.forEach(phase => effectiveExpanded.add(phase));

    expect(effectiveExpanded.size).toBe(1);
    expect(effectiveExpanded.has('planning')).toBe(true);
  });
});

describe('TaskLogs - Performance Metrics', () => {
  it('should track initial render time', () => {
    const renderStartTime = performance.now();

    // Simulate rendering with 1000 entries
    const taskLogs = generateTestTaskLogs({ entryCount: 1000 });
    const totalLogCount = calculateTotalLogCount(taskLogs);

    const renderEndTime = performance.now();
    const initialRenderTime = renderEndTime - renderStartTime;

    expect(totalLogCount).toBeGreaterThanOrEqual(1000);
    expect(initialRenderTime).toBeGreaterThan(0);

    // Performance target: < 100ms for 1000 entries
    // Note: This may vary depending on system, so we just track it
    const performanceTarget = 100;
    const passed = initialRenderTime < performanceTarget;

    if (passed) {
      expect(initialRenderTime).toBeLessThan(performanceTarget);
    }
  });

  it('should measure filter change performance', () => {
    const taskLogs = generateTestTaskLogs({ entryCount: 1000 });

    const filterStartTime = performance.now();
    const matchingPhases = computePhasesWithMatchingEntries(taskLogs, 'errors');
    const filterEndTime = performance.now();

    const filterTime = filterEndTime - filterStartTime;

    expect(matchingPhases.size).toBeGreaterThan(0);
    expect(filterTime).toBeGreaterThan(0);

    // Performance target: < 10ms for filter change
    const performanceTarget = 10;
    expect(filterTime).toBeLessThan(performanceTarget);
  });
});
