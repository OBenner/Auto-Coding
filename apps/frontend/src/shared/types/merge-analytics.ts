/**
 * Merge analytics types
 *
 * TypeScript definitions for merge analytics data structures.
 * Matches backend Python models in apps/backend/merge/analytics_recorder.py
 */

// ============================================
// Enums
// ============================================

export type MergeConflictSeverity = 'none' | 'low' | 'medium' | 'high' | 'critical';

// ============================================
// Statistics Types
// ============================================

export interface MergeOperationStats {
  files_processed: number;
  files_auto_merged: number;
  files_ai_merged: number;
  files_need_review: number;
  files_failed: number;
  conflicts_detected: number;
  conflicts_auto_resolved: number;
  conflicts_ai_resolved: number;
  ai_calls_made: number;
  estimated_tokens_used: number;
  duration_seconds: number;
}

// ============================================
// Operation Record Types
// ============================================

export interface MergeOperationRecord {
  operation_id: string;
  timestamp: string;  // ISO 8601 datetime string
  tasks_merged: string[];
  stats: MergeOperationStats;
  success: boolean;
  error?: string | null;
  duration_seconds: number;
}

// ============================================
// Conflict Pattern Types
// ============================================

export interface ConflictPattern {
  file_path: string;
  location: string;
  occurrence_count: number;
  severity: MergeConflictSeverity;
  tasks_involved: string[];
  last_seen?: string | null;  // ISO 8601 datetime string
}

// ============================================
// Analytics Summary Types
// ============================================

export interface MergeAnalytics {
  total_operations: number;
  total_files_merged: number;
  total_conflicts: number;
  successful_operations: number;
  failed_operations: number;
  total_ai_calls: number;
  total_tokens_used: number;
  average_duration_seconds: number;
  success_rate: number;  // 0.0 to 1.0
  auto_merge_rate: number;  // 0.0 to 1.0
  conflict_patterns: ConflictPattern[];
}

// ============================================
// Filter and Query Types
// ============================================

export interface MergeAnalyticsFilter {
  since?: string;  // ISO 8601 datetime string
  task_id?: string;
  limit?: number;
  success_only?: boolean;
  failed_only?: boolean;
}

export interface MergeAnalyticsExportOptions {
  format: 'json' | 'csv';
  output_path?: string;
  filter?: MergeAnalyticsFilter;
}

// ============================================
// UI State Types
// ============================================

export interface MergeAnalyticsSummary {
  analytics: MergeAnalytics;
  recentOperations: MergeOperationRecord[];
  topConflictPatterns: ConflictPattern[];
  lastUpdated: Date;
}

export interface MergeAnalyticsState {
  summary: MergeAnalyticsSummary | null;
  isLoading: boolean;
  error: string | null;
  filter: MergeAnalyticsFilter;
}
