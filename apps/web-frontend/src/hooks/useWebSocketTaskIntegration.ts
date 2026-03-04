/**
 * React Hooks for WebSocket Task Integration
 *
 * Provides easy-to-use React hooks for WebSocket real-time task updates.
 */

import { useEffect, useState } from 'react';
import {
  initializeWebSocketTaskIntegration,
  subscribeToTaskEvents,
  unsubscribeFromTaskEvents,
  isWebSocketIntegrationInitialized,
  getWebSocketConnectionState,
  isWebSocketConnected
} from '../store/websocket-task-integration';
import type { ConnectionState } from '../api/websocket';

/**
 * Hook to initialize WebSocket task integration
 * Should be called once in the app root component
 *
 * @returns Connection state and whether it's connected
 *
 * @example
 * ```tsx
 * function App() {
 *   const { connectionState, isConnected } = useWebSocketIntegration();
 *
 *   return (
 *     <div>
 *       {isConnected ? <TaskList /> : <LoadingSpinner />}
 *     </div>
 *   );
 * }
 * ```
 */
export function useWebSocketIntegration(): {
  connectionState: ConnectionState;
  isConnected: boolean;
  isInitialized: boolean;
} {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    // Initialize WebSocket integration on mount
    const cleanup = initializeWebSocketTaskIntegration();

    // Set up interval to check connection state
    const interval = setInterval(() => {
      const state = getWebSocketConnectionState() as ConnectionState;
      const connected = isWebSocketConnected();

      setConnectionState(state);
      setIsConnected(connected);
    }, 1000);

    // Initial check
    setConnectionState(getWebSocketConnectionState() as ConnectionState);
    setIsConnected(isWebSocketConnected());

    // Cleanup on unmount
    return () => {
      clearInterval(interval);
      cleanup();
    };
  }, []);

  return {
    connectionState,
    isConnected,
    isInitialized: isWebSocketIntegrationInitialized()
  };
}

/**
 * Hook to subscribe to WebSocket events for a specific task
 * Automatically subscribes when taskId changes, unsubscribes on unmount
 *
 * @param taskId - Task ID to subscribe to (null to unsubscribe)
 *
 * @example
 * ```tsx
 * function TaskDetail({ taskId }) {
 *   useTaskSubscription(taskId);
 *   const task = useTaskStore(state => state.currentTask);
 *
 *   return <div>{task?.name}</div>;
 * }
 * ```
 */
export function useTaskSubscription(taskId: string | null): void {
  useEffect(() => {
    if (!taskId) {
      return;
    }

    // Subscribe to task events
    subscribeToTaskEvents(taskId);

    // Unsubscribe on cleanup or when taskId changes
    return () => {
      unsubscribeFromTaskEvents(taskId);
    };
  }, [taskId]);
}

/**
 * Hook to get WebSocket connection status
 * Useful for displaying connection status indicators
 *
 * @returns Connection status and state
 *
 * @example
 * ```tsx
 * function ConnectionStatus() {
 *   const { connectionState, isConnected, isInitialized } = useWebSocketStatus();
 *
 *   if (!isInitialized) return <span>Initializing...</span>;
 *
 *   return (
 *     <span className={
 *       isConnected ? 'text-green-500' : 'text-red-500'
 *     }>
 *       {connectionState}
 *     </span>
 *   );
 * }
 * ```
 */
export function useWebSocketStatus(): {
  connectionState: ConnectionState;
  isConnected: boolean;
  isInitialized: boolean;
} {
  const [state, setState] = useState<{
    connectionState: ConnectionState;
    isConnected: boolean;
    isInitialized: boolean;
  }>({
    connectionState: 'disconnected',
    isConnected: false,
    isInitialized: false
  });

  useEffect(() => {
    // Update state every second
    const interval = setInterval(() => {
      setState({
        connectionState: getWebSocketConnectionState() as ConnectionState,
        isConnected: isWebSocketConnected(),
        isInitialized: isWebSocketIntegrationInitialized()
      });
    }, 1000);

    // Initial check
    setState({
      connectionState: getWebSocketConnectionState() as ConnectionState,
      isConnected: isWebSocketConnected(),
      isInitialized: isWebSocketIntegrationInitialized()
    });

    return () => clearInterval(interval);
  }, []);

  return state;
}
