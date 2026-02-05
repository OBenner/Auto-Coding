import { ipcMain } from "electron";
import type { BrowserWindow } from "electron";
import path from "path";
import { spawn } from "child_process";
import { promises as fsPromises } from "fs";
import { debugError } from "../../shared/utils/debug-logger";
import { IPC_CHANNELS, getSpecsDir } from "../../shared/constants";
import type { IPCResult } from "../../shared/types";
import { projectStore } from "../project-store";
import { parsePythonCommand } from "../python-detector";
import { getConfiguredPythonPath } from "../python-env-manager";
import { getAugmentedEnv } from "../env-utils";
import { getEffectiveSourcePath } from "../updater/path-resolver";

/**
 * Helper to check if a file exists asynchronously
 */
async function fileExists(filePath: string): Promise<boolean> {
  try {
    await fsPromises.access(filePath);
    return true;
  } catch {
    return false;
  }
}

/**
 * Execute Python analytics command and return parsed JSON result
 */
async function executeAnalyticsCommand(
  projectPath: string,
  command: string,
  args: string[]
): Promise<any> {
  return new Promise((resolve, reject) => {
    const pythonPath = getConfiguredPythonPath();
    const [pythonCommand, pythonBaseArgs] = parsePythonCommand(pythonPath);
    const sourcePath = getEffectiveSourcePath();
    const backendPath = path.join(sourcePath, "apps", "backend");
    const scriptPath = path.join(backendPath, "cli", "analytics_cli.py");

    // Build command: python -m apps.backend.cli.analytics_cli <command> <args>
    const fullArgs = [...pythonBaseArgs, scriptPath, command, ...args];

    const env = getAugmentedEnv();
    const pythonProcess = spawn(pythonCommand, fullArgs, {
      cwd: projectPath,
      env,
    });

    let stdout = "";
    let stderr = "";

    pythonProcess.stdout?.on("data", (data) => {
      stdout += data.toString();
    });

    pythonProcess.stderr?.on("data", (data) => {
      stderr += data.toString();
    });

    pythonProcess.on("close", (code) => {
      if (code !== 0) {
        debugError(`[Analytics] Command failed with code ${code}:`, stderr);
        reject(new Error(stderr || `Process exited with code ${code}`));
      } else {
        try {
          const result = JSON.parse(stdout);
          resolve(result);
        } catch (error) {
          debugError("[Analytics] Failed to parse JSON output:", error);
          reject(new Error(`Failed to parse JSON: ${error}`));
        }
      }
    });

    pythonProcess.on("error", (error) => {
      debugError("[Analytics] Process error:", error);
      reject(error);
    });
  });
}

/**
 * Get metrics summary for a project
 */
async function getAnalytics(projectPath: string, autoBuildPath?: string): Promise<any> {
  const specsBaseDir = getSpecsDir(autoBuildPath);
  const specsDir = path.join(projectPath, specsBaseDir);

  if (!(await fileExists(specsDir))) {
    return {
      summary: {
        total_specs: 0,
        completed_specs: 0,
        failed_specs: 0,
        in_progress_specs: 0,
        overall_success_rate: 0,
        total_cost: 0,
        total_tokens: 0,
        agent_stats: {},
        complexity_stats: {},
        qa_stats: {
          total_reviews: 0,
          approved: 0,
          rejected: 0,
          rejection_rate: 0,
          common_issues: {},
        },
        last_updated: new Date().toISOString(),
      },
    };
  }

  try {
    const result = await executeAnalyticsCommand(projectPath, "summary", [
      "--specs-dir",
      specsDir,
    ]);
    return result;
  } catch (error) {
    debugError("[Analytics] Failed to get summary:", error);
    throw error;
  }
}

/**
 * Get agent-specific statistics
 */
async function getAgentStats(projectPath: string, autoBuildPath?: string): Promise<any> {
  const specsBaseDir = getSpecsDir(autoBuildPath);
  const specsDir = path.join(projectPath, specsBaseDir);

  if (!(await fileExists(specsDir))) {
    return {};
  }

  try {
    const result = await executeAnalyticsCommand(projectPath, "agent-stats", [
      "--specs-dir",
      specsDir,
    ]);
    return result;
  } catch (error) {
    debugError("[Analytics] Failed to get agent stats:", error);
    throw error;
  }
}

/**
 * Get trend data for the last N days
 */
async function getTrends(
  projectPath: string,
  autoBuildPath: string | undefined,
  days: number = 30
): Promise<any> {
  const specsBaseDir = getSpecsDir(autoBuildPath);
  const specsDir = path.join(projectPath, specsBaseDir);

  if (!(await fileExists(specsDir))) {
    return [];
  }

  try {
    const result = await executeAnalyticsCommand(projectPath, "trends", [
      "--specs-dir",
      specsDir,
      "--days",
      days.toString(),
    ]);
    return result;
  } catch (error) {
    debugError("[Analytics] Failed to get trends:", error);
    throw error;
  }
}

/**
 * Get comprehensive analytics report
 */
async function getReport(projectPath: string, autoBuildPath?: string): Promise<any> {
  const specsBaseDir = getSpecsDir(autoBuildPath);
  const specsDir = path.join(projectPath, specsBaseDir);

  if (!(await fileExists(specsDir))) {
    return {
      summary: {
        total_specs: 0,
        completed_specs: 0,
        failed_specs: 0,
        in_progress_specs: 0,
        overall_success_rate: 0,
        total_cost: 0,
        total_tokens: 0,
        agent_stats: {},
        complexity_stats: {},
        qa_stats: {
          total_reviews: 0,
          approved: 0,
          rejected: 0,
          rejection_rate: 0,
          common_issues: {},
        },
        last_updated: new Date().toISOString(),
      },
      trends: [],
      generated_at: new Date().toISOString(),
    };
  }

  try {
    const result = await executeAnalyticsCommand(projectPath, "report", [
      "--specs-dir",
      specsDir,
    ]);
    return result;
  } catch (error) {
    debugError("[Analytics] Failed to get report:", error);
    throw error;
  }
}

/**
 * Register all analytics-related IPC handlers
 */
export function registerAnalyticsHandlers(getMainWindow: () => BrowserWindow | null): void {
  // ============================================
  // Analytics Operations
  // ============================================

  ipcMain.handle(
    IPC_CHANNELS.ANALYTICS_GET_SUMMARY,
    async (_, projectId: string): Promise<IPCResult<any>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: "Project not found" };
      }

      try {
        const summary = await getAnalytics(project.path, project.autoBuildPath);
        return { success: true, data: summary };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get analytics: ${errorMessage}` };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.ANALYTICS_GET_AGENT_STATS,
    async (_, projectId: string): Promise<IPCResult<any>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: "Project not found" };
      }

      try {
        const stats = await getAgentStats(project.path, project.autoBuildPath);
        return { success: true, data: stats };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get agent stats: ${errorMessage}` };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.ANALYTICS_GET_TRENDS,
    async (_, projectId: string, days?: number): Promise<IPCResult<any>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: "Project not found" };
      }

      try {
        const trends = await getTrends(project.path, project.autoBuildPath, days);
        return { success: true, data: trends };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get trends: ${errorMessage}` };
      }
    }
  );

  ipcMain.handle(
    IPC_CHANNELS.ANALYTICS_GET_REPORT,
    async (_, projectId: string): Promise<IPCResult<any>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: "Project not found" };
      }

      try {
        const report = await getReport(project.path, project.autoBuildPath);
        return { success: true, data: report };
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get report: ${errorMessage}` };
      }
    }
  );
}
