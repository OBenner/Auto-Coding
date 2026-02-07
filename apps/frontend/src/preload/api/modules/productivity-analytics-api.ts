import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
  ProductivityAnalyticsExportOptions,
  ProductivityAnalyticsFilter,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Productivity Analytics API operations
 */
export interface ProductivityAnalyticsAPI {
  getProductivitySummary: (projectId: string, filter?: ProductivityAnalyticsFilter) => Promise<IPCResult<ProductivitySummary>>;
  getProductivityTrends: (projectId: string, filter?: ProductivityAnalyticsFilter) => Promise<IPCResult<ProductivityTrendPoint[]>>;
  exportProductivityAnalytics: (projectId: string, options: ProductivityAnalyticsExportOptions) => Promise<IPCResult<{ path: string }>>;
}

/**
 * Creates the Productivity Analytics API implementation
 */
export const createProductivityAnalyticsAPI = (): ProductivityAnalyticsAPI => ({
  getProductivitySummary: (projectId: string, filter?: ProductivityAnalyticsFilter): Promise<IPCResult<ProductivitySummary>> => {
    const startDate = filter?.start_date;
    const endDate = filter?.end_date;
    return invokeIpc(IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_GET_SUMMARY, projectId, startDate, endDate);
  },

  getProductivityTrends: (projectId: string, filter?: ProductivityAnalyticsFilter): Promise<IPCResult<ProductivityTrendPoint[]>> => {
    const windowDays = filter?.window_days || 30;
    const granularity = filter?.granularity || 'daily';
    return invokeIpc(IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_GET_TRENDS, projectId, windowDays, granularity);
  },

  exportProductivityAnalytics: (projectId: string, options: ProductivityAnalyticsExportOptions): Promise<IPCResult<{ path: string }>> => {
    return invokeIpc<IPCResult<{ path: string }>>(IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_EXPORT, projectId, options);
  }
});
