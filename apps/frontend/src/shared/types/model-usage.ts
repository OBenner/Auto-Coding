/**
 * Model usage analytics types
 *
 * TypeScript definitions for model usage data structures.
 * Matches backend Python models in apps/backend/analysis/model_usage_analytics.py
 */

// ============================================
// Shared Base Metrics
// ============================================

/** Common usage/cost fields shared by model and agent metrics. */
interface BaseUsageMetrics {
  total_usage_count: number;
  total_tokens: number;
  total_cost: number;
  first_used: string | null;  // ISO 8601 datetime string
  last_used: string | null;   // ISO 8601 datetime string
}

// ============================================
// Model Metrics Types
// ============================================

/** Metrics for a single AI model across all specs. */
export interface ModelMetrics extends BaseUsageMetrics {
  model: string;
  provider: string;
  total_input_tokens: number;
  total_output_tokens: number;
  usage_by_agent: Record<string, number>;  // agent_type -> count
}

// ============================================
// Agent Metrics Types
// ============================================

/** Metrics for a single agent type across all specs. */
export interface AgentMetrics extends BaseUsageMetrics {
  agent_type: string;
  models_used: Record<string, number>;  // model_id -> count
  preferred_model: string;
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

/** Model usage trend point for time-series analysis. */
export interface ModelUsageTrendPoint {
  date: string;
  total_tokens: number;
  total_cost: number;
  usage_count: number;
  unique_models: number;
}

/** Per-model trend data. */
export interface ModelTrendPoint {
  date: string;
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
