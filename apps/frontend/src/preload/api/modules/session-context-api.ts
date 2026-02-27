import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  ConversationHistory,
  SessionContextSummary,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Session Context API operations
 */
export interface SessionContextAPI {
  getConversationHistory: (
    projectId: string,
    taskId: string,
    sessionId?: string
  ) => Promise<IPCResult<ConversationHistory[]>>;

  getSessionSummaries: (
    projectId: string,
    taskId: string,
    limit?: number
  ) => Promise<IPCResult<SessionContextSummary[]>>;

  getCodeReferences: (
    projectId: string,
    taskId: string,
    sessionId?: string,
    filePath?: string
  ) => Promise<IPCResult<string[]>>;

  getAllSessions: (
    projectId: string,
    limit?: number
  ) => Promise<IPCResult<SessionContextSummary[]>>;
}

/**
 * Creates the Session Context API implementation
 */
export const createSessionContextAPI = (): SessionContextAPI => ({
  getConversationHistory: (projectId, taskId, sessionId) =>
    invokeIpc(IPC_CHANNELS.SESSION_CONTEXT_GET_HISTORY, projectId, taskId, sessionId),

  getSessionSummaries: (projectId, taskId, limit) =>
    invokeIpc(IPC_CHANNELS.SESSION_CONTEXT_GET_SUMMARIES, projectId, taskId, limit ?? 20),

  getCodeReferences: (projectId, taskId, sessionId, filePath) =>
    invokeIpc(IPC_CHANNELS.SESSION_CONTEXT_GET_CODE_REFS, projectId, taskId, sessionId, filePath),

  getAllSessions: (projectId, limit) =>
    invokeIpc(IPC_CHANNELS.SESSION_CONTEXT_GET_ALL_SESSIONS, projectId, limit ?? 20)
});
