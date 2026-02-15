/**
 * Session Replay IPC Handlers
 *
 * Handlers for querying and displaying session replay data including
 * sessions, decision points, bookmarks, and timeline information.
 */

import { ipcMain } from 'electron';
import crypto from 'crypto';
import path from 'path';
import { promises as fsPromises } from 'fs';
import { IPC_CHANNELS, AUTO_BUILD_PATHS } from '../../shared/constants';
import { atomicWriteFile } from '../fs-utils';
import type { IPCResult } from '../../shared/types';
import type {
  SessionMetadata,
  Bookmark,
  ReplayDecisionPoint,
  SubtaskTransition,
  SessionFilterState,
} from '../../shared/types/session-replay';
import { debugError } from '../../shared/utils/debug-logger';

/**
 * Interface for task logs structure
 */
interface TaskLogs {
  spec_id: string;
  created_at: string;
  updated_at: string;
  phases: Record<string, PhaseData>;
  sessions: SessionMetadata[];
  subtask_transitions: SubtaskTransition[];
  bookmarks: Bookmark[];
}

/**
 * Interface for phase data
 */
interface PhaseData {
  phase: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  entries: LogEntry[];
}

/**
 * Interface for log entry
 */
interface LogEntry {
  timestamp: string;
  type: string;
  content: string;
  phase: string;
  subtask_id?: string;
  session?: number;
  tool_name?: string;
  is_decision_point?: boolean;
  decision_point?: ReplayDecisionPoint;
}

/**
 * Check if task logs file exists
 */
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Load task logs from spec directory
 */
async function loadTaskLogs(specDir: string): Promise<TaskLogs | null> {
  const logsPath = path.join(specDir, 'task_logs.json');

  if (!(await fileExists(logsPath))) {
    return null;
  }

  try {
    const content = await fsPromises.readFile(logsPath, 'utf-8');
    return JSON.parse(content) as TaskLogs;
  } catch (error) {
    debugError('[Session Replay] Failed to load task logs:', error);
    return null;
  }
}

/**
 * Filter sessions based on search query and status
 */
function filterSessions(
  sessions: SessionMetadata[],
  filter: SessionFilterState
): SessionMetadata[] {
  let filtered = [...sessions];

  // Apply status filter
  if (filter.status.length > 0) {
    const includeCompleted = filter.status.includes('completed');
    const includeInProgress = filter.status.includes('in-progress');

    filtered = filtered.filter((session) => {
      const isCompleted = session.completed_at !== null;
      return (isCompleted && includeCompleted) || (!isCompleted && includeInProgress);
    });
  }

  // Apply search query
  if (filter.searchQuery.trim()) {
    const query = filter.searchQuery.toLowerCase();
    filtered = filtered.filter(
      (session) =>
        session.session_id.toLowerCase().includes(query) ||
        session.subtasks.some((subtask) => subtask.toLowerCase().includes(query))
    );
  }

  return filtered;
}

/**
 * Get decision points from log entries
 */
function extractDecisionPoints(entries: LogEntry[]): ReplayDecisionPoint[] {
  return entries
    .filter((entry) => entry.is_decision_point && entry.decision_point)
    .map((entry) => entry.decision_point!)
    .sort(
      (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    );
}

/** Guard to prevent double-registration of IPC handlers */
let sessionReplayHandlersRegistered = false;

/**
 * Register all session replay IPC handlers
 */
export function registerSessionReplayHandlers(): void {
  if (sessionReplayHandlersRegistered) {
    return;
  }
  sessionReplayHandlersRegistered = true;
  // ============================================
  // Session List Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_LIST,
    async (
      _,
      projectPath: string,
      specId: string,
      filter: SessionFilterState
    ): Promise<IPCResult<SessionMetadata[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.sessions) {
          return { success: true, data: [] };
        }

        const filtered = filterSessions(logs.sessions, filter);

        return { success: true, data: filtered };
      } catch (error) {
        debugError('[Session Replay] Failed to list sessions:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Session Detail Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_GET_SESSION,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId: string
    ): Promise<IPCResult<SessionMetadata | null>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.sessions) {
          return { success: true, data: null };
        }

        const session = logs.sessions.find((s) => s.session_id === sessionId);

        return { success: true, data: session || null };
      } catch (error) {
        debugError('[Session Replay] Failed to get session:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Timeline Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_GET_TIMELINE,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId: string
    ): Promise<IPCResult<LogEntry[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.phases) {
          return { success: true, data: [] };
        }

        // Collect all entries from all phases for the specific session
        const allEntries: LogEntry[] = [];
        for (const phaseData of Object.values(logs.phases)) {
          const sessionEntries = phaseData.entries.filter(
            (entry) => !sessionId || entry.session === parseInt(sessionId, 10)
          );
          allEntries.push(...sessionEntries);
        }

        // Sort by timestamp
        allEntries.sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        return { success: true, data: allEntries };
      } catch (error) {
        debugError('[Session Replay] Failed to get timeline:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Decision Points Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_GET_DECISION_POINTS,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId?: string
    ): Promise<IPCResult<ReplayDecisionPoint[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.phases) {
          return { success: true, data: [] };
        }

        // Collect all entries from all phases
        const allEntries: LogEntry[] = [];
        for (const phaseData of Object.values(logs.phases)) {
          const sessionEntries = sessionId
            ? phaseData.entries.filter(
                (entry) => entry.session === parseInt(sessionId, 10)
              )
            : phaseData.entries;
          allEntries.push(...sessionEntries);
        }

        const decisionPoints = extractDecisionPoints(allEntries);

        return { success: true, data: decisionPoints };
      } catch (error) {
        debugError('[Session Replay] Failed to get decision points:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Bookmarks Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_GET_BOOKMARKS,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId?: string
    ): Promise<IPCResult<Bookmark[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.bookmarks) {
          return { success: true, data: [] };
        }

        let bookmarks = logs.bookmarks;

        // Filter by session if provided
        if (sessionId) {
          bookmarks = bookmarks.filter((b) => b.session === sessionId);
        }

        return { success: true, data: bookmarks };
      } catch (error) {
        debugError('[Session Replay] Failed to get bookmarks:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_ADD_BOOKMARK,
    async (
      _,
      projectPath: string,
      specId: string,
      bookmark: Omit<Bookmark, 'id'>
    ): Promise<IPCResult<Bookmark>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs) {
          return { success: false, error: 'No logs found' };
        }

        // Generate unique ID for bookmark
        const newBookmark: Bookmark = {
          ...bookmark,
          id: `bookmark-${Date.now()}-${crypto.randomUUID().slice(0, 9)}`,
        };

        // Add bookmark to logs
        if (!logs.bookmarks) {
          logs.bookmarks = [];
        }
        logs.bookmarks.push(newBookmark);

        // Save updated logs atomically to prevent corruption
        const logsPath = path.join(specDir, 'task_logs.json');
        await atomicWriteFile(
          logsPath,
          JSON.stringify(logs, null, 2),
          'utf-8'
        );

        return { success: true, data: newBookmark };
      } catch (error) {
        debugError('[Session Replay] Failed to add bookmark:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_REMOVE_BOOKMARK,
    async (
      _,
      projectPath: string,
      specId: string,
      bookmarkId: string
    ): Promise<IPCResult<void>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.bookmarks) {
          return { success: false, error: 'No bookmarks found' };
        }

        // Remove bookmark
        const index = logs.bookmarks.findIndex((b) => b.id === bookmarkId);
        if (index === -1) {
          return { success: false, error: 'Bookmark not found' };
        }

        logs.bookmarks.splice(index, 1);

        // Save updated logs atomically to prevent corruption
        const logsPath = path.join(specDir, 'task_logs.json');
        await atomicWriteFile(
          logsPath,
          JSON.stringify(logs, null, 2),
          'utf-8'
        );

        return { success: true, data: undefined };
      } catch (error) {
        debugError('[Session Replay] Failed to remove bookmark:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Entries Query Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_GET_ENTRIES,
    async (
      _,
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
    ): Promise<IPCResult<LogEntry[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.phases) {
          return { success: true, data: [] };
        }

        // Collect entries from specified phase or all phases
        let entries: LogEntry[] = [];

        if (filters.phase) {
          const phaseData = logs.phases[filters.phase];
          if (phaseData) {
            entries = [...phaseData.entries];
          }
        } else {
          for (const phaseData of Object.values(logs.phases)) {
            entries.push(...phaseData.entries);
          }
        }

        // Apply filters
        if (filters.session !== undefined) {
          entries = entries.filter(
            (entry) => entry.session === parseInt(filters.session!, 10)
          );
        }

        if (filters.subtask_id) {
          entries = entries.filter(
            (entry) => entry.subtask_id === filters.subtask_id
          );
        }

        if (filters.tool_name) {
          entries = entries.filter(
            (entry) => entry.tool_name === filters.tool_name
          );
        }

        if (filters.is_decision_point !== undefined) {
          entries = entries.filter(
            (entry) => entry.is_decision_point === filters.is_decision_point
          );
        }

        // Sort by timestamp
        entries.sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        // Apply limit
        if (filters.limit && filters.limit > 0) {
          entries = entries.slice(0, filters.limit);
        }

        return { success: true, data: entries };
      } catch (error) {
        debugError('[Session Replay] Failed to get entries:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Search Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_SEARCH,
    async (
      _,
      projectPath: string,
      specId: string,
      searchQuery: string
    ): Promise<IPCResult<LogEntry[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs || !logs.phases) {
          return { success: true, data: [] };
        }

        const query = searchQuery.toLowerCase();
        const results: LogEntry[] = [];

        // Search through all phases and entries
        for (const phaseData of Object.values(logs.phases)) {
          for (const entry of phaseData.entries) {
            const content = entry.content.toLowerCase();
            if (content.includes(query)) {
              results.push(entry);
            }
          }
        }

        // Sort by timestamp
        results.sort(
          (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        return { success: true, data: results };
      } catch (error) {
        debugError('[Session Replay] Failed to search:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Export Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_EXPORT_SESSION,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId: string,
      format: 'json' | 'markdown'
    ): Promise<IPCResult<string>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs) {
          return { success: false, error: 'No logs found to export' };
        }

        if (format === 'json') {
          const session = logs.sessions.find((s) => s.session_id === sessionId);
          if (!session) {
            return { success: false, error: 'Session not found' };
          }

          const sessionData = {
            session,
            entries: [],
            transitions: logs.subtask_transitions.filter(
              (t) => t.session === parseInt(sessionId, 10)
            ),
            bookmarks: (logs.bookmarks ?? []).filter((b) => b.session === sessionId),
          };

          return {
            success: true,
            data: JSON.stringify(sessionData, null, 2),
          };
        } else {
          // Markdown export
          const session = logs.sessions.find((s) => s.session_id === sessionId);
          if (!session) {
            return { success: false, error: 'Session not found' };
          }

          let markdown = `# Session ${session.session_id}\n\n`;
          markdown += `**Started:** ${session.started_at}\n`;
          markdown += `**Duration:** ${session.duration_seconds}s\n`;
          markdown += `**Subtasks:** ${session.subtasks.join(', ')}\n\n`;

          // Add decision points
          const allEntries: LogEntry[] = [];
          for (const phaseData of Object.values(logs.phases)) {
            const sessionEntries = phaseData.entries.filter(
              (entry) => entry.session === parseInt(sessionId, 10)
            );
            allEntries.push(...sessionEntries);
          }

          const decisionPoints = extractDecisionPoints(allEntries);
          if (decisionPoints.length > 0) {
            markdown += `## Decision Points\n\n`;
            for (const dp of decisionPoints) {
              markdown += `### ${dp.phase} - ${dp.subtask}\n`;
              markdown += `**Reasoning:** ${dp.reasoning}\n\n`;
              markdown += `**Chosen Approach:** ${dp.chosen_approach}\n\n`;
            }
          }

          return { success: true, data: markdown };
        }
      } catch (error) {
        debugError('[Session Replay] Failed to export session:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.SESSION_REPLAY_EXPORT_ALL,
    async (
      _,
      projectPath: string,
      specId: string,
      format: 'json' | 'markdown'
    ): Promise<IPCResult<string>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs) {
          return { success: false, error: 'No logs found to export' };
        }

        if (format === 'json') {
          return {
            success: true,
            data: JSON.stringify(logs, null, 2),
          };
        } else {
          // Markdown export for all sessions
          let markdown = `# Task Logs: ${logs.spec_id}\n\n`;
          markdown += `**Created:** ${logs.created_at}\n`;
          markdown += `**Updated:** ${logs.updated_at}\n\n`;

          for (const session of logs.sessions) {
            markdown += `## Session ${session.session_id}\n\n`;
            markdown += `**Started:** ${session.started_at}\n`;
            markdown += `**Duration:** ${session.duration_seconds}s\n`;
            markdown += `**Subtasks:** ${session.subtasks.join(', ')}\n\n`;
          }

          // Add bookmarks section
          const bookmarks = logs.bookmarks ?? [];
          if (bookmarks.length > 0) {
            markdown += `## Bookmarks\n\n`;
            for (const bookmark of bookmarks) {
              markdown += `### ${bookmark.label}\n`;
              markdown += `**Phase:** ${bookmark.phase}\n`;
              markdown += `**Timestamp:** ${bookmark.timestamp}\n`;
              if (bookmark.note) {
                markdown += `**Note:** ${bookmark.note}\n`;
              }
              markdown += '\n';
            }
          }

          return { success: true, data: markdown };
        }
      } catch (error) {
        debugError('[Session Replay] Failed to export all sessions:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );
}
