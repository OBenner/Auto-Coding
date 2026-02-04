/**
 * GitHub repository-related IPC handlers
 */

import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult, GitHubRepository, GitHubSyncStatus } from '../../../shared/types';
import { projectStore } from '../../project-store';
import { getGitHubConfig, githubFetch, normalizeRepoReference } from './utils';
import type { GitHubAPIRepository } from './types';
import {
  runPythonSubprocess,
  getPythonPath,
  getRunnerPath,
  validateGitHubModule,
  buildRunnerArgs,
  parseJSONFromOutput,
} from './utils/subprocess-runner';
import { getRunnerEnv } from './utils/runner-env';

/**
 * Check GitHub connection status
 */
export function registerCheckConnection(): void {
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_CHECK_CONNECTION,
    async (_, projectId: string): Promise<IPCResult<GitHubSyncStatus>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const config = getGitHubConfig(project);
      if (!config) {
        return {
          success: true,
          data: {
            connected: false,
            error: 'No GitHub token or repository configured'
          }
        };
      }

      try {
        // Normalize repo reference (handles full URLs, git URLs, etc.)
        const normalizedRepo = normalizeRepoReference(config.repo);
        if (!normalizedRepo) {
          return {
            success: true,
            data: {
              connected: false,
              error: 'Invalid repository format. Use owner/repo or GitHub URL.'
            }
          };
        }

        // Fetch repo info
        const repoData = await githubFetch(
          config.token,
          `/repos/${normalizedRepo}`
        ) as { full_name: string; description?: string };

        // Count open issues
        const issuesData = await githubFetch(
          config.token,
          `/repos/${normalizedRepo}/issues?state=open&per_page=1`
        ) as unknown[];

        const openCount = Array.isArray(issuesData) ? issuesData.length : 0;

        return {
          success: true,
          data: {
            connected: true,
            repoFullName: repoData.full_name,
            repoDescription: repoData.description,
            issueCount: openCount,
            lastSyncedAt: new Date().toISOString()
          }
        };
      } catch (error) {
        return {
          success: true,
          data: {
            connected: false,
            error: error instanceof Error ? error.message : 'Failed to connect to GitHub'
          }
        };
      }
    }
  );
}

/**
 * Get list of GitHub repositories (personal + organization)
 */
export function registerGetRepositories(): void {
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_GET_REPOSITORIES,
    async (_, projectId: string): Promise<IPCResult<GitHubRepository[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const config = getGitHubConfig(project);
      if (!config) {
        return { success: false, error: 'No GitHub token configured' };
      }

      try {
        // Fetch user's personal + organization repos
        // affiliation parameter includes: owner, collaborator, organization_member
        const repos = await githubFetch(
          config.token,
          '/user/repos?per_page=100&sort=updated&affiliation=owner,collaborator,organization_member'
        ) as GitHubAPIRepository[];

        const result: GitHubRepository[] = repos.map(repo => ({
          id: repo.id,
          name: repo.name,
          fullName: repo.full_name,
          description: repo.description,
          url: repo.html_url,
          defaultBranch: repo.default_branch,
          private: repo.private,
          owner: {
            login: repo.owner.login,
            avatarUrl: repo.owner.avatar_url
          }
        }));

        return { success: true, data: result };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to fetch repositories'
        };
      }
    }
  );
}

/**
 * Trigger code review for a repository
 * Channel: github:code-review:trigger
 */
export function registerCodeReviewTrigger(): void {
  ipcMain.handle(
    IPC_CHANNELS.GITHUB_CODE_REVIEW_TRIGGER,
    async (_, projectId: string, prNumber?: number): Promise<IPCResult<{ reviewId: string; findings?: any[] }>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      const config = getGitHubConfig(project);
      if (!config) {
        return { success: false, error: 'No GitHub token or repository configured' };
      }

      try {
        // Normalize repo reference
        const normalizedRepo = normalizeRepoReference(config.repo);
        if (!normalizedRepo) {
          return {
            success: false,
            error: 'Invalid repository format. Use owner/repo or GitHub URL.'
          };
        }

        // Validate GitHub module is available
        const validation = await validateGitHubModule(project);
        if (!validation.valid) {
          return {
            success: false,
            error: validation.error || 'GitHub runner not available'
          };
        }

        // Generate a review ID for tracking
        const reviewId = `review-${Date.now()}`;

        // Call backend code review service via Python runner
        const backendPath = validation.backendPath!;
        const pythonPath = getPythonPath(backendPath);
        const runnerPath = getRunnerPath(backendPath);

        // Build command arguments
        const args = buildRunnerArgs(
          runnerPath,
          project.path,
          'code-review-pr',
          prNumber ? [String(prNumber)] : []
        );

        // Get runner environment with authentication
        const env = await getRunnerEnv(project);

        // Execute the Python subprocess
        const { promise } = runPythonSubprocess<any>({
          pythonPath,
          args,
          cwd: project.path,
          env,
          onStdout: (line: string) => {
            console.log('[Code Review]', line);
          },
          onStderr: (line: string) => {
            console.error('[Code Review Error]', line);
          },
          onComplete: (stdout: string, stderr: string) => {
            // Try to parse findings from output
            try {
              return parseJSONFromOutput(stdout);
            } catch {
              // If no JSON, return stdout as message
              return { message: stdout };
            }
          },
        });

        const result = await promise;

        if (!result.success) {
          return {
            success: false,
            error: result.error || 'Code review failed'
          };
        }

        return {
          success: true,
          data: {
            reviewId,
            findings: result.data?.findings || [],
          }
        };
      } catch (error) {
        return {
          success: false,
          error: error instanceof Error ? error.message : 'Failed to trigger code review'
        };
      }
    }
  );
}

/**
 * Register all repository-related handlers
 */
export function registerRepositoryHandlers(): void {
  registerCheckConnection();
  registerGetRepositories();
  registerCodeReviewTrigger();
}
