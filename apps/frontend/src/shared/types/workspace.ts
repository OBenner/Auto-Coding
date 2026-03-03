/**
 * Workspace-related types for multi-codebase orchestration
 */

/**
 * Project relationship types
 */
export type ProjectRelationship = 'independent' | 'depends_on' | 'library' | 'monorepo_package';

/**
 * Project configuration within a workspace
 */
export interface WorkspaceProject {
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
  projects: WorkspaceProject[];
  createdAt: string;  // ISO timestamp
  updatedAt: string;  // ISO timestamp
}
