/**
 * Agent Performance Analytics types
 */

// ============================================
// Agent Statistics Types
// ============================================

export interface AgentStats {
  agent_type: string;
  total_attempts: number;
  successful_attempts: number;
  failed_attempts: number;
  success_rate: number; // Percentage (0-100)
  total_cost: number; // USD
  total_tokens: number;
  avg_completion_time: number; // Seconds
  error_patterns: Record<string, number>; // Error message -> count
}

// ============================================
// Task Complexity Statistics
// ============================================

export type SpecComplexity = 'simple' | 'standard' | 'complex' | 'unknown';

export interface TaskComplexityStats {
  complexity: SpecComplexity;
  total_tasks: number;
  successful_tasks: number;
  success_rate: number; // Percentage (0-100)
  avg_completion_time: number; // Seconds
  avg_cost: number; // USD
}

// ============================================
// QA Review Statistics
// ============================================

export interface QAStats {
  total_reviews: number;
  approved: number;
  rejected: number;
  rejection_rate: number; // Percentage (0-100)
  common_issues: Record<string, number>; // Issue category -> count
}

// ============================================
// Metrics Summary
// ============================================

export interface MetricsSummary {
  total_specs: number;
  completed_specs: number;
  failed_specs: number;
  in_progress_specs: number;
  overall_success_rate: number; // Percentage (0-100)
  total_cost: number; // USD
  total_tokens: number;
  agent_stats: Record<string, AgentStats>; // Agent type -> stats
  complexity_stats: Record<string, TaskComplexityStats>; // Complexity -> stats
  qa_stats: QAStats;
  last_updated: string; // ISO 8601 timestamp
}

// ============================================
// Trend Analysis Types
// ============================================

export interface TrendDataPoint {
  date: string; // YYYY-MM-DD
  success_rate: number; // Percentage (0-100)
  total_tasks: number;
  total_cost: number; // USD
}

// ============================================
// Analytics Report
// ============================================

export interface AnalyticsReport {
  summary: MetricsSummary;
  trends: TrendDataPoint[];
  generated_at: string; // ISO 8601 timestamp
}

// ============================================
// Analytics Query Parameters
// ============================================

export interface AnalyticsQueryParams {
  projectId: string;
  days?: number; // For trend data (default: 30)
}

// ============================================
// Analytics Dashboard State
// ============================================

export type AnalyticsView = 'overview' | 'agents' | 'trends' | 'qa';

export interface AnalyticsDashboardState {
  currentView: AnalyticsView;
  selectedAgentType?: string;
  selectedComplexity?: SpecComplexity;
  trendDays: number; // Number of days to show in trend analysis
  loading: boolean;
  error?: string;
}
