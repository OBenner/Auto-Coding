import { IPC_CHANNELS } from '../../../shared/constants';
import type { IPCResult } from '../../../shared/types';
import { invokeIpc } from './ipc-utils';

/**
 * Pattern information
 */
export interface Pattern {
  index: number;
  id: string;
  text: string;
  category?: 'naming-conventions' | 'error-handling' | 'code-organization';
  confidence?: 'high' | 'medium' | 'low';
  reasoning?: string;
  approved?: boolean;
}

/**
 * Pattern category type
 */
export type PatternCategory = 'naming-conventions' | 'error-handling' | 'code-organization';

/**
 * Pattern API operations
 */
export interface PatternAPI {
  listPatterns: (
    projectId: string,
    specId: string,
    category?: PatternCategory
  ) => Promise<IPCResult<Pattern[]>>;
  getPatternCategories: () => Promise<IPCResult<PatternCategory[]>>;
  getPatternDetails: (
    projectId: string,
    specId: string,
    patternIndex: number
  ) => Promise<IPCResult<Pattern>>;
  approvePattern: (
    projectId: string,
    specId: string,
    patternIndex: number
  ) => Promise<IPCResult<void>>;
  overridePattern: (
    projectId: string,
    specId: string,
    patternIndex: number,
    newText: string
  ) => Promise<IPCResult<void>>;
  deletePattern: (
    projectId: string,
    specId: string,
    patternIndex: number
  ) => Promise<IPCResult<void>>;
}

/**
 * Creates the Pattern API implementation
 */
export const createPatternAPI = (): PatternAPI => ({
  listPatterns: (
    projectId: string,
    specId: string,
    category?: PatternCategory
  ): Promise<IPCResult<Pattern[]>> =>
    invokeIpc(IPC_CHANNELS.PATTERN_LIST, projectId, specId, category),

  getPatternCategories: (): Promise<IPCResult<PatternCategory[]>> =>
    invokeIpc(IPC_CHANNELS.PATTERN_GET_CATEGORIES),

  getPatternDetails: (
    projectId: string,
    specId: string,
    patternIndex: number
  ): Promise<IPCResult<Pattern>> =>
    invokeIpc(IPC_CHANNELS.PATTERN_GET_DETAILS, projectId, specId, patternIndex),

  approvePattern: (
    projectId: string,
    specId: string,
    patternIndex: number
  ): Promise<IPCResult<void>> =>
    invokeIpc(IPC_CHANNELS.PATTERN_APPROVE, projectId, specId, patternIndex),

  overridePattern: (
    projectId: string,
    specId: string,
    patternIndex: number,
    newText: string
  ): Promise<IPCResult<void>> =>
    invokeIpc(IPC_CHANNELS.PATTERN_OVERRIDE, projectId, specId, patternIndex, newText),

  deletePattern: (
    projectId: string,
    specId: string,
    patternIndex: number
  ): Promise<IPCResult<void>> =>
    invokeIpc(IPC_CHANNELS.PATTERN_DELETE, projectId, specId, patternIndex)
});
