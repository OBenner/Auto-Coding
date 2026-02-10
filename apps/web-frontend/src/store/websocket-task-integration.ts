/**
 * WebSocket Task Store Integration
 *
 * Connects WebSocket events to the task store for real-time updates.
 * This bridges the WebSocket client with the Zustand task store.
 *
 * Usage:
 * ```tsx
 * // In App.tsx or main component
 * useEffect(() => {
 *   const cleanup = initializeWebSocketTaskIntegration();
 *   return cleanup;
 * }, []);
 * ```
 */

import { wsClient } from '../api/websocket';
import type {
  ExecutionEvent,
  IdeationEvent,
  RoadmapEvent,
  LogEvent,
  ErrorEvent,
  AgentEvent
} from '../api/types';
import {
  appendTaskLog,
  updateExecutionProgress,
  updateTaskStatus,
  type TaskState
} from './task-store';

/**
 * WebSocket task integration state
 */
interface IntegrationState {
  initialized: boolean;
  subscriptions: Set<string>;
  unsubscribeFunctions: Array<() => void>;
}

const integrationState: IntegrationState = {
  initialized: false,
  subscriptions: new Set(),
  unsubscribeFunctions: []
};

/**
 * Extract task ID from spec ID
 * spec_id format: "001", "002", etc.
 * task ID is the same as spec_id
 */
function extractTaskId(specId: string): string {
  return specId;
}

/**
 * Handle execution progress events
 */
function handleExecutionEvent(event: ExecutionEvent): void {
  const taskId = extractTaskId(event.spec_id);

  // Update execution progress in store
  updateExecutionProgress(taskId, event.data);

  // Also update task status based on phase
  const phaseToStatus: Record<string, string> = {
    idle: 'pending',
    planning: 'in_progress',
    coding: 'in_progress',
    qa_review: 'in_progress',
    qa_fixing: 'in_progress',
    complete: 'completed',
    failed: 'failed'
  };

  const status = phaseToStatus[event.data.phase];
  if (status) {
    updateTaskStatus(taskId, status);
  }
}

/**
 * Handle ideation progress events
 */
function handleIdeationEvent(event: IdeationEvent): void {
  const taskId = extractTaskId(event.spec_id);

  // Map ideation progress to execution progress format
  const executionProgress = {
    phase: event.data.phase as any,
    phase_progress: event.data.progress,
    overall_progress: event.data.progress,
    message: event.data.message,
    current_subtask: undefined
  };

  updateExecutionProgress(taskId, executionProgress);

  // Update status based on phase
  const phaseToStatus: Record<string, string> = {
    idle: 'pending',
    analyzing: 'in_progress',
    discovering: 'in_progress',
    generating: 'in_progress',
    finalizing: 'in_progress',
    complete: 'completed',
    error: 'failed'
  };

  const status = phaseToStatus[event.data.phase];
  if (status) {
    updateTaskStatus(taskId, status);
  }
}

/**
 * Handle roadmap progress events
 */
function handleRoadmapEvent(event: RoadmapEvent): void {
  const taskId = extractTaskId(event.spec_id);

  // Map roadmap progress to execution progress format
  const executionProgress = {
    phase: event.data.phase as any,
    phase_progress: event.data.progress,
    overall_progress: event.data.progress,
    message: event.data.message,
    current_subtask: undefined
  };

  updateExecutionProgress(taskId, executionProgress);

  // Update status based on phase
  const phaseToStatus: Record<string, string> = {
    idle: 'pending',
    analyzing: 'in_progress',
    discovering: 'in_progress',
    generating: 'in_progress',
    complete: 'completed',
    error: 'failed'
  };

  const status = phaseToStatus[event.data.phase];
  if (status) {
    updateTaskStatus(taskId, status);
  }
}

/**
 * Handle log events
 */
function handleLogEvent(event: LogEvent): void {
  const taskId = extractTaskId(event.spec_id);

  // Append log line to task
  const logLine = `[${event.level.toUpperCase()}] ${event.log_line}`;
  appendTaskLog(taskId, logLine);
}

/**
 * Handle error events
 */
function handleErrorEvent(event: ErrorEvent): void {
  const taskId = extractTaskId(event.spec_id);

  // Log error to task logs
  const errorLog = `[ERROR] ${event.error_message}`;
  appendTaskLog(taskId, errorLog);

  // If there's a traceback, add it too
  if (event.traceback) {
    appendTaskLog(taskId, `[TRACEBACK]\n${event.traceback}`);
  }

  // Update task status to failed
  updateTaskStatus(taskId, 'failed');
}

/**
 * Handle all WebSocket events
 */
function handleAgentEvent(event: AgentEvent): void {
  switch (event.event_type) {
    case 'execution':
      handleExecutionEvent(event as ExecutionEvent);
      break;

    case 'ideation':
      handleIdeationEvent(event as IdeationEvent);
      break;

    case 'roadmap':
      handleRoadmapEvent(event as RoadmapEvent);
      break;

    case 'log':
      handleLogEvent(event as LogEvent);
      break;

    case 'error':
      handleErrorEvent(event as ErrorEvent);
      break;

    default:
      console.warn('[WebSocketTaskIntegration] Unknown event type:', (event as AgentEvent).event_type);
  }
}

/**
 * Subscribe to WebSocket events for a specific task
 */
export function subscribeToTaskEvents(taskId: string): void {
  if (!integrationState.initialized) {
    console.warn('[WebSocketTaskIntegration] Not initialized, call initializeWebSocketTaskIntegration() first');
    return;
  }

  if (integrationState.subscriptions.has(taskId)) {
    console.log(`[WebSocketTaskIntegration] Already subscribed to task: ${taskId}`);
    return;
  }

  // Subscribe via WebSocket client
  wsClient.subscribe(taskId);
  integrationState.subscriptions.add(taskId);

  console.log(`[WebSocketTaskIntegration] Subscribed to task: ${taskId}`);
}

/**
 * Unsubscribe from WebSocket events for a specific task
 */
export function unsubscribeFromTaskEvents(taskId: string): void {
  if (!integrationState.subscriptions.has(taskId)) {
    return;
  }

  // Unsubscribe via WebSocket client
  wsClient.unsubscribe(taskId);
  integrationState.subscriptions.delete(taskId);

  console.log(`[WebSocketTaskIntegration] Unsubscribed from task: ${taskId}`);
}

/**
 * Initialize WebSocket task store integration
 * Connects WebSocket client and registers event handlers
 *
 * @returns Cleanup function to disconnect and unregister handlers
 */
export function initializeWebSocketTaskIntegration(): () => void {
  if (integrationState.initialized) {
    console.log('[WebSocketTaskIntegration] Already initialized');
    return () => cleanupWebSocketTaskIntegration();
  }

  console.log('[WebSocketTaskIntegration] Initializing...');

  // Register event handlers
  wsClient.on('execution', handleExecutionEvent as any);
  wsClient.on('ideation', handleIdeationEvent as any);
  wsClient.on('roadmap', handleRoadmapEvent as any);
  wsClient.on('log', handleLogEvent as any);
  wsClient.on('error', handleErrorEvent as any);

  // Store unsubscribe functions for cleanup
  integrationState.unsubscribeFunctions = [
    () => wsClient.off('execution', handleExecutionEvent as any),
    () => wsClient.off('ideation', handleIdeationEvent as any),
    () => wsClient.off('roadmap', handleRoadmapEvent as any),
    () => wsClient.off('log', handleLogEvent as any),
    () => wsClient.off('error', handleErrorEvent as any)
  ];

  // Connect to WebSocket server
  wsClient.connect();

  // Listen to connection state changes
  const stateHandler = (state: string) => {
    console.log(`[WebSocketTaskIntegration] Connection state: ${state}`);

    // Re-subscribe to all tasks when reconnected
    if (state === 'connected' && integrationState.subscriptions.size > 0) {
      console.log(`[WebSocketTaskIntegration] Re-subscribing to ${integrationState.subscriptions.size} tasks`);
      for (const taskId of integrationState.subscriptions) {
        wsClient.subscribe(taskId);
      }
    }
  };

  wsClient.onStateChange(stateHandler);
  integrationState.unsubscribeFunctions.push(
    () => wsClient.offStateChange(stateHandler)
  );

  integrationState.initialized = true;
  console.log('[WebSocketTaskIntegration] Initialized');

  // Return cleanup function
  return () => cleanupWebSocketTaskIntegration();
}

/**
 * Cleanup WebSocket task store integration
 */
function cleanupWebSocketTaskIntegration(): void {
  if (!integrationState.initialized) {
    return;
  }

  console.log('[WebSocketTaskIntegration] Cleaning up...');

  // Unsubscribe from all tasks
  for (const taskId of integrationState.subscriptions) {
    wsClient.unsubscribe(taskId);
  }
  integrationState.subscriptions.clear();

  // Unregister all event handlers
  for (const unsubscribe of integrationState.unsubscribeFunctions) {
    try {
      unsubscribe();
    } catch (error) {
      console.error('[WebSocketTaskIntegration] Error during cleanup:', error);
    }
  }
  integrationState.unsubscribeFunctions = [];

  // Disconnect from WebSocket server
  wsClient.disconnect();

  integrationState.initialized = false;
  console.log('[WebSocketTaskIntegration] Cleaned up');
}

/**
 * Check if WebSocket integration is initialized
 */
export function isWebSocketIntegrationInitialized(): boolean {
  return integrationState.initialized;
}

/**
 * Get current WebSocket connection state
 */
export function getWebSocketConnectionState(): string {
  return wsClient.getState();
}

/**
 * Check if WebSocket is connected
 */
export function isWebSocketConnected(): boolean {
  return wsClient.isConnected();
}
