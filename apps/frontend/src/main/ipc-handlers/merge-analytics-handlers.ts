import { ipcMain } from 'electron';
import { IPC_CHANNELS } from '../../shared/constants';
import type {
  IPCResult,
  MergeOperationRecord,
  MergeAnalytics,
  ConflictPattern,
  MergeAnalyticsFilter,
  MergeAnalyticsExportOptions,
} from '../../shared/types';
import { promises as fsPromises } from 'fs';
import path from 'path';
import { projectStore } from '../project-store';
import { debugError } from '../../shared/utils/debug-logger';

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
 * Register all merge analytics-related IPC handlers
 */
export function registerMergeAnalyticsHandlers(): void {
  // ============================================
  // Merge Analytics Operations
  // ============================================

  /**
   * Get merge operation history
   */
  ipcMain.handle(
    IPC_CHANNELS.MERGE_ANALYTICS_GET_HISTORY,
    async (
      _,
      projectId: string,
      filter?: MergeAnalyticsFilter
    ): Promise<IPCResult<MergeOperationRecord[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Read operations.json from .auto-claude/merge_analytics/
        const analyticsDir = path.join(project.path, '.auto-claude', 'merge_analytics');
        const operationsFile = path.join(analyticsDir, 'operations.json');

        if (!(await fileExists(operationsFile))) {
          // No operations recorded yet - return empty array
          return { success: true, data: [] };
        }

        const content = await fsPromises.readFile(operationsFile, 'utf-8');
        let operations: MergeOperationRecord[] = JSON.parse(content);

        // Apply filters
        if (filter?.task_id) {
          const taskId = filter.task_id;
          operations = operations.filter((op) => op.tasks_merged.includes(taskId));
        }

        if (filter?.since) {
          const sinceDate = new Date(filter.since);
          operations = operations.filter((op) => new Date(op.timestamp) >= sinceDate);
        }

        if (filter?.success_only) {
          operations = operations.filter((op) => op.success);
        }

        if (filter?.failed_only) {
          operations = operations.filter((op) => !op.success);
        }

        // Apply limit
        if (filter?.limit && filter.limit > 0) {
          operations = operations.slice(0, filter.limit);
        }

        return { success: true, data: operations };
      } catch (error) {
        debugError('[Merge Analytics] Failed to get history:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get merge history: ${errorMessage}` };
      }
    }
  );

  /**
   * Get aggregated merge analytics summary
   */
  ipcMain.handle(
    IPC_CHANNELS.MERGE_ANALYTICS_GET_SUMMARY,
    async (_, projectId: string): Promise<IPCResult<MergeAnalytics>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Read operations.json and conflict_patterns.json
        const analyticsDir = path.join(project.path, '.auto-claude', 'merge_analytics');
        const operationsFile = path.join(analyticsDir, 'operations.json');
        const patternsFile = path.join(analyticsDir, 'conflict_patterns.json');

        // Initialize empty analytics
        const analytics: MergeAnalytics = {
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
          conflict_patterns: [],
        };

        // Load operations if file exists
        if (await fileExists(operationsFile)) {
          const content = await fsPromises.readFile(operationsFile, 'utf-8');
          const operations: MergeOperationRecord[] = JSON.parse(content);

          // Aggregate statistics
          let totalDuration = 0;
          let totalConflicts = 0;
          let totalConflictsAutoResolved = 0;

          operations.forEach((op) => {
            analytics.total_files_merged += op.stats.files_processed;
            analytics.total_ai_calls += op.stats.ai_calls_made;
            analytics.total_tokens_used += op.stats.estimated_tokens_used;
            totalDuration += op.duration_seconds;

            if (op.success) {
              analytics.successful_operations += 1;
            } else {
              analytics.failed_operations += 1;
            }

            totalConflicts += op.stats.conflicts_detected;
            totalConflictsAutoResolved += op.stats.conflicts_auto_resolved;
          });

          analytics.total_operations = operations.length;

          // Calculate rates
          if (analytics.total_operations > 0) {
            analytics.success_rate = analytics.successful_operations / analytics.total_operations;
            analytics.average_duration_seconds = totalDuration / analytics.total_operations;
          }

          analytics.total_conflicts = totalConflicts;
          if (totalConflicts > 0) {
            analytics.auto_merge_rate = totalConflictsAutoResolved / totalConflicts;
          }
        }

        // Load conflict patterns if file exists
        if (await fileExists(patternsFile)) {
          const content = await fsPromises.readFile(patternsFile, 'utf-8');
          analytics.conflict_patterns = JSON.parse(content);
        }

        return { success: true, data: analytics };
      } catch (error) {
        debugError('[Merge Analytics] Failed to get summary:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get merge summary: ${errorMessage}` };
      }
    }
  );

  /**
   * Get conflict patterns
   */
  ipcMain.handle(
    IPC_CHANNELS.MERGE_ANALYTICS_GET_PATTERNS,
    async (_, projectId: string, limit?: number): Promise<IPCResult<ConflictPattern[]>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Read conflict_patterns.json
        const analyticsDir = path.join(project.path, '.auto-claude', 'merge_analytics');
        const patternsFile = path.join(analyticsDir, 'conflict_patterns.json');

        if (!(await fileExists(patternsFile))) {
          // No patterns recorded yet - return empty array
          return { success: true, data: [] };
        }

        const content = await fsPromises.readFile(patternsFile, 'utf-8');
        let patterns: ConflictPattern[] = JSON.parse(content);

        // Apply limit if provided
        if (limit && limit > 0) {
          patterns = patterns.slice(0, limit);
        }

        return { success: true, data: patterns };
      } catch (error) {
        debugError('[Merge Analytics] Failed to get patterns:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to get conflict patterns: ${errorMessage}` };
      }
    }
  );

  /**
   * Export merge analytics to file
   */
  ipcMain.handle(
    IPC_CHANNELS.MERGE_ANALYTICS_EXPORT,
    async (
      _,
      projectId: string,
      options: MergeAnalyticsExportOptions
    ): Promise<IPCResult<string>> => {
      const project = projectStore.getProject(projectId);
      if (!project) {
        return { success: false, error: 'Project not found' };
      }

      try {
        // Read analytics data
        const analyticsDir = path.join(project.path, '.auto-claude', 'merge_analytics');
        const operationsFile = path.join(analyticsDir, 'operations.json');

        if (!(await fileExists(operationsFile))) {
          return { success: false, error: 'No analytics data found' };
        }

        const content = await fsPromises.readFile(operationsFile, 'utf-8');
        let operations: MergeOperationRecord[] = JSON.parse(content);

        // Apply filters if provided
        if (options.filter) {
          const filter = options.filter;
          if (filter.task_id) {
            const taskId = filter.task_id;
            operations = operations.filter((op) =>
              op.tasks_merged.includes(taskId)
            );
          }

          if (options.filter.since) {
            const sinceDate = new Date(options.filter.since);
            operations = operations.filter((op) => new Date(op.timestamp) >= sinceDate);
          }

          if (options.filter.success_only) {
            operations = operations.filter((op) => op.success);
          }

          if (options.filter.failed_only) {
            operations = operations.filter((op) => !op.success);
          }

          if (options.filter.limit && options.filter.limit > 0) {
            operations = operations.slice(0, options.filter.limit);
          }
        }

        // Determine output path
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').substring(0, 19);
        const defaultOutputPath = path.join(
          project.path,
          `merge_analytics_${timestamp}.${options.format}`
        );
        const outputPath = options.output_path || defaultOutputPath;

        // Write export file
        if (options.format === 'json') {
          // Export as JSON
          await fsPromises.writeFile(outputPath, JSON.stringify(operations, null, 2), 'utf-8');
        } else if (options.format === 'csv') {
          // Export as CSV
          const csvLines: string[] = [];

          // Header
          csvLines.push(
            [
              'Operation ID',
              'Timestamp',
              'Tasks',
              'Files Processed',
              'Auto-merged',
              'AI-merged',
              'Conflicts Detected',
              'Conflicts Auto-resolved',
              'Duration (s)',
              'Success',
              'Error',
            ].join(',')
          );

          // Data rows
          operations.forEach((op) => {
            csvLines.push(
              [
                op.operation_id,
                op.timestamp,
                op.tasks_merged.join(';'),
                op.stats.files_processed,
                op.stats.files_auto_merged,
                op.stats.files_ai_merged,
                op.stats.conflicts_detected,
                op.stats.conflicts_auto_resolved,
                op.duration_seconds.toFixed(1),
                op.success ? 'Yes' : 'No',
                op.error || '',
              ].join(',')
            );
          });

          await fsPromises.writeFile(outputPath, csvLines.join('\n'), 'utf-8');
        } else {
          return { success: false, error: `Unknown export format: ${options.format}` };
        }

        return { success: true, data: outputPath };
      } catch (error) {
        debugError('[Merge Analytics] Failed to export:', error);
        const errorMessage = error instanceof Error ? error.message : String(error);
        return { success: false, error: `Failed to export analytics: ${errorMessage}` };
      }
    }
  );
}

