/**
 * Project Health Types
 *
 * TypeScript definitions for project health metrics and status.
 * Matches backend Python models in apps/backend/analysis/health_analyzer.py
 */

// ============================================
// Health Status Enums
// ============================================

export type HealthStatus = 'excellent' | 'good' | 'fair' | 'poor';
export type TrendDirection = 'improving' | 'stable' | 'declining' | 'unknown';

// ============================================
// Component Metrics Types
// ============================================

/**
 * Test coverage metrics
 */
export interface TestCoverageMetrics {
  percentage: number;
  covered_lines: number;
  total_lines: number;
  test_count: number;
  trend: TrendDirection;
}

/**
 * Code quality metrics
 */
export interface CodeQualityMetrics {
  complexity_score: number;
  duplication_percentage: number;
  maintainability_index: number;
  issues_count: number;
}

/**
 * Security vulnerability metrics
 */
export interface SecurityMetrics {
  vulnerability_count: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
  scan_date: string;  // ISO 8601 datetime string
}

/**
 * Dependency health metrics
 */
export interface DependencyMetrics {
  total_dependencies: number;
  outdated_count: number;
  major_updates_available: number;
  minor_updates_available: number;
  patch_updates_available: number;
  freshness_score: number;
}

/**
 * Agent activity metrics
 */
export interface AgentActivityMetrics {
  total_iterations: number;
  success_rate: number;
  average_fix_time: number;
  recent_activity: Array<{
    status: string;
    timestamp?: string;
    [key: string]: unknown;
  }>;
}

// ============================================
// Project Health Types
// ============================================

/**
 * Comprehensive project health data
 */
export interface ProjectHealth {
  overall_score: number;
  status: HealthStatus;
  test_coverage: TestCoverageMetrics;
  code_quality: CodeQualityMetrics;
  security: SecurityMetrics;
  dependencies: DependencyMetrics;
  agent_activity: AgentActivityMetrics;
  generated_at: string;  // ISO 8601 datetime string
}

/**
 * Condensed health summary for quick display
 */
export interface ProjectHealthSummary {
  overall_score: number;
  status: HealthStatus;
  critical_issues: string[];
  recommendations: string[];
}

// ============================================
// UI State Types
// ============================================

export interface ProjectHealthState {
  health: ProjectHealth | null;
  summary: ProjectHealthSummary | null;
  isLoading: boolean;
  error: string | null;
  lastUpdated: Date | null;
}
