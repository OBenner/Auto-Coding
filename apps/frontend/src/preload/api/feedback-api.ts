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
}

export interface FeedbackAPI {
  submitFeedback: (request: FeedbackRequest) => Promise<{
    success: boolean;
    data?: FeedbackResult;
    error?: string;
  }>;
}

export const createFeedbackAPI = (): FeedbackAPI => ({
  submitFeedback: (request) => ipcRenderer.invoke(IPC_CHANNELS.FEEDBACK_SUBMIT, request)
});
