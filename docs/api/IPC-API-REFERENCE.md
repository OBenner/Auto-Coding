# IPC API Reference

Complete reference for Auto Code's Electron IPC (Inter-Process Communication) API used for communication between the main process and renderer process in the desktop application.

## Overview

The IPC API enables the frontend (renderer process) to communicate with the backend (main process) in Electron. All IPC calls are typed and return `Promise<IPCResult<T>>` for invoke operations, while event-based APIs use callback registration patterns.

**Location:** `apps/frontend/src/preload/api/`

**IPC Channel Constants:** `apps/frontend/src/shared/constants/ipc.ts`

## API Modules

The IPC API is organized into the following modules:

| Module | Description |
|--------|-------------|
| **ProjectAPI** | Project management, initialization, settings, environment config |
| **TaskAPI** | Task creation, execution, workspace management, merge analytics |
| **TerminalAPI** | Terminal operations, Claude profile management, session management |
| **SettingsAPI** | App settings, CLI tools detection, version info |
| **FileAPI** | File explorer operations (read, write, list) |
| **AgentAPI** | Aggregates Roadmap, Ideation, Insights, Changelog, Linear, GitHub, GitLab, Shell, SessionContext, ProductivityAnalytics |
| **AppUpdateAPI** | Application auto-update management |
| **ProfileAPI** | API profile management (custom Anthropic-compatible endpoints) |
| **ScreenshotAPI** | Screenshot capture from screens/windows |
| **QueueAPI** | Queue routing for rate limit recovery |
| **SchedulerAPI** | Build scheduling and queue management |
| **PluginAPI** | Plugin management operations |
| **FeedbackAPI** | Feedback submission for adaptive learning |

---

## ProjectAPI

**File:** `apps/frontend/src/preload/api/project-api.ts`

Manages projects, initialization, environment configuration, and memory infrastructure.

### Project Management

#### `addProject(projectPath: string): Promise<IPCResult<Project>>`

Add a new project to the workspace.

**IPC Channel:** `project:add`

**Parameters:**
- `projectPath` - Absolute path to project directory

**Returns:** `IPCResult<Project>` with project details

**Example:**
```typescript
const result = await window.electron.addProject('/path/to/project');
if (result.success) {
  console.log('Project added:', result.data);
}
```

---

#### `removeProject(projectId: string): Promise<IPCResult>`

Remove a project from the workspace.

**IPC Channel:** `project:remove`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<void>`

---

#### `getProjects(): Promise<IPCResult<Project[]>>`

Get all projects in the workspace.

**IPC Channel:** `project:list`

**Returns:** `IPCResult<Project[]>` - Array of all projects

---

#### `updateProjectSettings(projectId: string, settings: Partial<ProjectSettings>): Promise<IPCResult>`

Update project settings.

**IPC Channel:** `project:updateSettings`

**Parameters:**
- `projectId` - Unique project identifier
- `settings` - Partial settings object to update

**Returns:** `IPCResult<void>`

---

#### `initializeProject(projectId: string): Promise<IPCResult<InitializationResult>>`

Initialize a project for Auto Code (creates .auto-claude directory).

**IPC Channel:** `project:initialize`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<InitializationResult>` with initialization status

---

#### `checkProjectVersion(projectId: string): Promise<IPCResult<AutoBuildVersionInfo>>`

Check project's Auto Code version.

**IPC Channel:** `project:checkVersion`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<AutoBuildVersionInfo>` with version information

---

### Tab State Management

#### `getTabState(): Promise<IPCResult<TabState>>`

Get persisted tab state (open projects, active project, order).

**IPC Channel:** `tabState:get`

**Returns:** `IPCResult<TabState>` with tab state

**TabState Interface:**
```typescript
interface TabState {
  openProjectIds: string[];
  activeProjectId: string | null;
  tabOrder: string[];
}
```

---

#### `saveTabState(tabState: TabState): Promise<IPCResult>`

Save tab state to persistent storage.

**IPC Channel:** `tabState:save`

**Parameters:**
- `tabState` - Tab state to persist

**Returns:** `IPCResult<void>`

---

### Context Operations

#### `getProjectContext(projectId: string): Promise<IPCResult<unknown>>`

Get project context (codebase analysis, dependencies, structure).

**IPC Channel:** `context:get`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<unknown>` with project context

---

#### `refreshProjectIndex(projectId: string): Promise<IPCResult<unknown>>`

Refresh project index (re-analyze codebase).

**IPC Channel:** `context:refreshIndex`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<void>`

---

#### `getMemoryStatus(projectId: string): Promise<IPCResult<unknown>>`

Get Graphiti memory system status.

**IPC Channel:** `context:memoryStatus`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<unknown>` with memory status

---

#### `searchMemories(projectId: string, query: string): Promise<IPCResult<unknown>>`

Search Graphiti memory for context.

**IPC Channel:** `context:searchMemories`

**Parameters:**
- `projectId` - Unique project identifier
- `query` - Search query

**Returns:** `IPCResult<unknown>` with search results

---

#### `getRecentMemories(projectId: string, limit?: number): Promise<IPCResult<unknown>>`

Get recent memories from Graphiti.

**IPC Channel:** `context:getMemories`

**Parameters:**
- `projectId` - Unique project identifier
- `limit` - Optional limit on number of memories

**Returns:** `IPCResult<unknown>` with recent memories

---

### Environment Configuration

#### `getProjectEnv(projectId: string): Promise<IPCResult<ProjectEnvConfig>>`

Get project environment configuration.

**IPC Channel:** `env:get`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<ProjectEnvConfig>`

---

#### `updateProjectEnv(projectId: string, config: Partial<ProjectEnvConfig>): Promise<IPCResult>`

Update project environment configuration.

**IPC Channel:** `env:update`

**Parameters:**
- `projectId` - Unique project identifier
- `config` - Partial environment config to update

**Returns:** `IPCResult<void>`

---

#### `checkClaudeAuth(projectId: string): Promise<IPCResult<ClaudeAuthResult>>`

Check Claude authentication status.

**IPC Channel:** `env:checkClaudeAuth`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<ClaudeAuthResult>` with auth status

---

#### `invokeClaudeSetup(projectId: string): Promise<IPCResult<ClaudeAuthResult>>`

Trigger Claude authentication setup flow.

**IPC Channel:** `env:invokeClaudeSetup`

**Parameters:**
- `projectId` - Unique project identifier

**Returns:** `IPCResult<ClaudeAuthResult>` with auth result

---

### Dialog Operations

#### `selectDirectory(): Promise<string | null>`

Open native directory selection dialog.

**IPC Channel:** `dialog:selectDirectory`

**Returns:** Selected directory path or null if cancelled

**Example:**
```typescript
const path = await window.electron.selectDirectory();
if (path) {
  console.log('Selected:', path);
}
```

---

#### `createProjectFolder(location: string, name: string, initGit: boolean): Promise<IPCResult<CreateProjectFolderResult>>`

Create a new project folder.

**IPC Channel:** `dialog:createProjectFolder`

**Parameters:**
- `location` - Parent directory path
- `name` - Project/folder name
- `initGit` - Whether to initialize git repository

**Returns:** `IPCResult<CreateProjectFolderResult>`

---

#### `getDefaultProjectLocation(): Promise<string | null>`

Get default project location from system settings.

**IPC Channel:** `dialog:getDefaultProjectLocation`

**Returns:** Default project path or null

---

### Memory Infrastructure (Graphiti)

#### `getMemoryInfrastructureStatus(dbPath?: string): Promise<IPCResult<InfrastructureStatus>>`

Get Graphiti memory infrastructure status (LadybugDB).

**IPC Channel:** `memory:status`

**Parameters:**
- `dbPath` - Optional database path

**Returns:** `IPCResult<InfrastructureStatus>`

---

#### `listMemoryDatabases(dbPath?: string): Promise<IPCResult<string[]>>`

List all Graphiti memory databases.

**IPC Channel:** `memory:listDatabases`

**Parameters:**
- `dbPath` - Optional database path

**Returns:** `IPCResult<string[]>` - Array of database names

---

#### `testMemoryConnection(dbPath?: string, database?: string): Promise<IPCResult<GraphitiValidationResult>>`

Test Graphiti memory connection.

**IPC Channel:** `memory:testConnection`

**Parameters:**
- `dbPath` - Optional database path
- `database` - Optional database name

**Returns:** `IPCResult<GraphitiValidationResult>`

---

#### `validateLLMApiKey(provider: string, apiKey: string): Promise<IPCResult<GraphitiValidationResult>>`

Validate LLM API key for Graphiti.

**IPC Channel:** `graphiti:validateLlm`

**Parameters:**
- `provider` - LLM provider (openai, anthropic, etc.)
- `apiKey` - API key to validate

**Returns:** `IPCResult<GraphitiValidationResult>`

---

#### `testGraphitiConnection(config: {dbPath?: string; database?: string; llmProvider: string; apiKey: string}): Promise<IPCResult<GraphitiConnectionTestResult>>`

Test full Graphiti connection (database + LLM).

**IPC Channel:** `graphiti:testConnection`

**Parameters:**
- `config.dbPath` - Optional database path
- `config.database` - Optional database name
- `config.llmProvider` - LLM provider
- `config.apiKey` - API key

**Returns:** `IPCResult<GraphitiConnectionTestResult>`

---

### Git Operations

#### `getGitBranches(projectPath: string): Promise<IPCResult<string[]>>`

Get all git branches in project.

**IPC Channel:** `git:getBranches`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<string[]>` - Array of branch names

---

#### `getCurrentGitBranch(projectPath: string): Promise<IPCResult<string | null>>`

Get current git branch.

**IPC Channel:** `git:getCurrentBranch`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<string | null>` - Current branch name

---

#### `detectMainBranch(projectPath: string): Promise<IPCResult<string | null>>`

Detect main branch name (main/master).

**IPC Channel:** `git:detectMainBranch`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<string | null>` - Main branch name

---

#### `checkGitStatus(projectPath: string): Promise<IPCResult<GitStatus>>`

Get git working tree status.

**IPC Channel:** `git:checkStatus`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<GitStatus>`

---

#### `initializeGit(projectPath: string): Promise<IPCResult<InitializationResult>>`

Initialize git repository.

**IPC Channel:** `git:initialize`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<InitializationResult>`

---

### Ollama Model Management

#### `checkOllamaStatus(baseUrl?: string): Promise<IPCResult<{running: boolean; url: string; version?: string; message?: string}>>`

Check if Ollama server is running.

**IPC Channel:** `ollama:checkStatus`

**Parameters:**
- `baseUrl` - Optional Ollama server URL (default: http://localhost:11434)

**Returns:** `IPCResult<{running: boolean; url: string; version?: string; message?: string}>`

---

#### `checkOllamaInstalled(): Promise<IPCResult<{installed: boolean; path?: string; version?: string}>>`

Check if Ollama is installed.

**IPC Channel:** `ollama:checkInstalled`

**Returns:** `IPCResult<{installed: boolean; path?: string; version?: string}>`

---

#### `installOllama(): Promise<IPCResult<{command: string}>>`

Install Ollama (platform-specific).

**IPC Channel:** `ollama:install`

**Returns:** `IPCResult<{command: string}>` - Installation command

---

#### `listOllamaModels(baseUrl?: string): Promise<IPCResult<{models: Array<{name: string; size_bytes: number; size_gb: number; modified_at: string; is_embedding: boolean; embedding_dim?: number | null; description?: string}>; count: number}>>`

List all Ollama models.

**IPC Channel:** `ollama:listModels`

**Parameters:**
- `baseUrl` - Optional Ollama server URL

**Returns:** `IPCResult<{models: ModelInfo[]; count: number}>`

---

#### `listOllamaEmbeddingModels(baseUrl?: string): Promise<IPCResult<{embedding_models: Array<{name: string; embedding_dim: number | null; description: string; size_bytes: number; size_gb: number}>; count: number}>>`

List Ollama embedding models.

**IPC Channel:** `ollama:listEmbeddingModels`

**Parameters:**
- `baseUrl` - Optional Ollama server URL

**Returns:** `IPCResult<{embedding_models: EmbeddingModel[]; count: number}>`

---

#### `pullOllamaModel(modelName: string, baseUrl?: string): Promise<IPCResult<{model: string; status: 'completed' | 'failed'; output: string[]}>>`

Pull/download Ollama model.

**IPC Channel:** `ollama:pullModel`

**Parameters:**
- `modelName` - Model name to pull
- `baseUrl` - Optional Ollama server URL

**Returns:** `IPCResult<{model: string; status: string; output: string[]}>`

**Event:** Listen to `ollama:pullProgress` for download progress

---

---

## TaskAPI

**File:** `apps/frontend/src/preload/api/task-api.ts`

Manages task creation, execution, workspace operations, and merge analytics.

### Task Operations

#### `getTasks(projectId: string, options?: {forceRefresh?: boolean}): Promise<IPCResult<Task[]>>`

Get all tasks for a project.

**IPC Channel:** `task:list`

**Parameters:**
- `projectId` - Project identifier
- `options.forceRefresh` - Force refresh from backend

**Returns:** `IPCResult<Task[]>` - Array of tasks

---

#### `createTask(projectId: string, title: string, description: string, metadata?: TaskMetadata): Promise<IPCResult<Task>>`

Create a new task.

**IPC Channel:** `task:create`

**Parameters:**
- `projectId` - Project identifier
- `title` - Task title
- `description` - Task description
- `metadata` - Optional task metadata

**Returns:** `IPCResult<Task>` - Created task

---

#### `createTaskFromTemplate(projectId: string, templateName: string, parameters: Record<string, unknown>): Promise<IPCResult<Task>>`

Create task from template.

**IPC Channel:** `task:createFromTemplate`

**Parameters:**
- `projectId` - Project identifier
- `templateName` - Template name
- `parameters` - Template parameters

**Returns:** `IPCResult<Task>` - Created task

---

#### `deleteTask(taskId: string): Promise<IPCResult>`

Delete a task.

**IPC Channel:** `task:delete`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<void>`

---

#### `updateTask(taskId: string, updates: {title?: string; description?: string}): Promise<IPCResult<Task>>`

Update task details.

**IPC Channel:** `task:update`

**Parameters:**
- `taskId` - Task identifier
- `updates.title` - Optional new title
- `updates.description` - Optional new description

**Returns:** `IPCResult<Task>` - Updated task

---

#### `startTask(taskId: string, options?: TaskStartOptions): void`

Start task execution (fire-and-forget, no return value).

**IPC Channel:** `task:start` (send, not invoke)

**Parameters:**
- `taskId` - Task identifier
- `options` - Optional start options (model, max_iterations, etc.)

**Event:** Listen to task events for progress updates

**Example:**
```typescript
window.electron.startTask(taskId, { model: 'claude-sonnet-4-5-20250929' });
```

---

#### `stopTask(taskId: string): void`

Stop running task.

**IPC Channel:** `task:stop` (send, not invoke)

**Parameters:**
- `taskId` - Task identifier

---

#### `submitReview(taskId: string, approved: boolean, feedback?: string, images?: ImageAttachment[]): Promise<IPCResult>`

Submit task review (approve/reject).

**IPC Channel:** `task:review`

**Parameters:**
- `taskId` - Task identifier
- `approved` - Approval status
- `feedback` - Optional feedback text
- `images` - Optional screenshot attachments

**Returns:** `IPCResult<void>`

---

#### `updateTaskStatus(taskId: string, status: TaskStatus, options?: {forceCleanup?: boolean}): Promise<IPCResult & {worktreeExists?: boolean; worktreePath?: string}>`

Update task status.

**IPC Channel:** `task:updateStatus`

**Parameters:**
- `taskId` - Task identifier
- `status` - New task status
- `options.forceCleanup` - Force cleanup of worktree

**Returns:** `IPCResult<{worktreeExists?: boolean; worktreePath?: string}>`

---

#### `recoverStuckTask(taskId: string, options?: TaskRecoveryOptions): Promise<IPCResult<TaskRecoveryResult>>`

Recover stuck/failed task.

**IPC Channel:** `task:recoverStuck`

**Parameters:**
- `taskId` - Task identifier
- `options` - Recovery options (force, cleanup, retry)

**Returns:** `IPCResult<TaskRecoveryResult>`

---

#### `checkTaskRunning(taskId: string): Promise<IPCResult<boolean>>`

Check if task is currently running.

**IPC Channel:** `task:checkRunning`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<boolean>` - Running status

---

### Workspace Management

#### `getWorktreeStatus(taskId: string): Promise<IPCResult<WorktreeStatus>>`

Get worktree status for task.

**IPC Channel:** `task:worktreeStatus`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<WorktreeStatus>`

**WorktreeStatus Interface:**
```typescript
interface WorktreeStatus {
  exists: boolean;
  branch: string | null;
  commit: string | null;
  ahead: number;
  behind: number;
  conflicted: number;
  staged: number;
  modified: number;
  untracked: number;
}
```

---

#### `getWorktreeDiff(taskId: string): Promise<IPCResult<WorktreeDiff>>`

Get worktree diff (changes made in worktree).

**IPC Channel:** `task:worktreeDiff`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<WorktreeDiff>`

---

#### `mergeWorktree(taskId: string, options?: {noCommit?: boolean}): Promise<IPCResult<WorktreeMergeResult>>`

Merge worktree changes into main branch.

**IPC Channel:** `task:worktreeMerge`

**Parameters:**
- `taskId` - Task identifier
- `options.noCommit` - Stage changes without committing

**Returns:** `IPCResult<WorktreeMergeResult>`

---

#### `mergeWorktreePreview(taskId: string): Promise<IPCResult<WorktreeMergeResult>>`

Preview merge conflicts before merging.

**IPC Channel:** `task:worktreeMergePreview`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<WorktreeMergeResult>`

---

#### `discardWorktree(taskId: string, skipStatusChange?: boolean): Promise<IPCResult<WorktreeDiscardResult>>`

Discard worktree changes.

**IPC Channel:** `task:worktreeDiscard`

**Parameters:**
- `taskId` - Task identifier
- `skipStatusChange` - Skip updating task status

**Returns:** `IPCResult<WorktreeDiscardResult>`

---

#### `clearStagedState(taskId: string): Promise<IPCResult<{cleared: boolean}>>`

Clear staged state (after failed merge).

**IPC Channel:** `task:clearStagedState`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<{cleared: boolean}>`

---

#### `listWorktrees(projectId: string): Promise<IPCResult<WorktreeListResult>>`

List all worktrees for project.

**IPC Channel:** `task:listWorktrees`

**Parameters:**
- `projectId` - Project identifier

**Returns:** `IPCResult<WorktreeListResult>`

---

#### `worktreeOpenInIDE(worktreePath: string, ide: SupportedIDE, customPath?: string): Promise<IPCResult<{opened: boolean}>>`

Open worktree in IDE.

**IPC Channel:** `task:worktreeOpenInIDE`

**Parameters:**
- `worktreePath` - Path to worktree
- `ide` - IDE identifier (vscode, cursor, windsurf, etc.)
- `customPath` - Optional custom IDE path

**Returns:** `IPCResult<{opened: boolean}>`

---

#### `worktreeOpenInTerminal(worktreePath: string, terminal: SupportedTerminal, customPath?: string): Promise<IPCResult<{opened: boolean}>>`

Open worktree in terminal.

**IPC Channel:** `task:worktreeOpenInTerminal`

**Parameters:**
- `worktreePath` - Path to worktree
- `terminal` - Terminal identifier (iterm2, terminal, windows-terminal, etc.)
- `customPath` - Optional custom terminal path

**Returns:** `IPCResult<{opened: boolean}>`

---

#### `worktreeDetectTools(): Promise<IPCResult<{ides: Array<{id: string; name: string; path: string; installed: boolean}>; terminals: Array<{id: string; name: string; path: string; installed: boolean}>}>>`

Detect installed IDEs and terminals.

**IPC Channel:** `task:worktreeDetectTools`

**Returns:** `IPCResult<{ides: ToolInfo[]; terminals: ToolInfo[]}>`

---

#### `archiveTasks(projectId: string, taskIds: string[], version?: string): Promise<IPCResult<boolean>>`

Archive completed tasks.

**IPC Channel:** `task:archive`

**Parameters:**
- `projectId` - Project identifier
- `taskIds` - Array of task IDs to archive
- `version` - Optional version label

**Returns:** `IPCResult<boolean>`

---

#### `unarchiveTasks(projectId: string, taskIds: string[]): Promise<IPCResult<boolean>>`

Unarchive tasks.

**IPC Channel:** `task:unarchive`

**Parameters:**
- `projectId` - Project identifier
- `taskIds` - Array of task IDs to unarchive

**Returns:** `IPCResult<boolean>`

---

#### `createWorktreePR(taskId: string, options?: WorktreeCreatePROptions): Promise<IPCResult<WorktreeCreatePRResult>>`

Create pull request from worktree.

**IPC Channel:** `task:worktreeCreatePR`

**Parameters:**
- `taskId` - Task identifier
- `options` - Optional PR options (title, body, draft, etc.)

**Returns:** `IPCResult<WorktreeCreatePRResult>`

---

#### `batchRunQA(taskId: string): Promise<IPCResult<{success: boolean; issues?: Array<{message: string; file?: string}>}>>`

Run QA validation on multiple issues in batch.

**IPC Channel:** `task:batchRunQA`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<{success: boolean; issues?: Issue[]}>`

---

### Task Event Listeners

#### `onTaskProgress(callback: (taskId: string, plan: ImplementationPlan, projectId?: string) => void): () => void`

Listen to task progress updates.

**IPC Channel:** `task:progress` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `plan` - Implementation plan with progress
- `projectId` - Optional project identifier

**Returns:** Cleanup function to unregister listener

**Example:**
```typescript
const cleanup = window.electron.onTaskProgress((taskId, plan, projectId) => {
  console.log(`Task ${taskId} progress:`, plan);
});

// Later: cleanup();
```

---

#### `onTaskError(callback: (taskId: string, error: string, projectId?: string) => void): () => void`

Listen to task errors.

**IPC Channel:** `task:error` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `error` - Error message
- `projectId` - Optional project identifier

**Returns:** Cleanup function

---

#### `onTaskLog(callback: (taskId: string, log: string, projectId?: string) => void): () => void`

Listen to task log output.

**IPC Channel:** `task:log` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `log` - Log line
- `projectId` - Optional project identifier

**Returns:** Cleanup function

---

#### `onTaskStatusChange(callback: (taskId: string, status: TaskStatus, projectId?: string) => void): () => void`

Listen to task status changes.

**IPC Channel:** `task:statusChange` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `status` - New task status
- `projectId` - Optional project identifier

**Returns:** Cleanup function

---

#### `onTaskExecutionProgress(callback: (taskId: string, progress: ExecutionProgress, projectId?: string) => void): () => void`

Listen to task execution progress.

**IPC Channel:** `task:executionProgress` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `progress` - Execution progress details
- `projectId` - Optional project identifier

**Returns:** Cleanup function

---

### Task Phase Logs

#### `getTaskLogs(projectId: string, specId: string): Promise<IPCResult<TaskLogs | null>>`

Get phase logs for a task.

**IPC Channel:** `task:logsGet`

**Parameters:**
- `projectId` - Project identifier
- `specId` - Spec identifier

**Returns:** `IPCResult<TaskLogs | null>`

---

#### `watchTaskLogs(projectId: string, specId: string): Promise<IPCResult>`

Start watching for log changes.

**IPC Channel:** `task:logsWatch`

**Parameters:**
- `projectId` - Project identifier
- `specId` - Spec identifier

**Returns:** `IPCResult<void>`

---

#### `unwatchTaskLogs(specId: string): Promise<IPCResult>`

Stop watching for log changes.

**IPC Channel:** `task:logsUnwatch`

**Parameters:**
- `specId` - Spec identifier

**Returns:** `IPCResult<void>`

---

#### `onTaskLogsChanged(callback: (specId: string, logs: TaskLogs) => void): () => void`

Listen to log file changes.

**IPC Channel:** `task:logsChanged` (event from main)

**Callback Parameters:**
- `specId` - Spec identifier
- `logs` - Updated task logs

**Returns:** Cleanup function

---

#### `onTaskLogsStream(callback: (specId: string, chunk: TaskLogStreamChunk) => void): () => void`

Listen to streaming log chunks.

**IPC Channel:** `task:logsStream` (event from main)

**Callback Parameters:**
- `specId` - Spec identifier
- `chunk` - Log chunk (phase, log, timestamp)

**Returns:** Cleanup function

---

### Task Token Statistics

#### `getTokenStats(projectPath: string, specId: string): Promise<IPCResult<TaskTokenStats | null>>`

Get token usage statistics for a task.

**IPC Channel:** `task:tokenStats:get`

**Parameters:**
- `projectPath` - Path to project
- `specId` - Spec identifier

**Returns:** `IPCResult<TaskTokenStats | null>`

---

### Merge Analytics

#### `getMergeHistory(projectId: string, filter?: MergeAnalyticsFilter): Promise<IPCResult<MergeOperationRecord[]>>`

Get merge operation history.

**IPC Channel:** `mergeAnalytics:getHistory`

**Parameters:**
- `projectId` - Project identifier
- `filter` - Optional filter (date range, branch, status)

**Returns:** `IPCResult<MergeOperationRecord[]>`

---

#### `getMergeSummary(projectId: string, filter?: MergeAnalyticsFilter): Promise<IPCResult<MergeAnalytics>>`

Get merge analytics summary.

**IPC Channel:** `mergeAnalytics:getSummary`

**Parameters:**
- `projectId` - Project identifier
- `filter` - Optional filter

**Returns:** `IPCResult<MergeAnalytics>`

---

#### `getConflictPatterns(projectId: string, limit?: number): Promise<IPCResult<ConflictPattern[]>>`

Get recurring conflict patterns.

**IPC Channel:** `mergeAnalytics:getPatterns`

**Parameters:**
- `projectId` - Project identifier
- `limit` - Optional limit on number of patterns

**Returns:** `IPCResult<ConflictPattern[]>`

---

#### `exportMergeAnalytics(projectId: string, options: MergeAnalyticsExportOptions): Promise<IPCResult<{path: string}>>`

Export merge analytics to file.

**IPC Channel:** `mergeAnalytics:export`

**Parameters:**
- `projectId` - Project identifier
- `options` - Export options (format, date range)

**Returns:** `IPCResult<{path: string}>` - Exported file path

---

---

## TerminalAPI

**File:** `apps/frontend/src/preload/api/terminal-api.ts`

Manages terminal instances, Claude profiles, session management, and worktree operations.

### Terminal Operations

#### `createTerminal(options: TerminalCreateOptions): Promise<IPCResult>`

Create new terminal instance.

**IPC Channel:** `terminal:create`

**Parameters:**
```typescript
interface TerminalCreateOptions {
  cwd?: string;
  shell?: string;
  profileId?: string;
  sessionId?: string;
  displayOrder?: number;
  rows?: number;
  cols?: number;
}
```

**Returns:** `IPCResult<{id: string}>` - Terminal ID

---

#### `destroyTerminal(id: string): Promise<IPCResult>`

Destroy terminal instance.

**IPC Channel:** `terminal:destroy`

**Parameters:**
- `id` - Terminal identifier

**Returns:** `IPCResult<void>`

---

#### `sendTerminalInput(id: string, data: string): void`

Send input to terminal (fire-and-forget).

**IPC Channel:** `terminal:input` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier
- `data` - Input data to send

---

#### `resizeTerminal(id: string, cols: number, rows: number): void`

Resize terminal.

**IPC Channel:** `terminal:resize` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier
- `cols` - Number of columns
- `rows` - Number of rows

---

#### `invokeClaudeInTerminal(id: string, cwd?: string): void`

Start Claude Code in terminal.

**IPC Channel:** `terminal:invokeClaude` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier
- `cwd` - Optional working directory

---

#### `generateTerminalName(command: string, cwd?: string): Promise<IPCResult<string>>`

Generate descriptive terminal name from command.

**IPC Channel:** `terminal:generateName`

**Parameters:**
- `command` - Command string
- `cwd` - Optional working directory

**Returns:** `IPCResult<string>` - Generated name

---

#### `setTerminalTitle(id: string, title: string): void`

Set terminal title (user override).

**IPC Channel:** `terminal:setTitle` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier
- `title` - Custom title

---

#### `setTerminalWorktreeConfig(id: string, config: TerminalWorktreeConfig | undefined): void`

Associate terminal with worktree.

**IPC Channel:** `terminal:setWorktreeConfig` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier
- `config` - Worktree config or undefined to clear

---

### Terminal Session Management

#### `getTerminalSessions(projectPath: string): Promise<IPCResult<TerminalSession[]>>`

Get saved terminal sessions for project.

**IPC Channel:** `terminal:getSessions`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<TerminalSession[]>`

---

#### `restoreTerminalSession(session: TerminalSession, cols?: number, rows?: number): Promise<IPCResult<TerminalRestoreResult>>`

Restore terminal session.

**IPC Channel:** `terminal:restoreSession`

**Parameters:**
- `session` - Session to restore
- `cols` - Optional columns
- `rows` - Optional rows

**Returns:** `IPCResult<TerminalRestoreResult>`

---

#### `clearTerminalSessions(projectPath: string): Promise<IPCResult>`

Clear all saved sessions.

**IPC Channel:** `terminal:clearSessions`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<void>`

---

#### `resumeClaudeInTerminal(id: string, sessionId?: string): void`

Resume Claude session in terminal.

**IPC Channel:** `terminal:resumeClaude` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier
- `sessionId` - Optional session ID

---

#### `activateDeferredClaudeResume(id: string): void`

Activate deferred Claude resume when terminal becomes active.

**IPC Channel:** `terminal:activateDeferredResume` (send, not invoke)

**Parameters:**
- `id` - Terminal identifier

---

#### `getTerminalSessionDates(projectPath?: string): Promise<IPCResult<SessionDateInfo[]>>`

Get available session dates.

**IPC Channel:** `terminal:getSessionDates`

**Parameters:**
- `projectPath` - Optional path to project

**Returns:** `IPCResult<SessionDateInfo[]>`

---

#### `getTerminalSessionsForDate(date: string, projectPath: string): Promise<IPCResult<TerminalSession[]>>`

Get sessions for specific date.

**IPC Channel:** `terminal:getSessionsForDate`

**Parameters:**
- `date` - Date string (YYYY-MM-DD)
- `projectPath` - Path to project

**Returns:** `IPCResult<TerminalSession[]>`

---

#### `restoreTerminalSessionsFromDate(date: string, projectPath: string, cols?: number, rows?: number): Promise<IPCResult<SessionDateRestoreResult>>`

Restore all sessions from date.

**IPC Channel:** `terminal:restoreFromDate`

**Parameters:**
- `date` - Date string (YYYY-MM-DD)
- `projectPath` - Path to project
- `cols` - Optional columns
- `rows` - Optional rows

**Returns:** `IPCResult<SessionDateRestoreResult>`

---

#### `checkTerminalPtyAlive(terminalId: string): Promise<IPCResult<{alive: boolean}>>`

Check if terminal PTY is still alive.

**IPC Channel:** `terminal:checkPtyAlive`

**Parameters:**
- `terminalId` - Terminal identifier

**Returns:** `IPCResult<{alive: boolean}>`

---

#### `updateTerminalDisplayOrders(projectPath: string, orders: Array<{terminalId: string; displayOrder: number}>): Promise<IPCResult>`

Update terminal display order after drag-drop.

**IPC Channel:** `terminal:updateDisplayOrders`

**Parameters:**
- `projectPath` - Path to project
- `orders` - Array of terminal ID + display order pairs

**Returns:** `IPCResult<void>`

---

### Terminal Worktree Operations

#### `createTerminalWorktree(request: CreateTerminalWorktreeRequest): Promise<TerminalWorktreeResult>`

Create isolated worktree for terminal.

**IPC Channel:** `terminal:worktreeCreate`

**Parameters:**
```typescript
interface CreateTerminalWorktreeRequest {
  projectPath: string;
  worktreeName: string;
  branchName: string;
  fromBranch?: string;
}
```

**Returns:** `TerminalWorktreeResult`

---

#### `listTerminalWorktrees(projectPath: string): Promise<IPCResult<TerminalWorktreeConfig[]>>`

List all terminal worktrees.

**IPC Channel:** `terminal:worktreeList`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<TerminalWorktreeConfig[]>`

---

#### `removeTerminalWorktree(projectPath: string, name: string, deleteBranch?: boolean): Promise<IPCResult>`

Remove terminal worktree.

**IPC Channel:** `terminal:worktreeRemove`

**Parameters:**
- `projectPath` - Path to project
- `name` - Worktree name
- `deleteBranch` - Whether to delete branch

**Returns:** `IPCResult<void>`

---

#### `listOtherWorktrees(projectPath: string): Promise<IPCResult<OtherWorktreeInfo[]>>`

List worktrees created by other means (not terminal).

**IPC Channel:** `terminal:worktreeListOther`

**Parameters:**
- `projectPath` - Path to project

**Returns:** `IPCResult<OtherWorktreeInfo[]>`

---

### Terminal Event Listeners

#### `onTerminalOutput(callback: (id: string, data: string) => void): () => void`

Listen to terminal output.

**IPC Channel:** `terminal:output` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `data` - Output data

**Returns:** Cleanup function

---

#### `onTerminalExit(callback: (id: string, exitCode: number) => void): () => void`

Listen to terminal exit.

**IPC Channel:** `terminal:exit` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `exitCode` - Exit code

**Returns:** Cleanup function

---

#### `onTerminalTitleChange(callback: (id: string, title: string) => void): () => void`

Listen to terminal title changes.

**IPC Channel:** `terminal:titleChange` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `title` - New title

**Returns:** Cleanup function

---

#### `onTerminalWorktreeConfigChange(callback: (id: string, config: TerminalWorktreeConfig | undefined) => void): () => void`

Listen to worktree config changes.

**IPC Channel:** `terminal:worktreeConfigChange` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `config` - Worktree config or undefined

**Returns:** Cleanup function

---

#### `onTerminalClaudeSession(callback: (id: string, sessionId: string) => void): () => void`

Listen to Claude session capture.

**IPC Channel:** `terminal:claudeSession` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `sessionId` - Captured session ID

**Returns:** Cleanup function

---

#### `onTerminalRateLimit(callback: (info: RateLimitInfo) => void): () => void`

Listen to rate limit events.

**IPC Channel:** `terminal:rateLimit` (event from main)

**Callback Parameters:**
```typescript
interface RateLimitInfo {
  terminalId: string;
  profileId: string;
  profileName: string;
  limit: number;
  remaining: number;
  resetAt: string;
}
```

**Returns:** Cleanup function

---

#### `onTerminalOAuthToken(callback: (info: {terminalId: string; profileId?: string; email?: string; success: boolean; message?: string; detectedAt: string; needsOnboarding?: boolean}) => void): () => void`

Listen to OAuth token capture events.

**IPC Channel:** `terminal:oauthToken` (event from main)

**Callback Parameters:**
- `terminalId` - Terminal identifier
- `profileId` - Profile identifier
- `email` - Email from token
- `success` - Success status
- `message` - Optional message
- `detectedAt` - Detection timestamp
- `needsOnboarding` - Whether onboarding needed

**Returns:** Cleanup function

---

#### `onTerminalAuthCreated(callback: (info: {terminalId: string; profileId: string; profileName: string}) => void): () => void`

Listen to auth terminal creation events.

**IPC Channel:** `terminal:authCreated` (event from main)

**Callback Parameters:**
- `terminalId` - Terminal identifier
- `profileId` - Profile identifier
- `profileName` - Profile name

**Returns:** Cleanup function

---

#### `onTerminalOAuthCodeNeeded(callback: (info: {terminalId: string; profileId: string; profileName: string}) => void): () => void`

Listen for OAuth code request events.

**IPC Channel:** `terminal:oauthCodeNeeded` (event from main)

**Callback Parameters:**
- `terminalId` - Terminal identifier
- `profileId` - Profile identifier
- `profileName` - Profile name

**Returns:** Cleanup function

---

#### `submitOAuthCode(terminalId: string, code: string): Promise<IPCResult>`

Submit OAuth code to terminal.

**IPC Channel:** `terminal:oauthCodeSubmit`

**Parameters:**
- `terminalId` - Terminal identifier
- `code` - OAuth code from browser

**Returns:** `IPCResult<void>`

---

#### `onTerminalClaudeBusy(callback: (id: string, isBusy: boolean) => void): () => void`

Listen to Claude busy state changes.

**IPC Channel:** `terminal:claudeBusy` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `isBusy` - Busy status

**Returns:** Cleanup function

---

#### `onTerminalClaudeExit(callback: (id: string) => void): () => void`

Listen to Claude exit events.

**IPC Channel:** `terminal:claudeExit` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier

**Returns:** Cleanup function

---

#### `onTerminalOnboardingComplete(callback: (info: {terminalId: string; profileId?: string; detectedAt: string}) => void): () => void`

Listen to onboarding completion events.

**IPC Channel:** `terminal:onboardingComplete` (event from main)

**Callback Parameters:**
- `terminalId` - Terminal identifier
- `profileId` - Profile identifier
- `detectedAt` - Detection timestamp

**Returns:** Cleanup function

---

#### `onTerminalPendingResume(callback: (id: string, sessionId?: string) => void): () => void`

Listen to pending resume events.

**IPC Channel:** `terminal:pendingResume` (event from main)

**Callback Parameters:**
- `id` - Terminal identifier
- `sessionId` - Optional session ID

**Returns:** Cleanup function

---

#### `onTerminalProfileChanged(callback: (event: TerminalProfileChangedEvent) => void): () => void`

Listen to profile change events.

**IPC Channel:** `terminal:profileChanged` (event from main)

**Callback Parameters:**
```typescript
interface TerminalProfileChangedEvent {
  type: 'swapped' | 'deleted' | 'renamed';
  fromProfile?: {id: string; name: string};
  toProfile?: {id: string; name: string};
  reason: string;
}
```

**Returns:** Cleanup function

---

### Claude Profile Management

#### `getClaudeProfiles(): Promise<IPCResult<ClaudeProfile[]>>`

Get all Claude profiles.

**IPC Channel:** `claude:profilesGet`

**Returns:** `IPCResult<ClaudeProfile[]>`

---

#### `saveClaudeProfile(profile: ClaudeProfileSettings): Promise<IPCResult<ClaudeProfile>>`

Save or update Claude profile.

**IPC Channel:** `claude:profileSave`

**Parameters:**
```typescript
interface ClaudeProfileSettings {
  id?: string;
  name: string;
  oauthToken?: string;
  isDefault?: boolean;
}
```

**Returns:** `IPCResult<ClaudeProfile>`

---

#### `deleteClaudeProfile(profileId: string): Promise<IPCResult>`

Delete Claude profile.

**IPC Channel:** `claude:profileDelete`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `renameClaudeProfile(profileId: string, newName: string): Promise<IPCResult>`

Rename Claude profile.

**IPC Channel:** `claude:profileRename`

**Parameters:**
- `profileId` - Profile identifier
- `newName` - New profile name

**Returns:** `IPCResult<void>`

---

#### `setActiveClaudeProfile(profileId: string): Promise<IPCResult>`

Set active Claude profile.

**IPC Channel:** `claude:profileSetActive`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `switchClaudeProfile(profileId: string): Promise<IPCResult>`

Switch Claude profile (updates all terminals).

**IPC Channel:** `claude:profileSwitch`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `initializeClaudeProfile(profileId: string): Promise<IPCResult>`

Initialize Claude profile (check auth, fetch usage).

**IPC Channel:** `claude:profileInitialize`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `setClaudeProfileToken(profileId: string, token: string): Promise<IPCResult>`

Set OAuth token for profile.

**IPC Channel:** `claude:profileSetToken`

**Parameters:**
- `profileId` - Profile identifier
- `token` - OAuth token

**Returns:** `IPCResult<void>`

---

#### `authenticateClaudeProfile(profileId: string): Promise<IPCResult>`

Open visible terminal for OAuth authentication.

**IPC Channel:** `claude:profileAuthenticate`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `verifyClaudeProfileAuth(profileId: string): Promise<IPCResult<{authenticated: boolean; email?: string}>>`

Verify profile authentication status.

**IPC Channel:** `claude:profileVerifyAuth`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<{authenticated: boolean; email?: string}>`

---

#### `setClaudeAutoSwitchSettings(settings: {enabled: boolean; thresholdPercent?: number}): Promise<IPCResult>`

Configure automatic profile switching.

**IPC Channel:** `claude:autoSwitchSettings`

**Parameters:**
```typescript
{
  enabled: boolean;  // Enable/disable auto-switching
  thresholdPercent?: number;  // Threshold percentage (default: 80)
}
```

**Returns:** `IPCResult<void>`

---

#### `updateClaudeAutoSwitch(profileId: string, enabled: boolean): Promise<IPCResult>`

Update auto-switch for specific profile.

**IPC Channel:** `claude:updateAutoSwitch`

**Parameters:**
- `profileId` - Profile identifier
- `enabled` - Enable/disable for this profile

**Returns:** `IPCResult<void>`

---

#### `fetchClaudeUsage(profileId?: string): Promise<IPCResult<ClaudeUsageSnapshot>>`

Fetch usage snapshot for profile.

**IPC Channel:** `claude:profileFetchUsage`

**Parameters:**
- `profileId` - Optional profile identifier (default: active profile)

**Returns:** `IPCResult<ClaudeUsageSnapshot>`

---

#### `getBestClaudeProfile(): Promise<IPCResult<ClaudeProfile | null>>`

Get best available profile based on usage.

**IPC Channel:** `claude:getBestProfile`

**Returns:** `IPCResult<ClaudeProfile | null>`

---

### Account Priority Management

#### `getAccountPriority(): Promise<IPCResult<string[]>>`

Get account priority order (OAuth + API profiles).

**IPC Channel:** `account:priorityGet`

**Returns:** `IPCResult<string[]>` - Array of profile IDs in priority order

---

#### `setAccountPriority(priority: string[]): Promise<IPCResult>`

Set account priority order.

**IPC Channel:** `account:prioritySet`

**Parameters:**
- `priority` - Array of profile IDs in priority order

**Returns:** `IPCResult<void>`

---

### Usage Monitoring Events

#### `onUsageUpdated(callback: (profileId: string, usage: ClaudeUsageSnapshot) => void): () => void`

Listen to usage data updates.

**IPC Channel:** `claude:usageUpdated` (event from main)

**Callback Parameters:**
- `profileId` - Profile identifier
- `usage` - Usage snapshot

**Returns:** Cleanup function

---

#### `requestUsage(): void`

Request current usage snapshot.

**IPC Channel:** `claude:usageRequest` (send, not invoke)

---

#### `requestAllProfilesUsage(): void`

Request all profiles usage immediately.

**IPC Channel:** `claude:allProfilesUsageRequest` (send, not invoke)

---

#### `onAllProfilesUsageUpdated(callback: (profiles: Array<{profileId: string; usage: ClaudeUsageSnapshot}>) => void): () => void`

Listen to all profiles usage data.

**IPC Channel:** `claude:allProfilesUsageUpdated` (event from main)

**Callback Parameters:**
- `profiles` - Array of profile usage data

**Returns:** Cleanup function

---

#### `onProactiveSwapNotification(callback: (notification: {fromProfile: {id: string; name: string}; toProfile: {id: string; name: string}; reason: string; usageSnapshot: ClaudeUsageSnapshot}) => void): () => void`

Listen to proactive swap notifications.

**IPC Channel:** `claude:proactiveSwapNotification` (event from main)

**Callback Parameters:**
- `fromProfile` - Source profile
- `toProfile` - Destination profile
- `reason` - Swap reason
- `usageSnapshot` - Usage snapshot at swap time

**Returns:** Cleanup function

---

---

## SettingsAPI

**File:** `apps/frontend/src/preload/api/settings-api.ts`

Manages application settings, CLI tools detection, and version information.

### App Settings

#### `getSettings(): Promise<IPCResult<AppSettings>>`

Get application settings.

**IPC Channel:** `settings:get`

**Returns:** `IPCResult<AppSettings>`

---

#### `saveSettings(settings: Partial<AppSettings>): Promise<IPCResult>`

Save application settings.

**IPC Channel:** `settings:save`

**Parameters:**
- `settings` - Partial settings object to update

**Returns:** `IPCResult<void>`

**Example:**
```typescript
await window.electron.saveSettings({
  theme: 'dark',
  checkForUpdates: true
});
```

---

### CLI Tools Detection

#### `getCliToolsInfo(): Promise<IPCResult<{python: ToolDetectionResult; git: ToolDetectionResult; gh: ToolDetectionResult; claude: ToolDetectionResult}>>`

Get detected CLI tools information.

**IPC Channel:** `settings:getCliToolsInfo`

**Returns:** `IPCResult<{python, git, gh, claude}>`

**ToolDetectionResult Interface:**
```typescript
interface ToolDetectionResult {
  installed: boolean;
  version?: string;
  path?: string;
  error?: string;
}
```

---

### App Info

#### `getAppVersion(): Promise<string>`

Get application version.

**IPC Channel:** `app:version`

**Returns:** Application version string

---

### Auto-Build Source Environment

#### `getSourceEnv(): Promise<IPCResult<SourceEnvConfig>>`

Get source environment configuration.

**IPC Channel:** `autobuild:source:env:get`

**Returns:** `IPCResult<SourceEnvConfig>`

---

#### `updateSourceEnv(config: {claudeOAuthToken?: string}): Promise<IPCResult>`

Update source environment configuration.

**IPC Channel:** `autobuild:source:env:update`

**Parameters:**
- `config.claudeOAuthToken` - Optional OAuth token

**Returns:** `IPCResult<void>`

---

#### `checkSourceToken(): Promise<IPCResult<SourceEnvCheckResult>>`

Check source token validity.

**IPC Channel:** `autobuild:source:env:checkToken`

**Returns:** `IPCResult<SourceEnvCheckResult>`

---

### Sentry Error Reporting

#### `notifySentryStateChanged(enabled: boolean): void`

Notify main process of Sentry state change.

**IPC Channel:** `sentry:state-changed` (send, not invoke)

**Parameters:**
- `enabled` - Sentry enabled status

---

#### `getSentryDsn(): Promise<string>`

Get Sentry DSN from environment.

**IPC Channel:** `sentry:get-dsn`

**Returns:** Sentry DSN string

---

#### `getSentryConfig(): Promise<{dsn: string; tracesSampleRate: number; profilesSampleRate: number}>`

Get full Sentry configuration.

**IPC Channel:** `sentry:get-config`

**Returns:** `{dsn, tracesSampleRate, profilesSampleRate}`

---

---

## FileAPI

**File:** `apps/frontend/src/preload/api/file-api.ts`

File explorer operations for reading and writing files.

### File Operations

#### `list(path: string): Promise<IPCResult<FileNode[]>>`

List directory contents.

**IPC Channel:** `fileExplorer:list`

**Parameters:**
- `path` - Directory path

**Returns:** `IPCResult<FileNode[]>`

**FileNode Interface:**
```typescript
interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: string;
  children?: FileNode[];
}
```

---

#### `read(path: string): Promise<IPCResult<string>>`

Read file contents.

**IPC Channel:** `fileExplorer:read`

**Parameters:**
- `path` - File path

**Returns:** `IPCResult<string>` - File contents

---

#### `write(path: string, content: string): Promise<IPCResult>`

Write file contents.

**IPC Channel:** `fileExplorer:write`

**Parameters:**
- `path` - File path
- `content` - File contents

**Returns:** `IPCResult<void>`

**Example:**
```typescript
await window.electron.file.write('/path/to/file.txt', 'Hello, World!');
```

---

---

## AgentAPI

**File:** `apps/frontend/src/preload/api/agent-api.ts`

Aggregates all agent-related APIs (Roadmap, Ideation, Insights, Changelog, Linear, GitHub, GitLab, Shell, SessionContext, ProductivityAnalytics).

The AgentAPI combines all these modules:
- `createRoadmapAPI()` - Roadmap operations
- `createIdeationAPI()` - Ideation operations
- `createInsightsAPI()` - Insights operations
- `createChangelogAPI()` - Changelog operations
- `createLinearAPI()` - Linear integration
- `createGitHubAPI()` - GitHub integration
- `createGitLabAPI()` - GitLab integration
- `createShellAPI()` - Shell operations
- `createSessionContextAPI()` - Session context operations
- `createProductivityAnalyticsAPI()` - Productivity analytics

### Key Operations (GitHub Example)

**File:** `apps/frontend/src/preload/api/modules/github-api.ts`

#### `github.checkConnection(): Promise<IPCResult<GitHubSyncStatus>>`

Check GitHub connection status.

**IPC Channel:** `github:checkConnection`

**Returns:** `IPCResult<GitHubSyncStatus>`

---

#### `github.getRepositories(): Promise<IPCResult<GitHubRepository[]>>`

Get GitHub repositories.

**IPC Channel:** `github:getRepositories`

**Returns:** `IPCResult<GitHubRepository[]>`

---

#### `github.getPullRequests(owner: string, repo: string, filters?: {state?: 'open' | 'closed' | 'all'; branch?: string}): Promise<IPCResult<GHPullRequest[]>>`

Get GitHub pull requests.

**IPC Channel:** `github:pr:list`

**Parameters:**
- `owner` - Repository owner
- `repo` - Repository name
- `filters.state` - Optional PR state
- `filters.branch` - Optional branch filter

**Returns:** `IPCResult<GHPullRequest[]>`

---

#### `github.prReview(owner: string, repo: string, prNumber: number, options: {model: string; thinkingLevel?: string}): Promise<IPCResult>`

Start AI-powered PR review.

**IPC Channel:** `github:pr:review`

**Parameters:**
- `owner` - Repository owner
- `repo` - Repository name
- `prNumber` - PR number
- `options.model` - Claude model to use
- `options.thinkingLevel` - Thinking level (optional)

**Returns:** `IPCResult<void>`

**Event:** Listen to `github:pr:reviewProgress` for progress

---

For complete GitHub, GitLab, Roadmap, Ideation, Insights, and Changelog API references, see their respective module documentation files in `apps/frontend/src/preload/api/modules/`.

---

## AppUpdateAPI

**File:** `apps/frontend/src/preload/api/app-update-api.ts`

Application auto-update management.

### Update Operations

#### `checkForUpdates(): Promise<IPCResult<UpdateInfo>>`

Check for application updates.

**IPC Channel:** `app-update:check`

**Returns:** `IPCResult<UpdateInfo>`

---

#### `downloadUpdate(): Promise<IPCResult>`

Download available update.

**IPC Channel:** `app-update:download`

**Returns:** `IPCResult<void>`

**Event:** Listen to `app-update:progress` for download progress

---

#### `installUpdate(): Promise<IPCResult>`

Install downloaded update and restart.

**IPC Channel:** `app-update:install`

**Returns:** `IPCResult<void>`

---

#### `getUpdateVersion(): Promise<IPCResult<string>>`

Get latest available update version.

**IPC Channel:** `app-update:get-version`

**Returns:** `IPCResult<string>` - Version string

---

#### `getDownloadedUpdate(): Promise<IPCResult<UpdateInfo | null>>`

Get downloaded update information.

**IPC Channel:** `app-update:get-downloaded`

**Returns:** `IPCResult<UpdateInfo | null>`

---

### Update Event Listeners

#### `onUpdateAvailable(callback: (info: UpdateInfo) => void): () => void`

Listen to update available events.

**IPC Channel:** `app-update:available` (event from main)

**Callback Parameters:**
- `info` - Update information

**Returns:** Cleanup function

---

#### `onUpdateDownloaded(callback: (info: UpdateInfo) => void): () => void`

Listen to update downloaded events.

**IPC Channel:** `app-update:downloaded` (event from main)

**Callback Parameters:**
- `info` - Update information

**Returns:** Cleanup function

---

#### `onUpdateProgress(callback: (progress: {percent: number; bytesPerSecond: number; transferred: number; total: number}) => void): () => void`

Listen to download progress.

**IPC Channel:** `app-update:progress` (event from main)

**Callback Parameters:**
- `progress.percent` - Download percentage
- `progress.bytesPerSecond` - Download speed
- `progress.transferred` - Bytes transferred
- `progress.total` - Total bytes

**Returns:** Cleanup function

---

## ProfileAPI

**File:** `apps/frontend/src/preload/api/profile-api.ts`

API profile management (custom Anthropic-compatible endpoints).

### Profile Operations

#### `getProfiles(): Promise<IPCResult<ApiProfile[]>>`

Get all API profiles.

**IPC Channel:** `profiles:get`

**Returns:** `IPCResult<ApiProfile[]>`

---

#### `saveProfile(profile: ApiProfile): Promise<IPCResult<ApiProfile>>`

Save or update API profile.

**IPC Channel:** `profiles:save`

**Parameters:**
```typescript
interface ApiProfile {
  id?: string;
  name: string;
  baseUrl: string;
  apiKey: string;
  isDefault?: boolean;
}
```

**Returns:** `IPCResult<ApiProfile>`

---

#### `updateProfile(profileId: string, updates: Partial<ApiProfile>): Promise<IPCResult<ApiProfile>>`

Update API profile.

**IPC Channel:** `profiles:update`

**Parameters:**
- `profileId` - Profile identifier
- `updates` - Partial profile updates

**Returns:** `IPCResult<ApiProfile>`

---

#### `deleteProfile(profileId: string): Promise<IPCResult>`

Delete API profile.

**IPC Channel:** `profiles:delete`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `setActiveProfile(profileId: string): Promise<IPCResult>`

Set active API profile.

**IPC Channel:** `profiles:setActive`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `testConnection(profileId: string): Promise<IPCResult<{success: boolean; error?: string}>>`

Test API profile connection.

**IPC Channel:** `profiles:test-connection`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<{success: boolean; error?: string}>`

**Event:** Listen to `profiles:test-connection-progress` for progress

---

#### `cancelConnectionTest(): void`

Cancel running connection test.

**IPC Channel:** `profiles:test-connection-cancel` (send, not invoke)

---

#### `discoverModels(profileId: string): Promise<IPCResult>`

Discover available models from API endpoint.

**IPC Channel:** `profiles:discover-models`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

**Event:** Listen to `profiles:discover-models-progress` for progress

---

#### `cancelModelDiscovery(): void`

Cancel running model discovery.

**IPC Channel:** `profiles:discover-models-cancel` (send, not invoke)

---

## ScreenshotAPI

**File:** `apps/frontend/src/preload/api/screenshot-api.ts`

Screenshot capture from screens and windows.

### Screenshot Operations

#### `getSources(): Promise<IPCResult<ScreenshotSource[]>>`

Get available screens and windows.

**IPC Channel:** `screenshot:getSources`

**Returns:** `IPCResult<ScreenshotSource[]>`

**ScreenshotSource Interface:**
```typescript
interface ScreenshotSource {
  id: string;
  name: string;
  thumbnail: Electron.NativeImage | undefined;
}
```

---

#### `capture(sourceId: string): Promise<IPCResult<{dataUrl: string}>>`

Capture screenshot from source.

**IPC Channel:** `screenshot:capture`

**Parameters:**
- `sourceId` - Source identifier (screen or window)

**Returns:** `IPCResult<{dataUrl: string}>` - Screenshot as data URL

**Example:**
```typescript
const sources = await window.electron.screenshot.getSources();
const screenshot = await window.electron.screenshot.capture(sources[0].id);
console.log('Screenshot:', screenshot.dataUrl);
```

---

## QueueAPI

**File:** `apps/frontend/src/preload/api/queue-api.ts`

Queue routing for rate limit recovery and profile management.

### Queue Operations

#### `getRunningTasksByProfile(profileId: string): Promise<IPCResult<Array<{taskId: string; sessionId: string}>>>`

Get all running tasks for a profile.

**IPC Channel:** `queue:getRunningTasksByProfile`

**Parameters:**
- `profileId` - Profile identifier

**Returns:** `IPCResult<Array<{taskId: string; sessionId: string}>>`

---

#### `getBestProfileForTask(taskId: string): Promise<IPCResult<{profileId: string; reason: string}>>`

Get best available profile for task.

**IPC Channel:** `queue:getBestProfileForTask`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<{profileId: string; reason: string}>`

---

#### `assignProfileToTask(taskId: string, profileId: string): Promise<IPCResult>`

Assign profile to task.

**IPC Channel:** `queue:assignProfileToTask`

**Parameters:**
- `taskId` - Task identifier
- `profileId` - Profile identifier

**Returns:** `IPCResult<void>`

---

#### `updateTaskSession(taskId: string, sessionId: string): Promise<IPCResult>`

Update task session ID.

**IPC Channel:** `queue:updateTaskSession`

**Parameters:**
- `taskId` - Task identifier
- `sessionId` - Session ID

**Returns:** `IPCResult<void>`

---

#### `getTaskSession(taskId: string): Promise<IPCResult<string | null>>`

Get task session ID.

**IPC Channel:** `queue:getTaskSession`

**Parameters:**
- `taskId` - Task identifier

**Returns:** `IPCResult<string | null>` - Session ID or null

---

### Queue Event Listeners

#### `onProfileSwapped(callback: (data: {taskId: string; fromProfileId: string; toProfileId: string; reason: string}) => void): () => void`

Listen to profile swap events.

**IPC Channel:** `queue:profileSwapped` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `fromProfileId` - Source profile ID
- `toProfileId` - Destination profile ID
- `reason` - Swap reason

**Returns:** Cleanup function

---

#### `onSessionCaptured(callback: (data: {taskId: string; sessionId: string; profileId: string}) => void): () => void`

Listen to session capture events.

**IPC Channel:** `queue:sessionCaptured` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `sessionId` - Session ID
- `profileId` - Profile ID

**Returns:** Cleanup function

---

#### `onBlockedNoProfiles(callback: (data: {taskId: string; message: string}) => void): () => void`

Listen to blocked tasks (no available profiles).

**IPC Channel:** `queue:blockedNoProfiles` (event from main)

**Callback Parameters:**
- `taskId` - Task identifier
- `message` - Block message

**Returns:** Cleanup function

---

## SchedulerAPI

**File:** `apps/frontend/src/preload/api/scheduler-api.ts`

Build scheduling and queue management.

### Scheduler Operations

#### `scheduleBuild(specId: string, scheduledTime: string, timezone: string): Promise<IPCResult<{buildId: string}>>`

Schedule a build for specific time.

**IPC Channel:** `scheduler:scheduleBuild`

**Parameters:**
- `specId` - Spec identifier
- `scheduledTime` - ISO 8601 datetime string
- `timezone` - Timezone (e.g., 'America/New_York')

**Returns:** `IPCResult<{buildId: string}>`

---

#### `getStatus(): Promise<IPCResult<SchedulerStatus>>`

Get scheduler status.

**IPC Channel:** `scheduler:getStatus`

**Returns:** `IPCResult<SchedulerStatus>`

---

#### `cancelBuild(buildId: string): Promise<IPCResult>`

Cancel scheduled build.

**IPC Channel:** `scheduler:cancelBuild`

**Parameters:**
- `buildId` - Build identifier

**Returns:** `IPCResult<void>`

---

#### `startScheduler(): Promise<IPCResult>`

Start scheduler service.

**IPC Channel:** `scheduler:start`

**Returns:** `IPCResult<void>`

---

#### `stopScheduler(): Promise<IPCResult>`

Stop scheduler service.

**IPC Channel:** `scheduler:stop`

**Returns:** `IPCResult<void>`

---

#### `getScheduledBuilds(): Promise<IPCResult<ScheduledBuild[]>>`

Get all scheduled builds.

**IPC Channel:** `scheduler:getBuilds`

**Returns:** `IPCResult<ScheduledBuild[]>`

---

### Scheduler Event Listeners

#### `onBuildScheduled(callback: (build: ScheduledBuild) => void): () => void`

Listen to build scheduled events.

**IPC Channel:** `scheduler:buildScheduled` (event from main)

**Callback Parameters:**
- `build` - Scheduled build details

**Returns:** Cleanup function

---

#### `onBuildCancelled(callback: (buildId: string) => void): () => void`

Listen to build cancelled events.

**IPC Channel:** `scheduler:buildCancelled` (event from main)

**Callback Parameters:**
- `buildId` - Build identifier

**Returns:** Cleanup function

---

#### `onStatusChanged(callback: (status: SchedulerStatus) => void): () => void`

Listen to scheduler status changes.

**IPC Channel:** `scheduler:statusChanged` (event from main)

**Callback Parameters:**
- `status` - New scheduler status

**Returns:** Cleanup function

---

#### `onBuildProgress(callback: (data: {buildId: string; phase: string; progress: number}) => void): () => void`

Listen to build progress events.

**IPC Channel:** `scheduler:buildProgress` (event from main)

**Callback Parameters:**
- `buildId` - Build identifier
- `phase` - Current phase
- `progress` - Progress percentage

**Returns:** Cleanup function

---

#### `onBuildComplete(callback: (data: {buildId: string; result: any}) => void): () => void`

Listen to build completion events.

**IPC Channel:** `scheduler:buildComplete` (event from main)

**Callback Parameters:**
- `buildId` - Build identifier
- `result` - Build result

**Returns:** Cleanup function

---

#### `onBuildFailed(callback: (data: {buildId: string; error: string}) => void): () => void`

Listen to build failure events.

**IPC Channel:** `scheduler:buildFailed` (event from main)

**Callback Parameters:**
- `buildId` - Build identifier
- `error` - Error message

**Returns:** Cleanup function

---

## PluginAPI

**File:** `apps/frontend/src/preload/api/plugin-api.ts`

Plugin management operations.

### Plugin Operations

#### `listPlugins(): Promise<IPCResult<Plugin[]>>`

List all plugins.

**IPC Channel:** `plugin:list`

**Returns:** `IPCResult<Plugin[]>`

---

#### `enablePlugin(pluginId: string): Promise<IPCResult>`

Enable plugin.

**IPC Channel:** `plugin:enable`

**Parameters:**
- `pluginId` - Plugin identifier

**Returns:** `IPCResult<void>`

---

#### `disablePlugin(pluginId: string): Promise<IPCResult>`

Disable plugin.

**IPC Channel:** `plugin:disable`

**Parameters:**
- `pluginId` - Plugin identifier

**Returns:** `IPCResult<void>`

---

#### `installPlugin(pluginPath: string): Promise<IPCResult>`

Install plugin from path.

**IPC Channel:** `plugin:install`

**Parameters:**
- `pluginPath` - Path to plugin

**Returns:** `IPCResult<void>`

---

#### `uninstallPlugin(pluginId: string): Promise<IPCResult>`

Uninstall plugin.

**IPC Channel:** `plugin:uninstall`

**Parameters:**
- `pluginId` - Plugin identifier

**Returns:** `IPCResult<void>`

---

## FeedbackAPI

**File:** `apps/frontend/src/preload/api/feedback-api.ts`

Feedback submission for adaptive agent learning.

### Feedback Operations

#### `submitFeedback(feedback: {taskId: string; type: string; content: string; rating?: number}): Promise<IPCResult>`

Submit feedback for task.

**IPC Channel:** `feedback:submit`

**Parameters:**
```typescript
{
  taskId: string;       // Task identifier
  type: string;        // Feedback type (bug, improvement, etc.)
  content: string;      // Feedback content
  rating?: number;      // Optional rating (1-5)
}
```

**Returns:** `IPCResult<void>`

**Example:**
```typescript
await window.electron.feedback.submitFeedback({
  taskId: 'task-123',
  type: 'improvement',
  content: 'Agent should have asked for clarification',
  rating: 4
});
```

---

## IPC Result Type

All invoke operations return `Promise<IPCResult<T>>`:

```typescript
interface IPCResult<T = void> {
  success: boolean;
  data?: T;
  error?: string;
}
```

**Usage Pattern:**
```typescript
const result = await window.electron.getProjects();
if (result.success) {
  console.log('Projects:', result.data);
} else {
  console.error('Error:', result.error);
}
```

---

## Event Listener Pattern

Event-based APIs follow this pattern:

```typescript
// Register listener
const cleanup = window.electron.onTaskProgress((taskId, plan) => {
  console.log('Progress:', taskId, plan);
});

// Later: unregister listener
cleanup();
```

---

## IPC Channels Reference

All IPC channel names are defined in `apps/frontend/src/shared/constants/ipc.ts`.

**Common prefixes:**
- `project:*` - Project operations
- `task:*` - Task operations
- `terminal:*` - Terminal operations
- `settings:*` - Settings operations
- `github:*` - GitHub integration
- `gitlab:*` - GitLab integration
- `scheduler:*` - Scheduler operations
- `app-update:*` - App update operations
- `memory:*` - Memory infrastructure
- `queue:*` - Queue routing

---

## Type Definitions

Complete TypeScript type definitions are available in:
- `apps/frontend/src/shared/types.ts` - Shared types
- `apps/frontend/src/preload/api/*.ts` - API-specific types

---

## Security Considerations

All IPC communication is isolated through Electron's contextBridge:
- Renderer process cannot access Node.js APIs directly
- All APIs are exposed through `window.electron` in preload script
- Filesystem access is restricted to allowed directories
- Command execution is sandboxed with dynamic allowlists

See `apps/backend/core/security.py` and `apps/backend/context/project_analyzer.py` for security implementation details.

---

## Related Documentation

- [Backend API Reference](backend-api.md) - Python CLI and backend API
- [CLI API Reference](CLI-API-REFERENCE.md) - Command-line interface reference
- [Frontend Architecture](../features/MULTI-AGENT-PIPELINE.md) - Multi-agent system overview
- [Memory System](../features/MEMORY-SYSTEM.md) - Graphiti memory integration
