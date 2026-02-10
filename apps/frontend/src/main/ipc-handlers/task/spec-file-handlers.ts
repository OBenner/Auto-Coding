import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult, ImplementationPlan, QAEscalation } from '../../../shared/types';
import { findTaskAndProject } from './shared';
import {
  readImplementationPlan,
  readQAReport,
  readQAEscalation
} from './spec-file-readers';

/**
 * Register spec file reading IPC handlers
 *
 * These handlers provide read-only access to task specification files:
 * - implementation_plan.json: Implementation stages and progress
 * - qa_report.md: QA testing results
 * - QA_ESCALATION.md: Escalated issues requiring attention
 */
export function registerSpecFileHandlers(): void {
  /**
   * Get implementation plan for a task
   * @param taskId - The task ID
   */
  ipcMain.handle(
    IPC_CHANNELS.TASK_SPEC_IMPLEMENTATION_PLAN_GET,
    async (_, taskId: string): Promise<IPCResult<ImplementationPlan>> => {
      console.warn('[IPC] TASK_SPEC_IMPLEMENTATION_PLAN_GET called with taskId:', taskId);

      const { task, project } = await findTaskAndProject(taskId);
      if (!task || !project) {
        return { success: false, error: 'Task or project not found' };
      }

      try {
        const plan = readImplementationPlan(project, task);
        if (!plan) {
          return { success: false, error: 'Implementation plan not found' };
        }

        console.warn('[IPC] TASK_SPEC_IMPLEMENTATION_PLAN_GET returning plan');
        return { success: true, data: plan };
      } catch (err) {
        console.error('[IPC] TASK_SPEC_IMPLEMENTATION_PLAN_GET error:', err);
        return {
          success: false,
          error: err instanceof Error ? err.message : 'Failed to read implementation plan'
        };
      }
    }
  );

  /**
   * Get QA report for a task
   * @param taskId - The task ID
   */
  ipcMain.handle(
    IPC_CHANNELS.TASK_SPEC_QA_REPORT_GET,
    async (_, taskId: string): Promise<IPCResult<string>> => {
      console.warn('[IPC] TASK_SPEC_QA_REPORT_GET called with taskId:', taskId);

      const { task, project } = await findTaskAndProject(taskId);
      if (!task || !project) {
        return { success: false, error: 'Task or project not found' };
      }

      try {
        const qaReport = readQAReport(project, task);
        if (!qaReport) {
          return { success: false, error: 'QA report not found' };
        }

        console.warn('[IPC] TASK_SPEC_QA_REPORT_GET returning report');
        return { success: true, data: qaReport };
      } catch (err) {
        console.error('[IPC] TASK_SPEC_QA_REPORT_GET error:', err);
        return {
          success: false,
          error: err instanceof Error ? err.message : 'Failed to read QA report'
        };
      }
    }
  );

  /**
   * Get QA escalation for a task
   * @param taskId - The task ID
   */
  ipcMain.handle(
    IPC_CHANNELS.TASK_SPEC_QA_ESCALATION_GET,
    async (_, taskId: string): Promise<IPCResult<QAEscalation>> => {
      console.warn('[IPC] TASK_SPEC_QA_ESCALATION_GET called with taskId:', taskId);

      const { task, project } = await findTaskAndProject(taskId);
      if (!task || !project) {
        return { success: false, error: 'Task or project not found' };
      }

      try {
        const escalation = readQAEscalation(project, task);
        if (!escalation) {
          return { success: false, error: 'QA escalation not found' };
        }

        console.warn('[IPC] TASK_SPEC_QA_ESCALATION_GET returning escalation');
        return { success: true, data: escalation };
      } catch (err) {
        console.error('[IPC] TASK_SPEC_QA_ESCALATION_GET error:', err);
        return {
          success: false,
          error: err instanceof Error ? err.message : 'Failed to read QA escalation'
        };
      }
    }
  );
}
