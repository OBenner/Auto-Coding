/**
 * IPC Handlers Module Index
 *
 * This module exports a single setup function that registers all IPC handlers
 * organized by domain into separate handler modules.
 */

import type { BrowserWindow } from 'electron';
import { AgentManager } from '../agent';
import { TerminalManager } from '../terminal-manager';
import { PythonEnvManager } from '../python-env-manager';

// Import all handler registration functions
import { registerProjectHandlers } from './project-handlers';
import { registerWorkspaceHandlers } from './workspace-handlers';
import { registerTaskHandlers } from './task-handlers';
import { registerTerminalHandlers } from './terminal-handlers';
import { registerAgenteventsHandlers } from './agent-events-handlers';
import { registerSettingsHandlers } from './settings-handlers';
import { registerFileHandlers } from './file-handlers';
import { registerRoadmapHandlers } from './roadmap-handlers';
import { registerContextHandlers } from './context-handlers';
import { registerEnvHandlers } from './env-handlers';
import { registerLinearHandlers } from './linear-handlers';
import { registerGithubHandlers } from './github-handlers';
import { registerGitlabHandlers } from './gitlab-handlers';
import { registerIdeationHandlers } from './ideation-handlers';
import { registerChangelogHandlers } from './changelog-handlers';
import { registerInsightsHandlers } from './insights-handlers';
import { registerAgentAnalyticsHandlers } from './agent-analytics-handlers';
import { registerMemoryHandlers } from './memory-handlers';
import { registerSessionContextHandlers } from './session-context-handlers';
import { registerSchedulerHandlers } from './scheduler-handlers';
import { registerAppUpdateHandlers } from './app-update-handlers';
import { registerDebugHandlers } from './debug-handlers';
import { registerClaudeCodeHandlers } from './claude-code-handlers';
import { registerMcpHandlers } from './mcp-handlers';
import { registerProfileHandlers } from './profile-handlers';
import { registerCodexProfileHandlers } from './codex-profile-handlers';
import { registerSecurityHandlers } from './security-handlers';
import { registerScreenshotHandlers } from './screenshot-handlers';
import { registerTerminalWorktreeIpcHandlers } from './terminal';
import { registerMergeAnalyticsHandlers } from './merge-analytics-handlers';
import { registerAnalyticsHandlers } from './analytics-handlers';
import { registerModelUsageHandlers } from './model-usage-handlers';
import { registerTokenStatsHandlers } from './token-stats-handler';
import { registerTemplateHandlers } from './template-handlers';
import { registerWebhookHandlers } from './webhook-handlers';
import { registerPatternHandlers } from './pattern-handlers';
import { registerSessionReplayHandlers } from './session-replay-handlers';
import { registerFeedbackHandlers } from './feedback-handlers';
import { registerCollaborationHandlers } from './collaboration-handlers';
import { notificationService } from '../notification-service';
import { setAgentManagerRef } from './utils';

/**
 * Setup all IPC handlers across all domains
 *
 * @param agentManager - The agent manager instance
 * @param terminalManager - The terminal manager instance
 * @param getMainWindow - Function to get the main BrowserWindow
 * @param pythonEnvManager - The Python environment manager instance
 */
export function setupIpcHandlers(
  agentManager: AgentManager,
  terminalManager: TerminalManager,
  getMainWindow: () => BrowserWindow | null,
  pythonEnvManager: PythonEnvManager
): void {
  // Initialize notification service
  notificationService.initialize(getMainWindow);

  // Wire up agent manager for circuit breaker cleanup
  setAgentManagerRef(agentManager);

  // Project handlers (including Python environment setup)
  registerProjectHandlers(pythonEnvManager, agentManager, getMainWindow);

  // Workspace handlers (multi-codebase orchestration)
  registerWorkspaceHandlers();

  // Task handlers
  registerTaskHandlers(agentManager, pythonEnvManager, getMainWindow);

  // Terminal and Claude profile handlers
  registerTerminalHandlers(terminalManager, getMainWindow);

  // Terminal worktree handlers (isolated development in worktrees)
  registerTerminalWorktreeIpcHandlers();

  // Agent event handlers (event forwarding from agent manager to renderer)
  registerAgenteventsHandlers(agentManager, getMainWindow);

  // Settings and dialog handlers
  registerSettingsHandlers(agentManager, getMainWindow);

  // File explorer handlers
  registerFileHandlers();

  // Roadmap handlers
  registerRoadmapHandlers(agentManager, getMainWindow);

  // Context and memory handlers
  registerContextHandlers(getMainWindow);

  // Environment configuration handlers
  registerEnvHandlers(getMainWindow);

  // Linear integration handlers
  registerLinearHandlers(agentManager, getMainWindow);

  // GitHub integration handlers
  registerGithubHandlers(agentManager, getMainWindow);

  // GitLab integration handlers
  registerGitlabHandlers(agentManager, getMainWindow);

  // Ideation handlers
  registerIdeationHandlers(agentManager, getMainWindow);

  // Changelog handlers
  registerChangelogHandlers(getMainWindow);

  // Insights handlers
  registerInsightsHandlers(getMainWindow);

  // Agent analytics handlers (Python-based agent performance metrics)
  registerAgentAnalyticsHandlers(getMainWindow);

  // Memory & infrastructure handlers (for Graphiti/LadybugDB)
  registerMemoryHandlers();

  // Session context handlers (conversation history tracking)
  registerSessionContextHandlers(getMainWindow);

  // App auto-update handlers
  registerAppUpdateHandlers();

  // Debug handlers (logs, debug info, etc.)
  registerDebugHandlers();

  // Claude Code CLI handlers (version checking, installation)
  registerClaudeCodeHandlers();

  // MCP server health check handlers
  registerMcpHandlers();

  // API Profile handlers (custom Anthropic-compatible endpoints)
  registerProfileHandlers();

  // Codex/OpenAI account profile handlers
  registerCodexProfileHandlers();

  // Security profile handlers
  registerSecurityHandlers();

  // Screenshot capture handlers
  registerScreenshotHandlers();

  // Merge analytics handlers
  registerMergeAnalyticsHandlers();

  // Productivity analytics handlers
  registerAnalyticsHandlers();

  // Model usage analytics and lock handlers
  registerModelUsageHandlers();

  // Token statistics handlers
  registerTokenStatsHandlers();

  // Template library handlers
  registerTemplateHandlers();

  // Webhook handlers
  registerWebhookHandlers();

  // Pattern learning handlers
  registerPatternHandlers();

  // Session replay handlers
  registerSessionReplayHandlers();

  // Feedback handlers (adaptive agent learning)
  registerFeedbackHandlers(getMainWindow);

  // Scheduler handlers (build scheduling and queue management)
  registerSchedulerHandlers(getMainWindow);

  // Collaboration handlers (multi-user spec collaboration)
  registerCollaborationHandlers(getMainWindow);

  console.warn('[IPC] All handler modules registered successfully');
}

// Re-export all individual registration functions for potential custom usage
export { registerProjectHandlers } from './project-handlers';
export { registerWorkspaceHandlers } from './workspace-handlers';
export { registerTaskHandlers } from './task-handlers';
export { registerTerminalHandlers } from './terminal-handlers';
export { registerTerminalWorktreeIpcHandlers } from './terminal';
export { registerAgenteventsHandlers } from './agent-events-handlers';
export { registerSettingsHandlers } from './settings-handlers';
export { registerFileHandlers } from './file-handlers';
export { registerRoadmapHandlers } from './roadmap-handlers';
export { registerContextHandlers } from './context-handlers';
export { registerEnvHandlers } from './env-handlers';
export { registerLinearHandlers } from './linear-handlers';
export { registerGithubHandlers } from './github-handlers';
export { registerGitlabHandlers } from './gitlab-handlers';
export { registerIdeationHandlers } from './ideation-handlers';
export { registerChangelogHandlers } from './changelog-handlers';
export { registerInsightsHandlers } from './insights-handlers';
export { registerAgentAnalyticsHandlers } from './agent-analytics-handlers';
export { registerMemoryHandlers } from './memory-handlers';
export { registerSessionContextHandlers } from './session-context-handlers';
export { registerAppUpdateHandlers } from './app-update-handlers';
export { registerDebugHandlers } from './debug-handlers';
export { registerClaudeCodeHandlers } from './claude-code-handlers';
export { registerMcpHandlers } from './mcp-handlers';
export { registerProfileHandlers } from './profile-handlers';
export { registerCodexProfileHandlers } from './codex-profile-handlers';
export { registerSecurityHandlers } from './security-handlers';
export { registerScreenshotHandlers } from './screenshot-handlers';
export { registerMergeAnalyticsHandlers } from './merge-analytics-handlers';
export { registerAnalyticsHandlers } from './analytics-handlers';
export { registerModelUsageHandlers } from './model-usage-handlers';
export { registerTokenStatsHandlers } from './token-stats-handler';
export { registerTemplateHandlers } from './template-handlers';
export { registerWebhookHandlers } from './webhook-handlers';
export { registerPatternHandlers } from './pattern-handlers';
export { registerSessionReplayHandlers } from './session-replay-handlers';
export { registerFeedbackHandlers } from './feedback-handlers';
export { registerSchedulerHandlers } from './scheduler-handlers';
export { registerCollaborationHandlers } from './collaboration-handlers';
