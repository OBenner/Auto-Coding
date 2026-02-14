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

export interface FeedbackAPI {
  submitFeedback: (request: FeedbackRequest) => Promise<{
    success: boolean;
    data?: FeedbackResult;
    error?: string;
  }>;
}

const VALID_FEEDBACK_TYPES = ['accepted', 'rejected', 'modified'] as const;

export const createFeedbackAPI = (): FeedbackAPI => ({
  submitFeedback: (rawRequest) => {
    // Validate feedbackType
    if (!VALID_FEEDBACK_TYPES.includes(rawRequest.feedbackType as typeof VALID_FEEDBACK_TYPES[number])) {
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
  }
});
