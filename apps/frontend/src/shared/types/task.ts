/**
 * Task-related types
 */

import type { ThinkingLevel, PhaseModelConfig, PhaseThinkingConfig } from './settings';
import type { ExecutionPhase as ExecutionPhaseType, CompletablePhase } from '../constants/phase-protocol';
import type { AIProvider } from './common';

export type TaskStatus = 'backlog' | 'queue' | 'in_progress' | 'ai_review' | 'human_review' | 'done' | 'pr_created' | 'error';

// Maps task status columns to ordered task IDs for kanban board reordering
export type TaskOrderState = Record<TaskStatus, string[]>;

// Reason why a task is in human_review status
// - 'completed': All subtasks done and QA passed, ready for final approval/merge
// - 'errors': Subtasks failed during execution
// - 'qa_rejected': QA found issues that need fixing
// - 'plan_review': Spec/plan created and awaiting approval before coding starts
export type ReviewReason = 'completed' | 'errors' | 'qa_rejected' | 'plan_review';

export type SubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

// Re-exported from constants - single source of truth
export type ExecutionPhase = ExecutionPhaseType;

export interface ExecutionProgress {
  phase: ExecutionPhase;
  phaseProgress: number;  // 0-100 within current phase
  overallProgress: number;  // 0-100 overall
  currentSubtask?: string;  // Current subtask being processed
  message?: string;  // Current status message
  startedAt?: Date;
  sequenceNumber?: number;  // Monotonically increasing counter to detect stale updates
  // FIX (ACS-203): Track completed phases to prevent phase overlaps
  // When a phase completes, it's added to this array before transitioning to the next phase
  // This ensures that planning is marked complete before coding starts, etc.
  completedPhases?: CompletablePhase[];  // Phases that have successfully completed

  // Resource usage metrics (from backend resource_tracker.py)
  cpu_percent?: number;  // CPU usage percentage
  memory_mb?: number;  // Memory usage in megabytes
  memory_percent?: number;  // Memory usage percentage
  elapsed_seconds?: number;  // Elapsed time since phase started

  // Timing estimates (from backend timing_history.py)
  estimated_seconds?: number;  // Estimated time to completion
  confidence?: 'high' | 'medium' | 'low';  // Estimate confidence level
  sample_size?: number;  // Number of historical samples used for estimate
}

export interface Subtask {
  id: string;
  title: string;
  description: string;
  status: SubtaskStatus;
  files: string[];
  verification?: {
    type: 'command' | 'browser';
    run?: string;
    scenario?: string;
  };
}

export interface QAReport {
  status: 'passed' | 'failed' | 'pending';
  issues: QAIssue[];
  timestamp: Date;
}

export interface QAIssue {
  id: string;
  severity: 'critical' | 'major' | 'minor';
  description: string;
  file?: string;
  line?: number;
}

// QA Escalation types - for QA_ESCALATION.md parsing
export interface QAEscalation {
  generated: string;  // ISO timestamp
  iteration: number;
  maxIterations: number;
  reason: string;
  summary: QAEscalationSummary;
  recurringIssues: QARecurringIssue[];
  mostCommonIssues: QACommonIssue[];
}

export interface QAEscalationSummary {
  totalIterations: number;
  totalIssues: number;
  uniqueIssues: number;
  fixSuccessRate: number;  // 0-1 (percentage as decimal)
}

export interface QARecurringIssue {
  title: string;
  file?: string;
  line?: number;
  type?: string;
  occurrences: number;
  description: string;
}

export interface QACommonIssue {
  title: string;
  file?: string;
  occurrences: number;
}

export interface GenericEditArtifactManifestEntry {
  name: string;
  kind: string;
  path: string | null;
  active: boolean;
  required: boolean;
  present: boolean;
}

export interface GenericEditRecentEvent {
  sequence: number;
  event_type: string;
  tool?: string;
  ok?: boolean;
  message?: string;
  status?: string;
  transaction_id?: string;
  batch_id?: string;
  active_batch_id?: string;
  group_id?: string;
  path?: string;
  iteration?: number | string | null;
  from_loop?: string;
  to_loop?: string;
  reason?: string;
  tool_schema_count?: number;
  action_index?: number;
  timeline_stage?: string;
  recovery_required?: boolean;
  requires_user_action?: boolean;
  failed_action_count?: number;
  recovery_attempt_count?: number;
  failed_recovery_attempt_count?: number;
  [key: string]: unknown;
}

export interface GenericEditRecoverySummary {
  version: number;
  status: string;
  finish_blocked: boolean;
  unresolved_transaction_group_count: number;
  unresolved_transaction_group_ids: string[];
  warning_count: number;
  warnings: string[];
  resolution_strategies: string[];
  recommended_verification_tools: string[];
}

export interface GenericEditRecoveryAction {
  id: string;
  kind: string;
  tool: string;
  transaction_id?: string;
  transaction_group_id?: string;
  rollback_operation_id?: string;
  paths?: string[];
  mutation_snapshot_ids?: string[];
  required_before_finish: boolean;
}

export interface GenericEditNativeToolFallback {
  provider: string;
  from_loop: string;
  to_loop: string;
  reason: string;
  message: string;
  tool_schema_count: number;
}

export interface GenericEditResumeAction {
  runtime: 'generic_edit';
  checkpoint_path: string;
  strategy: string;
  next_iteration: number;
}

export interface GenericEditResumePolicy {
  version: number;
  runtime: 'generic_edit';
  status: string;
  can_resume: boolean;
  finish_blocked: boolean;
  strategy: string;
  checkpoint_path: string;
  next_iteration: number;
  required_resolution_action_kinds: string[];
  required_artifacts: string[];
  unresolved_partial_failure_ids: string[];
  unresolved_transaction_group_ids: string[];
  open_transaction_batch_ids?: string[];
}

export interface GenericEditMcpBridgePlan {
  status: string | null;
  action_required: string | null;
  recommended_runtime_path: string | null;
  native_required_servers: string[];
  local_bridge_required_servers: string[];
  external_bridge_required_servers: string[];
  unsupported_servers: string[];
  bridged_servers: string[];
  external_bridged_servers: string[];
}

export interface GenericEditMcpServerStatus {
  server: string;
  display_name: string | null;
  availability: string | null;
  runtime_path: string | null;
  bridgeable: boolean | null;
  reason: string | null;
  notes: string | null;
  external_client: Record<string, unknown> | null;
}

export interface GenericEditMcpToolPolicy {
  server: string | null;
  name: string;
  exposed_name: string;
  permission: string | null;
  audit_level: string | null;
  mutating: boolean | null;
  audit_required: boolean | null;
}

export interface GenericEditMcpPermissionPolicy {
  mode: string | null;
  allowed_permissions: string[] | null;
}

export interface GenericEditMcpOpenSession {
  server: string;
  transport: string;
  status: string;
}

export interface GenericEditMcpSessionLifecycle {
  reuse: string;
  open_session_count: number;
  open_sessions: GenericEditMcpOpenSession[];
}

export interface GenericEditMcpBridge {
  tools: string[];
  tool_policies: GenericEditMcpToolPolicy[];
  permission_policy: GenericEditMcpPermissionPolicy | null;
  server_statuses: GenericEditMcpServerStatus[];
  session_lifecycle: GenericEditMcpSessionLifecycle | null;
}

export interface GenericEditMcpSupport {
  strategy: string;
  reason: string | null;
  server: string | null;
  tool_count: number | null;
  available_servers: string[];
  unavailable_servers: string[];
  server_statuses: GenericEditMcpServerStatus[];
  bridge_plan: GenericEditMcpBridgePlan | null;
  bridge: GenericEditMcpBridge | null;
}

export interface GenericEditArtifactManifest {
  artifact_type: 'generic_edit_artifact_manifest';
  schema_version: 1;
  timestamp: string;
  provider: string;
  subtask_id: string | null;
  status: string;
  stop_reason: string;
  entrypoints: {
    result?: string;
    summary?: string;
    events?: string;
    session_state?: string;
    trace?: string;
    [key: string]: string | undefined;
  };
  flags: {
    recoverable: boolean;
    resumable: boolean;
    resumed: boolean;
    recovery_required: boolean;
    recovery_resolved: boolean;
    has_recovery_plan: boolean;
    has_mutation_snapshots: boolean;
    has_transaction_groups: boolean;
    [key: string]: boolean;
  };
  counts: {
    iteration_count: number;
    action_count: number;
    failed_action_count: number;
    native_tool_fallback_count: number;
    event_count: number;
    transaction_count: number;
    transaction_group_count: number;
    mutation_snapshot_count: number;
    recovery_attempt_count: number;
    failed_recovery_attempt_count: number;
    [key: string]: number;
  };
  artifacts: GenericEditArtifactManifestEntry[];
  recent_events: GenericEditRecentEvent[];
  recovery_timeline: GenericEditRecentEvent[];
  native_tool_fallbacks: GenericEditNativeToolFallback[];
  recovery_summary: GenericEditRecoverySummary | null;
  recovery_actions: GenericEditRecoveryAction[];
  mcp_support: GenericEditMcpSupport | null;
  resume_action: GenericEditResumeAction | null;
  resume_inputs: Record<string, string>;
  resume_policy: GenericEditResumePolicy | null;
  resume: Record<string, unknown> | null;
}

// Task Log Types - for persistent, phase-based logging
export type TaskLogPhase = 'planning' | 'coding' | 'validation';
export type TaskLogPhaseStatus = 'pending' | 'active' | 'completed' | 'failed';
export type TaskLogEntryType = 'text' | 'tool_start' | 'tool_end' | 'phase_start' | 'phase_end' | 'error' | 'success' | 'info' | 'decision';

export interface TaskLogEntry {
  timestamp: string;
  type: TaskLogEntryType;
  content: string;
  phase: TaskLogPhase;
  tool_name?: string;
  tool_input?: string;
  subtask_id?: string;
  session?: number;
  // Fields for expandable detail view
  detail?: string;  // Full content that can be expanded (e.g., file contents, command output)
  subphase?: string;  // Subphase grouping (e.g., "PROJECT DISCOVERY", "CONTEXT GATHERING")
  collapsed?: boolean;  // Whether to show collapsed by default in UI
  // Decision data for decision log entries
  decision_data?: Record<string, unknown>;  // DecisionPoint data (imported separately to avoid circular deps)
}

export interface TaskPhaseLog {
  phase: TaskLogPhase;
  status: TaskLogPhaseStatus;
  started_at: string | null;
  completed_at: string | null;
  entries: TaskLogEntry[];
}

export interface TaskLogs {
  spec_id: string;
  created_at: string;
  updated_at: string;
  phases: {
    planning: TaskPhaseLog;
    coding: TaskPhaseLog;
    validation: TaskPhaseLog;
  };
}

// Streaming markers from Python (similar to InsightsStreamChunk)
export interface TaskLogStreamChunk {
  type: 'text' | 'tool_start' | 'tool_end' | 'phase_start' | 'phase_end' | 'error' | 'decision';
  content?: string;
  phase?: TaskLogPhase;
  timestamp?: string;
  tool?: {
    name: string;
    input?: string;
    success?: boolean;
  };
  subtask_id?: string;
  decision_data?: Record<string, unknown>;  // DecisionPoint data for decision entries
}

// Log filtering and search types
export interface LogFilterState {
  searchQuery: string;
  phases: TaskLogPhase[];  // Empty array = all phases
  entryTypes: TaskLogEntryType[];  // Empty array = all types
  tools: string[];  // Empty array = all tools (e.g., 'Read', 'Write', 'Bash')
  showToolOutput: boolean;  // Whether to show tool_start/tool_end entries
}

export interface LogSearchResult {
  phase: TaskLogPhase;
  entryIndex: number;
  matchType: 'content' | 'tool_name' | 'tool_input' | 'detail';
  matchText: string;  // The actual text that matched
}

export interface LogSearchState {
  query: string;
  results: LogSearchResult[];
  currentResultIndex: number;  // For navigating through results
  isSearching: boolean;
}

// Image attachment types for task creation
export interface ImageAttachment {
  id: string;           // Unique identifier (UUID)
  filename: string;     // Original filename
  mimeType: string;     // e.g., 'image/png'
  size: number;         // Size in bytes
  data?: string;        // Base64 data (for transport)
  path?: string;        // Relative path after storage
  thumbnail?: string;   // Base64 thumbnail for preview
}

// Referenced file types for task creation (files/folders from project)
export interface ReferencedFile {
  id: string;           // Unique identifier (UUID)
  path: string;         // Relative path from project root
  name: string;         // File or folder name
  isDirectory: boolean; // True if this is a directory
  addedAt: Date;        // When the file was added as reference
}

// Draft state for task creation (auto-saved when dialog closes)
export interface TaskDraft {
  projectId: string;
  title: string;
  description: string;
  category: TaskCategory | '';
  priority: TaskPriority | '';
  complexity: TaskComplexity | '';
  impact: TaskImpact | '';
  profileId?: string;  // Agent profile ID ('auto', 'complex', 'balanced', 'quick', 'custom')
  model: ModelType | '';
  thinkingLevel: ThinkingLevel | '';
  // Auto profile - per-phase configuration
  phaseModels?: PhaseModelConfig;
  phaseThinking?: PhaseThinkingConfig;
  images: ImageAttachment[];
  referencedFiles: ReferencedFile[];
  requireReviewBeforeCoding?: boolean;
  agentModels?: Record<string, string>;  // Agent-specific model overrides
  provider?: AIProvider;  // AI provider selection
  providerModel?: string;  // Provider-specific model ID
  customTemplateId?: string;  // Custom agent template ID
  savedAt: Date;
}

// Task metadata from ideation or manual entry
export type TaskComplexity = 'trivial' | 'small' | 'medium' | 'large' | 'complex';
export type TaskImpact = 'low' | 'medium' | 'high' | 'critical';
export type TaskPriority = 'low' | 'medium' | 'high' | 'urgent';
// Re-export ThinkingLevel (defined in settings.ts) for convenience
export type { ThinkingLevel };
export type ModelType = 'haiku' | 'sonnet' | 'opus';
export type TaskCategory =
  | 'feature'
  | 'bug_fix'
  | 'refactoring'
  | 'documentation'
  | 'security'
  | 'performance'
  | 'ui_ux'
  | 'infrastructure'
  | 'testing';

export interface TaskMetadata {
  // Origin tracking
  sourceType?: 'ideation' | 'manual' | 'imported' | 'insights' | 'roadmap' | 'linear' | 'github' | 'gitlab' | 'template';
  ideationType?: string;  // e.g., 'code_improvements', 'security_hardening'
  ideaId?: string;  // Reference to original idea if converted
  featureId?: string;  // Reference to roadmap feature if from roadmap
  linearIssueId?: string;  // Reference to Linear issue if from Linear
  linearIdentifier?: string;  // Linear issue identifier (e.g., 'ABC-123')
  linearUrl?: string;  // Linear issue URL
  githubIssueNumber?: number;  // Reference to GitHub issue number if from GitHub (single issue)
  githubIssueNumbers?: number[];  // Reference to multiple GitHub issues if from a batch
  githubUrl?: string;  // GitHub issue URL
  githubBatchTheme?: string;  // Theme/title of the GitHub issue batch
  gitlabIssueIid?: number;  // Reference to GitLab issue IID if from GitLab
  gitlabUrl?: string;  // GitLab issue URL
  templateName?: string;  // Template name if created from template
  customTemplateId?: string;  // Custom agent template ID if using custom template

  // Classification
  category?: TaskCategory;
  complexity?: TaskComplexity;
  impact?: TaskImpact;
  priority?: TaskPriority;

  // Context
  rationale?: string;  // Why this task matters
  problemSolved?: string;  // What problem this addresses
  targetAudience?: string;  // Who benefits

  // Technical details
  affectedFiles?: string[];  // Files likely to be modified
  dependencies?: string[];  // Other features/tasks this depends on
  acceptanceCriteria?: string[];  // What defines "done"

  // Effort estimation
  estimatedEffort?: TaskComplexity;

  // Type-specific metadata (from different idea types)
  securitySeverity?: 'low' | 'medium' | 'high' | 'critical';
  performanceCategory?: string;
  uiuxCategory?: string;
  codeQualitySeverity?: 'suggestion' | 'minor' | 'major' | 'critical';

  // Image attachments (screenshots, mockups, diagrams)
  attachedImages?: ImageAttachment[];

  // Referenced files (files/folders from project for context)
  referencedFiles?: ReferencedFile[];

  // Review settings
  requireReviewBeforeCoding?: boolean;  // Require human review of spec/plan before coding starts

  // Agent configuration (from agent profile or manual selection)
  model?: ModelType;  // Claude model to use (haiku, sonnet, opus) - used when not auto profile
  thinkingLevel?: ThinkingLevel;  // Thinking budget level (none, low, medium, high, ultrathink)
  // Auto profile - per-phase model configuration
  isAutoProfile?: boolean;  // True when using Auto (Optimized) profile
  phaseModels?: PhaseModelConfig;  // Per-phase model configuration
  phaseThinking?: PhaseThinkingConfig;  // Per-phase thinking configuration

  // Git/Worktree configuration
  baseBranch?: string;  // Override base branch for this task's worktree
  prUrl?: string;  // GitHub PR URL if task has been submitted as a PR
  useWorktree?: boolean;  // If false, use direct mode (no worktree isolation) - default is true for safety

  // Multi-model agent orchestration
  agentModels?: Record<string, string>;  // Agent-specific model overrides (e.g., { coder: 'haiku', planner: 'sonnet' })

  // Provider selection
  provider?: AIProvider;  // AI engine provider (claude, litellm, openrouter, zhipuai)
  providerModel?: string;  // Provider-specific model ID

  // Archive status
  archivedAt?: string;  // ISO date when task was archived
  archivedInVersion?: string;  // Version in which task was archived (from changelog)
}

export interface Task {
  id: string;
  specId: string;
  projectId: string;
  title: string;
  description: string;
  status: TaskStatus;
  reviewReason?: ReviewReason;  // Why task needs human review (only set when status is 'human_review')
  subtasks: Subtask[];
  qaReport?: QAReport;
  logs: string[];
  metadata?: TaskMetadata;  // Rich metadata from ideation or manual entry
  executionProgress?: ExecutionProgress;  // Real-time execution progress
  releasedInVersion?: string;  // Version in which this task was released
  stagedInMainProject?: boolean;  // True if changes were staged to main project (worktree merged with --no-commit)
  stagedAt?: string;  // ISO timestamp when changes were staged
  location?: 'main' | 'worktree';  // Where task was loaded from (main project or worktree)
  specsPath?: string;  // Full path to specs directory for this task
  tokenStats?: TaskTokenStats;  // Token usage statistics from token_stats.json
  createdAt: Date;
  updatedAt: Date;
}

// Implementation Plan (from auto-claude)
export interface ImplementationPlan {
  feature?: string;  // Some plans use 'feature', some use 'title'
  title?: string;    // Alternative to 'feature' for task name
  workflow_type: string;
  services_involved?: string[];
  phases: Phase[];
  final_acceptance: string[];
  created_at: string;
  updated_at: string;
  spec_file: string;
  // Added for UI status persistence
  status?: TaskStatus;
  planStatus?: string;
  recoveryNote?: string;
  description?: string;
}

export interface Phase {
  phase: number;
  name: string;
  type: string;
  subtasks: PlanSubtask[];
  depends_on?: number[];
}

export interface PlanSubtask {
  id: string;
  description: string;
  status: SubtaskStatus;
  verification?: {
    type: string;
    run?: string;
    scenario?: string;
  };
}

// Cost tracking types (from cost_tracking.py)
export interface UsageRecord {
  agent_type: string;
  model: string;
  input_tokens: number;
  output_tokens: number;
  cost: number;
  timestamp: string;
}

export interface CostReport {
  spec_dir: string;
  total_cost: number;
  records: UsageRecord[];
  last_updated: string;
}

// Workspace management types (for human review)
export interface WorktreeStatus {
  exists: boolean;
  worktreePath?: string;
  branch?: string;
  baseBranch?: string;
  currentProjectBranch?: string; // User's current checked-out branch in main project (merge target)
  commitCount?: number;
  filesChanged?: number;
  additions?: number;
  deletions?: number;
}

export interface WorktreeDiff {
  files: WorktreeDiffFile[];
  summary: string;
}

export interface WorktreeDiffFile {
  path: string;
  status: 'added' | 'modified' | 'deleted' | 'renamed';
  additions: number;
  deletions: number;
}

// Conflict severity levels from merge system
export type ConflictSeverity = 'none' | 'low' | 'medium' | 'high' | 'critical';

// Type of conflict
export type ConflictType = 'semantic' | 'git';

// Information about a detected conflict
export interface MergeConflict {
  file: string;
  location: string;
  tasks: string[];
  severity: ConflictSeverity;
  canAutoMerge: boolean;
  strategy?: string;
  reason: string;
  type?: ConflictType; // 'semantic' = parallel task conflict, 'git' = branch divergence
}

// Path-mapped file that needs AI merge due to rename
export interface PathMappedAIMerge {
  oldPath: string;
  newPath: string;
  reason: string;
}

// Git-level conflict information (branch divergence)
export interface GitConflictInfo {
  hasConflicts: boolean;
  conflictingFiles: string[];
  needsRebase: boolean;
  commitsBehind: number;
  baseBranch: string;
  specBranch: string;
  // Files that need AI merge due to path mappings (file renames)
  pathMappedAIMerges?: PathMappedAIMerge[];
  // Total number of file renames detected
  totalRenames?: number;
}

// Summary statistics from merge preview/execution
export interface MergeStats {
  totalFiles: number;
  conflictFiles: number;
  totalConflicts: number;
  autoMergeable: number;
  aiResolved?: number;
  humanRequired?: number;
  hasGitConflicts?: boolean; // True if there are git-level conflicts requiring rebase
  // Count of files needing AI merge due to path mappings (file renames)
  pathMappedAIMergeCount?: number;
}

export interface WorktreeMergeResult {
  success: boolean;
  message: string;
  merged?: boolean;
  conflictFiles?: string[];
  staged?: boolean;
  alreadyStaged?: boolean;
  projectPath?: string;
  // AI-generated commit message suggestion (for stage-only mode)
  suggestedCommitMessage?: string;
  // New conflict info from smart merge
  conflicts?: MergeConflict[];
  stats?: MergeStats;
  gitConflicts?: GitConflictInfo; // Git-level conflict info
  // Preview mode results
  preview?: {
    files: string[];
    conflicts: MergeConflict[];
    summary: MergeStats;
    gitConflicts?: GitConflictInfo;
    // Uncommitted changes in the main project that could block merge
    uncommittedChanges?: {
      hasChanges: boolean;
      files: string[];
      count: number;
    } | null;
  };
}

export interface WorktreeDiscardResult {
  success: boolean;
  message: string;
}

/**
 * Options for creating a PR from a worktree
 */
export interface WorktreeCreatePROptions {
  targetBranch?: string;
  title?: string;
  draft?: boolean;
}

/**
 * Result of creating a PR from a worktree
 */
export interface WorktreeCreatePRResult {
  success: boolean;
  prUrl?: string;
  error?: string;
  message?: string;  // Human-readable message for both success and error cases
  alreadyExists?: boolean;
}

/**
 * Information about a single spec worktree
 * Per-spec architecture: Each spec has its own worktree at .worktrees/{spec-name}/
 */
export interface WorktreeListItem {
  specName: string;
  path: string;
  branch: string;
  baseBranch: string;
  commitCount: number;
  filesChanged: number;
  additions: number;
  deletions: number;
}

/**
 * Result of listing all spec worktrees
 */
export interface WorktreeListResult {
  worktrees: WorktreeListItem[];
}

// Stuck task recovery types
export interface StuckTaskInfo {
  taskId: string;
  specId: string;
  title: string;
  status: TaskStatus;
  isActuallyRunning: boolean;
  lastUpdated: Date;
}

export interface TaskRecoveryResult {
  taskId: string;
  recovered: boolean;
  newStatus: TaskStatus;
  message: string;
  autoRestarted?: boolean;
}

export interface TaskRecoveryOptions {
  targetStatus?: TaskStatus;
  autoRestart?: boolean;
}

export interface TaskProgressUpdate {
  taskId: string;
  plan: ImplementationPlan;
  currentSubtask?: string;
}

export interface TaskStartOptions {
  parallel?: boolean;
  workers?: number;
  model?: string;
  baseBranch?: string; // Override base branch for worktree creation
}

// Token statistics types (mirrors Python core/token_stats.py)
export interface PhaseTokenStats {
  phase: 'planning' | 'coding' | 'validation';
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  session_count: number;
  updated_at: string;
}

export interface TaskTokenStats {
  phases: Record<string, PhaseTokenStats>;
  total_input_tokens: number;
  total_output_tokens: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

// Background task types (long-running commands)
export type BackgroundTaskStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';

export interface BackgroundTask {
  id: string;
  command: string;
  workingDir: string;
  status: BackgroundTaskStatus;
  createdAt: string;
  startedAt: string | null;
  completedAt: string | null;
  timeout: number;
  output: string;
  error: string | null;
  exitCode: number | null;
  pid: number | null;
  memoryStats?: {
    percent: number;
    availableMb: number;
    totalMb: number;
    usedMb: number;
  };
}

// ============================================================================
// Multi-User Spec Collaboration Types
// ============================================================================

export type PermissionLevel = 'read' | 'write' | 'admin';

export type ApprovalStatus = 'pending' | 'approved' | 'rejected';

export interface CollaborationUser {
  user_id: string;
  username: string;
  email?: string;
}

export interface SpecPermission {
  spec_id: string;
  user: CollaborationUser;
  level: PermissionLevel;
  granted_by: string;
  granted_at: string;
}

export interface Comment {
  comment_id: string;
  spec_id: string;
  author: CollaborationUser;
  content: string;
  created_at: string;
  parent_id?: string;
  mentions: string[];
  resolved: boolean;
  updated_at?: string;
}

export interface Approval {
  approval_id: string;
  spec_id: string;
  approver: CollaborationUser;
  status: ApprovalStatus;
  reason?: string;
  created_at: string;
  reviewed_at?: string;
}

export type NotificationType =
  | 'mention'
  | 'permission_granted'
  | 'permission_revoked'
  | 'approval_requested'
  | 'approval_approved'
  | 'approval_rejected'
  | 'spec_modified';

export type ChangeType =
  | 'comment_added'
  | 'comment_edited'
  | 'comment_resolved'
  | 'permission_granted'
  | 'permission_revoked'
  | 'approval_requested'
  | 'approval_approved'
  | 'approval_rejected'
  | 'spec_edited';

export interface Notification {
  notification_id: string;
  spec_id: string;
  notification_type: NotificationType;
  target_user: string;
  actor_user: string;
  created_at: string;
  read: boolean;
  metadata?: Record<string, unknown>;
}

export interface ChangeRecord {
  change_id: string;
  spec_id: string;
  change_type: ChangeType;
  actor_user: string;
  created_at: string;
  details?: Record<string, unknown>;
}
