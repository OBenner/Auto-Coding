import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  AnalyticsReport,
  MetricsSummary,
  AgentStats,
  TrendDataPoint,
  IPCResult
} from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Analytics API operations
 */
export interface AnalyticsAPI {
  // Operations
  getSummary: (projectId: string) => Promise<IPCResult<MetricsSummary>>;
  getAgentStats: (projectId: string) => Promise<IPCResult<Record<string, AgentStats>>>;
  getTrends: (projectId: string, days?: number) => Promise<IPCResult<TrendDataPoint[]>>;
  getReport: (projectId: string) => Promise<IPCResult<AnalyticsReport>>;
}

/**
 * Creates the Analytics API implementation
 */
export const createAnalyticsAPI = (): AnalyticsAPI => ({
  getSummary: (projectId: string): Promise<IPCResult<MetricsSummary>> =>
    invokeIpc(IPC_CHANNELS.ANALYTICS_GET_SUMMARY, projectId),

  getAgentStats: (projectId: string): Promise<IPCResult<Record<string, AgentStats>>> =>
    invokeIpc(IPC_CHANNELS.ANALYTICS_GET_AGENT_STATS, projectId),

  getTrends: (projectId: string, days?: number): Promise<IPCResult<TrendDataPoint[]>> =>
    invokeIpc(IPC_CHANNELS.ANALYTICS_GET_TRENDS, projectId, days),

  getReport: (projectId: string): Promise<IPCResult<AnalyticsReport>> =>
    invokeIpc(IPC_CHANNELS.ANALYTICS_GET_REPORT, projectId)
});
