/**
 * Productivity analytics types
 *
 * TypeScript definitions for productivity analytics data structures.
 * Matches backend Python models in apps/backend/analysis/productivity_analytics.py
 */

// ============================================
// Spec Metrics Types
// ============================================

export interface SpecMetrics {
  spec_id: string;
  spec_name: string;
  workflow_type: string;  // feature, bug, refactor, etc.
  complexity: string;  // simple, standard, complex
  status: string;  // pending, in_progress, completed, failed

  // Time tracking
  created_at: string | null;  // ISO 8601 datetime string
  completed_at: string | null;  // ISO 8601 datetime string
  duration_seconds: number;

  // Subtask metrics
  total_subtasks: number;
  completed_subtasks: number;
  failed_subtasks: number;

  // QA metrics
  qa_iterations: number;
  qa_status: string;

  // Session metrics
  unique_sessions: number;
}

// ============================================
// Productivity Summary Types
// ============================================

export interface ProductivitySummary {
  // Time period
  period_start: string;  // ISO 8601 datetime string
  period_end: string;  // ISO 8601 datetime string

  // Overall metrics
  total_specs: number;
  completed_specs: number;
  in_progress_specs: number;
  failed_specs: number;

  // Time savings (estimated)
  total_time_saved_hours: number;
  total_build_time_hours: number;

  // Success metrics
  average_success_rate: number;  // 0.0 to 1.0
  first_attempt_success_rate: number;  // 0.0 to 1.0

  // Breakdown by type
  specs_by_type: Record<string, number>;
  specs_by_complexity: Record<string, number>;

  // Productivity metrics
  average_subtasks_per_spec: number;
  average_qa_iterations: number;
  total_subtasks_completed: number;

  // Detailed spec list
  specs: SpecMetrics[];
}

// ============================================
// Trend Data Types
// ============================================

export interface ProductivityTrendPoint {
  date: string;  // ISO 8601 datetime string
  total_specs: number;
  completed_specs: number;
  time_saved_hours: number;
  success_rate: number;
}

// ============================================
// Filter and Export Types
// ============================================

export interface ProductivityAnalyticsFilter {
  start_date?: string;  // ISO 8601 datetime string
  end_date?: string;  // ISO 8601 datetime string
  workflow_type?: string;
  complexity?: string;
  window_days?: number;  // Number of days for trend analysis
  granularity?: 'daily' | 'weekly' | 'monthly';  // Trend granularity
}

export interface ProductivityAnalyticsExportOptions {
  format: 'json' | 'csv';
  output_path?: string;
  filter?: ProductivityAnalyticsFilter;
}

// ============================================
// Failure Analysis Types
// ============================================

export interface FailureFileCount {
  file: string;
  count: number;
}

export interface FailureCategoryCount {
  category: string;
  count: number;
}

export interface FailureMetrics {
  total_failures: number;
  failure_types?: Record<string, number>;  // Count by type (qa_rejection, build_error, etc.)
  failure_categories?: Record<string, number>;  // Count by category
  root_causes_identified?: number;
  /** Ratio of failures with identified root causes. Range: 0.0 - 1.0 */
  root_cause_rate?: number;
  recurring_failures?: number;
  /** Ratio of failures that are recurring. Range: 0.0 - 1.0 */
  recurrence_rate?: number;
  top_failure_files?: FailureFileCount[];  // Top 5 files with most issues
  top_failure_categories?: FailureCategoryCount[];  // Top 5 categories
  /** Ratio of issues with detected patterns vs total issues. Range: 0.0 - 1.0 */
  pattern_detection_rate?: number;
  avg_occurrences_per_failure?: number;
}
