import { ProjectAPI, createProjectAPI } from './project-api';
import { TerminalAPI, createTerminalAPI } from './terminal-api';
import { TaskAPI, createTaskAPI } from './task-api';
import { SettingsAPI, createSettingsAPI } from './settings-api';
import { FileAPI, createFileAPI } from './file-api';
import { AgentAPI, createAgentAPI } from './agent-api';
import { TemplateAPI, createTemplateAPI } from './template-api';
import type { IdeationAPI } from './modules/ideation-api';
import type { InsightsAPI } from './modules/insights-api';
import type { AnalyticsAPI } from './modules/analytics-api';
import { AppUpdateAPI, createAppUpdateAPI } from './app-update-api';
import { GitHubAPI, createGitHubAPI } from './modules/github-api';
import type { GitLabAPI } from './modules/gitlab-api';
import { DebugAPI, createDebugAPI } from './modules/debug-api';
import { ClaudeCodeAPI, createClaudeCodeAPI } from './modules/claude-code-api';
import { McpAPI, createMcpAPI } from './modules/mcp-api';
import { ProfileAPI, createProfileAPI } from './profile-api';
import { ScreenshotAPI, createScreenshotAPI } from './screenshot-api';
import { QueueAPI, createQueueAPI } from './queue-api';
import { PluginAPI, createPluginAPI } from './plugin-api';
import type { PatternAPI } from './modules/pattern-api';
import { createPatternAPI } from './modules/pattern-api';
import type { SessionReplayAPI } from './modules/session-replay-api';
import { createSessionReplayAPI } from './modules/session-replay-api';
import { ContextViewerAPI, createContextViewerAPI } from './modules/context-viewer-api';
import { SchedulerAPI, createSchedulerAPI } from './scheduler-api';
import { FeedbackAPI, createFeedbackAPI } from './feedback-api';
import { SecurityAPI, createSecurityAPI } from './security-api';
import { SetupAPI, createSetupAPI } from './setup-api';

export interface ElectronAPI extends
  ProjectAPI,
  TerminalAPI,
  TaskAPI,
  SettingsAPI,
  FileAPI,
  AgentAPI,
  TemplateAPI,
  IdeationAPI,
  InsightsAPI,
  AppUpdateAPI,
  GitLabAPI,
  DebugAPI,
  ClaudeCodeAPI,
  McpAPI,
  ProfileAPI,
  ScreenshotAPI,
  PluginAPI,
  ContextViewerAPI,
  FeedbackAPI,
  SecurityAPI {
  /** Setup wizard API for first-run configuration */
  setup: SetupAPI;
  /** Security API (nested access for security store) */
  security: SecurityAPI;
  github: GitHubAPI;
  /** Queue routing API for rate limit recovery */
  queue: QueueAPI;
  /** Pattern learning API for codebase patterns */
  pattern: PatternAPI;
  /** Session replay API for learning and review */
  sessionReplay: SessionReplayAPI;
  /** Scheduler API for build scheduling and queue management */
  scheduler: SchedulerAPI;
}

export const createElectronAPI = (): ElectronAPI => {
  const securityAPI = createSecurityAPI();
  return {
    ...createProjectAPI(),
    ...createSetupAPI(),
    ...createTerminalAPI(),
    ...createTaskAPI(),
    ...createSettingsAPI(),
    ...createFileAPI(),
    ...createTemplateAPI(),
    ...createAgentAPI(),  // Includes: Roadmap, Ideation, Insights, Changelog, Linear, GitHub, GitLab, Shell, SessionContext
    ...createAppUpdateAPI(),
    ...createDebugAPI(),
    ...createClaudeCodeAPI(),
    ...createMcpAPI(),
    ...createProfileAPI(),
    ...createScreenshotAPI(),
    ...createPluginAPI(),
    ...createContextViewerAPI(),
    ...createFeedbackAPI(),
    ...securityAPI,
    security: securityAPI,
    github: createGitHubAPI(),
    setup: createSetupAPI(),
    queue: createQueueAPI(),  // Queue routing for rate limit recovery
    pattern: createPatternAPI(),
    sessionReplay: createSessionReplayAPI(),
    scheduler: createSchedulerAPI()
  };
};

// Export individual API creators for potential use in tests or specialized contexts
// Note: IdeationAPI, InsightsAPI, AnalyticsAPI, and GitLabAPI are included in AgentAPI
export {
  createProjectAPI,
  createTerminalAPI,
  createTaskAPI,
  createSettingsAPI,
  createFileAPI,
  createAgentAPI,
  createTemplateAPI,
  createAppUpdateAPI,
  createProfileAPI,
  createGitHubAPI,
  createDebugAPI,
  createClaudeCodeAPI,
  createMcpAPI,
  createScreenshotAPI,
  createQueueAPI,
  createPluginAPI,
  createPatternAPI,
  createSessionReplayAPI,
  createContextViewerAPI,
  createSchedulerAPI,
  createFeedbackAPI,
  createSetupAPI,
  createSecurityAPI
};

export type {
  ProjectAPI,
  TerminalAPI,
  TaskAPI,
  SettingsAPI,
  FileAPI,
  AgentAPI,
  TemplateAPI,
  IdeationAPI,
  InsightsAPI,
  AnalyticsAPI,
  AppUpdateAPI,
  ProfileAPI,
  GitHubAPI,
  GitLabAPI,
  DebugAPI,
  ClaudeCodeAPI,
  McpAPI,
  ScreenshotAPI,
  QueueAPI,
  PluginAPI,
  PatternAPI,
  SessionReplayAPI,
  ContextViewerAPI,
  SchedulerAPI,
  FeedbackAPI,
  SecurityAPI
};
