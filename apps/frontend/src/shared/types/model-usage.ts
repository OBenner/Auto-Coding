/**
 * Model usage analytics types
 *
 * TypeScript definitions for model usage data structures.
 * Matches backend Python models in apps/backend/analysis/model_usage_analytics.py
 */

// ============================================
// Model Metrics Types
// ============================================

/**
 * Metrics for a single AI model.
 * Captures usage statistics for one model across all specs.
 */
export interface ModelMetrics {
  model: string;
  provider: string;

  // Usage metrics
  total_usage_count: number;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;

  // Cost metrics
  total_cost: number;

  // Agent breakdown
  usage_by_agent: Record<string, number>;  // agent_type -> count

  // Time period
  first_used: string | null;  // ISO 8601 datetime string
  last_used: string | null;  // ISO 8601 datetime string
}

// ============================================
// Agent Metrics Types
// ============================================

/**
 * Metrics for a single agent type.
 * Captures model usage patterns for one agent across all specs.
 */
export interface AgentMetrics {
  agent_type: string;

  // Usage metrics
  total_usage_count: number;

  // Model breakdown
  models_used: Record<string, number>;  // model_id -> count

  // Preferred model (most used)
  preferred_model: string;

  // Cost metrics
  total_cost: number;
  total_tokens: number;

  // Time period
  first_used: string | null;  // ISO 8601 datetime string
  last_used: string | null;  // ISO 8601 datetime string
}

// ============================================
// Model Usage Summary Types
// ============================================

/**
 * Aggregated model usage metrics across all specs.
 */
export interface ModelUsageSummary {
  // Time period
  period_start: string;  // ISO 8601 datetime string
  period_end: string;  // ISO 8601 datetime string

  // Overall metrics
  total_usage_count: number;
  total_tokens: number;
  total_cost: number;

  // Model breakdown
  models: ModelMetrics[];

  // Agent breakdown
  agents: AgentMetrics[];

  // Top models
  top_models_by_usage: ModelMetrics[];
  top_models_by_cost: ModelMetrics[];
}

// ============================================
// Trend Data Types
// ============================================

/**
 * Model usage trend point for time-series analysis.
 */
export interface ModelUsageTrendPoint {
  date: string;  // ISO 8601 datetime string
  total_tokens: number;
  total_cost: number;
  usage_count: number;
  unique_models: number;
}

/**
 * Per-model trend data.
 */
export interface ModelTrendPoint {
  date: string;  // ISO 8601 datetime string
  model: string;
  tokens: number;
  cost: number;
  usage_count: number;
}

// ============================================
// Filter and Export Types
// ============================================

export interface ModelUsageFilter {
  start_date?: string;  // ISO 8601 datetime string
  end_date?: string;  // ISO 8601 datetime string
  model?: string;  // Filter by specific model
  agent_type?: string;  // Filter by agent type
  window_days?: number;  // Number of days for trend analysis
  granularity?: 'daily' | 'weekly' | 'monthly';  // Trend granularity
}

export interface ModelUsageExportOptions {
  format: 'json' | 'csv';
  output_path?: string;
  filter?: ModelUsageFilter;
}

// ============================================
// Model Lock Types
// ============================================

/**
 * Model lock configuration.
 * Stores locked models for phases and agent types.
 */
export interface ModelLockConfig {
  phaseModels?: Record<string, string>;  // phase -> model_id
  agentModels?: Record<string, string>;  // agent_type -> model_id
}

/**
 * Model lock operation types.
 */
export type ModelLockTarget = 'phase' | 'agent';

export type ModelLockOperation =
  | 'list'
  | 'lock-phase'
  | 'lock-agent'
  | 'unlock-phase'
  | 'unlock-agent'
  | 'clear';

/**
 * Model lock operation parameters.
 */
export interface ModelLockParams {
  operation: ModelLockOperation;
  specId: string;  // Project ID (not spec directory path)
  phase?: string;  // Required for lock-phase/unlock-phase
  agentType?: string;  // Required for lock-agent/unlock-agent
  modelId?: string;  // Required for lock operations
}
