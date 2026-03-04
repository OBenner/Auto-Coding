import { IPC_CHANNELS } from '../../../shared/constants';
import type {
  ModelUsageSummary,
  ModelUsageTrendPoint,
  ModelUsageExportOptions,
  ModelUsageFilter,
  ModelLockConfig,
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

  // Model Lock operations
  listModelLocks: (projectId: string) => Promise<IPCResult<ModelLockConfig>>;
  lockPhaseModel: (projectId: string, phase: string, modelId: string) => Promise<IPCResult<{ success: boolean }>>;
  lockAgentModel: (projectId: string, agentType: string, modelId: string) => Promise<IPCResult<{ success: boolean }>>;
  unlockPhaseModel: (projectId: string, phase: string) => Promise<IPCResult<{ success: boolean }>>;
  unlockAgentModel: (projectId: string, agentType: string) => Promise<IPCResult<{ success: boolean }>>;
  clearModelLocks: (projectId: string) => Promise<IPCResult<{ success: boolean }>>;
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
    const startDate = filter?.start_date;
    const endDate = filter?.end_date;
    return invokeIpc(IPC_CHANNELS.MODEL_USAGE_GET_TRENDS, projectId, windowDays, granularity, startDate, endDate);
  },

  exportModelUsageAnalytics: (projectId: string, options: ModelUsageExportOptions): Promise<IPCResult<string>> => {
    return invokeIpc<IPCResult<string>>(IPC_CHANNELS.MODEL_USAGE_EXPORT, projectId, options);
  },

  // Model Lock operations
  listModelLocks: (projectId: string): Promise<IPCResult<ModelLockConfig>> => {
    return invokeIpc(IPC_CHANNELS.MODEL_LOCK_LIST, projectId);
  },

  lockPhaseModel: (projectId: string, phase: string, modelId: string): Promise<IPCResult<{ success: boolean }>> => {
    return invokeIpc(IPC_CHANNELS.MODEL_LOCK_PHASE, projectId, phase, modelId);
  },

  lockAgentModel: (projectId: string, agentType: string, modelId: string): Promise<IPCResult<{ success: boolean }>> => {
    return invokeIpc(IPC_CHANNELS.MODEL_LOCK_AGENT, projectId, agentType, modelId);
  },

  unlockPhaseModel: (projectId: string, phase: string): Promise<IPCResult<{ success: boolean }>> => {
    return invokeIpc(IPC_CHANNELS.MODEL_UNLOCK_PHASE, projectId, phase);
  },

  unlockAgentModel: (projectId: string, agentType: string): Promise<IPCResult<{ success: boolean }>> => {
    return invokeIpc(IPC_CHANNELS.MODEL_UNLOCK_AGENT, projectId, agentType);
  },

  clearModelLocks: (projectId: string): Promise<IPCResult<{ success: boolean }>> => {
    return invokeIpc(IPC_CHANNELS.MODEL_LOCK_CLEAR, projectId);
  }
});
