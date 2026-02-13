/**
 * Agent API - Aggregates all agent-related API modules
 *
 * This file serves as the main entry point for agent APIs, combining:
 * - Roadmap operations
 * - Ideation operations
 * - Insights operations
 * - Changelog operations
 * - Linear integration
 * - GitHub integration
 * - Shell operations
 * - Session context operations
 * - Productivity analytics
 */

import { createRoadmapAPI, RoadmapAPI } from './modules/roadmap-api';
import { createIdeationAPI, IdeationAPI } from './modules/ideation-api';
import { createInsightsAPI, InsightsAPI } from './modules/insights-api';
import { createChangelogAPI, ChangelogAPI } from './modules/changelog-api';
import { createLinearAPI, LinearAPI } from './modules/linear-api';
import { createGitHubAPI, GitHubAPI } from './modules/github-api';
import { createGitLabAPI, GitLabAPI } from './modules/gitlab-api';
import { createShellAPI, ShellAPI } from './modules/shell-api';
import { createSessionContextAPI, SessionContextAPI } from './modules/session-context-api';
import { createProductivityAnalyticsAPI, ProductivityAnalyticsAPI } from './modules/productivity-analytics-api';
import { createModelUsageAPI, ModelUsageAPI } from './modules/model-usage-api';

/**
 * Combined Agent API interface
 * Includes all operations from individual API modules
 */
export interface AgentAPI extends
  RoadmapAPI,
  IdeationAPI,
  InsightsAPI,
  ChangelogAPI,
  LinearAPI,
  GitHubAPI,
  GitLabAPI,
  ShellAPI,
  SessionContextAPI,
  ProductivityAnalyticsAPI,
  ModelUsageAPI {}

/**
 * Creates the complete Agent API by combining all module APIs
 *
 * @returns Complete AgentAPI with all operations available
 */
export const createAgentAPI = (): AgentAPI => {
  const roadmapAPI = createRoadmapAPI();
  const ideationAPI = createIdeationAPI();
  const insightsAPI = createInsightsAPI();
  const changelogAPI = createChangelogAPI();
  const linearAPI = createLinearAPI();
  const githubAPI = createGitHubAPI();
  const gitlabAPI = createGitLabAPI();
  const shellAPI = createShellAPI();
  const sessionContextAPI = createSessionContextAPI();
  const productivityAnalyticsAPI = createProductivityAnalyticsAPI();
  const modelUsageAPI = createModelUsageAPI();

  return {
    // Roadmap API
    ...roadmapAPI,

    // Ideation API
    ...ideationAPI,

    // Insights API
    ...insightsAPI,

    // Changelog API
    ...changelogAPI,

    // Linear Integration API
    ...linearAPI,

    // GitHub Integration API
    ...githubAPI,

    // GitLab Integration API
    ...gitlabAPI,

    // Shell Operations API
    ...shellAPI,

    // Session Context API
    ...sessionContextAPI,

    // Productivity Analytics API
    ...productivityAnalyticsAPI,

    // Model Usage Analytics API
    ...modelUsageAPI
  };
};

// Re-export individual API interfaces for consumers who need them
export type {
  RoadmapAPI,
  IdeationAPI,
  InsightsAPI,
  ChangelogAPI,
  LinearAPI,
  GitHubAPI,
  GitLabAPI,
  ShellAPI,
  SessionContextAPI,
  ProductivityAnalyticsAPI,
  ModelUsageAPI
};
