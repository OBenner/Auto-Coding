import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  ModelUsageSummary,
  ModelUsageTrendPoint,
  ModelUsageExportOptions,
  ModelUsageFilter,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Model Usage Analytics API operations
 */
export interface ModelUsageAPI {
  getModelUsageSummary: (projectId: string, filter?: ModelUsageFilter) => Promise<IPCResult<ModelUsageSummary>>;
  getModelUsageTrends: (projectId: string, filter?: ModelUsageFilter) => Promise<IPCResult<ModelUsageTrendPoint[]>>;
  exportModelUsageAnalytics: (projectId: string, options: ModelUsageExportOptions) => Promise<IPCResult<string>>;
}

/**
 * Creates the Model Usage Analytics API implementation
 */
export const createModelUsageAPI = (): ModelUsageAPI => ({
  getModelUsageSummary: (projectId: string, filter?: ModelUsageFilter): Promise<IPCResult<ModelUsageSummary>> => {
    const startDate = filter?.start_date;
    const endDate = filter?.end_date;
    return invokeIpc(IPC_CHANNELS.MODEL_USAGE_GET_SUMMARY, projectId, startDate, endDate);
  },

  getModelUsageTrends: (projectId: string, filter?: ModelUsageFilter): Promise<IPCResult<ModelUsageTrendPoint[]>> => {
    const windowDays = filter?.window_days || 30;
    const granularity = filter?.granularity || 'daily';
    return invokeIpc(IPC_CHANNELS.MODEL_USAGE_GET_TRENDS, projectId, windowDays, granularity);
  },

  exportModelUsageAnalytics: (projectId: string, options: ModelUsageExportOptions): Promise<IPCResult<string>> => {
    return invokeIpc<IPCResult<string>>(IPC_CHANNELS.MODEL_USAGE_EXPORT, projectId, options);
  }
});
