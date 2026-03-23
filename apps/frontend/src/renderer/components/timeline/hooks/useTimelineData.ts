/**
 * useTimelineData hook
 *
 * Hook for accessing and transforming implementation plan and execution progress
 * data into TimelineData format for visual timeline component.
 */

import { useEffect, useState, useCallback, useMemo, useRef } from 'react';
import type {
  ImplementationPlan,
  Phase,
  PlanSubtask,
  ExecutionProgress,
  SubtaskStatus,
} from '../../../../shared/types';
import type {
  TimelineData,
  TimelinePhase,
  TimelineSubtask,
  TimelineMetadata,
  TimelineAgentType,
  PhaseProgressData,
} from '../types';

export interface UseTimelineDataResult {
  /** Timeline data with phases, subtasks, and progress */
  timelineData: TimelineData | null;
  /** Loading state */
  isLoading: boolean;
  /** Error message if loading failed */
  error: string | null;
  /** Refresh timeline data */
  refresh: () => void;
  /** Get phase by phase number */
  getPhase: (phaseNumber: number) => TimelinePhase | undefined;
  /** Get subtask by ID */
  getSubtask: (subtaskId: string) => TimelineSubtask | undefined;
  /** Get subtasks for a phase */
  getSubtasksForPhase: (phaseNumber: number) => TimelineSubtask[];
  /** Get current executing subtask */
  getCurrentSubtask: () => TimelineSubtask | undefined;
  /** Get overall progress percentage */
  getOverallProgress: () => number;
}

/**
 * Determine agent type for a phase based on phase name and type
 */
function getAgentTypeForPhase(phase: Phase): TimelineAgentType {
  const name = phase.name.toLowerCase();
  const type = phase.type.toLowerCase();

  if (name.includes('plan') || type.includes('plan') || name.includes('discovery')) {
    return 'planner';
  }
  if (name.includes('qa') || name.includes('review') || name.includes('validation') || name.includes('test')) {
    return 'qa';
  }
  // Default to coder for implementation/coding phases
  return 'coder';
}

/**
 * Transform implementation plan phase to timeline phase
 */
function transformPhase(
  phase: Phase,
  displayIndex: number,
  executionProgress?: ExecutionProgress
): TimelinePhase {
  const agentType = getAgentTypeForPhase(phase);

  // Calculate progress data for this phase
  const completedSubtasks = phase.subtasks.filter((st) => st.status === 'completed').length;
  const totalSubtasks = phase.subtasks.length;

  // Check if this is the current phase and identify current subtask
  const isCurrentPhase = executionProgress?.phase === phase.type;
  const currentSubtaskId = isCurrentPhase ? executionProgress?.currentSubtask : undefined;

  // Only the active phase gets the execution status; others derive from subtask completion
  const status = isCurrentPhase
    ? (executionProgress?.phase || 'idle')
    : (completedSubtasks === totalSubtasks && totalSubtasks > 0 ? 'complete' : 'idle');

  const progress: PhaseProgressData = {
    status,
    progress: totalSubtasks > 0 ? Math.round((completedSubtasks / totalSubtasks) * 100) : 0,
    currentSubtaskId,
    completedCount: completedSubtasks,
    totalCount: totalSubtasks,
  };

  return {
    ...phase,
    displayIndex,
    agentType,
    layout: {
      y: displayIndex * 120, // Will be calculated by layout utility
      height: 120,
      width: 0, // Will be calculated by layout utility
      totalWidth: 0, // Will be calculated by layout utility
    },
    progress,
  };
}

/**
 * Transform implementation plan subtask to timeline subtask
 */
function transformSubtask(
  subtask: PlanSubtask,
  phaseNumber: number,
  displayIndex: number
): TimelineSubtask {
  return {
    ...subtask,
    phaseId: `phase-${phaseNumber}`,
    displayIndex,
    layout: {
      x: 0, // Will be calculated by layout utility
      y: 0, // Will be calculated by layout utility
      width: 150, // Will be calculated by layout utility
      height: 60, // Will be calculated by layout utility
      zIndex: 10,
    },
    files: subtask.verification?.run ? [subtask.verification.run] : [],
    dependsOn: [], // Will be populated from dependency analysis
  };
}

/**
 * Calculate timeline metadata
 */
function calculateMetadata(
  phases: TimelinePhase[],
  subtasks: TimelineSubtask[],
  executionProgress?: ExecutionProgress,
  plan?: ImplementationPlan
): TimelineMetadata {
  const completedSubtasks = subtasks.filter((st) => st.status === 'completed').length;
  const totalSubtasks = subtasks.length;
  const overallProgress = totalSubtasks > 0 ? Math.round((completedSubtasks / totalSubtasks) * 100) : 0;

  // Calculate total estimated time (placeholder - will be enhanced with actual time tracking)
  const totalEstimatedTime = 0;
  const totalActualTime = executionProgress?.elapsed_seconds ?? 0;

  return {
    totalEstimatedTime,
    totalActualTime,
    completedSubtasks,
    totalSubtasks,
    overallProgress,
    createdAt: plan?.created_at ? new Date(plan.created_at) : new Date(),
    updatedAt: plan?.updated_at ? new Date(plan.updated_at) : new Date(),
  };
}

/**
 * Hook for accessing timeline data
 */
export function useTimelineData(taskId: string, executionProgress?: ExecutionProgress): UseTimelineDataResult {
  const [implementationPlan, setImplementationPlan] = useState<ImplementationPlan | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Request token to ignore stale async responses
  const requestIdRef = useRef(0);

  /**
   * Load implementation plan
   */
  const loadData = useCallback(async () => {
    const currentRequestId = ++requestIdRef.current;

    setIsLoading(true);
    setError(null);

    try {
      // Load implementation plan
      const planResult = await window.electronAPI.getImplementationPlan(taskId);

      // Ignore stale response if taskId changed during await
      if (currentRequestId !== requestIdRef.current) return;

      if (!planResult.success || !planResult.data) {
        throw new Error(planResult.error || 'timeline:errors.loadPlan');
      }
      setImplementationPlan(planResult.data);
    } catch (err) {
      // Ignore stale errors
      if (currentRequestId !== requestIdRef.current) return;
      setError(err instanceof Error ? err.message : 'timeline:errors.loadData');
    } finally {
      if (currentRequestId === requestIdRef.current) {
        setIsLoading(false);
      }
    }
  }, [taskId]);

  /**
   * Transform data into TimelineData format
   */
  const timelineData = useMemo((): TimelineData | null => {
    if (!implementationPlan) {
      return null;
    }

    // Transform phases
    const phases: TimelinePhase[] = implementationPlan.phases.map((phase, index) =>
      transformPhase(phase, index, executionProgress)
    );

    // Transform subtasks
    const subtasks: TimelineSubtask[] = implementationPlan.phases.flatMap((phase) =>
      phase.subtasks.map((subtask, index) =>
        transformSubtask(subtask, phase.phase, index)
      )
    );

    // Calculate metadata
    const metadata = calculateMetadata(phases, subtasks, executionProgress, implementationPlan);

    return {
      phases,
      subtasks,
      executionProgress,
      metadata,
    };
  }, [implementationPlan, executionProgress]);

  /**
   * Get phase by phase number
   */
  const getPhase = useCallback(
    (phaseNumber: number): TimelinePhase | undefined => {
      return timelineData?.phases.find((phase) => phase.phase === phaseNumber);
    },
    [timelineData]
  );

  /**
   * Get subtask by ID
   */
  const getSubtask = useCallback(
    (subtaskId: string): TimelineSubtask | undefined => {
      return timelineData?.subtasks.find((subtask) => subtask.id === subtaskId);
    },
    [timelineData]
  );

  /**
   * Get subtasks for a phase
   */
  const getSubtasksForPhase = useCallback(
    (phaseNumber: number): TimelineSubtask[] => {
      return timelineData?.subtasks.filter((subtask) => subtask.phaseId === `phase-${phaseNumber}`) || [];
    },
    [timelineData]
  );

  /**
   * Get current executing subtask
   */
  const getCurrentSubtask = useCallback((): TimelineSubtask | undefined => {
    if (!executionProgress?.currentSubtask) {
      return undefined;
    }
    return timelineData?.subtasks.find((subtask) => subtask.id === executionProgress.currentSubtask);
  }, [timelineData, executionProgress]);

  /**
   * Get overall progress percentage
   */
  const getOverallProgress = useCallback((): number => {
    return timelineData?.metadata.overallProgress ?? 0;
  }, [timelineData]);

  /**
   * Refresh timeline data
   */
  const refresh = useCallback(() => {
    loadData();
  }, [loadData]);

  // Load data on mount and when taskId changes
  useEffect(() => {
    loadData();
  }, [loadData]);

  return {
    timelineData,
    isLoading,
    error,
    refresh,
    getPhase,
    getSubtask,
    getSubtasksForPhase,
    getCurrentSubtask,
    getOverallProgress,
  };
}
