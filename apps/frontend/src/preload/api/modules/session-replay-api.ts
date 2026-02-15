/**
 * Session Replay API
 *
 * Provides IPC communication for session replay features including
 * listing sessions, retrieving timeline entries, decision points,
 * bookmarks, and exporting session data.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  IPCResult,
  SessionMetadata,
  SessionFilterState,
  LogEntry,
  ReplayDecisionPoint,
  Bookmark,
} from '../../../shared/types';

export interface SessionReplayAPI {
  /** List and filter sessions */
  listSessions: (
    projectPath: string,
    specId: string,
    filter: SessionFilterState
  ) => Promise<IPCResult<SessionMetadata[]>>;

  /** Get specific session details */
  getSession: (
    projectPath: string,
    specId: string,
    sessionId: string
  ) => Promise<IPCResult<SessionMetadata | null>>;

  /** Get timeline entries for a session */
  getTimeline: (
    projectPath: string,
    specId: string,
    sessionId: string
  ) => Promise<IPCResult<LogEntry[]>>;

  /** Get decision points (optionally filtered by session) */
  getDecisionPoints: (
    projectPath: string,
    specId: string,
    sessionId?: string
  ) => Promise<IPCResult<ReplayDecisionPoint[]>>;

  /** Get bookmarks (optionally filtered by session) */
  getBookmarks: (
    projectPath: string,
    specId: string,
    sessionId?: string
  ) => Promise<IPCResult<Bookmark[]>>;

  /** Add a new bookmark */
  addBookmark: (
    projectPath: string,
    specId: string,
    bookmark: Omit<Bookmark, 'id'>
  ) => Promise<IPCResult<Bookmark>>;

  /** Remove a bookmark */
  removeBookmark: (
    projectPath: string,
    specId: string,
    bookmarkId: string
  ) => Promise<IPCResult<void>>;

  /** Query entries with filters */
  getEntries: (
    projectPath: string,
    specId: string,
    filters: {
      phase?: string;
      session?: string;
      subtask_id?: string;
      tool_name?: string;
      is_decision_point?: boolean;
      limit?: number;
    }
  ) => Promise<IPCResult<LogEntry[]>>;

  /** Search across all entries */
  search: (
    projectPath: string,
    specId: string,
    searchQuery: string
  ) => Promise<IPCResult<LogEntry[]>>;

  /** Export a single session */
  exportSession: (
    projectPath: string,
    specId: string,
    sessionId: string,
    format: 'json' | 'markdown'
  ) => Promise<IPCResult<string>>;

  /** Export all sessions */
  exportAll: (
    projectPath: string,
    specId: string,
    format: 'json' | 'markdown'
  ) => Promise<IPCResult<string>>;
}

export const createSessionReplayAPI = (): SessionReplayAPI => ({
  listSessions: (projectPath, specId, filter) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_LIST, projectPath, specId, filter),

  getSession: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_GET_SESSION, projectPath, specId, sessionId),

  getTimeline: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_GET_TIMELINE, projectPath, specId, sessionId),

  getDecisionPoints: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_GET_DECISION_POINTS, projectPath, specId, sessionId),

  getBookmarks: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_GET_BOOKMARKS, projectPath, specId, sessionId),

  addBookmark: (projectPath, specId, bookmark) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_ADD_BOOKMARK, projectPath, specId, bookmark),

  removeBookmark: (projectPath, specId, bookmarkId) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_REMOVE_BOOKMARK, projectPath, specId, bookmarkId),

  getEntries: (projectPath, specId, filters) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_GET_ENTRIES, projectPath, specId, filters),

  search: (projectPath, specId, searchQuery) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_SEARCH, projectPath, specId, searchQuery),

  exportSession: (projectPath, specId, sessionId, format) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_EXPORT_SESSION, projectPath, specId, sessionId, format),

  exportAll: (projectPath, specId, format) =>
    ipcRenderer.invoke(IPC_CHANNELS.SESSION_REPLAY_EXPORT_ALL, projectPath, specId, format),
});
