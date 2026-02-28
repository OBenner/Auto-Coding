import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  ProductivitySummary,
  ProductivityTrendPoint,
  ProductivityAnalyticsExportOptions,
  ProductivityAnalyticsFilter,
  FailureMetrics,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Productivity Analytics API operations
 */
export interface ProductivityAnalyticsAPI {
  getProductivitySummary: (projectId: string, filter?: ProductivityAnalyticsFilter) => Promise<IPCResult<ProductivitySummary>>;
  getProductivityTrends: (projectId: string, filter?: ProductivityAnalyticsFilter) => Promise<IPCResult<ProductivityTrendPoint[]>>;
  getFailureMetrics: (projectId: string) => Promise<IPCResult<FailureMetrics>>;
  exportProductivityAnalytics: (projectId: string, options: ProductivityAnalyticsExportOptions) => Promise<IPCResult<string>>;
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

  getFailureMetrics: (projectId: string): Promise<IPCResult<FailureMetrics>> => {
    return invokeIpc(IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_GET_FAILURE_METRICS, projectId);
  },

  exportProductivityAnalytics: (projectId: string, options: ProductivityAnalyticsExportOptions): Promise<IPCResult<string>> => {
    return invokeIpc<IPCResult<string>>(IPC_CHANNELS.PRODUCTIVITY_ANALYTICS_EXPORT, projectId, options);
  }
});
