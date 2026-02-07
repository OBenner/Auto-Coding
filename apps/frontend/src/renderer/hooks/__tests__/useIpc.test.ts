/**
 * @vitest-environment jsdom
 */

/**
 * Tests for IPC Hooks
 *
 * Tests IPC event listeners, batching logic, project filtering, and app settings/version hooks.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useIpcListeners, useAppSettings, useAppVersion } from '../useIpc';
import type { ImplementationPlan, TaskStatus, ExecutionProgress, RoadmapGenerationStatus, Roadmap, RateLimitInfo, SDKRateLimitInfo, AuthFailureInfo } from '../../../shared/types';
import { useTaskStore } from '../../stores/task-store';
import { useRoadmapStore } from '../../stores/roadmap-store';
import { useRateLimitStore } from '../../stores/rate-limit-store';
import { useAuthFailureStore } from '../../stores/auth-failure-store';
import { useProjectStore } from '../../stores/project-store';

// Mock stores
vi.mock('../../stores/task-store');
vi.mock('../../stores/roadmap-store');
vi.mock('../../stores/rate-limit-store');
vi.mock('../../stores/auth-failure-store');
vi.mock('../../stores/project-store');

// Mock react-dom batched updates
vi.mock('react-dom', () => ({
  unstable_batchedUpdates: (fn: () => void) => fn()
}));

// Setup mock electronAPI
const mockOnTaskProgress = vi.fn();
const mockOnTaskError = vi.fn();
const mockOnTaskLog = vi.fn();
const mockOnTaskStatusChange = vi.fn();
const mockOnTaskExecutionProgress = vi.fn();
const mockOnRoadmapProgress = vi.fn();
const mockOnRoadmapComplete = vi.fn();
const mockOnRoadmapError = vi.fn();
const mockOnRoadmapStopped = vi.fn();
const mockOnTerminalRateLimit = vi.fn();
const mockOnSDKRateLimit = vi.fn();
const mockOnAuthFailure = vi.fn();
const mockGetSettings = vi.fn();
const mockSaveSettings = vi.fn();
const mockGetAppVersion = vi.fn();

// Mock store actions
const mockUpdateTaskFromPlan = vi.fn();
const mockUpdateTaskStatus = vi.fn();
const mockUpdateExecutionProgress = vi.fn();
const mockAppendLog = vi.fn();
const mockBatchAppendLogs = vi.fn();
const mockSetError = vi.fn();
const mockShowRateLimitModal = vi.fn();
const mockShowSDKRateLimitModal = vi.fn();
const mockShowAuthFailureModal = vi.fn();
const mockSetGenerationStatus = vi.fn();
const mockSetRoadmap = vi.fn();

describe('useIpcListeners', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Setup window.electronAPI mock
    (window as unknown as { electronAPI: unknown }).electronAPI = {
      onTaskProgress: mockOnTaskProgress.mockReturnValue(() => {}),
      onTaskError: mockOnTaskError.mockReturnValue(() => {}),
      onTaskLog: mockOnTaskLog.mockReturnValue(() => {}),
      onTaskStatusChange: mockOnTaskStatusChange.mockReturnValue(() => {}),
      onTaskExecutionProgress: mockOnTaskExecutionProgress.mockReturnValue(() => {}),
      onRoadmapProgress: mockOnRoadmapProgress.mockReturnValue(() => {}),
      onRoadmapComplete: mockOnRoadmapComplete.mockReturnValue(() => {}),
      onRoadmapError: mockOnRoadmapError.mockReturnValue(() => {}),
      onRoadmapStopped: mockOnRoadmapStopped.mockReturnValue(() => {}),
      onTerminalRateLimit: mockOnTerminalRateLimit.mockReturnValue(() => {}),
      onSDKRateLimit: mockOnSDKRateLimit.mockReturnValue(() => {}),
      onAuthFailure: mockOnAuthFailure.mockReturnValue(() => {}),
      getSettings: mockGetSettings,
      saveSettings: mockSaveSettings,
      getAppVersion: mockGetAppVersion
    };

    // Setup store mocks
    (useTaskStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
      tasks: []
    });

    vi.mocked(useTaskStore).mockImplementation((selector) => {
      const state = {
        updateTaskFromPlan: mockUpdateTaskFromPlan,
        updateTaskStatus: mockUpdateTaskStatus,
        updateExecutionProgress: mockUpdateExecutionProgress,
        appendLog: mockAppendLog,
        batchAppendLogs: mockBatchAppendLogs,
        setError: mockSetError,
        tasks: []
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    vi.mocked(useRoadmapStore).mockImplementation((selector) => {
      const state = {
        setGenerationStatus: mockSetGenerationStatus,
        setRoadmap: mockSetRoadmap,
        currentProjectId: null
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    (useRoadmapStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
      setGenerationStatus: mockSetGenerationStatus,
      setRoadmap: mockSetRoadmap,
      currentProjectId: null
    });

    vi.mocked(useRateLimitStore).mockImplementation((selector) => {
      const state = {
        showRateLimitModal: mockShowRateLimitModal,
        showSDKRateLimitModal: mockShowSDKRateLimitModal
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    (useRateLimitStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
      showRateLimitModal: mockShowRateLimitModal,
      showSDKRateLimitModal: mockShowSDKRateLimitModal
    });

    vi.mocked(useAuthFailureStore).mockImplementation((selector) => {
      const state = {
        showAuthFailureModal: mockShowAuthFailureModal
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    (useAuthFailureStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
      showAuthFailureModal: mockShowAuthFailureModal
    });

    vi.mocked(useProjectStore).mockImplementation((selector) => {
      const state = {
        selectedProjectId: null
      };
      return typeof selector === 'function' ? selector(state) : state;
    });

    (useProjectStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
      selectedProjectId: null
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    delete (window as unknown as { electronAPI?: unknown }).electronAPI;
  });

  describe('subscription', () => {
    it('should subscribe to all IPC events on mount', () => {
      renderHook(() => useIpcListeners());

      expect(mockOnTaskProgress).toHaveBeenCalledTimes(1);
      expect(mockOnTaskError).toHaveBeenCalledTimes(1);
      expect(mockOnTaskLog).toHaveBeenCalledTimes(1);
      expect(mockOnTaskStatusChange).toHaveBeenCalledTimes(1);
      expect(mockOnTaskExecutionProgress).toHaveBeenCalledTimes(1);
      expect(mockOnRoadmapProgress).toHaveBeenCalledTimes(1);
      expect(mockOnRoadmapComplete).toHaveBeenCalledTimes(1);
      expect(mockOnRoadmapError).toHaveBeenCalledTimes(1);
      expect(mockOnRoadmapStopped).toHaveBeenCalledTimes(1);
      expect(mockOnTerminalRateLimit).toHaveBeenCalledTimes(1);
      expect(mockOnSDKRateLimit).toHaveBeenCalledTimes(1);
      expect(mockOnAuthFailure).toHaveBeenCalledTimes(1);
    });

    it('should unsubscribe from all events on unmount', () => {
      const unsubProgress = vi.fn();
      const unsubError = vi.fn();
      const unsubLog = vi.fn();
      const unsubStatus = vi.fn();
      const unsubExecProgress = vi.fn();
      const unsubRoadmapProgress = vi.fn();
      const unsubRoadmapComplete = vi.fn();
      const unsubRoadmapError = vi.fn();
      const unsubRoadmapStopped = vi.fn();
      const unsubRateLimit = vi.fn();
      const unsubSDKRateLimit = vi.fn();
      const unsubAuthFailure = vi.fn();

      mockOnTaskProgress.mockReturnValue(unsubProgress);
      mockOnTaskError.mockReturnValue(unsubError);
      mockOnTaskLog.mockReturnValue(unsubLog);
      mockOnTaskStatusChange.mockReturnValue(unsubStatus);
      mockOnTaskExecutionProgress.mockReturnValue(unsubExecProgress);
      mockOnRoadmapProgress.mockReturnValue(unsubRoadmapProgress);
      mockOnRoadmapComplete.mockReturnValue(unsubRoadmapComplete);
      mockOnRoadmapError.mockReturnValue(unsubRoadmapError);
      mockOnRoadmapStopped.mockReturnValue(unsubRoadmapStopped);
      mockOnTerminalRateLimit.mockReturnValue(unsubRateLimit);
      mockOnSDKRateLimit.mockReturnValue(unsubSDKRateLimit);
      mockOnAuthFailure.mockReturnValue(unsubAuthFailure);

      const { unmount } = renderHook(() => useIpcListeners());
      unmount();

      expect(unsubProgress).toHaveBeenCalled();
      expect(unsubError).toHaveBeenCalled();
      expect(unsubLog).toHaveBeenCalled();
      expect(unsubStatus).toHaveBeenCalled();
      expect(unsubExecProgress).toHaveBeenCalled();
      expect(unsubRoadmapProgress).toHaveBeenCalled();
      expect(unsubRoadmapComplete).toHaveBeenCalled();
      expect(unsubRoadmapError).toHaveBeenCalled();
      expect(unsubRoadmapStopped).toHaveBeenCalled();
      expect(unsubRateLimit).toHaveBeenCalled();
      expect(unsubSDKRateLimit).toHaveBeenCalled();
      expect(unsubAuthFailure).toHaveBeenCalled();
    });
  });

  describe('task progress batching', () => {
    it('should batch task plan updates within 16ms window', () => {
      let progressCallback: ((taskId: string, plan: ImplementationPlan, projectId?: string) => void) | undefined;
      mockOnTaskProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const plan: ImplementationPlan = {
        taskId: 'task-1',
        subtasks: [],
        estimatedComplexity: 'medium',
        requiresReasoning: false
      };

      act(() => {
        progressCallback?.('task-1', plan);
      });

      // Should not update immediately
      expect(mockUpdateTaskFromPlan).not.toHaveBeenCalled();

      // Advance timer to trigger batch flush (16ms)
      act(() => {
        vi.advanceTimersByTime(16);
      });

      expect(mockUpdateTaskFromPlan).toHaveBeenCalledWith('task-1', plan);
    });

    it('should batch multiple log messages together', () => {
      let logCallback: ((taskId: string, log: string, projectId?: string) => void) | undefined;
      mockOnTaskLog.mockImplementation((cb) => {
        logCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      act(() => {
        logCallback?.('task-1', 'Log line 1');
        logCallback?.('task-1', 'Log line 2');
        logCallback?.('task-1', 'Log line 3');
      });

      // Should not update immediately
      expect(mockBatchAppendLogs).not.toHaveBeenCalled();

      // Advance timer to trigger batch flush
      act(() => {
        vi.advanceTimersByTime(16);
      });

      // Should batch all logs in one call
      expect(mockBatchAppendLogs).toHaveBeenCalledTimes(1);
      expect(mockBatchAppendLogs).toHaveBeenCalledWith('task-1', ['Log line 1', 'Log line 2', 'Log line 3']);
    });

    it('should batch status and progress updates together', () => {
      let statusCallback: ((taskId: string, status: TaskStatus, projectId?: string) => void) | undefined;
      let progressCallback: ((taskId: string, progress: ExecutionProgress, projectId?: string) => void) | undefined;

      mockOnTaskStatusChange.mockImplementation((cb) => {
        statusCallback = cb;
        return () => {};
      });

      mockOnTaskExecutionProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      // Mock task store to have existing phase to avoid phase change detection
      (useTaskStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        tasks: [{
          id: 'task-1',
          executionProgress: {
            phase: 'coding',
            currentSubtask: 'subtask-1',
            subtaskProgress: 30
          }
        }]
      });

      renderHook(() => useIpcListeners());

      const status: TaskStatus = 'running';
      const progress: ExecutionProgress = {
        phase: 'coding', // Same phase to avoid immediate application
        currentSubtask: 'subtask-2',
        subtaskProgress: 50
      };

      act(() => {
        statusCallback?.('task-1', status);
        progressCallback?.('task-1', progress);
      });

      // Should not update immediately (batched)
      expect(mockUpdateTaskStatus).not.toHaveBeenCalled();
      expect(mockUpdateExecutionProgress).not.toHaveBeenCalled();

      // Advance timer to trigger batch flush
      act(() => {
        vi.advanceTimersByTime(16);
      });

      // Both updates should be applied
      expect(mockUpdateTaskStatus).toHaveBeenCalledWith('task-1', status);
      expect(mockUpdateExecutionProgress).toHaveBeenCalledWith('task-1', progress);
    });
  });

  describe('phase change immediate updates', () => {
    it('should apply phase changes immediately without batching', () => {
      let progressCallback: ((taskId: string, progress: ExecutionProgress, projectId?: string) => void) | undefined;
      mockOnTaskExecutionProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const progress: ExecutionProgress = {
        phase: 'coding',
        currentSubtask: 'subtask-1',
        subtaskProgress: 50
      };

      act(() => {
        progressCallback?.('task-1', progress);
      });

      // Phase change should be applied immediately
      expect(mockUpdateExecutionProgress).toHaveBeenCalledWith('task-1', progress);
    });

    it('should flush pending updates before applying phase change', () => {
      let logCallback: ((taskId: string, log: string, projectId?: string) => void) | undefined;
      let progressCallback: ((taskId: string, progress: ExecutionProgress, projectId?: string) => void) | undefined;

      mockOnTaskLog.mockImplementation((cb) => {
        logCallback = cb;
        return () => {};
      });

      mockOnTaskExecutionProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      // Queue some logs
      act(() => {
        logCallback?.('task-1', 'Log line 1');
        logCallback?.('task-1', 'Log line 2');
      });

      // Trigger phase change - should flush logs first
      const progress: ExecutionProgress = {
        phase: 'planning',
        currentSubtask: null,
        subtaskProgress: 0
      };

      act(() => {
        progressCallback?.('task-1', progress);
      });

      // Logs should be flushed
      expect(mockBatchAppendLogs).toHaveBeenCalledWith('task-1', ['Log line 1', 'Log line 2']);
      // Phase change should be applied immediately
      expect(mockUpdateExecutionProgress).toHaveBeenCalledWith('task-1', progress);
    });
  });

  describe('project filtering', () => {
    it('should accept events when no projectId is provided (backward compatibility)', () => {
      let progressCallback: ((taskId: string, plan: ImplementationPlan, projectId?: string) => void) | undefined;
      mockOnTaskProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const plan: ImplementationPlan = {
        taskId: 'task-1',
        subtasks: [],
        estimatedComplexity: 'medium',
        requiresReasoning: false
      };

      act(() => {
        progressCallback?.('task-1', plan); // No projectId
      });

      act(() => {
        vi.advanceTimersByTime(16);
      });

      expect(mockUpdateTaskFromPlan).toHaveBeenCalledWith('task-1', plan);
    });

    it('should accept events when no project is selected', () => {
      let progressCallback: ((taskId: string, plan: ImplementationPlan, projectId?: string) => void) | undefined;
      mockOnTaskProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const plan: ImplementationPlan = {
        taskId: 'task-1',
        subtasks: [],
        estimatedComplexity: 'medium',
        requiresReasoning: false
      };

      act(() => {
        progressCallback?.('task-1', plan, 'project-1');
      });

      act(() => {
        vi.advanceTimersByTime(16);
      });

      expect(mockUpdateTaskFromPlan).toHaveBeenCalledWith('task-1', plan);
    });

    it('should reject events from different project', () => {
      (useProjectStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        selectedProjectId: 'project-1'
      });

      let progressCallback: ((taskId: string, plan: ImplementationPlan, projectId?: string) => void) | undefined;
      mockOnTaskProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const plan: ImplementationPlan = {
        taskId: 'task-1',
        subtasks: [],
        estimatedComplexity: 'medium',
        requiresReasoning: false
      };

      act(() => {
        progressCallback?.('task-1', plan, 'project-2'); // Different project
      });

      act(() => {
        vi.advanceTimersByTime(16);
      });

      expect(mockUpdateTaskFromPlan).not.toHaveBeenCalled();
    });

    it('should accept events from same project', () => {
      (useProjectStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        selectedProjectId: 'project-1'
      });

      let progressCallback: ((taskId: string, plan: ImplementationPlan, projectId?: string) => void) | undefined;
      mockOnTaskProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const plan: ImplementationPlan = {
        taskId: 'task-1',
        subtasks: [],
        estimatedComplexity: 'medium',
        requiresReasoning: false
      };

      act(() => {
        progressCallback?.('task-1', plan, 'project-1'); // Same project
      });

      act(() => {
        vi.advanceTimersByTime(16);
      });

      expect(mockUpdateTaskFromPlan).toHaveBeenCalledWith('task-1', plan);
    });
  });

  describe('error handling', () => {
    it('should display errors immediately without batching', () => {
      let errorCallback: ((taskId: string, error: string, projectId?: string) => void) | undefined;
      mockOnTaskError.mockImplementation((cb) => {
        errorCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      act(() => {
        errorCallback?.('task-1', 'Test error');
      });

      // Should be applied immediately, no batching
      expect(mockSetError).toHaveBeenCalledWith('Task task-1: Test error');
      expect(mockAppendLog).toHaveBeenCalledWith('task-1', '[ERROR] Test error');
    });
  });

  describe('roadmap events', () => {
    it('should update roadmap progress for current project', () => {
      (useRoadmapStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        setGenerationStatus: mockSetGenerationStatus,
        setRoadmap: mockSetRoadmap,
        currentProjectId: 'project-1'
      });

      let progressCallback: ((projectId: string, status: RoadmapGenerationStatus) => void) | undefined;
      mockOnRoadmapProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const status: RoadmapGenerationStatus = {
        phase: 'analyzing',
        progress: 50,
        message: 'Analyzing codebase'
      };

      act(() => {
        progressCallback?.('project-1', status);
      });

      expect(mockSetGenerationStatus).toHaveBeenCalledWith(status);
    });

    it('should ignore roadmap progress for different project', () => {
      (useRoadmapStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        setGenerationStatus: mockSetGenerationStatus,
        setRoadmap: mockSetRoadmap,
        currentProjectId: 'project-1'
      });

      let progressCallback: ((projectId: string, status: RoadmapGenerationStatus) => void) | undefined;
      mockOnRoadmapProgress.mockImplementation((cb) => {
        progressCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const status: RoadmapGenerationStatus = {
        phase: 'analyzing',
        progress: 50,
        message: 'Analyzing codebase'
      };

      act(() => {
        progressCallback?.('project-2', status);
      });

      expect(mockSetGenerationStatus).not.toHaveBeenCalled();
    });

    it('should handle roadmap completion', () => {
      (useRoadmapStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        setGenerationStatus: mockSetGenerationStatus,
        setRoadmap: mockSetRoadmap,
        currentProjectId: 'project-1'
      });

      let completeCallback: ((projectId: string, roadmap: Roadmap) => void) | undefined;
      mockOnRoadmapComplete.mockImplementation((cb) => {
        completeCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const roadmap: Roadmap = {
        projectId: 'project-1',
        features: [],
        phases: []
      };

      act(() => {
        completeCallback?.('project-1', roadmap);
      });

      expect(mockSetRoadmap).toHaveBeenCalledWith(roadmap);
      expect(mockSetGenerationStatus).toHaveBeenCalledWith({
        phase: 'complete',
        progress: 100,
        message: 'Roadmap ready'
      });
    });

    it('should handle roadmap errors', () => {
      (useRoadmapStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        setGenerationStatus: mockSetGenerationStatus,
        setRoadmap: mockSetRoadmap,
        currentProjectId: 'project-1'
      });

      let errorCallback: ((projectId: string, error: string) => void) | undefined;
      mockOnRoadmapError.mockImplementation((cb) => {
        errorCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      act(() => {
        errorCallback?.('project-1', 'Failed to generate roadmap');
      });

      expect(mockSetGenerationStatus).toHaveBeenCalledWith({
        phase: 'error',
        progress: 0,
        message: 'Generation failed',
        error: 'Failed to generate roadmap'
      });
    });

    it('should handle roadmap stopped event', () => {
      (useRoadmapStore as unknown as { getState: () => unknown }).getState = vi.fn().mockReturnValue({
        setGenerationStatus: mockSetGenerationStatus,
        setRoadmap: mockSetRoadmap,
        currentProjectId: 'project-1'
      });

      let stoppedCallback: ((projectId: string) => void) | undefined;
      mockOnRoadmapStopped.mockImplementation((cb) => {
        stoppedCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      act(() => {
        stoppedCallback?.('project-1');
      });

      expect(mockSetGenerationStatus).toHaveBeenCalledWith({
        phase: 'idle',
        progress: 0,
        message: 'Generation stopped'
      });
    });
  });

  describe('rate limit events', () => {
    it('should show terminal rate limit modal', () => {
      let rateLimitCallback: ((info: RateLimitInfo) => void) | undefined;
      mockOnTerminalRateLimit.mockImplementation((cb) => {
        rateLimitCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const info: RateLimitInfo = {
        taskId: 'task-1',
        detectedAt: new Date().toISOString(),
        message: 'Rate limit exceeded'
      };

      act(() => {
        rateLimitCallback?.(info);
      });

      expect(mockShowRateLimitModal).toHaveBeenCalledWith(
        expect.objectContaining({
          taskId: 'task-1',
          message: 'Rate limit exceeded',
          detectedAt: expect.any(Date)
        })
      );
    });

    it('should show SDK rate limit modal', () => {
      let sdkRateLimitCallback: ((info: SDKRateLimitInfo) => void) | undefined;
      mockOnSDKRateLimit.mockImplementation((cb) => {
        sdkRateLimitCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const info: SDKRateLimitInfo = {
        operation: 'changelog',
        detectedAt: new Date().toISOString(),
        message: 'SDK rate limit exceeded'
      };

      act(() => {
        sdkRateLimitCallback?.(info);
      });

      expect(mockShowSDKRateLimitModal).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: 'changelog',
          message: 'SDK rate limit exceeded',
          detectedAt: expect.any(Date)
        })
      );
    });

    it('should convert string detectedAt to Date object for terminal rate limit', () => {
      let rateLimitCallback: ((info: RateLimitInfo) => void) | undefined;
      mockOnTerminalRateLimit.mockImplementation((cb) => {
        rateLimitCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const dateString = '2024-01-01T12:00:00Z';
      const info: RateLimitInfo = {
        taskId: 'task-1',
        detectedAt: dateString,
        message: 'Rate limit exceeded'
      };

      act(() => {
        rateLimitCallback?.(info);
      });

      expect(mockShowRateLimitModal).toHaveBeenCalledWith(
        expect.objectContaining({
          detectedAt: new Date(dateString)
        })
      );
    });
  });

  describe('auth failure events', () => {
    it('should show auth failure modal', () => {
      let authFailureCallback: ((info: AuthFailureInfo) => void) | undefined;
      mockOnAuthFailure.mockImplementation((cb) => {
        authFailureCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const info: AuthFailureInfo = {
        operation: 'task-execution',
        detectedAt: new Date().toISOString(),
        message: 'Authentication failed'
      };

      act(() => {
        authFailureCallback?.(info);
      });

      expect(mockShowAuthFailureModal).toHaveBeenCalledWith(
        expect.objectContaining({
          operation: 'task-execution',
          message: 'Authentication failed',
          detectedAt: expect.any(Date)
        })
      );
    });

    it('should convert string detectedAt to Date object for auth failure', () => {
      let authFailureCallback: ((info: AuthFailureInfo) => void) | undefined;
      mockOnAuthFailure.mockImplementation((cb) => {
        authFailureCallback = cb;
        return () => {};
      });

      renderHook(() => useIpcListeners());

      const dateString = '2024-01-01T12:00:00Z';
      const info: AuthFailureInfo = {
        operation: 'task-execution',
        detectedAt: dateString,
        message: 'Authentication failed'
      };

      act(() => {
        authFailureCallback?.(info);
      });

      expect(mockShowAuthFailureModal).toHaveBeenCalledWith(
        expect.objectContaining({
          detectedAt: new Date(dateString)
        })
      );
    });
  });

  describe('cleanup', () => {
    it('should flush pending updates on unmount', () => {
      let logCallback: ((taskId: string, log: string, projectId?: string) => void) | undefined;
      mockOnTaskLog.mockImplementation((cb) => {
        logCallback = cb;
        return () => {};
      });

      const { unmount } = renderHook(() => useIpcListeners());

      // Queue some logs
      act(() => {
        logCallback?.('task-1', 'Log line 1');
        logCallback?.('task-1', 'Log line 2');
      });

      // Unmount should flush pending updates
      unmount();

      expect(mockBatchAppendLogs).toHaveBeenCalledWith('task-1', ['Log line 1', 'Log line 2']);
    });

    it('should not error if unmounted with no pending updates', () => {
      const { unmount } = renderHook(() => useIpcListeners());

      expect(() => unmount()).not.toThrow();
    });
  });
});

describe('useAppSettings', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (window as unknown as { electronAPI: unknown }).electronAPI = {
      getSettings: mockGetSettings,
      saveSettings: mockSaveSettings
    };
  });

  afterEach(() => {
    delete (window as unknown as { electronAPI?: unknown }).electronAPI;
  });

  describe('getSettings', () => {
    it('should return settings when successful', async () => {
      const mockSettings = {
        theme: 'dark',
        language: 'en'
      };

      mockGetSettings.mockResolvedValue({
        success: true,
        data: mockSettings
      });

      const { result } = renderHook(() => useAppSettings());
      const settings = await result.current.getSettings();

      expect(settings).toEqual(mockSettings);
      expect(mockGetSettings).toHaveBeenCalled();
    });

    it('should return null when unsuccessful', async () => {
      mockGetSettings.mockResolvedValue({
        success: false
      });

      const { result } = renderHook(() => useAppSettings());
      const settings = await result.current.getSettings();

      expect(settings).toBeNull();
    });

    it('should return null when data is missing', async () => {
      mockGetSettings.mockResolvedValue({
        success: true,
        data: null
      });

      const { result } = renderHook(() => useAppSettings());
      const settings = await result.current.getSettings();

      expect(settings).toBeNull();
    });
  });

  describe('saveSettings', () => {
    it('should return true when save is successful', async () => {
      mockSaveSettings.mockResolvedValue({
        success: true
      });

      const { result } = renderHook(() => useAppSettings());
      const settingsToSave = {
        theme: 'light',
        language: 'fr'
      };

      const success = await result.current.saveSettings(settingsToSave);

      expect(success).toBe(true);
      expect(mockSaveSettings).toHaveBeenCalledWith(settingsToSave);
    });

    it('should return false when save fails', async () => {
      mockSaveSettings.mockResolvedValue({
        success: false
      });

      const { result } = renderHook(() => useAppSettings());
      const settingsToSave = {
        theme: 'light',
        language: 'fr'
      };

      const success = await result.current.saveSettings(settingsToSave);

      expect(success).toBe(false);
    });
  });
});

describe('useAppVersion', () => {
  beforeEach(() => {
    vi.clearAllMocks();

    (window as unknown as { electronAPI: unknown }).electronAPI = {
      getAppVersion: mockGetAppVersion
    };
  });

  afterEach(() => {
    delete (window as unknown as { electronAPI?: unknown }).electronAPI;
  });

  it('should return app version', async () => {
    mockGetAppVersion.mockResolvedValue('1.2.3');

    const { result } = renderHook(() => useAppVersion());
    const version = await result.current.getVersion();

    expect(version).toBe('1.2.3');
    expect(mockGetAppVersion).toHaveBeenCalled();
  });

  it('should handle version retrieval correctly', async () => {
    mockGetAppVersion.mockResolvedValue('2.0.0-beta.1');

    const { result } = renderHook(() => useAppVersion());
    const version = await result.current.getVersion();

    expect(version).toBe('2.0.0-beta.1');
  });
});
