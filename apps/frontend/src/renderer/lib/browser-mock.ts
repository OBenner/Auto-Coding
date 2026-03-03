/**
 * Browser mock for window.electronAPI
 * This allows the app to run in a regular browser for UI development/testing
 *
 * This module aggregates all mock implementations from separate modules
 * for better code organization and maintainability.
 */

import type { ElectronAPI } from '../../shared/types';
import {
  projectMock,
  taskMock,
  workspaceMock,
  terminalMock,
  claudeProfileMock,
  contextMock,
  integrationMock,
  changelogMock,
  insightsMock,
  infrastructureMock,
  settingsMock
} from './mocks';

// Check if we're in a browser (not Electron)
const isElectron = typeof window !== 'undefined' && window.electronAPI !== undefined;

/**
 * Create mock electronAPI for browser
 * Aggregates all mock implementations from separate modules
 */
const browserMockAPI: ElectronAPI = {
  // Project Operations
  ...projectMock,

  // Task Operations
  ...taskMock,

  // Workspace Management
  ...workspaceMock,

  // Terminal Operations
  ...terminalMock,

  // Claude Profile Management
  ...claudeProfileMock,

  // Settings
  ...settingsMock,

  // Roadmap Operations
  getRoadmap: async () => ({
    success: true,
    data: null
  }),

  getRoadmapStatus: async () => ({
    success: true,
    data: { isRunning: false }
  }),

  saveRoadmap: async () => ({
    success: true
  }),

  saveCompetitorAnalysis: async () => ({
    success: true
  }),

  generateRoadmap: (_projectId: string, _enableCompetitorAnalysis?: boolean, _refreshCompetitorAnalysis?: boolean) => {
    console.warn('[Browser Mock] generateRoadmap called');
  },

  refreshRoadmap: (_projectId: string, _enableCompetitorAnalysis?: boolean, _refreshCompetitorAnalysis?: boolean) => {
    console.warn('[Browser Mock] refreshRoadmap called');
  },

  updateFeatureStatus: async () => ({ success: true }),

  convertFeatureToSpec: async (projectId: string, _featureId: string) => ({
    success: true,
    data: {
      id: `task-${Date.now()}`,
      specId: '',
      projectId,
      title: 'Converted Feature',
      description: 'Feature converted from roadmap',
      status: 'backlog' as const,
      subtasks: [],
      logs: [],
      createdAt: new Date(),
      updatedAt: new Date()
    }
  }),

  stopRoadmap: async () => ({ success: true }),

  // Roadmap Progress Persistence
  saveRoadmapProgress: async () => ({ success: true }),
  loadRoadmapProgress: async () => ({ success: true, data: null }),
  clearRoadmapProgress: async () => ({ success: true }),

  // Roadmap Event Listeners
  onRoadmapProgress: () => () => {},
  onRoadmapComplete: () => () => {},
  onRoadmapError: () => () => {},
  onRoadmapStopped: () => () => {},
  // Context Operations
  ...contextMock,

  // Environment Configuration & Integration Operations
  ...integrationMock,

  // Changelog & Release Operations
  ...changelogMock,

  // Insights Operations
  ...insightsMock,

  // Infrastructure & Docker Operations
  ...infrastructureMock,

  // API Profile Management (custom Anthropic-compatible endpoints)
  getAPIProfiles: async () => ({
    success: true,
    data: {
      profiles: [],
      activeProfileId: null,
      version: 1
    }
  }),

  saveAPIProfile: async (profile) => ({
    success: true,
    data: {
      id: `mock-profile-${Date.now()}`,
      ...profile,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  }),

  updateAPIProfile: async (profile) => ({
    success: true,
    data: {
      ...profile,
      updatedAt: Date.now()
    }
  }),

  deleteAPIProfile: async (_profileId: string) => ({
    success: true
  }),

  setActiveAPIProfile: async (_profileId: string | null) => ({
    success: true
  }),

  testConnection: async (_baseUrl: string, _apiKey: string, _signal?: AbortSignal) => ({
    success: true,
    data: {
      success: true,
      message: 'Connection successful (mock)'
    }
  }),

  discoverModels: async (_baseUrl: string, _apiKey: string, _signal?: AbortSignal) => ({
    success: true,
    data: {
      models: []
    }
  }),

  // GitHub API
  github: {
    getGitHubRepositories: async () => ({ success: true, data: [] }),
    getGitHubIssues: async () => ({ success: true, data: { issues: [], hasMore: false } }),
    getGitHubIssue: async () => ({ success: true, data: null as any }),
    getIssueComments: async () => ({ success: true, data: [] }),
    checkGitHubConnection: async () => ({ success: true, data: { connected: false, repoFullName: undefined, error: undefined } }),
    investigateGitHubIssue: () => {},
    importGitHubIssues: async () => ({ success: true, data: { success: true, imported: 0, failed: 0, issues: [] } }),
    createGitHubRelease: async () => ({ success: true, data: { url: '' } }),
    suggestReleaseVersion: async () => ({ success: true, data: { suggestedVersion: '1.0.0', currentVersion: '0.0.0', bumpType: 'minor' as const, commitCount: 0, reason: 'Initial' } }),
    checkGitHubCli: async () => ({ success: true, data: { installed: false } }),
    checkGitHubAuth: async () => ({ success: true, data: { authenticated: false } }),
    startGitHubAuth: async () => ({ success: true, data: { success: false } }),
    getGitHubToken: async () => ({ success: true, data: { token: '' } }),
    getGitHubUser: async () => ({ success: true, data: { username: '' } }),
    listGitHubUserRepos: async () => ({ success: true, data: { repos: [] } }),
    detectGitHubRepo: async () => ({ success: true, data: '' }),
    getGitHubBranches: async () => ({ success: true, data: [] }),
    createGitHubRepo: async () => ({ success: true, data: { fullName: '', url: '' } }),
    addGitRemote: async () => ({ success: true, data: { remoteUrl: '' } }),
    listGitHubOrgs: async () => ({ success: true, data: { orgs: [] } }),
    onGitHubAuthDeviceCode: () => () => {},
    onGitHubAuthChanged: () => () => {},
    onGitHubInvestigationProgress: () => () => {},
    onGitHubInvestigationComplete: () => () => {},
    onGitHubInvestigationError: () => () => {},
    getAutoFixConfig: async () => null,
    saveAutoFixConfig: async () => true,
    getAutoFixQueue: async () => [],
    checkAutoFixLabels: async () => [],
    checkNewIssues: async () => [],
    startAutoFix: () => {},
    onAutoFixProgress: () => () => {},
    onAutoFixComplete: () => () => {},
    onAutoFixError: () => () => {},
    listPRs: async () => ({ prs: [], hasNextPage: false }),
    getPR: async () => null,
    runPRReview: () => {},
    cancelPRReview: async () => true,
    postPRReview: async () => true,
    postPRComment: async () => true,
    mergePR: async () => true,
    assignPR: async () => true,
    markReviewPosted: async () => true,
    getPRReview: async () => null,
    getPRReviewsBatch: async () => ({}),
    deletePRReview: async () => true,
    checkNewCommits: async () => ({ hasNewCommits: false, newCommitCount: 0 }),
    checkMergeReadiness: async () => ({ isDraft: false, mergeable: 'UNKNOWN' as const, isBehind: false, ciStatus: 'none' as const, blockers: [] }),
    updatePRBranch: async () => ({ success: true }),
    runFollowupReview: () => {},
    getPRLogs: async () => null,
    getWorkflowsAwaitingApproval: async () => ({ awaiting_approval: 0, workflow_runs: [], can_approve: false }),
    approveWorkflow: async () => true,
    onPRReviewProgress: () => () => {},
    onPRReviewComplete: () => () => {},
    onPRReviewError: () => () => {},
    batchAutoFix: () => {},
    getBatches: async () => [],
    onBatchProgress: () => () => {},
    onBatchComplete: () => () => {},
    onBatchError: () => () => {},
    // Analyze & Group Issues (proactive workflow)
    analyzeIssuesPreview: () => {},
    approveBatches: async () => ({ success: true, batches: [] }),
    onAnalyzePreviewProgress: () => () => {},
    onAnalyzePreviewComplete: () => () => {},
    onAnalyzePreviewError: () => () => {},
    // Inline comments operations
    getInlineComments: async () => [],
    replyToComment: async () => true,
    applySuggestion: async () => ({ success: true }),
    requestReReview: async () => true,
    onPRUpdated: () => () => {}
  },

  // GitLab API
  gitlab: {
    getGitLabProjects: async () => ({ success: true, data: [] }),
    checkGitLabConnection: async () => ({ success: true, data: { connected: false, projectPathWithNamespace: undefined, error: undefined } }),
    getGitLabIssues: async () => ({ success: true, data: [] }),
    getGitLabIssue: async () => ({ success: true, data: null as any }),
    getGitLabIssueNotes: async () => ({ success: true, data: [] }),
    investigateGitLabIssue: () => {},
    importGitLabIssues: async () => ({ success: true, data: { success: true, imported: 0, failed: 0, errors: undefined } }),
    getGitLabMergeRequests: async () => ({ success: true, data: [] }),
    getGitLabMergeRequest: async () => ({ success: true, data: null as any }),
    createGitLabMergeRequest: async () => ({ success: true, data: null as any }),
    updateGitLabMergeRequest: async () => ({ success: true, data: null as any }),
    getGitLabMRDiff: async () => null,
    getGitLabMRReview: async () => null,
    runGitLabMRReview: () => {},
    runGitLabMRFollowupReview: () => {},
    postGitLabMRReview: async () => true,
    postGitLabMRNote: async () => true,
    mergeGitLabMR: async () => true,
    assignGitLabMR: async () => true,
    approveGitLabMR: async () => true,
    cancelGitLabMRReview: async () => true,
    checkGitLabMRNewCommits: async () => ({ hasNewCommits: false, newCommitCount: 0 }),
    onGitLabMRReviewProgress: () => () => {},
    onGitLabMRReviewComplete: () => () => {},
    onGitLabMRReviewError: () => () => {},
    getGitLabAutoFixConfig: async () => null,
    saveGitLabAutoFixConfig: async () => true,
    getGitLabAutoFixQueue: async () => [],
    checkGitLabAutoFixLabels: async () => [],
    checkNewGitLabAutoFixIssues: async () => [],
    startGitLabAutoFix: () => {},
    getGitLabAutoFixBatches: async () => [],
    analyzeGitLabAutoFixPreview: () => {},
    approveGitLabAutoFixBatches: async () => ({ success: true, batches: [] }),
    onGitLabAutoFixProgress: () => () => {},
    onGitLabAutoFixComplete: () => () => {},
    onGitLabAutoFixError: () => () => {},
    onGitLabAutoFixAnalyzePreviewProgress: () => () => {},
    onGitLabAutoFixAnalyzePreviewComplete: () => () => {},
    onGitLabAutoFixAnalyzePreviewError: () => () => {},
    getGitLabTriageConfig: async () => null,
    saveGitLabTriageConfig: async () => true,
    getGitLabTriageResults: async () => [],
    runGitLabTriage: () => {},
    applyGitLabTriageLabels: async () => true,
    onGitLabTriageProgress: () => () => {},
    onGitLabTriageComplete: () => () => {},
    onGitLabTriageError: () => () => {},
    createGitLabRelease: async () => ({ success: true, data: { url: '' } }),
    checkGitLabCli: async () => ({ success: true, data: { installed: false } }),
    installGitLabCli: async () => ({ success: true, data: { command: '' } }),
    checkGitLabAuth: async () => ({ success: true, data: { authenticated: false } }),
    startGitLabAuth: async () => ({ success: true, data: { deviceCode: '', verificationUrl: '', userCode: '' } }),
    getGitLabToken: async () => ({ success: true, data: { token: '' } }),
    getGitLabUser: async () => ({ success: true, data: { username: '' } }),
    listGitLabUserProjects: async () => ({ success: true, data: { projects: [] } }),
    detectGitLabProject: async () => ({ success: true, data: { project: '', instanceUrl: '' } }),
    getGitLabBranches: async () => ({ success: true, data: [] }),
    createGitLabProject: async () => ({ success: true, data: { pathWithNamespace: '', webUrl: '' } }),
    addGitLabRemote: async () => ({ success: true, data: { remoteUrl: '' } }),
    listGitLabGroups: async () => ({ success: true, data: { groups: [] } }),
    onGitLabInvestigationProgress: () => () => {},
    onGitLabInvestigationComplete: () => () => {},
    onGitLabInvestigationError: () => () => {}
  },

  // Template Library Operations
  listTemplates: async (_projectId: string, _options?: { category?: string | 'all'; tags?: string[] }) => ({
    success: true,
    data: []
  }),
  getTemplate: async (_projectId: string, _templateName: string) => ({
    success: true,
    data: {
      name: 'mock-template',
      description: 'Mock template',
      category: 'api' as const,
      parameters: {},
      tags: []
    }
  }),
  getTemplateCategories: async (_projectId: string) => ({
    success: true,
    data: ['api', 'authentication', 'database', 'ui', 'file', 'search', 'pagination', 'caching', 'notification', 'data_processing', 'user_management', 'settings', 'dashboard', 'admin', 'logging', 'testing', 'documentation', 'cicd', 'security', 'performance', 'other']
  }),
  searchTemplates: async (_projectId: string, _query: string) => ({
    success: true,
    data: []
  }),
  previewTemplate: async (_projectId: string, _templateName: string, _parameters: Record<string, unknown>) => ({
    success: true,
    data: {
      title: 'Mock Template',
      description: 'Template preview',
      rationale: 'Mock rationale',
      user_stories: [],
      acceptance_criteria: [],
      technical_details: 'Mock technical details'
    }
  }),
  createSpecFromTemplate: async (_projectId: string, _templateName: string, _parameters: Record<string, unknown>, _specId?: string) => ({
    success: true,
    data: {
      specId: '001-mock',
      specPath: '/mock/path'
    }
  }),
  suggestTemplates: async (_projectId: string, _taskDescription: string) => ({
    success: true,
    data: []
  }),

  // Custom Agent Template Operations
  listCustomTemplates: async () => ({
    success: true,
    data: []
  }),
  saveCustomTemplate: async (template: Omit<import('../../shared/types/template').CustomTemplate, 'id' | 'createdAt' | 'updatedAt'>) => ({
    success: true,
    data: {
      id: `custom-template-${Date.now()}`,
      ...template,
      createdAt: new Date(),
      updatedAt: new Date()
    }
  }),
  updateCustomTemplate: async (template: import('../../shared/types/template').CustomTemplate) => ({
    success: true,
    data: {
      ...template,
      updatedAt: new Date()
    }
  }),
  deleteCustomTemplate: async (_templateId: string) => ({
    success: true
  }),
  exportCustomTemplate: async (_templateId: string) => ({
    success: true,
    data: '{"mock": "template"}'
  }),
  importCustomTemplate: async (_jsonData: string) => ({
    success: true,
    data: {
      id: `custom-template-${Date.now()}`,
      name: 'Imported Template',
      description: 'Imported from JSON',
      category: 'other' as const,
      parameters: {},
      createdAt: new Date(),
      updatedAt: new Date(),
      isPublic: false
    }
  }),
  testCustomTemplate: async (_templateId: string, _testInput: string) => ({
    success: true,
    data: {
      title: 'Test Result',
      description: 'Template test result',
      rationale: 'Test rationale',
      user_stories: [],
      acceptance_criteria: [],
      technical_details: 'Test details'
    }
  }),

  // Queue Routing API (rate limit recovery)
  queue: {
    getRunningTasksByProfile: async () => ({ success: true, data: { byProfile: {}, totalRunning: 0 } }),
    getBestProfileForTask: async () => ({ success: true, data: null }),
    assignProfileToTask: async () => ({ success: true }),
    updateTaskSession: async () => ({ success: true }),
    getTaskSession: async () => ({ success: true, data: null }),
    onQueueProfileSwapped: () => () => {},
    onQueueSessionCaptured: () => () => {},
    onQueueBlockedNoProfiles: () => () => {}
  },

  // Pattern learning API (codebase patterns)
  pattern: {
    listPatterns: async () => ({ success: true, data: [] }),
    getPatternCategories: async () => ({ success: true, data: ['naming-conventions' as const, 'error-handling' as const, 'code-organization' as const] }),
    getPatternDetails: async () => ({ success: true, data: { index: 1, id: '1', text: 'Mock pattern', category: 'naming-conventions', confidence: 'high' as const, reasoning: 'Mock reasoning' } }),
    approvePattern: async () => ({ success: true, data: undefined }),
    overridePattern: async () => ({ success: true, data: undefined }),
    deletePattern: async () => ({ success: true, data: undefined })
  },

  // Session Replay API
  sessionReplay: {
    listSessions: async () => ({ success: true, data: [] }),
    getSession: async () => ({ success: true, data: null }),
    getTimeline: async () => ({ success: true, data: [] }),
    getDecisionPoints: async () => ({ success: true, data: [] }),
    getBookmarks: async () => ({ success: true, data: [] }),
    addBookmark: async () => ({ success: true, data: { id: 'mock', timestamp: '', entry_timestamp: '', phase: '', label: '', note: null, session: 0, subtask_id: '' } }),
    removeBookmark: async () => ({ success: true, data: undefined }),
    getEntries: async () => ({ success: true, data: [] }),
    search: async () => ({ success: true, data: [] }),
    exportSession: async () => ({ success: true, data: '' }),
    exportAll: async () => ({ success: true, data: '' }),
  },

  // Scheduler API (build scheduling and queue management)
  scheduler: {
    scheduleBuild: async () => ({ success: true, data: { buildId: 'mock-build-1' } }),
    getStatus: async () => ({ success: true, data: { schedulerRunning: false, totalBuilds: 0, byStatus: { pending: 0, queued: 0, running: 0, completed: 0, failed: 0, cancelled: 0, retrying: 0 }, builds: [], nextBuild: null } }),
    cancelBuild: async () => ({ success: true }),
    start: async () => ({ success: true }),
    stop: async () => ({ success: true }),
    getBuilds: async () => ({ success: true, data: [] }),
    onBuildScheduled: () => () => {},
    onBuildCancelled: () => () => {},
    onStatusChanged: () => () => {},
    onBuildProgress: () => () => {},
    onBuildComplete: () => () => {},
    onBuildFailed: () => () => {}
  },

  // Claude Code Operations
  checkClaudeCodeVersion: async () => ({
    success: true,
    data: {
      installed: '1.0.0',
      latest: '1.0.0',
      isOutdated: false,
      path: '/usr/local/bin/claude',
      detectionResult: {
        found: true,
        version: '1.0.0',
        path: '/usr/local/bin/claude',
        source: 'system-path' as const,
        message: 'Claude Code CLI found'
      }
    }
  }),
  installClaudeCode: async () => ({
    success: true,
    data: { command: 'npm install -g @anthropic-ai/claude-code' }
  }),
  getClaudeCodeVersions: async () => ({
    success: true,
    data: {
      versions: ['1.0.5', '1.0.4', '1.0.3', '1.0.2', '1.0.1', '1.0.0']
    }
  }),
  installClaudeCodeVersion: async (version: string) => ({
    success: true,
    data: { command: `npm install -g @anthropic-ai/claude-code@${version}`, version }
  }),
  getClaudeCodeInstallations: async () => ({
    success: true,
    data: {
      installations: [
        {
          path: '/usr/local/bin/claude',
          version: '1.0.0',
          source: 'system-path' as const,
          isActive: true,
        }
      ],
      activePath: '/usr/local/bin/claude',
    }
  }),
  setClaudeCodeActivePath: async (cliPath: string) => ({
    success: true,
    data: { path: cliPath }
  }),

  // Terminal Worktree Operations
  createTerminalWorktree: async () => ({
    success: false,
    error: 'Not available in browser mode'
  }),
  listTerminalWorktrees: async () => ({
    success: true,
    data: []
  }),
  removeTerminalWorktree: async () => ({
    success: false,
    error: 'Not available in browser mode'
  }),
  listOtherWorktrees: async () => ({
    success: true,
    data: []
  }),

  // MCP Server Health Check Operations
  checkMcpHealth: async (server) => ({
    success: true,
    data: {
      serverId: server.id,
      status: 'unknown' as const,
      message: 'Health check not available in browser mode',
      checkedAt: new Date().toISOString()
    }
  }),
  testMcpConnection: async (server) => ({
    success: true,
    data: {
      serverId: server.id,
      success: false,
      message: 'Connection test not available in browser mode'
    }
  }),

  // Screenshot capture operations
  getSources: async () => ({
    success: true,
    data: []
  }),
  capture: async (_options: { sourceId: string }) => ({
    success: false,
    error: 'Screenshot capture not available in browser mode'
  }),

  // Debug Operations
  getDebugInfo: async () => ({
    systemInfo: {
      appVersion: '0.0.0-browser-mock',
      platform: 'browser',
      isPackaged: 'false'
    },
    recentErrors: [],
    logsPath: '/mock/logs',
    debugReport: '[Browser Mock] Debug report not available in browser mode'
  }),
  openLogsFolder: async () => ({ success: false, error: 'Not available in browser mode' }),
  copyDebugInfo: async () => ({ success: false, error: 'Not available in browser mode' }),
  getRecentErrors: async () => [],
  listLogFiles: async () => [],

  // Merge Analytics Operations
  getMergeHistory: async () => ({ success: true, data: [] }),
  getMergeSummary: async () => ({
    success: true,
    data: {
      total_operations: 0,
      total_files_merged: 0,
      total_conflicts: 0,
      successful_operations: 0,
      failed_operations: 0,
      total_ai_calls: 0,
      total_tokens_used: 0,
      average_duration_seconds: 0,
      success_rate: 0,
      auto_merge_rate: 0,
      conflict_patterns: []
    }
  }),
  getConflictPatterns: async () => ({ success: true, data: [] }),
  exportMergeAnalytics: async () => ({ success: true, data: { path: '/mock/export' } }),

  // Memory graph operations
  getGraphData: async () => ({ success: true, data: { nodes: [], edges: [], node_count: 0, edge_count: 0 } }),
  deleteMemory: async () => ({ success: true, data: { success: true } }),
  exportMemories: async () => ({ success: true, data: { memory_count: 0, entity_count: 0 } }),

  // Token statistics
  getTokenStats: async () => ({ success: true, data: null }),

  // Plugin operations
  listPlugins: async () => ({ success: true, data: [] }),
  enablePlugin: async () => ({ success: true, data: { success: true } }),
  disablePlugin: async () => ({ success: true, data: { success: true } }),
  installPlugin: async () => ({ success: true, data: { success: true } }),
  uninstallPlugin: async () => ({ success: true, data: { success: true } }),

  // Context Viewer API
  getContextStats: async () => ({ success: true, data: null }),
  getTokenBreakdown: async () => ({ success: true, data: null }),
  getPrioritizationScores: async () => ({ success: true, data: null }),
  getOptimizationReport: async () => ({ success: true, data: null }),
  exportContextSnapshot: async () => ({ success: true, data: null }),

  // Productivity analytics operations
  getProductivitySummary: async (
    _projectId?: string,
    filter?: import('../../shared/types').ProductivityAnalyticsFilter
  ) => {
    const now = Date.now();
    const windowDays = filter?.window_days ?? 30;
    const periodEnd = filter?.end_date ? new Date(filter.end_date).getTime() : now;
    const periodStart = filter?.start_date
      ? new Date(filter.start_date).getTime()
      : periodEnd - windowDays * 24 * 60 * 60 * 1000;

    return {
      success: true as const,
      data: {
        period_start: new Date(periodStart).toISOString(),
        period_end: new Date(periodEnd).toISOString(),
        total_specs: 0,
        completed_specs: 0,
        in_progress_specs: 0,
        failed_specs: 0,
        total_time_saved_hours: 0,
        total_build_time_hours: 0,
        average_success_rate: 0,
        first_attempt_success_rate: 0,
        specs_by_type: {},
        specs_by_complexity: {},
        average_subtasks_per_spec: 0,
        average_qa_iterations: 0,
        total_subtasks_completed: 0,
        specs: []
      }
    };
  },
  getProductivityTrends: async (
    _projectId?: string,
    _filter?: import('../../shared/types').ProductivityAnalyticsFilter
  ) => ({ success: true as const, data: [] as import('../../shared/types').ProductivityTrendPoint[] }),
  getFailureMetrics: async (_projectId?: string) => ({
    success: true as const,
    data: { total_failures: 0 } as import('../../shared/types').FailureMetrics
  }),
  exportProductivityAnalytics: async () => ({ success: true as const, data: '/mock/export/productivity' }),

  // Model Usage Analytics
  getModelUsageSummary: async () => ({ success: true as const, data: { period_start: '', period_end: '', total_usage_count: 0, total_tokens: 0, total_cost: 0, models: [], agents: [], top_models_by_usage: [], top_models_by_cost: [] } }),
  getModelUsageTrends: async () => ({ success: true as const, data: [] }),
  exportModelUsageAnalytics: async () => ({ success: true as const, data: '' }),

  // Agent performance analytics (nested API)
  analytics: {
    getSummary: async () => ({
      success: true as const,
      data: {
        total_specs: 0, completed_specs: 0, failed_specs: 0, in_progress_specs: 0,
        overall_success_rate: 0, total_cost: 0, total_tokens: 0,
        agent_stats: {}, complexity_stats: {},
        qa_stats: { total_reviews: 0, approved: 0, rejected: 0, rejection_rate: 0, common_issues: {} },
        last_updated: new Date().toISOString(),
      }
    }),
    getAgentStats: async () => ({ success: true as const, data: {} }),
    getTrends: async () => ({ success: true as const, data: [] }),
    getReport: async () => ({
      success: true as const,
      data: {
        summary: {
          total_specs: 0, completed_specs: 0, failed_specs: 0, in_progress_specs: 0,
          overall_success_rate: 0, total_cost: 0, total_tokens: 0,
          agent_stats: {}, complexity_stats: {},
          qa_stats: { total_reviews: 0, approved: 0, rejected: 0, rejection_rate: 0, common_issues: {} },
          last_updated: new Date().toISOString(),
        },
        trends: [],
        generated_at: new Date().toISOString(),
      }
    }),
  }
};

/**
 * Initialize browser mock if not running in Electron
 */
export function initBrowserMock(): void {
  if (!isElectron) {
    console.warn('%c[Browser Mock] Initializing mock electronAPI for browser preview', 'color: #f0ad4e; font-weight: bold;');
    (window as Window & { electronAPI: ElectronAPI }).electronAPI = browserMockAPI;
  }
}

// Auto-initialize
initBrowserMock();
