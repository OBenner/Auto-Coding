/**
 * Unit tests for progress calculation utilities
 * Tests progress percentage calculations and status determination
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  calculateProgress,
  countSubtasksByStatus,
  determineOverallStatus,
  formatProgressString,
  estimateRemainingTime,
  formatElapsedTime,
  formatRemainingTime,
  formatConfidence,
  millisecondsToSeconds
} from '../progress';
import type { Subtask, SubtaskStatus } from '../types';

// Helper to create subtasks
function createSubtasks(statuses: SubtaskStatus[]): Subtask[] {
  return statuses.map((status, i) => ({
    id: `subtask-${i}`,
    title: `Subtask ${i}`,
    description: `Description ${i}`,
    status,
    files: []
  }));
}

describe('calculateProgress', () => {
  describe('with 0 subtasks', () => {
    it('should return 0 for empty array', () => {
      const progress = calculateProgress([]);
      expect(progress).toBe(0);
    });
  });

  describe('with all pending subtasks', () => {
    it('should return 0 when all subtasks are pending', () => {
      const subtasks = createSubtasks(['pending', 'pending', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(0);
    });
  });

  describe('with all completed subtasks', () => {
    it('should return 100 when all subtasks are completed', () => {
      const subtasks = createSubtasks(['completed', 'completed', 'completed']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(100);
    });

    it('should return 100 for single completed subtask', () => {
      const subtasks = createSubtasks(['completed']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(100);
    });
  });

  describe('with mixed status subtasks', () => {
    it('should calculate correct percentage for mixed statuses', () => {
      // 2 completed out of 4 = 50%
      const subtasks = createSubtasks(['completed', 'completed', 'pending', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(50);
    });

    it('should round to nearest integer', () => {
      // 1 completed out of 3 = 33.33... → 33%
      const subtasks = createSubtasks(['completed', 'pending', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(33);
    });

    it('should handle in_progress as not completed', () => {
      // Only 'completed' status counts
      const subtasks = createSubtasks(['completed', 'in_progress', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(33);
    });

    it('should handle failed as not completed', () => {
      const subtasks = createSubtasks(['completed', 'failed', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(33);
    });

    it('should calculate 25% correctly', () => {
      const subtasks = createSubtasks(['completed', 'pending', 'pending', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(25);
    });

    it('should calculate 75% correctly', () => {
      const subtasks = createSubtasks(['completed', 'completed', 'completed', 'pending']);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(75);
    });

    it('should handle large number of subtasks', () => {
      const statuses: SubtaskStatus[] = Array(100)
        .fill('completed', 0, 73)
        .fill('pending', 73);
      const subtasks = createSubtasks(statuses as SubtaskStatus[]);
      const progress = calculateProgress(subtasks);
      expect(progress).toBe(73);
    });
  });
});

describe('countSubtasksByStatus', () => {
  it('should return zeros for empty array', () => {
    const counts = countSubtasksByStatus([]);
    expect(counts).toEqual({
      pending: 0,
      in_progress: 0,
      completed: 0,
      failed: 0
    });
  });

  it('should count all statuses correctly', () => {
    const subtasks = createSubtasks([
      'pending',
      'pending',
      'in_progress',
      'completed',
      'completed',
      'completed',
      'failed'
    ]);
    const counts = countSubtasksByStatus(subtasks);
    expect(counts).toEqual({
      pending: 2,
      in_progress: 1,
      completed: 3,
      failed: 1
    });
  });

  it('should handle single status', () => {
    const subtasks = createSubtasks(['pending', 'pending', 'pending']);
    const counts = countSubtasksByStatus(subtasks);
    expect(counts.pending).toBe(3);
    expect(counts.in_progress).toBe(0);
    expect(counts.completed).toBe(0);
    expect(counts.failed).toBe(0);
  });
});

describe('determineOverallStatus', () => {
  it('should return not_started for empty array', () => {
    const status = determineOverallStatus([]);
    expect(status).toBe('not_started');
  });

  it('should return not_started when all pending', () => {
    const subtasks = createSubtasks(['pending', 'pending']);
    const status = determineOverallStatus(subtasks);
    expect(status).toBe('not_started');
  });

  it('should return completed when all completed', () => {
    const subtasks = createSubtasks(['completed', 'completed']);
    const status = determineOverallStatus(subtasks);
    expect(status).toBe('completed');
  });

  it('should return in_progress when some in_progress', () => {
    const subtasks = createSubtasks(['pending', 'in_progress', 'completed']);
    const status = determineOverallStatus(subtasks);
    expect(status).toBe('in_progress');
  });

  it('should return in_progress when some completed', () => {
    const subtasks = createSubtasks(['pending', 'completed']);
    const status = determineOverallStatus(subtasks);
    expect(status).toBe('in_progress');
  });

  it('should return failed when any failed', () => {
    const subtasks = createSubtasks(['completed', 'failed', 'pending']);
    const status = determineOverallStatus(subtasks);
    expect(status).toBe('failed');
  });

  it('should prioritize failed over in_progress', () => {
    const subtasks = createSubtasks(['in_progress', 'failed']);
    const status = determineOverallStatus(subtasks);
    expect(status).toBe('failed');
  });
});

describe('formatProgressString', () => {
  it('should return "No subtasks" for 0 total', () => {
    const str = formatProgressString(0, 0);
    expect(str).toBe('No subtasks');
  });

  it('should format completed/total correctly', () => {
    expect(formatProgressString(3, 5)).toBe('3/5 subtasks');
    expect(formatProgressString(0, 10)).toBe('0/10 subtasks');
    expect(formatProgressString(10, 10)).toBe('10/10 subtasks');
    expect(formatProgressString(1, 1)).toBe('1/1 subtasks');
  });
});

describe('estimateRemainingTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('should return null for 0% progress', () => {
    const startTime = new Date();
    vi.advanceTimersByTime(60000); // 1 minute
    const remaining = estimateRemainingTime(startTime, 0);
    expect(remaining).toBeNull();
  });

  it('should return null for 100% progress', () => {
    const startTime = new Date();
    vi.advanceTimersByTime(60000);
    const remaining = estimateRemainingTime(startTime, 100);
    expect(remaining).toBeNull();
  });

  it('should return null for negative progress', () => {
    const startTime = new Date();
    vi.advanceTimersByTime(60000);
    const remaining = estimateRemainingTime(startTime, -10);
    expect(remaining).toBeNull();
  });

  it('should estimate remaining time at 50%', () => {
    const startTime = new Date();
    vi.advanceTimersByTime(60000); // 1 minute elapsed

    const remaining = estimateRemainingTime(startTime, 50);

    // At 50% with 1 minute elapsed, total should be 2 minutes
    // So remaining should be about 1 minute (60000ms)
    expect(remaining).toBe(60000);
  });

  it('should estimate remaining time at 25%', () => {
    const startTime = new Date();
    vi.advanceTimersByTime(30000); // 30 seconds elapsed

    const remaining = estimateRemainingTime(startTime, 25);

    // At 25% with 30s elapsed, total should be 120s
    // Remaining should be 90s (90000ms)
    expect(remaining).toBe(90000);
  });

  it('should estimate remaining time at 75%', () => {
    const startTime = new Date();
    vi.advanceTimersByTime(90000); // 90 seconds elapsed

    const remaining = estimateRemainingTime(startTime, 75);

    // At 75% with 90s elapsed, total should be 120s
    // Remaining should be 30s (30000ms)
    expect(remaining).toBe(30000);
  });

  it('should return 0 if calculation results in negative', () => {
    // This shouldn't happen in practice but we handle it
    const startTime = new Date();
    vi.advanceTimersByTime(1000);

    // If somehow progress is very high relative to time
    const remaining = estimateRemainingTime(startTime, 99);

    // Should be a small positive number or 0, not negative
    expect(remaining).toBeGreaterThanOrEqual(0);
  });
});

describe('formatElapsedTime', () => {
  it('should format zero seconds', () => {
    expect(formatElapsedTime(0)).toBe('0:00');
  });

  it('should format negative seconds as 0:00', () => {
    expect(formatElapsedTime(-10)).toBe('0:00');
  });

  it('should format seconds less than 1 minute', () => {
    expect(formatElapsedTime(5)).toBe('0:05');
    expect(formatElapsedTime(30)).toBe('0:30');
    expect(formatElapsedTime(59)).toBe('0:59');
  });

  it('should format minutes and seconds', () => {
    expect(formatElapsedTime(60)).toBe('1:00');
    expect(formatElapsedTime(83)).toBe('1:23');
    expect(formatElapsedTime(725)).toBe('12:05');
    expect(formatElapsedTime(3599)).toBe('59:59');
  });

  it('should format hours, minutes, and seconds', () => {
    expect(formatElapsedTime(3600)).toBe('1:00:00');
    expect(formatElapsedTime(3605)).toBe('1:00:05');
    expect(formatElapsedTime(3665)).toBe('1:01:05');
    expect(formatElapsedTime(43200)).toBe('12:00:00');
  });

  it('should pad minutes and seconds with leading zeros when hours present', () => {
    expect(formatElapsedTime(3665)).toBe('1:01:05');
    expect(formatElapsedTime(36005)).toBe('10:00:05');
  });
});

describe('formatRemainingTime', () => {
  it('should return "Unknown" for negative seconds', () => {
    expect(formatRemainingTime(-10)).toBe('Unknown');
  });

  it('should return "Less than 1 minute" for < 60 seconds', () => {
    expect(formatRemainingTime(0)).toBe('Less than 1 minute');
    expect(formatRemainingTime(30)).toBe('Less than 1 minute');
    expect(formatRemainingTime(59)).toBe('Less than 1 minute');
  });

  it('should format minutes with "About" prefix by default', () => {
    expect(formatRemainingTime(60)).toBe('About 1 minute');
    expect(formatRemainingTime(120)).toBe('About 2 minutes');
    expect(formatRemainingTime(300)).toBe('About 5 minutes');
    expect(formatRemainingTime(3540)).toBe('About 59 minutes');
  });

  it('should format hours with "About" prefix by default', () => {
    expect(formatRemainingTime(3600)).toBe('About 1 hour');
    expect(formatRemainingTime(7200)).toBe('About 2 hours');
    expect(formatRemainingTime(43200)).toBe('About 12 hours');
  });

  it('should format days with "About" prefix by default', () => {
    expect(formatRemainingTime(86400)).toBe('About 1 day');
    expect(formatRemainingTime(172800)).toBe('About 2 days');
  });

  it('should use "About" prefix for high confidence', () => {
    expect(formatRemainingTime(300, 'high')).toBe('About 5 minutes');
    expect(formatRemainingTime(3600, 'high')).toBe('About 1 hour');
  });

  it('should use "Roughly" prefix for low confidence', () => {
    expect(formatRemainingTime(300, 'low')).toBe('Roughly 5 minutes');
    expect(formatRemainingTime(3600, 'low')).toBe('Roughly 1 hour');
  });

  it('should use "About" prefix for medium confidence', () => {
    expect(formatRemainingTime(300, 'medium')).toBe('About 5 minutes');
    expect(formatRemainingTime(3600, 'medium')).toBe('About 1 hour');
  });

  it('should round to nearest unit', () => {
    expect(formatRemainingTime(90)).toBe('About 2 minutes'); // 1.5 minutes rounds to 2
    expect(formatRemainingTime(5400)).toBe('About 2 hours'); // 1.5 hours rounds to 2
  });
});

describe('formatConfidence', () => {
  it('should return empty string for undefined confidence', () => {
    expect(formatConfidence(undefined)).toBe('');
  });

  it('should format high confidence', () => {
    expect(formatConfidence('high')).toBe('● High confidence');
  });

  it('should format medium confidence', () => {
    expect(formatConfidence('medium')).toBe('◐ Medium confidence');
  });

  it('should format low confidence', () => {
    expect(formatConfidence('low')).toBe('○ Low confidence');
  });

  it('should include sample size when provided', () => {
    expect(formatConfidence('high', 10)).toBe('● High confidence (10 samples)');
    expect(formatConfidence('medium', 5)).toBe('◐ Medium confidence (5 samples)');
    expect(formatConfidence('low', 2)).toBe('○ Low confidence (2 samples)');
  });

  it('should not show sample size for 0 samples', () => {
    expect(formatConfidence('high', 0)).toBe('● High confidence');
  });

  it('should handle undefined sample size', () => {
    expect(formatConfidence('high', undefined)).toBe('● High confidence');
  });
});

describe('millisecondsToSeconds', () => {
  it('should convert milliseconds to seconds', () => {
    expect(millisecondsToSeconds(0)).toBe(0);
    expect(millisecondsToSeconds(1000)).toBe(1);
    expect(millisecondsToSeconds(5000)).toBe(5);
    expect(millisecondsToSeconds(60000)).toBe(60);
  });

  it('should floor fractional seconds', () => {
    expect(millisecondsToSeconds(1500)).toBe(1);
    expect(millisecondsToSeconds(1999)).toBe(1);
    expect(millisecondsToSeconds(2001)).toBe(2);
  });

  it('should handle negative values', () => {
    expect(millisecondsToSeconds(-1000)).toBe(-1);
  });
});
