/**
 * Feedback API
 *
 * Provides feedback submission functionality for adaptive agent learning.
 * Records user feedback (accept/reject/modify) to preference profiles.
 */
import { IPC_CHANNELS } from '../../shared/constants/ipc';
import { ipcRenderer } from 'electron';

/**
 * Feedback submission request
 */
export interface FeedbackRequest {
  feedbackType: 'accepted' | 'rejected' | 'modified';
  taskId?: string;
  agentType?: string;
  taskDescription?: string;
  context?: string;
  specDir?: string;
  projectDir?: string;
}

/**
 * Feedback submission result
 */
export interface FeedbackResult {
  recorded: boolean;
  message?: string;
  reason?: string;
}

/**
 * Feedback metrics for individual items
 */
export interface FeedbackMetrics {
  feedback_id: string;
  spec_id?: string;
  spec_name?: string;
  feedback_type: 'accepted' | 'rejected' | 'modified';
  agent_type: string;
  task_description: string;
  rating?: number;
  sentiment?: 'positive' | 'negative' | 'neutral';
  sentiment_confidence: number;
  category?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  created_at?: string;
  context?: Record<string, unknown>;
}

/**
 * Feedback summary response (matches backend FeedbackSummary)
 */
export interface FeedbackSummary {
  period_start: string;
  period_end: string;
  total_feedback: number;
  accepted_count: number;
  rejected_count: number;
  modified_count: number;
  average_rating?: number;
  total_ratings: number;
  positive_sentiment_count: number;
  negative_sentiment_count: number;
  neutral_sentiment_count: number;
  feedback_by_agent: Record<string, number>;
  ratings_by_agent: Record<string, number>;
  top_issues: Array<{
    task: string;
    agent_type: string;
    severity?: string;
    category?: string;
    created_at?: string;
  }>;
  feedback_by_category: Record<string, number>;
  satisfaction_rate: number;
  net_promoter_score?: number;
  feedback_items: FeedbackMetrics[];
}

/**
 * Metric change for improvement tracking
 */
export interface MetricChange {
  before: number;
  after: number;
  delta: number;
  percent_change: number;
}

/**
 * Improvement data for tracking feedback impact
 */
export interface ImprovementData {
  improvement_id: string;
  improvement_description: string;
  feedback_ids: string[];
  agent_type?: string;
  created_at?: string;
  improvement_delta: Record<string, MetricChange>;
  context?: Record<string, unknown>;
}

export interface FeedbackAPI {
  submitFeedback: (request: FeedbackRequest) => Promise<{
    success: boolean;
    data?: FeedbackResult;
    error?: string;
  }>;

  getFeedbackSummary?: (projectId: string, days: number) => Promise<{
    success: boolean;
    data?: FeedbackSummary;
    error?: string;
  }>;

  exportFeedbackData?: (projectId: string, format: 'json' | 'csv', days: number) => Promise<{
    success: boolean;
    data?: string;
    error?: string;
  }>;

  getImprovements?: (projectId: string, days: number) => Promise<{
    success: boolean;
    data?: ImprovementData[];
    error?: string;
  }>;
}

const VALID_FEEDBACK_TYPES = ['accepted', 'rejected', 'modified'] as const;

export const createFeedbackAPI = (): FeedbackAPI => ({
  submitFeedback: (rawRequest) => {
    // Validate feedbackType
    if (!(VALID_FEEDBACK_TYPES as readonly string[]).includes(rawRequest.feedbackType)) {
      return Promise.resolve({
        success: false,
        error: `Invalid feedbackType: ${rawRequest.feedbackType}`
      });
    }

    // Sanitize and cap field lengths to prevent large payloads
    const request: FeedbackRequest = {
      feedbackType: rawRequest.feedbackType,
      taskId: rawRequest.taskId?.trim().slice(0, 256),
      agentType: rawRequest.agentType?.trim().slice(0, 128),
      taskDescription: rawRequest.taskDescription?.trim().slice(0, 1024),
      context: rawRequest.context?.trim().slice(0, 2048),
      specDir: rawRequest.specDir?.trim().slice(0, 512),
      projectDir: rawRequest.projectDir?.trim().slice(0, 512),
    };

    return ipcRenderer.invoke(IPC_CHANNELS.FEEDBACK_SUBMIT, request);
  },
  // Stub implementations — reject until backend support is ready
  getFeedbackSummary: () => Promise.reject(new Error('getFeedbackSummary not implemented')),
  exportFeedbackData: () => Promise.reject(new Error('exportFeedbackData not implemented')),
  getImprovements: () => Promise.reject(new Error('getImprovements not implemented')),
});
