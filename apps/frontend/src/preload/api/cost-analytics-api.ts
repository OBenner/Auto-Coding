import { ipcRenderer } from 'electron';
import type {
  IPCResult,
  CostSummary,
  CostTrendPoint,
} from '../../shared/types';

export interface CostAPI {
  /**
   * Get cost analytics summary for a project
   * @param projectId - Project ID to get cost summary for
   * @param startDate - Optional start date filter (ISO string)
   * @param endDate - Optional end date filter (ISO string)
   */
  getCostSummary: (
    projectId: string,
    startDate?: string,
    endDate?: string
  ) => Promise<IPCResult<CostSummary>>;

  /**
   * Get cost trends over time
   * @param projectId - Project ID to get trends for
   * @param windowDays - Number of days to look back (default: 30)
   * @param granularity - Time granularity: 'daily', 'weekly', 'monthly' (default: 'daily')
   */
  getCostTrends: (
    projectId: string,
    windowDays?: number,
    granularity?: 'daily' | 'weekly' | 'monthly'
  ) => Promise<IPCResult<CostTrendPoint[]>>;

  /**
   * Export cost analytics to file
   * @param projectId - Project ID to export costs for
   * @param format - Export format: 'json' or 'csv'
   * @param outputPath - Optional custom output path
   * @param startDate - Optional start date filter (ISO string)
   * @param endDate - Optional end date filter (ISO string)
   */
  exportCostAnalytics: (
    projectId: string,
    format: 'json' | 'csv',
    outputPath?: string,
    startDate?: string,
    endDate?: string
  ) => Promise<IPCResult<string>>;
}

export const createCostAPI = (): CostAPI => ({
  getCostSummary: (
    projectId: string,
    startDate?: string,
    endDate?: string
  ): Promise<IPCResult<CostSummary>> =>
    ipcRenderer.invoke('costAnalytics:getSummary', projectId, startDate, endDate),

  getCostTrends: (
    projectId: string,
    windowDays: number = 30,
    granularity: 'daily' | 'weekly' | 'monthly' = 'daily'
  ): Promise<IPCResult<CostTrendPoint[]>> =>
    ipcRenderer.invoke('costAnalytics:getTrends', projectId, windowDays, granularity),

  exportCostAnalytics: (
    projectId: string,
    format: 'json' | 'csv',
    outputPath?: string,
    startDate?: string,
    endDate?: string
  ): Promise<IPCResult<string>> =>
    ipcRenderer.invoke('costAnalytics:export', projectId, format, outputPath, startDate, endDate)
});
