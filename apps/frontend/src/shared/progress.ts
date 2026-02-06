/**
 * Shared progress calculation utilities
 * Used by both main and renderer processes
 */
import type { Subtask, SubtaskStatus } from './types';

/**
 * Calculate progress percentage from subtasks
 * @param subtasks Array of subtasks with status
 * @returns Progress percentage (0-100)
 */
export function calculateProgress(subtasks: { status: string }[]): number {
  if (subtasks.length === 0) return 0;
  const completed = subtasks.filter((c) => c.status === 'completed').length;
  return Math.round((completed / subtasks.length) * 100);
}

/**
 * Count subtasks by status
 * @param subtasks Array of subtasks
 * @returns Object with counts per status
 */
export function countSubtasksByStatus(subtasks: Subtask[]): Record<SubtaskStatus, number> {
  return {
    pending: subtasks.filter((c) => c.status === 'pending').length,
    in_progress: subtasks.filter((c) => c.status === 'in_progress').length,
    completed: subtasks.filter((c) => c.status === 'completed').length,
    failed: subtasks.filter((c) => c.status === 'failed').length
  };
}

/**
 * Determine overall status from subtask statuses
 * @param subtasks Array of subtasks
 * @returns Overall status string
 */
export function determineOverallStatus(
  subtasks: { status: string }[]
): 'not_started' | 'in_progress' | 'completed' | 'failed' {
  if (subtasks.length === 0) return 'not_started';

  const hasCompleted = subtasks.some((c) => c.status === 'completed');
  const hasFailed = subtasks.some((c) => c.status === 'failed');
  const hasInProgress = subtasks.some((c) => c.status === 'in_progress');
  const allCompleted = subtasks.every((c) => c.status === 'completed');
  const allPending = subtasks.every((c) => c.status === 'pending');

  if (allCompleted) return 'completed';
  if (hasFailed) return 'failed';
  if (hasInProgress || hasCompleted) return 'in_progress';
  if (allPending) return 'not_started';

  return 'in_progress';
}

/**
 * Format progress as display string
 * @param completed Number of completed subtasks
 * @param total Total number of subtasks
 * @returns Formatted string like "3/5 subtasks"
 */
export function formatProgressString(completed: number, total: number): string {
  if (total === 0) return 'No subtasks';
  return `${completed}/${total} subtasks`;
}

/**
 * Calculate estimated remaining time based on progress
 * @param startTime Start time of the task
 * @param progress Current progress percentage (0-100)
 * @returns Estimated remaining time in milliseconds, or null if cannot estimate
 */
export function estimateRemainingTime(
  startTime: Date,
  progress: number
): number | null {
  if (progress <= 0 || progress >= 100) return null;

  const elapsed = Date.now() - startTime.getTime();
  const estimatedTotal = (elapsed / progress) * 100;
  const remaining = estimatedTotal - elapsed;

  return Math.max(0, Math.round(remaining));
}

/**
 * Formats elapsed time in seconds into a human-readable string.
 * Examples: "0:05", "1:23", "12:05", "1:00:05"
 *
 * @param seconds - The elapsed time in seconds
 * @returns Formatted time string (MM:SS or H:MM:SS for >= 1 hour)
 */
export function formatElapsedTime(seconds: number): string {
  if (seconds < 0) return '0:00';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${minutes}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Formats remaining time in seconds into a human-readable estimate.
 * Uses natural language for better user experience.
 * Examples: "Less than 1 minute", "About 5 minutes", "About 2 hours"
 *
 * @param seconds - The remaining time in seconds
 * @param confidence - Optional confidence level from historical data
 * @returns Formatted remaining time string
 */
export function formatRemainingTime(
  seconds: number,
  confidence?: 'high' | 'medium' | 'low'
): string {
  if (seconds < 0) return 'Unknown';

  const prefix = confidence === 'high' ? 'About' : confidence === 'low' ? 'Roughly' : 'About';

  // Less than 1 minute
  if (seconds < 60) {
    return 'Less than 1 minute';
  }

  // 1-59 minutes
  if (seconds < 3600) {
    const minutes = Math.round(seconds / 60);
    return minutes === 1 ? `${prefix} 1 minute` : `${prefix} ${minutes} minutes`;
  }

  // 1-23 hours
  if (seconds < 86400) {
    const hours = Math.round(seconds / 3600);
    return hours === 1 ? `${prefix} 1 hour` : `${prefix} ${hours} hours`;
  }

  // Days
  const days = Math.round(seconds / 86400);
  return days === 1 ? `${prefix} 1 day` : `${prefix} ${days} days`;
}

/**
 * Formats a confidence level for display with an emoji indicator.
 * Used to show the reliability of time estimates based on historical data.
 *
 * @param confidence - Confidence level from historical timing data
 * @param sampleSize - Number of historical samples (optional)
 * @returns Formatted confidence string with indicator
 */
export function formatConfidence(
  confidence: 'high' | 'medium' | 'low' | undefined,
  sampleSize?: number
): string {
  if (!confidence) return '';

  const indicators = {
    high: '●',    // Solid circle
    medium: '◐',  // Half circle
    low: '○'      // Empty circle
  };

  const labels = {
    high: 'High confidence',
    medium: 'Medium confidence',
    low: 'Low confidence'
  };

  const indicator = indicators[confidence];
  const label = labels[confidence];

  if (sampleSize !== undefined && sampleSize > 0) {
    return `${indicator} ${label} (${sampleSize} samples)`;
  }

  return `${indicator} ${label}`;
}

/**
 * Formats milliseconds into seconds for display.
 * Helper utility to convert between time units.
 *
 * @param milliseconds - Time in milliseconds
 * @returns Time in seconds
 */
export function millisecondsToSeconds(milliseconds: number): number {
  return Math.floor(milliseconds / 1000);
}

/**
 * Historical timing data for a task or subtask.
 * Used to improve time estimates based on past performance.
 */
export interface HistoricalTiming {
  taskType: string;    // e.g., "subtask", "spec_creation", "implementation"
  taskId: string;      // e.g., "subtask-5-1"
  duration: number;    // Duration in milliseconds
  completedAt: Date;   // When it was completed
  complexity?: string; // Optional complexity indicator
}

/**
 * Time estimate with confidence level based on historical data.
 */
export interface TimeEstimate {
  estimatedMs: number;
  confidence: 'high' | 'medium' | 'low';
  sampleSize: number;
  basedOn: 'historical' | 'progress' | 'default';
}

/**
 * Calculate average duration from historical timing data.
 *
 * @param timings - Array of historical timing records
 * @returns Average duration in milliseconds
 */
export function calculateAverageDuration(timings: HistoricalTiming[]): number {
  if (timings.length === 0) return 0;
  const sum = timings.reduce((acc, t) => acc + t.duration, 0);
  return Math.round(sum / timings.length);
}

/**
 * Calculate standard deviation of durations.
 * Used to assess variability in historical timing data.
 *
 * @param timings - Array of historical timing records
 * @returns Standard deviation in milliseconds
 */
export function calculateStandardDeviation(timings: HistoricalTiming[]): number {
  if (timings.length === 0) return 0;

  const avg = calculateAverageDuration(timings);
  const squaredDiffs = timings.map(t => Math.pow(t.duration - avg, 2));
  const variance = squaredDiffs.reduce((acc, val) => acc + val, 0) / timings.length;

  return Math.sqrt(variance);
}

/**
 * Determine confidence level based on sample size and variance.
 * More samples and less variance = higher confidence.
 *
 * @param timings - Array of historical timing records
 * @returns Confidence level: high, medium, or low
 */
export function calculateConfidenceLevel(
  timings: HistoricalTiming[]
): 'high' | 'medium' | 'low' {
  if (timings.length === 0) return 'low';

  const sampleSize = timings.length;
  const avg = calculateAverageDuration(timings);
  const stdDev = calculateStandardDeviation(timings);

  // Coefficient of variation (CV) = std dev / mean
  // Low CV = consistent timing, High CV = variable timing
  const coefficientOfVariation = avg > 0 ? stdDev / avg : 0;

  // High confidence: >= 5 samples with low variance (CV < 0.3)
  if (sampleSize >= 5 && coefficientOfVariation < 0.3) return 'high';

  // Medium confidence: >= 3 samples with moderate variance (CV < 0.5)
  if (sampleSize >= 3 && coefficientOfVariation < 0.5) return 'medium';

  // Low confidence: everything else
  return 'low';
}

/**
 * Estimate time based on historical data.
 * Optionally adjusts estimate based on current progress.
 *
 * @param timings - Array of historical timing records
 * @param currentProgress - Optional current progress percentage (0-100)
 * @returns Time estimate with confidence, or null if no data
 */
export function estimateFromHistoricalData(
  timings: HistoricalTiming[],
  currentProgress?: number
): TimeEstimate | null {
  if (timings.length === 0) return null;

  const avgDuration = calculateAverageDuration(timings);
  const confidence = calculateConfidenceLevel(timings);

  // If we have current progress, adjust estimate for remaining work
  let estimatedMs = avgDuration;
  if (currentProgress !== undefined && currentProgress > 0 && currentProgress < 100) {
    // Scale based on remaining progress
    const remainingProgress = 100 - currentProgress;
    estimatedMs = (avgDuration / 100) * remainingProgress;
  }

  return {
    estimatedMs,
    confidence,
    sampleSize: timings.length,
    basedOn: 'historical'
  };
}

/**
 * Filter historical data by recency (last N days).
 * More recent data may be more relevant for estimates.
 *
 * @param timings - Array of historical timing records
 * @param daysAgo - Number of days to look back (default: 30)
 * @returns Filtered array of recent timing records
 */
export function filterRecentTimings(
  timings: HistoricalTiming[],
  daysAgo: number = 30
): HistoricalTiming[] {
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - daysAgo);

  return timings.filter(t => {
    const completedDate = t.completedAt instanceof Date ? t.completedAt : new Date(t.completedAt);
    return completedDate >= cutoffDate;
  });
}

/**
 * Get best time estimate combining historical data and current progress.
 * Falls back to progress-based estimate if historical data is insufficient.
 *
 * @param historicalTimings - Array of historical timing records
 * @param startTime - When the current task started
 * @param currentProgress - Current progress percentage (0-100)
 * @returns Time estimate with confidence level
 */
export function getHybridEstimate(
  historicalTimings: HistoricalTiming[],
  startTime: Date,
  currentProgress: number
): TimeEstimate {
  // Try historical estimate first (prefer recent data)
  const recentTimings = filterRecentTimings(historicalTimings, 30);
  const historicalEstimate = estimateFromHistoricalData(recentTimings, currentProgress);

  if (historicalEstimate && historicalEstimate.confidence !== 'low') {
    return historicalEstimate;
  }

  // Fall back to progress-based estimate
  const progressEstimate = estimateRemainingTime(startTime, currentProgress);
  if (progressEstimate !== null) {
    return {
      estimatedMs: progressEstimate,
      confidence: 'low',
      sampleSize: 0,
      basedOn: 'progress'
    };
  }

  // Default fallback (no estimate available)
  return {
    estimatedMs: 0,
    confidence: 'low',
    sampleSize: 0,
    basedOn: 'default'
  };
}
