import { app } from 'electron';
import { join } from 'path';
import { existsSync, readFileSync, writeFileSync, mkdirSync, renameSync, unlinkSync } from 'fs';

/**
 * Project relationship types
 */
export type ProjectRelationship = 'independent' | 'depends_on' | 'library' | 'monorepo_package';

/**
 * Project configuration within a workspace
 */
export interface Project {
  name: string;
  path: string;  // Absolute path to project directory
  enabled: boolean;
  relationship: ProjectRelationship;
  dependencies: string[];  // Names of projects this depends on
  description?: string;
  tags: string[];
}

/**
 * Workspace configuration
 */
export interface Workspace {
  name: string;
  description?: string;
  projects: Project[];
  createdAt: string;  // ISO timestamp
  updatedAt: string;  // ISO timestamp
}

/**
 * All persisted workspace data
 */
interface WorkspaceData {
  version: number;
  workspaces: Record<string, Workspace>;  // workspace name -> workspace
}

const STORE_VERSION = 1;

/**
 * Manages persistent workspace storage
 * Workspaces are saved to userData/workspaces/workspaces.json
 */
export class WorkspaceStore {
  private storePath: string;
  private tempPath: string;
  private backupPath: string;
  private data: WorkspaceData;
  /**
   * Tracks workspace names that are being deleted to prevent async writes from
   * resurrecting them. This fixes a race condition where saveWorkspaceAsync()
   * could complete after removeWorkspace() and re-add deleted workspaces.
   */
  private pendingDelete: Set<string> = new Set();
  /**
   * Tracks cleanup timers for pendingDelete entries to prevent timer accumulation
   * when many workspaces are deleted rapidly.
   */
  private pendingDeleteTimers: Map<string, ReturnType<typeof setTimeout>> = new Map();
  /**
   * Write serialization state - prevents concurrent async writes from
   * interleaving and potentially losing data.
   */
  private writeInProgress = false;
  private writePending = false;
  /**
   * Failure tracking for async writes - helps detect persistent write issues
   * that might otherwise go unnoticed in fire-and-forget scenarios.
   */
  private consecutiveFailures = 0;
  private static readonly MAX_FAILURES_BEFORE_WARNING = 3;

  constructor() {
    const workspacesDir = join(app.getPath('userData'), 'workspaces');
    this.storePath = join(workspacesDir, 'workspaces.json');
    this.tempPath = join(workspacesDir, 'workspaces.json.tmp');
    this.backupPath = join(workspacesDir, 'workspaces.json.backup');

    // Ensure directory exists
    if (!existsSync(workspacesDir)) {
      mkdirSync(workspacesDir, { recursive: true });
    }

    // Load existing data or initialize
    this.data = this.load();
  }

  /**
   * Load workspaces from disk with backup recovery
   */
  private load(): WorkspaceData {
    // Try loading from main file first
    const mainResult = this.tryLoadFile(this.storePath);
    if (mainResult.success && mainResult.data) {
      return mainResult.data;
    }

    // If main file failed, try backup
    if (mainResult.error) {
      console.warn('[WorkspaceStore] Main file corrupted, attempting backup recovery...');
      const backupResult = this.tryLoadFile(this.backupPath);
      if (backupResult.success && backupResult.data) {
        console.warn('[WorkspaceStore] Successfully recovered from backup!');
        // Immediately save the recovered data to main file
        try {
          writeFileSync(this.storePath, JSON.stringify(backupResult.data, null, 2));
          console.warn('[WorkspaceStore] Restored main file from backup');
        } catch (writeError) {
          console.error('[WorkspaceStore] Failed to restore main file:', writeError);
        }
        return backupResult.data;
      }
      console.error('[WorkspaceStore] Backup recovery failed, starting fresh');
    }

    return { version: STORE_VERSION, workspaces: {} };
  }

  /**
   * Try to load and parse a workspace file
   */
  private tryLoadFile(filePath: string): { success: boolean; data?: WorkspaceData; error?: Error } {
    try {
      if (!existsSync(filePath)) {
        return { success: false };
      }

      const content = readFileSync(filePath, 'utf-8');
      const data = JSON.parse(content);

      if (data.version === STORE_VERSION) {
        return { success: true, data: data as WorkspaceData };
      }

      console.warn('[WorkspaceStore] Version mismatch, resetting workspaces');
      return { success: false };
    } catch (error) {
      console.error(`[WorkspaceStore] Error loading ${filePath}:`, error);
      return { success: false, error: error as Error };
    }
  }

  /**
   * Save workspaces to disk using atomic write pattern:
   * 1. Write to temp file
   * 2. Rotate current file to backup
   * 3. Rename temp to target (atomic on most filesystems)
   */
  private save(): void {
    try {
      const content = JSON.stringify(this.data, null, 2);

      // Step 1: Write to temp file
      writeFileSync(this.tempPath, content, 'utf-8');

      // Step 2: Rotate current to backup (if exists)
      if (existsSync(this.storePath)) {
        if (existsSync(this.backupPath)) {
          unlinkSync(this.backupPath);
        }
        renameSync(this.storePath, this.backupPath);
      }

      // Step 3: Atomic rename
      renameSync(this.tempPath, this.storePath);

      this.consecutiveFailures = 0;
    } catch (error) {
      this.consecutiveFailures++;
      console.error('[WorkspaceStore] Failed to save workspaces:', error);

      if (this.consecutiveFailures >= WorkspaceStore.MAX_FAILURES_BEFORE_WARNING) {
        console.error(
          `[WorkspaceStore] WARNING: ${this.consecutiveFailures} consecutive save failures. Data may be at risk!`
        );
      }

      // Clean up temp file if it exists
      try {
        if (existsSync(this.tempPath)) {
          unlinkSync(this.tempPath);
        }
      } catch (cleanupError) {
        console.error('[WorkspaceStore] Failed to clean up temp file:', cleanupError);
      }

      throw error;
    }
  }

  /**
   * Async wrapper around save() with write serialization
   */
  private async saveAsync(): Promise<void> {
    // If a write is in progress, mark that another write is needed
    if (this.writeInProgress) {
      this.writePending = true;
      return;
    }

    this.writeInProgress = true;

    try {
      // Perform the write
      this.save();

      // If another write was requested while we were writing, do it now
      if (this.writePending) {
        this.writePending = false;
        this.save();
      }
    } finally {
      this.writeInProgress = false;
    }
  }

  /**
   * Get all workspaces
   */
  getWorkspaces(): Workspace[] {
    return Object.values(this.data.workspaces);
  }

  /**
   * Get workspace by name
   */
  getWorkspace(name: string): Workspace | undefined {
    return this.data.workspaces[name];
  }

  /**
   * Add or update a workspace
   */
  saveWorkspace(workspace: Workspace): void {
    // Don't save if workspace is pending deletion
    if (this.pendingDelete.has(workspace.name)) {
      console.warn(`[WorkspaceStore] Ignoring save for workspace ${workspace.name} (pending deletion)`);
      return;
    }

    workspace.updatedAt = new Date().toISOString();
    this.data.workspaces[workspace.name] = workspace;
    this.save();
  }

  /**
   * Add or update a workspace (async)
   */
  async saveWorkspaceAsync(workspace: Workspace): Promise<void> {
    // Don't save if workspace is pending deletion
    if (this.pendingDelete.has(workspace.name)) {
      console.warn(`[WorkspaceStore] Ignoring async save for workspace ${workspace.name} (pending deletion)`);
      return;
    }

    workspace.updatedAt = new Date().toISOString();
    this.data.workspaces[workspace.name] = workspace;
    await this.saveAsync();
  }

  /**
   * Remove a workspace
   */
  removeWorkspace(name: string): boolean {
    if (!this.data.workspaces[name]) {
      return false;
    }

    // Mark as pending deletion to prevent race condition with async saves
    this.pendingDelete.add(name);

    // Clear any existing timer for this workspace
    const existingTimer = this.pendingDeleteTimers.get(name);
    if (existingTimer) {
      clearTimeout(existingTimer);
    }

    // Set a timer to remove from pendingDelete after a reasonable delay
    const timer = setTimeout(() => {
      this.pendingDelete.delete(name);
      this.pendingDeleteTimers.delete(name);
    }, 5000);  // 5 seconds

    this.pendingDeleteTimers.set(name, timer);

    delete this.data.workspaces[name];
    this.save();
    return true;
  }

  /**
   * Create a new workspace
   */
  createWorkspace(name: string, description?: string): Workspace {
    if (this.data.workspaces[name]) {
      throw new Error(`Workspace '${name}' already exists`);
    }

    const now = new Date().toISOString();
    const workspace: Workspace = {
      name,
      description,
      projects: [],
      createdAt: now,
      updatedAt: now,
    };

    this.saveWorkspace(workspace);
    return workspace;
  }

  /**
   * Add a project to a workspace
   */
  addProject(
    workspaceName: string,
    project: Omit<Project, 'enabled' | 'dependencies' | 'tags'> & {
      enabled?: boolean;
      dependencies?: string[];
      tags?: string[];
    }
  ): void {
    const workspace = this.data.workspaces[workspaceName];
    if (!workspace) {
      throw new Error(`Workspace '${workspaceName}' not found`);
    }

    // Check if project name already exists
    if (workspace.projects.some(p => p.name === project.name)) {
      throw new Error(`Project '${project.name}' already exists in workspace '${workspaceName}'`);
    }

    // Add project with defaults
    const newProject: Project = {
      ...project,
      enabled: project.enabled ?? true,
      dependencies: project.dependencies ?? [],
      tags: project.tags ?? [],
    };

    workspace.projects.push(newProject);
    this.saveWorkspace(workspace);
  }

  /**
   * Remove a project from a workspace
   */
  removeProject(workspaceName: string, projectName: string): boolean {
    const workspace = this.data.workspaces[workspaceName];
    if (!workspace) {
      return false;
    }

    const projectIndex = workspace.projects.findIndex(p => p.name === projectName);
    if (projectIndex === -1) {
      return false;
    }

    // Check if other projects depend on this one
    const dependents = workspace.projects.filter(p => p.dependencies.includes(projectName));
    if (dependents.length > 0) {
      const depNames = dependents.map(p => p.name).join(', ');
      throw new Error(
        `Cannot remove project '${projectName}': projects [${depNames}] depend on it`
      );
    }

    workspace.projects.splice(projectIndex, 1);
    this.saveWorkspace(workspace);
    return true;
  }

  /**
   * Update a project in a workspace
   */
  updateProject(workspaceName: string, projectName: string, updates: Partial<Project>): void {
    const workspace = this.data.workspaces[workspaceName];
    if (!workspace) {
      throw new Error(`Workspace '${workspaceName}' not found`);
    }

    const project = workspace.projects.find(p => p.name === projectName);
    if (!project) {
      throw new Error(`Project '${projectName}' not found in workspace '${workspaceName}'`);
    }

    // Apply updates
    Object.assign(project, updates);
    this.saveWorkspace(workspace);
  }

  /**
   * Get projects for a workspace
   */
  getProjects(workspaceName: string): Project[] {
    const workspace = this.data.workspaces[workspaceName];
    return workspace?.projects ?? [];
  }

  /**
   * Get enabled projects for a workspace
   */
  getEnabledProjects(workspaceName: string): Project[] {
    const workspace = this.data.workspaces[workspaceName];
    return workspace?.projects.filter(p => p.enabled) ?? [];
  }

  /**
   * Check if a workspace exists
   */
  hasWorkspace(name: string): boolean {
    return !!this.data.workspaces[name];
  }

  /**
   * Rename a workspace
   */
  renameWorkspace(oldName: string, newName: string): void {
    const workspace = this.data.workspaces[oldName];
    if (!workspace) {
      throw new Error(`Workspace '${oldName}' not found`);
    }

    if (this.data.workspaces[newName]) {
      throw new Error(`Workspace '${newName}' already exists`);
    }

    workspace.name = newName;
    workspace.updatedAt = new Date().toISOString();
    this.data.workspaces[newName] = workspace;
    delete this.data.workspaces[oldName];
    this.save();
  }

  /**
   * Get build order for projects (topological sort)
   * Returns projects in dependency order (dependencies first)
   */
  getBuildOrder(workspaceName: string): Project[] {
    const workspace = this.data.workspaces[workspaceName];
    if (!workspace) {
      return [];
    }

    const enabledProjects = workspace.projects.filter(p => p.enabled);
    const inDegree = new Map<string, number>();
    const adjList = new Map<string, string[]>();

    // Initialize
    for (const project of enabledProjects) {
      inDegree.set(project.name, 0);
      adjList.set(project.name, []);
    }

    // Build adjacency list and in-degree count
    for (const project of enabledProjects) {
      for (const dep of project.dependencies) {
        if (adjList.has(dep)) {  // Only include enabled projects
          adjList.get(dep)!.push(project.name);
          inDegree.set(project.name, inDegree.get(project.name)! + 1);
        }
      }
    }

    // Kahn's algorithm for topological sort
    const queue: string[] = [];
    for (const [name, degree] of inDegree.entries()) {
      if (degree === 0) {
        queue.push(name);
      }
    }

    const result: string[] = [];
    while (queue.length > 0) {
      const current = queue.shift()!;
      result.push(current);

      // Reduce in-degree for dependents
      for (const dependent of adjList.get(current) || []) {
        const newDegree = inDegree.get(dependent)! - 1;
        inDegree.set(dependent, newDegree);
        if (newDegree === 0) {
          queue.push(dependent);
        }
      }
    }

    // Check for cycles
    if (result.length !== enabledProjects.length) {
      throw new Error(`Circular dependency detected in workspace '${workspaceName}'`);
    }

    // Convert names back to Project objects
    return result
      .map(name => workspace.projects.find(p => p.name === name))
      .filter((p): p is Project => p !== undefined);
  }
}
