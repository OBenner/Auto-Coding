import type { BrowserWindow } from "electron";
import path from "path";
import { existsSync, readFileSync } from "fs";
import { IPC_CHANNELS, AUTO_BUILD_PATHS, getSpecsDir } from "../../shared/constants";
import {
  wouldPhaseRegress,
  isTerminalPhase,
  isValidExecutionPhase,
  isValidPhaseTransition,
  type ExecutionPhase,
} from "../../shared/constants/phase-protocol";
import type {
  SDKRateLimitInfo,
  AuthFailureInfo,
  Task,
  TaskStatus,
  Project,
  ImplementationPlan,
} from "../../shared/types";
import { AgentManager } from "../agent";
import type { ProcessType, ExecutionProgressData } from "../agent";
import { titleGenerator } from "../title-generator";
import { fileWatcher } from "../file-watcher";
import { projectStore } from "../project-store";
import { notificationService } from "../notification-service";
import { persistPlanStatusSync, getPlanPath } from "./task/plan-file-utils";
import { findTaskWorktree } from "../worktree-paths";
import { findTaskAndProject } from "./task/shared";
import { safeSendToRenderer } from "./utils";
import { getClaudeProfileManager } from "../claude-profile-manager";

/**
 * Validates status transitions to prevent invalid state changes.
 * FIX (ACS-55, ACS-71): Adds guardrails against bad status transitions.
 * FIX (PR Review): Uses comprehensive wouldPhaseRegress() utility instead of hardcoded checks.
 * FIX (ACS-203): Adds phase completion validation to prevent phase overlaps.
 *
 * @param task - The current task (may be undefined if not found)
 * @param newStatus - The proposed new status
 * @param phase - The execution phase that triggered this transition
 * @returns true if transition is valid, false if it should be blocked
 */
function validateStatusTransition(
  task: Task | undefined,
  newStatus: TaskStatus,
  phase: string
): boolean {
  // Can't validate without task data - allow the transition
  if (!task) return true;

  // Don't allow human_review without subtasks
  // This prevents tasks from jumping to review before planning is complete
  if (newStatus === "human_review" && (!task.subtasks || task.subtasks.length === 0)) {
    console.warn(
      `[validateStatusTransition] Blocking human_review - task ${task.id} has no subtasks (phase: ${phase})`
    );
    return false;
  }

  // FIX (PR Review): Use comprehensive phase regression check instead of hardcoded checks
  // This handles all phase regressions (qa_review→coding, complete→coding, etc.)
  // not just the specific coding→planning case
  const currentPhase = task.executionProgress?.phase;
  const completedPhases = task.executionProgress?.completedPhases || [];

  if (currentPhase && isValidExecutionPhase(currentPhase) && isValidExecutionPhase(phase)) {
    // Block transitions from terminal phases (complete/failed)
    if (isTerminalPhase(currentPhase)) {
      console.warn(
        `[validateStatusTransition] Blocking transition from terminal phase: ${currentPhase} for task ${task.id}`
      );
      return false;
    }

    // Block any phase regression (going backwards in the workflow)
    // Note: Cast phase to ExecutionPhase since isValidExecutionPhase() type guard doesn't narrow through function calls
    if (wouldPhaseRegress(currentPhase, phase as ExecutionPhase)) {
      console.warn(
        `[validateStatusTransition] Blocking phase regression: ${currentPhase} -> ${phase} for task ${task.id}`
      );
      return false;
    }

    // FIX (ACS-203): Validate phase transitions based on completed phases
    // This prevents multiple phases from being active simultaneously
    // e.g., coding starting while planning is still marked as active
    const newPhase = phase as ExecutionPhase;
    if (!isValidPhaseTransition(currentPhase, newPhase, completedPhases)) {
      console.warn(
        `[validateStatusTransition] Blocking invalid phase transition: ${currentPhase} -> ${newPhase} for task ${task.id}`,
        {
          currentPhase,
          newPhase,
          completedPhases,
          reason: "Prerequisite phases not completed",
        }
      );
      return false;
    }
  }

  return true;
}

/**
 * Register all agent-events-related IPC handlers
 */
export function registerAgenteventsHandlers(
  agentManager: AgentManager,
  getMainWindow: () => BrowserWindow | null
): void {
  // ============================================
  // Agent Manager Events → Renderer
  // ============================================

  agentManager.on("log", (taskId: string, log: string) => {
    // Include projectId for multi-project filtering (issue #723)
    // Wrap in async IIFE since findTaskAndProject is now async
    (async () => {
      const { project } = await findTaskAndProject(taskId);
      safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_LOG, taskId, log, project?.id);
    })().catch((err) => console.error('[agent-events] Error in log handler:', err));
  });

  agentManager.on("error", (taskId: string, error: string) => {
    // Include projectId for multi-project filtering (issue #723)
    // Wrap in async IIFE since findTaskAndProject is now async
    (async () => {
      const { project } = await findTaskAndProject(taskId);
      safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_ERROR, taskId, error, project?.id);
    })().catch((err) => console.error('[agent-events] Error in error handler:', err));
  });

  // Handle SDK rate limit events from agent manager
  agentManager.on("sdk-rate-limit", (rateLimitInfo: SDKRateLimitInfo) => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_SDK_RATE_LIMIT, rateLimitInfo);
  });

  // Handle SDK rate limit events from title generator
  titleGenerator.on("sdk-rate-limit", (rateLimitInfo: SDKRateLimitInfo) => {
    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_SDK_RATE_LIMIT, rateLimitInfo);
  });

  // Handle auth failure events (401 errors requiring re-authentication)
  agentManager.on("auth-failure", (taskId: string, authFailure: {
    profileId?: string;
    failureType?: 'missing' | 'invalid' | 'expired' | 'unknown';
    message?: string;
    originalError?: string;
  }) => {
    console.warn(`[AgentEvents] Auth failure detected for task ${taskId}:`, authFailure);

    // Get profile name for display
    const profileManager = getClaudeProfileManager();
    const profile = authFailure.profileId
      ? profileManager.getProfile(authFailure.profileId)
      : profileManager.getActiveProfile();

    const authFailureInfo: AuthFailureInfo = {
      profileId: authFailure.profileId || profile?.id || 'unknown',
      profileName: profile?.name,
      failureType: authFailure.failureType || 'unknown',
      message: authFailure.message || 'Authentication failed. Please re-authenticate.',
      originalError: authFailure.originalError,
      taskId,
      detectedAt: new Date(),
    };

    safeSendToRenderer(getMainWindow, IPC_CHANNELS.CLAUDE_AUTH_FAILURE, authFailureInfo);
  });

  agentManager.on("exit", (taskId: string, code: number | null, processType: ProcessType) => {
    // Wrap in async IIFE since we need to await async operations
    (async () => {
      // Get project info early for multi-project filtering (issue #723)
      const { task: exitTask, project: exitProject } = await findTaskAndProject(taskId);
      const exitProjectId = exitProject?.id;

    // Send final plan state to renderer BEFORE unwatching
    // This ensures the renderer has the final subtask data (fixes 0/0 subtask bug)
    // Try the file watcher's current path first, then fall back to worktree path
    let finalPlan = fileWatcher.getCurrentPlan(taskId);
    if (!finalPlan && exitTask && exitProject) {
      // File watcher may have been watching the wrong path (main vs worktree)
      // Try reading directly from the worktree
      const worktreePath = findTaskWorktree(exitProject.path, exitTask.specId);
      if (worktreePath) {
        const specsBaseDir = getSpecsDir(exitProject.autoBuildPath);
        const worktreePlanPath = path.join(worktreePath, specsBaseDir, exitTask.specId, AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN);
        try {
          const content = readFileSync(worktreePlanPath, 'utf-8');
          finalPlan = JSON.parse(content);
        } catch {
          // Worktree plan file not readable - not critical
        }
      }
    }
    if (finalPlan) {
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.TASK_PROGRESS,
        taskId,
        finalPlan,
        exitProjectId
      );
    }

      fileWatcher.unwatch(taskId).catch((err) => {
        console.error(`[agent-events-handlers] Failed to unwatch for ${taskId}:`, err);
      });

      if (processType === "spec-creation") {
        console.warn(`[Task ${taskId}] Spec creation completed with code ${code}`);
        return;
      }

      let task: Task | undefined;
      let project: Project | undefined;

      try {
        const projects = projectStore.getProjects();

        // IMPORTANT: Invalidate cache for all projects to ensure we get fresh data
        // This prevents race conditions where cached task data has stale status
        for (const p of projects) {
          projectStore.invalidateTasksCache(p.id);
        }

        for (const p of projects) {
          const tasks = await projectStore.getTasks(p.id);
          task = tasks.find((t) => t.id === taskId || t.specId === taskId);
          if (task) {
            project = p;
            break;
          }
        }

      if (task && project) {
        const taskTitle = task.title || task.specId;
        const mainPlanPath = getPlanPath(project, task);
        const projectId = project.id; // Capture for closure

        // Capture task values for closure
        const taskSpecId = task.specId;
        const projectPath = project.path;
        const autoBuildPath = project.autoBuildPath;

        // Use shared utility for persisting status (prevents race conditions)
        // Persist to both main project AND worktree (if exists) for consistency
        const persistStatus = (status: TaskStatus) => {
          // Persist to main project
          const mainPersisted = persistPlanStatusSync(mainPlanPath, status, projectId);
          if (mainPersisted) {
            console.warn(`[Task ${taskId}] Persisted status to main plan: ${status}`);
          }

          // Also persist to worktree if it exists
          const worktreePath = findTaskWorktree(projectPath, taskSpecId);
          if (worktreePath) {
            const specsBaseDir = getSpecsDir(autoBuildPath);
            const worktreePlanPath = path.join(
              worktreePath,
              specsBaseDir,
              taskSpecId,
              AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN
            );
            if (existsSync(worktreePlanPath)) {
              const worktreePersisted = persistPlanStatusSync(worktreePlanPath, status, projectId);
              if (worktreePersisted) {
                console.warn(`[Task ${taskId}] Persisted status to worktree plan: ${status}`);
              }
            }
          }
        };

        if (code === 0) {
          notificationService.notifyReviewNeeded(taskTitle, project.id, taskId);

          // Fallback: Ensure status is updated even if COMPLETE phase event was missed
          // This prevents tasks from getting stuck in ai_review status
          // FIX (ACS-71): Only move to human_review if subtasks exist AND are all completed
          // If no subtasks exist, the task is still in planning and shouldn't move to human_review
          const isActiveStatus = task.status === "in_progress" || task.status === "ai_review";
          const hasSubtasks = task.subtasks && task.subtasks.length > 0;
          const hasIncompleteSubtasks =
            hasSubtasks && task.subtasks.some((s) => s.status !== "completed");

          if (isActiveStatus && hasSubtasks && !hasIncompleteSubtasks) {
            // All subtasks completed - safe to move to human_review
            console.warn(
              `[Task ${taskId}] Fallback: Moving to human_review (process exited successfully, all ${task.subtasks.length} subtasks completed)`
            );
            persistStatus("human_review");
            // Include projectId for multi-project filtering (issue #723)
            safeSendToRenderer(
              getMainWindow,
              IPC_CHANNELS.TASK_STATUS_CHANGE,
              taskId,
              "human_review" as TaskStatus,
              projectId
            );
          } else if (isActiveStatus && !hasSubtasks) {
            // No subtasks yet - task is still in planning phase, don't change status
            // This prevents the bug where tasks jump to human_review before planning completes
            console.warn(
              `[Task ${taskId}] Process exited but no subtasks created yet - keeping current status (${task.status})`
            );
          }
        } else {
          notificationService.notifyTaskFailed(taskTitle, project.id, taskId);
          persistStatus("human_review");
          // Include projectId for multi-project filtering (issue #723)
          safeSendToRenderer(
            getMainWindow,
            IPC_CHANNELS.TASK_STATUS_CHANGE,
            taskId,
            "human_review" as TaskStatus,
            projectId
          );
        }
      }
      } catch (error) {
        console.error(`[Task ${taskId}] Exit handler error:`, error);
      }
    })().catch((err) => console.error('[agent-events] Error in exit handler:', err));
  });

  agentManager.on("execution-progress", (taskId: string, progress: ExecutionProgressData) => {
    // Wrap in async IIFE since findTaskAndProject is now async
    (async () => {
      // Use shared helper to find task and project (issue #723 - deduplicate lookup)
      const { task, project } = await findTaskAndProject(taskId);
      const taskProjectId = project?.id;

    // Include projectId in execution progress event for multi-project filtering
    safeSendToRenderer(
      getMainWindow,
      IPC_CHANNELS.TASK_EXECUTION_PROGRESS,
      taskId,
      progress,
      taskProjectId
    );

    const phaseToStatus: Record<string, TaskStatus | null> = {
      idle: null,
      planning: "in_progress",
      coding: "in_progress",
      qa_review: "ai_review",
      qa_fixing: "ai_review",
      complete: "human_review",
      failed: "human_review",
    };

    const newStatus = phaseToStatus[progress.phase];
    // FIX (ACS-55, ACS-71): Validate status transition before sending/persisting
    if (newStatus && validateStatusTransition(task, newStatus, progress.phase)) {
      // Include projectId in status change event for multi-project filtering
      safeSendToRenderer(
        getMainWindow,
        IPC_CHANNELS.TASK_STATUS_CHANGE,
        taskId,
        newStatus,
        taskProjectId
      );

      // Send notifications when task requires attention (FIX: Enhanced real-time progress indicators)
      // Notify immediately on phase transition, not waiting for process exit
      if (task && project) {
        const taskTitle = task.title || task.specId;

        // Notify on task completion
        if (progress.phase === 'complete') {
          notificationService.notifyTaskComplete(taskTitle, project.id, taskId);
        }

        // Notify on task failure
        if (progress.phase === 'failed') {
          notificationService.notifyTaskFailed(taskTitle, project.id, taskId);
        }
      }

      // CRITICAL: Persist status to plan file(s) to prevent flip-flop on task list refresh
      // When getTasks() is called, it reads status from the plan file. Without persisting,
      // the status in the file might differ from the UI, causing inconsistent state.
      // Uses shared utility with locking to prevent race conditions.
      // IMPORTANT: We persist to BOTH main project AND worktree (if exists) to ensure
      // consistency, since getTasks() prefers the worktree version.
      if (task && project) {
        try {
          // Persist to main project plan file
          const mainPlanPath = getPlanPath(project, task);
          persistPlanStatusSync(mainPlanPath, newStatus, project.id);

          // Also persist to worktree plan file if it exists
          // This ensures consistency since getTasks() prefers worktree version
          const worktreePath = findTaskWorktree(project.path, task.specId);
          if (worktreePath) {
            const specsBaseDir = getSpecsDir(project.autoBuildPath);
            const worktreeSpecDir = path.join(worktreePath, specsBaseDir, task.specId);
            const worktreePlanPath = path.join(
              worktreeSpecDir,
              AUTO_BUILD_PATHS.IMPLEMENTATION_PLAN
            );
            if (existsSync(worktreePlanPath)) {
              persistPlanStatusSync(worktreePlanPath, newStatus, project.id);
            }

            // Re-watch the worktree path if the file watcher is still watching the main project path.
            // This handles the case where the task started before the worktree existed:
            // the initial watch fell back to the main project spec dir, but now the worktree
            // is available and implementation_plan.json is being written there.
            const currentWatchDir = fileWatcher.getWatchedSpecDir(taskId);
            if (currentWatchDir && currentWatchDir !== worktreeSpecDir && existsSync(worktreePlanPath)) {
              console.warn(`[agent-events-handlers] Re-watching worktree path for ${taskId}: ${worktreeSpecDir}`);
              fileWatcher.watch(taskId, worktreeSpecDir).catch((err) => {
                console.error(`[agent-events-handlers] Failed to re-watch worktree for ${taskId}:`, err);
              });
            }
          }
        } catch (err) {
          // Ignore persistence errors - UI will still work, just might flip on refresh
          console.warn("[execution-progress] Could not persist status:", err);
        }
      }
      }
    })().catch((err) => console.error('[agent-events] Error in execution-progress handler:', err));
  });

  // ============================================
  // File Watcher Events → Renderer
  // ============================================

  fileWatcher.on("progress", (taskId: string, plan: ImplementationPlan) => {
    // Wrap in async IIFE since findTaskAndProject is now async
    (async () => {
      // Use shared helper to find project (issue #723 - deduplicate lookup)
      const { project } = await findTaskAndProject(taskId);
      safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_PROGRESS, taskId, plan, project?.id);
    })().catch((err) => console.error('[agent-events] Error in progress handler:', err));
  });

  fileWatcher.on("error", (taskId: string, error: string) => {
    // Wrap in async IIFE since findTaskAndProject is now async
    (async () => {
      // Include projectId for multi-project filtering (issue #723)
      const { project } = await findTaskAndProject(taskId);
      safeSendToRenderer(getMainWindow, IPC_CHANNELS.TASK_ERROR, taskId, error, project?.id);
    })().catch((err) => console.error('[agent-events] Error in error handler:', err));
  });
}
