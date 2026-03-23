/**
 * Session Replay IPC Handlers
 *
 * Handlers for querying and displaying session replay data including
 * sessions, decision points, bookmarks, and timeline information.
 */

import { ipcMain } from 'electron';
import crypto from 'node:crypto';
import path from 'node:path';
import { promises as fsPromises } from 'node:fs';
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
  tool_input?: string | Record<string, unknown>;
  thinking_block?: string;
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
        String(session.session_id).includes(query) ||
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

/**
 * Collect entries from specified phase or all phases
 */
function collectEntries(
  phases: Record<string, PhaseData>,
  phaseName?: string
): LogEntry[] {
  if (phaseName) {
    const phaseData = phases[phaseName];
    return phaseData ? [...phaseData.entries] : [];
  }

  const entries: LogEntry[] = [];
  for (const phaseData of Object.values(phases)) {
    entries.push(...phaseData.entries);
  }
  return entries;
}

/**
 * Apply entry filters for session, subtask, tool, and decision point
 */
function applyEntryFilters(
  entries: LogEntry[],
  filters: {
    session?: string;
    subtask_id?: string;
    tool_name?: string;
    is_decision_point?: boolean;
    limit?: number;
  }
): LogEntry[] {
  let filtered = entries;

  if (filters.session !== undefined) {
    filtered = filtered.filter(
      (entry) => entry.session === Number.parseInt(filters.session!, 10)
    );
  }

  if (filters.subtask_id) {
    filtered = filtered.filter(
      (entry) => entry.subtask_id === filters.subtask_id
    );
  }

  if (filters.tool_name) {
    filtered = filtered.filter(
      (entry) => entry.tool_name === filters.tool_name
    );
  }

  if (filters.is_decision_point !== undefined) {
    filtered = filtered.filter(
      (entry) => entry.is_decision_point === filters.is_decision_point
    );
  }

  return filtered;
}

/**
 * Sort entries by timestamp ascending
 */
function sortEntriesByTimestamp(entries: LogEntry[]): void {
  entries.sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  );
}

/**
 * Collect entries for a specific session from all phases
 */
function collectSessionEntries(
  phases: Record<string, PhaseData>,
  numericSessionId: number
): LogEntry[] {
  const entries: LogEntry[] = [];
  for (const phaseData of Object.values(phases)) {
    const phaseEntries = phaseData.entries.filter(
      (entry) => entry.session === numericSessionId
    );
    entries.push(...phaseEntries);
  }
  sortEntriesByTimestamp(entries);
  return entries;
}

/**
 * Export a single session as JSON
 */
function exportSessionAsJson(logs: TaskLogs, numericSessionId: number): IPCResult<string> {
  const session = logs.sessions.find((s) => s.session_id === numericSessionId);
  if (!session) {
    return { success: false, error: 'Session not found' };
  }

  const sessionEntries = logs.phases
    ? collectSessionEntries(logs.phases, numericSessionId)
    : [];

  const sessionData = {
    session,
    entries: sessionEntries,
    transitions: logs.subtask_transitions.filter(
      (t) => t.session === numericSessionId
    ),
    bookmarks: (logs.bookmarks ?? []).filter((b) => b.session === numericSessionId),
  };

  return {
    success: true,
    data: JSON.stringify(sessionData, null, 2),
  };
}

/**
 * Export a single session as Markdown
 */
function exportSessionAsMarkdown(logs: TaskLogs, numericSessionId: number): IPCResult<string> {
  const session = logs.sessions.find((s) => s.session_id === numericSessionId);
  if (!session) {
    return { success: false, error: 'Session not found' };
  }

  let markdown = `# Session ${session.session_id}\n\n`;
  markdown += `**Started:** ${session.started_at}\n`;
  markdown += `**Duration:** ${session.duration_seconds}s\n`;
  markdown += `**Subtasks:** ${session.subtasks.join(', ')}\n\n`;

  const allEntries = logs.phases
    ? collectSessionEntries(logs.phases, numericSessionId)
    : [];

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

/**
 * Export all sessions as Markdown
 */
function exportAllAsMarkdown(logs: TaskLogs): string {
  let markdown = `# Task Logs: ${logs.spec_id}\n\n`;
  markdown += `**Created:** ${logs.created_at}\n`;
  markdown += `**Updated:** ${logs.updated_at}\n\n`;

  for (const session of logs.sessions) {
    markdown += `## Session ${session.session_id}\n\n`;
    markdown += `**Started:** ${session.started_at}\n`;
    markdown += `**Duration:** ${session.duration_seconds}s\n`;
    markdown += `**Subtasks:** ${session.subtasks.join(', ')}\n\n`;
  }

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

  return markdown;
}

/**
 * Agent thinking block data structure used by inspector handlers
 */
interface AgentThinkingBlock {
  id: string;
  timestamp: string;
  phase: string;
  subtask?: string;
  content: string;
  session?: number;
}

/**
 * Agent tool call data structure used by inspector handlers
 */
interface AgentInspectorToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown> | string;
  timestamp: string;
  phase?: string;
  subtask?: string;
  session?: number;
  success?: boolean;
  error?: string;
  duration_ms?: number;
}

/**
 * Extract thinking blocks from task logs, optionally filtered by session
 */
function extractThoughts(logs: TaskLogs, sessionId?: string): AgentThinkingBlock[] {
  const thoughts: AgentThinkingBlock[] = [];
  let thoughtIdCounter = 0;

  for (const phaseData of Object.values(logs.phases)) {
    for (const entry of phaseData.entries) {
      if (
        entry.type === 'thinking' ||
        (entry.thinking_block && entry.thinking_block.trim() !== '')
      ) {
        if (sessionId !== undefined) {
          const numericSessionId = Number.parseInt(sessionId, 10);
          if (entry.session !== numericSessionId) {
            continue;
          }
        }

        thoughts.push({
          id: `thought-${thoughtIdCounter++}`,
          timestamp: entry.timestamp,
          phase: entry.phase,
          subtask: entry.subtask_id,
          content: entry.thinking_block || entry.content,
          session: entry.session,
        });
      }
    }
  }

  // Sort by timestamp (newest first)
  thoughts.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return thoughts;
}

/**
 * Extract tool calls from task logs, optionally filtered by session.
 * Shared helper used by both GET_TOOL_CALLS and GET_INSPECTOR_DATA handlers.
 */
function extractToolCalls(logs: TaskLogs, sessionId?: string): AgentInspectorToolCall[] {
  const toolCallsMap = new Map<string, AgentInspectorToolCall>();

  for (const phaseData of Object.values(logs.phases)) {
    for (const entry of phaseData.entries) {
      // Filter by session if provided
      if (sessionId !== undefined) {
        const numericSessionId = Number.parseInt(sessionId, 10);
        if (entry.session !== numericSessionId) {
          continue;
        }
      }

      // Process tool_start entries
      if (entry.type === 'tool_start' && entry.tool_name) {
        const toolId = `${entry.tool_name}-${entry.timestamp}`;

        let parsedInput: Record<string, unknown> = {};
        if (entry.tool_input) {
          try {
            parsedInput = typeof entry.tool_input === 'string'
              ? JSON.parse(entry.tool_input)
              : entry.tool_input;
          } catch {
            parsedInput = { raw: entry.tool_input };
          }
        }

        toolCallsMap.set(toolId, {
          id: toolId,
          name: entry.tool_name,
          input: parsedInput,
          timestamp: entry.timestamp,
          phase: entry.phase,
          subtask: entry.subtask_id,
          session: entry.session,
          success: undefined,
          output: undefined,
          error: undefined,
          duration_ms: undefined,
        });
      }

      // Process tool_end entries to match with tool_start
      if (entry.type === 'tool_end' && entry.tool_name) {
        const matchingToolId = Array.from(toolCallsMap.keys())
          .reverse()
          .find((id) => id.startsWith(`${entry.tool_name}-`));

        if (matchingToolId) {
          const toolCall = toolCallsMap.get(matchingToolId)!;

          let parsedOutput: Record<string, unknown> | string | undefined;
          if (entry.content) {
            try {
              parsedOutput = JSON.parse(entry.content);
            } catch {
              parsedOutput = entry.content;
            }
          }

          toolCall.output = parsedOutput;
          toolCall.success = true;

          const startTime = new Date(toolCall.timestamp).getTime();
          const endTime = new Date(entry.timestamp).getTime();
          toolCall.duration_ms = endTime - startTime;
        }
      }

      // Process error entries for tool calls
      if (entry.type === 'error' && entry.tool_name) {
        const matchingToolId = Array.from(toolCallsMap.keys())
          .reverse()
          .find((id) => id.startsWith(`${entry.tool_name}-`));

        if (matchingToolId) {
          const toolCall = toolCallsMap.get(matchingToolId)!;
          toolCall.success = false;
          toolCall.error = entry.content;
        }
      }
    }
  }

  const toolCalls = Array.from(toolCallsMap.values());

  // Sort by timestamp (newest first)
  toolCalls.sort(
    (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
  );

  return toolCalls;
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

        if (!logs?.sessions) {
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

        if (!logs?.sessions) {
          return { success: true, data: null };
        }

        const numericSessionId = Number.parseInt(sessionId, 10);
        const session = logs.sessions.find((s) => s.session_id === numericSessionId);

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

        if (!logs?.phases) {
          return { success: true, data: [] };
        }

        // Collect all entries from all phases for the specific session
        const allEntries: LogEntry[] = [];
        for (const phaseData of Object.values(logs.phases)) {
          const sessionEntries = phaseData.entries.filter(
            (entry) => !sessionId || entry.session === Number.parseInt(sessionId, 10)
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

        if (!logs?.phases) {
          return { success: true, data: [] };
        }

        // Collect all entries from all phases
        const allEntries: LogEntry[] = [];
        for (const phaseData of Object.values(logs.phases)) {
          const sessionEntries = sessionId
            ? phaseData.entries.filter(
                (entry) => entry.session === Number.parseInt(sessionId, 10)
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

        if (!logs?.bookmarks) {
          return { success: true, data: [] };
        }

        let bookmarks = logs.bookmarks;

        // Filter by session if provided
        if (sessionId) {
          const numericSessionId = Number.parseInt(sessionId, 10);
          bookmarks = bookmarks.filter((b) => b.session === numericSessionId);
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

        // Add bookmark to logs
        if (!logs.bookmarks) {
          logs.bookmarks = [];
        }

        // Check for duplicate bookmark (same entry_timestamp and session)
        const existingBookmark = logs.bookmarks.find(
          (b) =>
            b.entry_timestamp === bookmark.entry_timestamp &&
            b.session === bookmark.session
        );
        if (existingBookmark) {
          return { success: true, data: existingBookmark };
        }

        // Generate unique ID for new bookmark
        const newBookmark: Bookmark = {
          ...bookmark,
          id: `bookmark-${Date.now()}-${crypto.randomUUID().slice(0, 9)}`,
        };
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

        if (!logs?.bookmarks) {
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

        if (!logs?.phases) {
          return { success: true, data: [] };
        }

        let entries = collectEntries(logs.phases, filters.phase);
        entries = applyEntryFilters(entries, filters);
        sortEntriesByTimestamp(entries);

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

        if (!logs?.phases) {
          return { success: true, data: [] };
        }

        const query = searchQuery.toLowerCase();
        const results: LogEntry[] = [];

        // Search through all phases and entries
        for (const phaseData of Object.values(logs.phases)) {
          for (const entry of phaseData.entries) {
            const content = entry.content.toLowerCase();
            const toolName = (entry.tool_name ?? '').toLowerCase();
            const phase = (entry.phase ?? '').toLowerCase();
            const subtaskId = (entry.subtask_id ?? '').toLowerCase();
            if (
              content.includes(query) ||
              toolName.includes(query) ||
              phase.includes(query) ||
              subtaskId.includes(query)
            ) {
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

        const numericSessionId = Number.parseInt(sessionId, 10);

        return format === 'json'
          ? exportSessionAsJson(logs, numericSessionId)
          : exportSessionAsMarkdown(logs, numericSessionId);
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
        }

        return { success: true, data: exportAllAsMarkdown(logs) };
      } catch (error) {
        debugError('[Session Replay] Failed to export all sessions:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  // ============================================
  // Agent Inspector Operations
  // ============================================

  /**
   * Get agent thinking blocks from task logs
   */
  ipcMain.handle(
    IPC_CHANNELS.AGENT_INSPECTOR_GET_THOUGHTS,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId?: string
    ): Promise<IPCResult<AgentThinkingBlock[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs?.phases) {
          return { success: true, data: [] };
        }

        const thoughts = extractThoughts(logs, sessionId);

        return { success: true, data: thoughts };
      } catch (error) {
        debugError('[Agent Inspector] Failed to get thoughts:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  /**
   * Get agent tool calls from task logs
   */
  ipcMain.handle(
    IPC_CHANNELS.AGENT_INSPECTOR_GET_TOOL_CALLS,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId?: string
    ): Promise<IPCResult<AgentInspectorToolCall[]>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs?.phases) {
          return { success: true, data: [] };
        }

        const toolCalls = extractToolCalls(logs, sessionId);

        return { success: true, data: toolCalls };
      } catch (error) {
        debugError('[Agent Inspector] Failed to get tool calls:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  /**
   * Get combined inspector data (thoughts + tool calls)
   */
  ipcMain.handle(
    IPC_CHANNELS.AGENT_INSPECTOR_GET_INSPECTOR_DATA,
    async (
      _,
      projectPath: string,
      specId: string,
      sessionId?: string
    ): Promise<IPCResult<{ thoughts: AgentThinkingBlock[]; toolCalls: AgentInspectorToolCall[] }>> => {
      try {
        const specDir = path.join(
          projectPath,
          AUTO_BUILD_PATHS.SPECS_DIR,
          specId
        );

        const logs = await loadTaskLogs(specDir);

        if (!logs?.phases) {
          return {
            success: true,
            data: {
              thoughts: [],
              toolCalls: [],
            },
          };
        }

        const thoughts = extractThoughts(logs, sessionId);
        const toolCalls = extractToolCalls(logs, sessionId);

        return {
          success: true,
          data: {
            thoughts,
            toolCalls,
          },
        };
      } catch (error) {
        debugError('[Agent Inspector] Failed to get inspector data:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );

  /**
   * Export agent inspector session data as JSON or Markdown
   */
  ipcMain.handle(
    IPC_CHANNELS.AGENT_INSPECTOR_EXPORT_SESSION,
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

        const numericSessionId = Number.parseInt(sessionId, 10);

        if (format === 'json') {
          return exportSessionAsJson(logs, numericSessionId);
        }

        return exportSessionAsMarkdown(logs, numericSessionId);
      } catch (error) {
        debugError('[Agent Inspector] Failed to export session:', error);
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Unknown error',
        };
      }
    }
  );
}
