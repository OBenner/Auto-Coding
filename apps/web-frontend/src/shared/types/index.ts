/**
 * Shared types for web frontend
 * Adapted from Electron frontend types
 */

import type { TaskStatus, TaskCategory } from '../constants';

export type { TaskStatus, TaskCategory };

export type ReviewReason = 'completed' | 'errors' | 'qa_rejected' | 'plan_review';
export type SubtaskStatus = 'pending' | 'in_progress' | 'completed' | 'failed';

export type ExecutionPhase =
  | 'idle'
  | 'planning'
  | 'coding'
  | 'qa_review'
  | 'qa_fixing'
  | 'complete'
  | 'failed';

export interface ExecutionProgress {
  phase: ExecutionPhase;
  phaseProgress: number;
  overallProgress?: number;
  currentSubtask?: string;
  message?: string;
}

export interface Subtask {
  id: string;
  title?: string;
  description: string;
  status: SubtaskStatus;
  files?: string[];
}

export interface TaskMetadata {
  category?: TaskCategory;
  complexity?: string;
  impact?: string;
  priority?: string;
  archivedAt?: string;
  prUrl?: string;
}

export interface Task {
  id: string;
  specId: string;
  title: string;
  description: string;
  status: TaskStatus;
  reviewReason?: ReviewReason;
  subtasks: Subtask[];
  metadata?: TaskMetadata;
  executionProgress?: ExecutionProgress;
  createdAt: Date | string;
  updatedAt: Date | string;
}
