/**
 * Common utility types shared across the application
 */

// AI Provider Types
export type AIProvider = 'claude' | 'litellm' | 'openrouter' | 'zhipuai';

// IPC Types
export interface IPCResult<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
}
