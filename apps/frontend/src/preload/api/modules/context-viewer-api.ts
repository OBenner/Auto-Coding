import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Context Viewer API operations
 *
 * Provides access to context window statistics, token breakdown,
 * file prioritization scores, and optimization reports.
 */
export interface ContextViewerAPI {
  /**
   * Get comprehensive context window statistics
   */
  getContextStats: (projectId: string, specId?: string) => Promise<IPCResult<ContextStats>>;

  /**
   * Get detailed token usage breakdown by file and category
   */
  getTokenBreakdown: (projectId: string, specId?: string) => Promise<IPCResult<TokenBreakdown>>;

  /**
   * Get file prioritization scores for the current context
   */
  getPrioritizationScores: (projectId: string, task?: string) => Promise<IPCResult<PrioritizationScores>>;

  /**
   * Get optimization effectiveness report
   */
  getOptimizationReport: (projectId: string, specId: string) => Promise<IPCResult<OptimizationReport>>;

  /**
   * Export complete context snapshot
   */
  exportContextSnapshot: (projectId: string, specId: string) => Promise<IPCResult<ContextSnapshot>>;
}

/**
 * Context statistics
 */
export interface ContextStats {
  token_stats: {
    total_budget: number;
    used: number;
    remaining: number;
    utilization_percent: number;
  };
  session_stats: {
    current_turn: number;
    total_tokens_sent: number;
    unique_files_sent: number;
    recent_files: string[];
    most_frequent_files: Array<{ file: string; count: number }>;
  };
  optimization_stats: {
    deduplication_enabled: boolean;
    semantic_search_enabled: boolean;
    prioritization_enabled: boolean;
    tokens_saved: number;
    files_deduplicated: number;
  };
  files_stats: {
    total_files_in_context: number;
    files_to_modify: number;
    files_to_reference: number;
    top_priority_files: string[];
  };
}

/**
 * Token breakdown by file and category
 */
export interface TokenBreakdown {
  by_file: Record<string, number>;
  by_category: {
    to_modify: number;
    to_reference: number;
    patterns: number;
    summaries: number;
  };
  total: number;
}

/**
 * File prioritization scores
 */
export interface PrioritizationScores {
  scored_files: Array<{
    file_path: string;
    relevance_score: number;
    recency_score: number;
    combined_score: number;
  }>;
  algorithm: string;
  factors: {
    relevance_weight: number;
    recency_weight: number;
    dependency_boost: number;
  };
}

/**
 * Optimization effectiveness report
 */
export interface OptimizationReport {
  deduplication: {
    files_processed: number;
    duplicates_found: number;
    tokens_saved: number;
    savings_percent: number;
  };
  prioritization: {
    files_ranked: number;
    top_files_selected: number;
    relevance_score_avg: number;
  };
  semantic_search: {
    queries_made: number;
    results_found: number;
    avg_similarity: number;
  };
  overall: {
    total_tokens_saved: number;
    optimization_percent: number;
    target_percent: number;
  };
}

/**
 * Complete context snapshot
 */
export interface ContextSnapshot {
  timestamp: string;
  spec: string;
  context_entries: Array<{
    file_path: string;
    token_count: number;
    sent_count: number;
    turn_number: number;
    timestamp: string;
  }>;
  session_summary: any;
  token_stats: any;
}

/**
 * Creates the Context Viewer API implementation
 */
export const createContextViewerAPI = (): ContextViewerAPI => ({
  getContextStats: (projectId: string, specId?: string): Promise<IPCResult<ContextStats>> =>
    invokeIpc(IPC_CHANNELS.CONTEXT_GET_STATS, projectId, specId),

  getTokenBreakdown: (projectId: string, specId?: string): Promise<IPCResult<TokenBreakdown>> =>
    invokeIpc(IPC_CHANNELS.CONTEXT_GET_TOKEN_BREAKDOWN, projectId, specId),

  getPrioritizationScores: (projectId: string, task?: string): Promise<IPCResult<PrioritizationScores>> =>
    invokeIpc(IPC_CHANNELS.CONTEXT_GET_PRIORITIZATION_SCORES, projectId, task),

  getOptimizationReport: (projectId: string, specId: string): Promise<IPCResult<OptimizationReport>> =>
    invokeIpc(IPC_CHANNELS.CONTEXT_GET_OPTIMIZATION_REPORT, projectId, specId),

  exportContextSnapshot: (projectId: string, specId: string): Promise<IPCResult<ContextSnapshot>> =>
    invokeIpc(IPC_CHANNELS.CONTEXT_EXPORT_SNAPSHOT, projectId, specId)
});
