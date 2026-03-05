/**
 * Agent Inspector API
 *
 * Provides IPC communication for agent thought process inspector features
 * including exporting session logs with thoughts, tool calls, and metrics.
 */

import { ipcRenderer } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';

export interface AgentInspectorAPI {
  /** Export a single agent session log */
  exportSession: (
    projectPath: string,
    specId: string,
    sessionId: string,
    format: 'json' | 'markdown'
  ) => Promise<IPCResult<string>>;
}

export const createAgentInspectorAPI = (): AgentInspectorAPI => ({
  exportSession: (projectPath, specId, sessionId, format) =>
    ipcRenderer.invoke(IPC_CHANNELS.AGENT_INSPECTOR_EXPORT_SESSION, projectPath, specId, sessionId, format),
});
