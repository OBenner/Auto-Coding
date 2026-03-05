/**
 * Agent Inspector API
 *
 * Provides IPC communication for agent thought process inspector features
 * including exporting session logs with thoughts, tool calls, and metrics.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';

/** Agent thinking block data */
export interface AgentThinkingBlock {
  id: string;
  timestamp: string;
  phase: string;
  subtask?: string;
  content: string;
  session?: number;
}

/** Agent tool call data */
export interface AgentToolCall {
  id: string;
  name: string;
  input: Record<string, unknown>;
  output?: Record<string, unknown> | string;
  timestamp: string;
  phase?: string;
  subtask?: string;
  duration_ms?: number;
  success?: boolean;
  error?: string;
}

/** Combined inspector data with thoughts and tool calls */
export interface InspectorData {
  thoughts: AgentThinkingBlock[];
  toolCalls: AgentToolCall[];
}

export interface AgentInspectorAPI {
  /** Get agent thinking blocks for a session */
  getThoughts: (
    projectPath: string,
    specId: string,
    sessionId?: string
  ) => Promise<IPCResult<AgentThinkingBlock[]>>;

  /** Get agent tool calls for a session */
  getToolCalls: (
    projectPath: string,
    specId: string,
    sessionId?: string
  ) => Promise<IPCResult<AgentToolCall[]>>;

  /** Get combined inspector data (thoughts + tool calls) */
  getInspectorData: (
    projectPath: string,
    specId: string,
    sessionId?: string
  ) => Promise<IPCResult<InspectorData>>;

  /** Export a single agent session log */
  exportSession: (
    projectPath: string,
    specId: string,
    sessionId: string,
    format: 'json' | 'markdown'
  ) => Promise<IPCResult<string>>;
}

export const createAgentInspectorAPI = (): AgentInspectorAPI => ({
  getThoughts: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.AGENT_INSPECTOR_GET_THOUGHTS, projectPath, specId, sessionId),
  getToolCalls: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.AGENT_INSPECTOR_GET_TOOL_CALLS, projectPath, specId, sessionId),
  getInspectorData: (projectPath, specId, sessionId) =>
    ipcRenderer.invoke(IPC_CHANNELS.AGENT_INSPECTOR_GET_INSPECTOR_DATA, projectPath, specId, sessionId),
  exportSession: (projectPath, specId, sessionId, format) =>
    ipcRenderer.invoke(IPC_CHANNELS.AGENT_INSPECTOR_EXPORT_SESSION, projectPath, specId, sessionId, format),
});
