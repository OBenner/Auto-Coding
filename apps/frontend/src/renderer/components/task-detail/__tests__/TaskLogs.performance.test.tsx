/**
 * @vitest-environment jsdom
 */
/**
 * Performance benchmark tests for TaskLogs component with large log sets
 *
 * These tests verify that virtual scrolling maintains acceptable performance
 * with large datasets (1000+ log entries) by measuring:
 * - Initial render time
 * - Filter change performance
 * - Search query performance
 * - Phase expansion/collapse performance
 * - Memory usage patterns
 *
 * Performance targets:
 * - Initial render: <100ms for 1000 entries
 * - Filter change: <50ms for any filter type
 * - Search query: <50ms for typical search terms
 * - Virtual scrolling should only render visible items (~20 items)
 *
 * Test approach:
 * - Generate large datasets using test-data.ts utilities
 * - Measure actual render times using performance.now()
 * - Verify virtual scrolling behavior (not all items rendered)
 * - Test with different data patterns (errors-only, tools-only, etc.)
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import { render, waitFor } from '@testing-library/react';
import React from 'react';
import type { TaskLogs, TaskLogPhase } from '../../../../shared/types';
import {
  generateTestTaskLogs,
  generateTestLogEntries,
  generateSpecializedTestLogs
} from './test-data';
import { TaskLogs as TaskLogsComponent } from '../TaskLogs';

/**
 * Factory function to create a mock Task object
 */
function createMockTask(overrides: Partial<any> = {}): any {
  return {
    id: 'task-1',
    specId: 'spec-1',
    projectId: 'project-1',
    title: 'Test Task',
    description: 'Test description',
    status: 'in_progress',
    subtasks: [],
    logs: [],
    createdAt: new Date('2025-01-01T10:00:00Z'),
    updatedAt: new Date('2025-01-01T11:00:00Z'),
    metadata: {
      model: 'sonnet',
      thinkingLevel: 'medium',
      isAutoProfile: false
    },
    ...overrides,
  };
}

/**
 * Factory function to create refs for TaskLogs component
 */
function createMockRefs() {
  return {
    logsEndRef: React.createRef<HTMLDivElement>(),
  };
}

/**
 * Performance measurement utility
 */
function measurePerformance<T>(
  operation: () => T,
  measurements: number[] = []
): { result: T; duration: number } {
  const startTime = performance.now();
  const result = operation();
  const endTime = performance.now();
  const duration = endTime - startTime;

  measurements.push(duration);

  return { result, duration };
}

/**
 * Performance measurement utility for void operations
 */
function measurePerformanceVoid(
  operation: () => void,
  measurements: number[] = []
): { duration: number } {
  const startTime = performance.now();
  operation();
  const endTime = performance.now();
  const duration = endTime - startTime;

  measurements.push(duration);

  return { duration };
}

/**
 * Calculate statistics from performance measurements
 */
function calculateStats(measurements: number[]) {
  if (measurements.length === 0) {
    return { min: 0, max: 0, avg: 0, median: 0 };
  }

  const sorted = [...measurements].sort((a, b) => a - b);
  const min = sorted[0];
  const max = sorted[sorted.length - 1];
  const sum = sorted.reduce((acc, val) => acc + val, 0);
  const avg = sum / sorted.length;
  const median = sorted[Math.floor(sorted.length / 2)];

  return { min, max, avg, median };
}

describe('TaskLogs Performance Benchmarks', () => {
  let mockConsoleGroup: ReturnType<typeof vi.spyOn>;
  let mockConsoleLog: ReturnType<typeof vi.spyOn>;
  let mockConsoleGroupEnd: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Mock console methods to avoid cluttering test output
    // The TaskLogs component logs performance metrics in development mode
    mockConsoleGroup = vi.spyOn(console, 'group').mockImplementation(() => {});
    mockConsoleLog = vi.spyOn(console, 'log').mockImplementation(() => {});
    mockConsoleGroupEnd = vi.spyOn(console, 'groupEnd').mockImplementation(() => {});

    // Set NODE_ENV to development to enable performance logging
    vi.stubEnv('NODE_ENV', 'development');
  });

  describe('Initial Render Performance', () => {
    it('should render 1000 log entries in less than 100ms', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });
      const totalEntries = Object.values(largeLogs.phases).reduce(
        (sum, phase) => sum + (phase?.entries?.length || 0),
        0
      );

      expect(totalEntries).toBeGreaterThanOrEqual(1000);

      const { result, duration } = measurePerformance(() => {
        return render(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={largeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      });

      // Verify render time is within acceptable limits
      expect(duration).toBeLessThan(100);

      // Verify component rendered successfully
      expect(result.container).toBeDefined();

      // Cleanup
      result.unmount();
    });

    it('should render 5000 log entries with acceptable performance', async () => {
      const veryLargeLogs = generateTestTaskLogs({ entryCount: 5000 });
      const totalEntries = Object.values(veryLargeLogs.phases).reduce(
        (sum, phase) => sum + (phase?.entries?.length || 0),
        0
      );

      expect(totalEntries).toBeGreaterThanOrEqual(5000);

      const { result, duration } = measurePerformance(() => {
        return render(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={veryLargeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      });

      // For 5000 entries, we allow more time but should still be under 200ms
      expect(duration).toBeLessThan(200);

      expect(result.container).toBeDefined();
      result.unmount();
    });

    it('should have consistent render times across multiple renders', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });
      const measurements: number[] = [];

      // Render the same component 5 times to measure consistency
      for (let i = 0; i < 5; i++) {
        const { result, duration } = measurePerformance(
          () =>
            render(
              <TaskLogsComponent
                task={createMockTask()}
                phaseLogs={largeLogs}
                isLoadingLogs={false}
                expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
                isStuck={false}
                {...createMockRefs()}
                onLogsScroll={vi.fn()}
                onTogglePhase={vi.fn()}
                shouldAutoScroll={false}
              />
            ),
          measurements
        );

        result.unmount();
      }

      const stats = calculateStats(measurements);

      // All renders should be under 100ms
      expect(stats.max).toBeLessThan(100);

      // Variance should be relatively low (max - min < 50ms)
      expect(stats.max - stats.min).toBeLessThan(50);
    });
  });

  describe('Filter Change Performance', () => {
    it('should switch between filters quickly with 1000 entries', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      const { result, duration: initialDuration } = measurePerformance(() => {
        return render(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={largeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      });

      // Find and click filter buttons
      const filterButtons = result.container.querySelectorAll('button');
      const errorsButton = Array.from(filterButtons).find(
        btn => btn.textContent === 'Errors'
      );

      expect(errorsButton).toBeDefined();

      // Measure filter change performance
      const { duration: filterDuration } = measurePerformance(() => {
        if (errorsButton) {
          errorsButton.click();
        }
      });

      // Filter change should be very fast (<50ms)
      expect(filterDuration).toBeLessThan(50);

      result.unmount();
    });

    it('should handle rapid filter changes without performance degradation', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      const renderResult = render(
        <TaskLogsComponent
          task={createMockTask()}
          phaseLogs={largeLogs}
          isLoadingLogs={false}
          expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
          isStuck={false}
          {...createMockRefs()}
          onLogsScroll={vi.fn()}
          onTogglePhase={vi.fn()}
          shouldAutoScroll={false}
        />
      );

      const filterButtons = renderResult.container.querySelectorAll('button');
      const filterLabels = ['All', 'Errors', 'Tools', 'Info'];

      const measurements: number[] = [];

      // Rapidly switch between all filters
      for (let i = 0; i < 10; i++) {
        for (const label of filterLabels) {
          const button = Array.from(filterButtons).find(btn => btn.textContent === label);

          if (button) {
            measurePerformanceVoid(() => {
              button.click();
            }, measurements);
          }
        }
      }

      const stats = calculateStats(measurements);

      // Even with rapid changes, each filter should be under 50ms
      expect(stats.max).toBeLessThan(50);

      // Average should be quite fast (<30ms)
      expect(stats.avg).toBeLessThan(30);

      renderResult.unmount();
    });
  });

  describe('Search Performance', () => {
    it('should handle search input updates efficiently with 1000 entries', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      const renderResult = render(
        <TaskLogsComponent
          task={createMockTask()}
          phaseLogs={largeLogs}
          isLoadingLogs={false}
          expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
          isStuck={false}
          {...createMockRefs()}
          onLogsScroll={vi.fn()}
          onTogglePhase={vi.fn()}
          shouldAutoScroll={false}
        />
      );

      const searchInput = renderResult.container.querySelector('input[type="text"]') as HTMLInputElement | null;
      expect(searchInput).toBeDefined();

      // Measure search input performance
      const searchTerms = ['error', 'Read', 'test', 'file'];

      const measurements: number[] = [];

      for (const term of searchTerms) {
        measurePerformanceVoid(() => {
          if (searchInput) {
            searchInput.value = term;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
          }
        }, measurements);
      }

      const stats = calculateStats(measurements);

      // All search updates should be under 50ms
      expect(stats.max).toBeLessThan(50);

      renderResult.unmount();
    });

    it('should handle complex search queries efficiently', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      const renderResult = render(
        <TaskLogsComponent
          task={createMockTask()}
          phaseLogs={largeLogs}
          isLoadingLogs={false}
          expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
          isStuck={false}
          {...createMockRefs()}
          onLogsScroll={vi.fn()}
          onTogglePhase={vi.fn()}
          shouldAutoScroll={false}
        />
      );

      const searchInput = renderResult.container.querySelector('input[type="text"]') as HTMLInputElement | null;
      expect(searchInput).toBeDefined();

      const complexQueries = [
        'Read file permissions',
        'Write component with error handling',
        'test connection timeout',
        'configuration error invalid settings'
      ];

      const measurements: number[] = [];

      for (const query of complexQueries) {
        if (searchInput) {
          searchInput.value = '';
          searchInput.dispatchEvent(new Event('input', { bubbles: true }));

          measurePerformanceVoid(() => {
            searchInput.value = query;
            searchInput.dispatchEvent(new Event('input', { bubbles: true }));
          }, measurements);
        }
      }

      const stats = calculateStats(measurements);

      // Even complex searches should be fast (<50ms)
      expect(stats.max).toBeLessThan(50);

      renderResult.unmount();
    });
  });

  describe('Memory and Rendering Efficiency', () => {
    it('should only render visible items with virtual scrolling', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      const renderResult = render(
        <TaskLogsComponent
          task={createMockTask()}
          phaseLogs={largeLogs}
          isLoadingLogs={false}
          expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
          isStuck={false}
          {...createMockRefs()}
          onLogsScroll={vi.fn()}
          onTogglePhase={vi.fn()}
          shouldAutoScroll={false}
        />
      );

      // Wait for component to fully render
      await waitFor(() => {
        expect(renderResult.container).toBeDefined();
      });

      // Count actual rendered log entries (not all 1000 should be in DOM)
      const allEntries = Object.values(largeLogs.phases).reduce(
        (sum, phase) => sum + (phase?.entries?.length || 0),
        0
      );

      expect(allEntries).toBeGreaterThan(1000);

      // Virtual scrolling should render much fewer items than total
      // Typically only ~20-30 items are visible at once
      const renderedElements = renderResult.container.querySelectorAll('[class*="ml-6"]').length;
      expect(renderedElements).toBeLessThan(100);

      renderResult.unmount();
    });

    it('should handle specialized log patterns efficiently', async () => {
      const scenarios: Array<'errors-only' | 'tools-only' | 'text-only' | 'mixed-heavy'> = [
        'errors-only',
        'tools-only',
        'text-only',
        'mixed-heavy'
      ];

      const measurements: number[] = [];

      for (const scenario of scenarios) {
        const entries = generateSpecializedTestLogs(scenario, 500);
        const mockLogs: TaskLogs = {
          spec_id: 'test-spec',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          phases: {
            planning: {
              phase: 'planning',
              status: 'completed',
              started_at: new Date().toISOString(),
              completed_at: new Date().toISOString(),
              entries: []
            },
            coding: {
              phase: 'coding',
              status: 'completed',
              started_at: new Date().toISOString(),
              completed_at: new Date().toISOString(),
              entries
            },
            validation: {
              phase: 'validation',
              status: 'pending',
              started_at: null,
              completed_at: null,
              entries: []
            }
          }
        };

        const { result, duration } = measurePerformance(
          () =>
            render(
              <TaskLogsComponent
                task={createMockTask()}
                phaseLogs={mockLogs}
                isLoadingLogs={false}
                expandedPhases={new Set<TaskLogPhase>(['coding'])}
                isStuck={false}
                {...createMockRefs()}
                onLogsScroll={vi.fn()}
                onTogglePhase={vi.fn()}
                shouldAutoScroll={false}
              />
            ),
          measurements
        );

        result.unmount();
      }

      const stats = calculateStats(measurements);

      // All specialized scenarios should render quickly
      expect(stats.max).toBeLessThan(100);
      expect(stats.avg).toBeLessThan(50);
    });
  });

  describe('Phase Expansion Performance', () => {
    it('should handle phase expansion/collapse efficiently', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      // Start with all phases expanded
      const renderResult = render(
        <TaskLogsComponent
          task={createMockTask()}
          phaseLogs={largeLogs}
          isLoadingLogs={false}
          expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
          isStuck={false}
          {...createMockRefs()}
          onLogsScroll={vi.fn()}
          onTogglePhase={vi.fn()}
          shouldAutoScroll={false}
        />
      );

      const measurements: number[] = [];

      // Measure collapse performance by re-rendering with collapsed phase
      const { duration: collapseDuration } = measurePerformanceVoid(() => {
        renderResult.rerender(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={largeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'validation'])} // Collapse coding
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      }, measurements);

      // Collapse should be fast (<50ms)
      expect(collapseDuration).toBeLessThan(50);

      // Measure expansion performance
      const { duration: expandDuration } = measurePerformanceVoid(() => {
        renderResult.rerender(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={largeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])} // Expand coding again
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      }, measurements);

      // Expansion should be fast (<50ms)
      expect(expandDuration).toBeLessThan(50);

      renderResult.unmount();
    });

    it('should handle all phases expanded efficiently', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      // Start with all phases collapsed
      const { result, duration } = measurePerformance(() => {
        return render(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={largeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>()} // No phases expanded
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      });

      // Initial render with collapsed phases should be very fast
      expect(duration).toBeLessThan(50);

      result.unmount();
    });
  });

  describe('Performance Regression Tests', () => {
    it('should maintain performance with increasing log sizes', async () => {
      const sizes = [100, 500, 1000, 2000];
      const measurements: Array<{ size: number; duration: number }> = [];

      for (const size of sizes) {
        const logs = generateTestTaskLogs({ entryCount: size });

        const startTime = performance.now();
        const renderResult = render(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={logs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
        const endTime = performance.now();
        const duration = endTime - startTime;

        measurements.push({ size, duration });

        renderResult.unmount();
      }

      // Verify performance scales roughly linearly (not exponentially)
      // The ratio of duration for 2000 vs 1000 should be reasonable
      const duration1000 = measurements.find(m => m.size === 1000)?.duration || 0;
      const duration2000 = measurements.find(m => m.size === 2000)?.duration || 0;

      if (duration1000 > 0 && duration2000 > 0) {
        const ratio = duration2000 / duration1000;

        // 2x data should take less than 3x time (linear scaling with some overhead)
        expect(ratio).toBeLessThan(3);
      }
    });

    it('should complete all operations within performance targets', async () => {
      const largeLogs = generateTestTaskLogs({ entryCount: 1000 });

      const allDurations: number[] = [];

      // Measure initial render
      const { result: initialResult, duration: initialDuration } = measurePerformance(() => {
        return render(
          <TaskLogsComponent
            task={createMockTask()}
            phaseLogs={largeLogs}
            isLoadingLogs={false}
            expandedPhases={new Set<TaskLogPhase>(['planning', 'coding', 'validation'])}
            isStuck={false}
            {...createMockRefs()}
            onLogsScroll={vi.fn()}
            onTogglePhase={vi.fn()}
            shouldAutoScroll={false}
          />
        );
      });

      allDurations.push(initialDuration);

      // Measure filter changes
      const filterButtons = initialResult.container.querySelectorAll('button');
      for (const label of ['Errors', 'Tools', 'Info']) {
        const button = Array.from(filterButtons).find(btn => btn.textContent === label);
        if (button) {
          measurePerformanceVoid(() => button.click(), allDurations);
        }
      }

      // Measure search
      const searchInput = initialResult.container.querySelector('input[type="text"]') as HTMLInputElement | null;
      if (searchInput) {
        measurePerformanceVoid(() => {
          searchInput.value = 'test';
          searchInput.dispatchEvent(new Event('input', { bubbles: true }));
        }, allDurations);
      }

      // All operations should be under their respective targets
      const stats = calculateStats(allDurations);

      // Max duration for any operation should be under 100ms
      expect(stats.max).toBeLessThan(100);

      // Average should be well under 50ms
      expect(stats.avg).toBeLessThan(50);

      initialResult.unmount();
    });
  });
});
