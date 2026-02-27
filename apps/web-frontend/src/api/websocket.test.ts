/**
 * WebSocket Client Unit Tests
 *
 * Comprehensive tests for the WebSocketClient class covering:
 * - Constructor and configuration
 * - Connection lifecycle (connect, disconnect, reconnect)
 * - Event handling and subscriptions
 * - State management
 * - Error handling
 * - Ping/pong functionality
 * - Edge cases
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { WebSocketClient, createWebSocketClient } from './websocket';
import type {
  ExecutionEvent,
  IdeationEvent,
  RoadmapEvent,
  LogEvent,
  ErrorEvent,
} from './types';

// Mock WebSocket
class MockWebSocket {
  public readyState: number = WebSocket.CONNECTING;
  public onopen: ((event: Event) => void) | null = null;
  public onclose: ((event: CloseEvent) => void) | null = null;
  public onerror: ((event: Event) => void) | null = null;
  public onmessage: ((event: MessageEvent) => void) | null = null;

  private sentMessages: string[] = [];

  constructor(public url: string) {}

  send(data: string): void {
    if (this.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
    this.sentMessages.push(data);
  }

  close(): void {
    this.readyState = WebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Test helpers
  simulateOpen(): void {
    this.readyState = WebSocket.OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  simulateMessage(data: unknown): void {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data: JSON.stringify(data) }));
    }
  }

  simulateError(): void {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }

  getSentMessages(): string[] {
    return [...this.sentMessages];
  }

  clearSentMessages(): void {
    this.sentMessages = [];
  }
}

// Setup WebSocket mock globally
let mockWsInstance: MockWebSocket | null = null;

// Factory function acting as a WebSocket constructor mock.
// Using a function instead of a class avoids "class with only a constructor" and
// "unexpected return in constructor" linter rules while retaining the same behaviour.
function WebSocketMock(url: string): WebSocket {
  mockWsInstance = new MockWebSocket(url);
  return mockWsInstance as unknown as WebSocket;
}
// Required static constants mirroring the real WebSocket interface
WebSocketMock.CONNECTING = 0;
WebSocketMock.OPEN = 1;
WebSocketMock.CLOSING = 2;
WebSocketMock.CLOSED = 3;

const originalWebSocket = globalThis.WebSocket;
globalThis.WebSocket = WebSocketMock as unknown as typeof WebSocket;

describe('WebSocketClient', () => {
  let client: WebSocketClient;
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;
  let websocketSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    // Reset state before each test
    mockWsInstance = null;
    vi.useFakeTimers();

    // Install mock WebSocket
    globalThis.WebSocket = WebSocketMock as unknown as typeof WebSocket;

    // Spy on WebSocket constructor to track calls
    websocketSpy = vi.spyOn(globalThis, 'WebSocket');

    // Spy on console.error to suppress error output in tests
    consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

    // Create client with test config
    client = new WebSocketClient({
      url: 'ws://test-server.local',
      reconnect: true,
      reconnectDelay: 1000,
      maxReconnectAttempts: 5,
      pingInterval: 5000,
      debug: false,
    });
  });

  afterEach(() => {
    client.disconnect();
    // Restore original WebSocket
    globalThis.WebSocket = originalWebSocket;
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ============================================
  // CONSTRUCTOR & CONFIGURATION TESTS
  // ============================================

  describe('Constructor', () => {
    it('should initialize with default config', () => {
      const defaultClient = new WebSocketClient();
      const config = defaultClient.getConfig();

      expect(config.url).toBeDefined();
      expect(config.reconnect).toBe(true);
      expect(config.reconnectDelay).toBe(3000);
      expect(config.maxReconnectAttempts).toBe(10);
      expect(config.pingInterval).toBe(30000);
    });

    it('should merge custom config with defaults', () => {
      const customClient = new WebSocketClient({
        url: 'ws://custom.local',
        reconnectDelay: 5000,
      });
      const config = customClient.getConfig();

      expect(config.url).toBe('ws://custom.local');
      expect(config.reconnectDelay).toBe(5000);
      expect(config.reconnect).toBe(true); // Default value
    });

    it('should not log when debug is false', () => {
      const consoleSpy = vi.spyOn(console, 'log');
      const silentClient = new WebSocketClient({ debug: false });
      expect(silentClient).toBeDefined();

      expect(consoleSpy).not.toHaveBeenCalled();
    });

    it('should log when debug is true', () => {
      const consoleSpy = vi.spyOn(console, 'log');
      const verboseClient = new WebSocketClient({ debug: true });
      expect(verboseClient).toBeDefined();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('[WebSocketClient] WebSocketClient initialized'),
        expect.any(Object)
      );
    });
  });

  describe('updateConfig', () => {
    it('should update configuration', () => {
      client.updateConfig({ url: 'ws://new-server.local' });
      const config = client.getConfig();

      expect(config.url).toBe('ws://new-server.local');
    });

    it('should merge partial config updates', () => {
      const originalConfig = client.getConfig();
      client.updateConfig({ pingInterval: 10000 });
      const newConfig = client.getConfig();

      expect(newConfig.pingInterval).toBe(10000);
      expect(newConfig.url).toBe(originalConfig.url);
      expect(newConfig.reconnect).toBe(originalConfig.reconnect);
    });
  });

  describe('getConfig', () => {
    it('should return a copy of config', () => {
      const config1 = client.getConfig();
      const config2 = client.getConfig();

      expect(config1).toEqual(config2);
      expect(config1).not.toBe(config2); // Different objects
    });
  });

  // ============================================
  // CONNECTION LIFECYCLE TESTS
  // ============================================

  describe('connect', () => {
    it('should create WebSocket connection', () => {
      client.connect();

      expect(websocketSpy).toHaveBeenCalledWith(
        'ws://test-server.local/ws/agent-events'
      );
      expect(client.getState()).toBe('connecting');
    });

    it('should transition to connected state on open', () => {
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      client.connect();
      expect(client.getState()).toBe('connecting');

      mockWsInstance?.simulateOpen();
      expect(client.getState()).toBe('connected');
      expect(stateHandler).toHaveBeenCalledWith('connected');
    });

    it('should not reconnect if already connected', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      const wsCallCount = websocketSpy.mock.calls.length;
      client.connect();

      expect(websocketSpy.mock.calls.length).toBe(wsCallCount);
    });

    it('should not reconnect if already connecting', () => {
      client.connect();

      const wsCallCount = websocketSpy.mock.calls.length;
      client.connect();

      expect(websocketSpy.mock.calls.length).toBe(wsCallCount);
    });

    it('should start ping interval after connection', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      // Fast-forward time to trigger ping
      vi.advanceTimersByTime(5000);

      const messages = ws?.getSentMessages() || [];
      expect(messages.length).toBeGreaterThan(0);
      expect(JSON.parse(messages[0])).toEqual({ action: 'ping' });
    });

    it('should re-subscribe after reconnection', () => {
      // Connect and subscribe
      client.connect();
      const ws1 = mockWsInstance;
      ws1?.simulateOpen();
      client.subscribe('spec-001');

      ws1?.clearSentMessages();

      // Simulate disconnect and reconnect
      ws1?.close();
      vi.advanceTimersByTime(1000);

      // Get the new instance created during reconnection
      const ws2 = mockWsInstance;
      ws2?.simulateOpen();

      // Should re-subscribe
      const messages = ws2?.getSentMessages() || [];
      const subscribeMessages = messages.filter((msg) => {
        const parsed = JSON.parse(msg);
        return parsed.action === 'subscribe' && parsed.spec_id === 'spec-001';
      });

      expect(subscribeMessages.length).toBeGreaterThan(0);
    });
  });

  describe('disconnect', () => {
    it('should close WebSocket connection', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.disconnect();

      expect(client.getState()).toBe('disconnected');
      expect(client.isConnected()).toBe(false);
    });

    it('should disable auto-reconnect on manual disconnect', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.disconnect();

      // Wait for reconnect delay
      vi.advanceTimersByTime(10000);

      // Should not reconnect
      expect(client.getState()).toBe('disconnected');
    });

    it('should stop ping interval', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      client.disconnect();

      ws?.clearSentMessages();
      vi.advanceTimersByTime(10000);

      expect(ws?.getSentMessages().length).toBe(0);
    });
  });

  describe('reconnection', () => {
    it('should attempt reconnection after connection loss', () => {
      client.connect();
      const ws1 = mockWsInstance;
      ws1?.simulateOpen();

      // Simulate connection loss
      ws1?.close();

      expect(client.getState()).toBe('disconnected');

      // Fast-forward to trigger reconnect
      vi.advanceTimersByTime(1000);

      // Should attempt reconnection
      expect(websocketSpy.mock.calls.length).toBe(2);
    });

    it('should use exponential backoff for reconnection', () => {
      client.connect();
      let ws = mockWsInstance;
      ws?.simulateOpen();

      // First reconnect attempt (1000ms)
      ws?.close();
      vi.advanceTimersByTime(1000);
      expect(websocketSpy.mock.calls.length).toBe(2);

      // Second reconnect attempt (2000ms)
      ws = mockWsInstance;
      ws?.close();
      vi.advanceTimersByTime(2000);
      expect(websocketSpy.mock.calls.length).toBe(3);

      // Third reconnect attempt (3000ms)
      ws = mockWsInstance;
      ws?.close();
      vi.advanceTimersByTime(3000);
      expect(websocketSpy.mock.calls.length).toBe(4);
    });

    it('should stop reconnecting after max attempts', () => {
      client.connect();
      let ws = mockWsInstance;
      ws?.simulateOpen();

      // Simulate 5 failed reconnections
      for (let i = 0; i < 5; i++) {
        ws = mockWsInstance;
        ws?.close();
        vi.advanceTimersByTime((i + 1) * 1000 + 100);
      }

      const finalCallCount = websocketSpy.mock.calls.length;

      // Try to trigger another reconnect
      vi.advanceTimersByTime(10000);

      expect(websocketSpy.mock.calls.length).toBe(finalCallCount);
    });

    it('should reset reconnect attempts on successful connection', () => {
      client.connect();
      let ws = mockWsInstance;
      ws?.simulateOpen();

      // Simulate reconnection
      ws?.close();
      vi.advanceTimersByTime(1000);

      // Successful reconnection
      ws = mockWsInstance;
      ws?.simulateOpen();

      // Next reconnection should start from delay = 1000ms again
      ws?.close();
      vi.advanceTimersByTime(1000);

      expect(websocketSpy.mock.calls.length).toBe(3);
    });

    it('should not reconnect when reconnect is disabled', () => {
      const noReconnectClient = new WebSocketClient({
        url: 'ws://test.local',
        reconnect: false,
      });

      noReconnectClient.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const initialCallCount = websocketSpy.mock.calls.length;

      ws?.close();
      vi.advanceTimersByTime(10000);

      expect(websocketSpy.mock.calls.length).toBe(initialCallCount);

      noReconnectClient.disconnect();
    });
  });

  // ============================================
  // STATE MANAGEMENT TESTS
  // ============================================

  describe('getState', () => {
    it('should return current connection state', () => {
      expect(client.getState()).toBe('disconnected');

      client.connect();
      const ws = mockWsInstance;
      expect(client.getState()).toBe('connecting');

      ws?.simulateOpen();
      expect(client.getState()).toBe('connected');

      client.disconnect();
      expect(client.getState()).toBe('disconnected');
    });
  });

  describe('isConnected', () => {
    it('should return true when connected', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      expect(client.isConnected()).toBe(true);
    });

    it('should return false when not connected', () => {
      expect(client.isConnected()).toBe(false);

      client.connect();
      expect(client.isConnected()).toBe(false);

      const ws = mockWsInstance;
      ws?.simulateOpen();
      client.disconnect();
      expect(client.isConnected()).toBe(false);
    });
  });

  describe('onStateChange', () => {
    it('should notify handlers on state change', () => {
      const handler = vi.fn();
      client.onStateChange(handler);

      client.connect();
      const ws = mockWsInstance;
      expect(handler).toHaveBeenCalledWith('connecting');

      ws?.simulateOpen();
      expect(handler).toHaveBeenCalledWith('connected');

      client.disconnect();
      expect(handler).toHaveBeenCalledWith('disconnected');
    });

    it('should support multiple state handlers', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.onStateChange(handler1);
      client.onStateChange(handler2);

      client.connect();

      expect(handler1).toHaveBeenCalledWith('connecting');
      expect(handler2).toHaveBeenCalledWith('connecting');
    });

    it('should not notify on same state', () => {
      const handler = vi.fn();
      client.onStateChange(handler);

      client.connect();
      handler.mockClear();

      // Try to connect again while connecting
      client.connect();

      expect(handler).not.toHaveBeenCalled();
    });

    it('should handle errors in state handlers gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      const normalHandler = vi.fn();

      client.onStateChange(errorHandler);
      client.onStateChange(normalHandler);

      client.connect();

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Error in state handler:',
        expect.any(Error)
      );
      expect(normalHandler).toHaveBeenCalledWith('connecting');
    });
  });

  describe('offStateChange', () => {
    it('should remove state change handler', () => {
      const handler = vi.fn();
      client.onStateChange(handler);

      client.connect();
      expect(handler).toHaveBeenCalledWith('connecting');

      handler.mockClear();
      client.offStateChange(handler);

      mockWsInstance?.simulateOpen();
      expect(handler).not.toHaveBeenCalled();
    });
  });

  // ============================================
  // EVENT HANDLING TESTS
  // ============================================

  describe('on', () => {
    it('should register event handler', () => {
      const handler = vi.fn();
      client.on('execution', handler);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const event: ExecutionEvent = {
        event_type: 'execution',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        data: {
          phase: 'coding',
          phase_progress: 50,
          overall_progress: 25,
          message: 'Implementing feature',
        },
      };

      ws?.simulateMessage(event);

      expect(handler).toHaveBeenCalledWith(event);
    });

    it('should support multiple handlers for same event type', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.on('log', handler1);
      client.on('log', handler2);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const event: LogEvent = {
        event_type: 'log',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        log_line: 'Test log message',
        level: 'info',
      };

      ws?.simulateMessage(event);

      expect(handler1).toHaveBeenCalledWith(event);
      expect(handler2).toHaveBeenCalledWith(event);
    });

    it('should support wildcard event handler', () => {
      const wildcardHandler = vi.fn();
      client.on('*', wildcardHandler);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const executionEvent: ExecutionEvent = {
        event_type: 'execution',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        data: {
          phase: 'planning',
          phase_progress: 100,
          overall_progress: 10,
        },
      };

      const logEvent: LogEvent = {
        event_type: 'log',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        log_line: 'Log message',
        level: 'info',
      };

      ws?.simulateMessage(executionEvent);
      ws?.simulateMessage(logEvent);

      expect(wildcardHandler).toHaveBeenCalledTimes(2);
      expect(wildcardHandler).toHaveBeenCalledWith(executionEvent);
      expect(wildcardHandler).toHaveBeenCalledWith(logEvent);
    });

    it('should call both specific and wildcard handlers', () => {
      const specificHandler = vi.fn();
      const wildcardHandler = vi.fn();

      client.on('error', specificHandler);
      client.on('*', wildcardHandler);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const event: ErrorEvent = {
        event_type: 'error',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        error_message: 'Something went wrong',
        error_type: 'RuntimeError',
      };

      ws?.simulateMessage(event);

      expect(specificHandler).toHaveBeenCalledWith(event);
      expect(wildcardHandler).toHaveBeenCalledWith(event);
    });

    it('should handle errors in event handlers gracefully', () => {
      const errorHandler = vi.fn(() => {
        throw new Error('Handler error');
      });
      const normalHandler = vi.fn();

      client.on('ideation', errorHandler);
      client.on('ideation', normalHandler);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const event: IdeationEvent = {
        event_type: 'ideation',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        data: {
          phase: 'analyzing',
          progress: 50,
          completed_types: 3,
          total_types: 6,
        },
      };

      ws?.simulateMessage(event);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        expect.stringContaining('Error in ideation event handler:'),
        expect.any(Error)
      );
      expect(normalHandler).toHaveBeenCalledWith(event);
    });

    it('should handle JSON parse errors', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      // Simulate invalid JSON message
      if (ws?.onmessage) {
        ws.onmessage(
          new MessageEvent('message', { data: 'invalid json' })
        );
      }

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Error parsing WebSocket message:',
        expect.any(Error)
      );
    });
  });

  describe('off', () => {
    it('should unregister event handler', () => {
      const handler = vi.fn();
      client.on('roadmap', handler);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const event: RoadmapEvent = {
        event_type: 'roadmap',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        data: {
          phase: 'generating',
          progress: 75,
          message: 'Creating roadmap',
        },
      };

      ws?.simulateMessage(event);
      expect(handler).toHaveBeenCalledWith(event);

      handler.mockClear();
      client.off('roadmap', handler);

      ws?.simulateMessage(event);
      expect(handler).not.toHaveBeenCalled();
    });

    it('should only remove specified handler', () => {
      const handler1 = vi.fn();
      const handler2 = vi.fn();

      client.on('execution', handler1);
      client.on('execution', handler2);

      client.off('execution', handler1);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      const event: ExecutionEvent = {
        event_type: 'execution',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        data: {
          phase: 'complete',
          phase_progress: 100,
          overall_progress: 100,
        },
      };

      ws?.simulateMessage(event);

      expect(handler1).not.toHaveBeenCalled();
      expect(handler2).toHaveBeenCalledWith(event);
    });
  });

  // ============================================
  // SUBSCRIPTION TESTS
  // ============================================

  describe('subscribe', () => {
    it('should send subscribe message', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      client.subscribe('spec-001');

      const messages = ws?.getSentMessages() || [];
      const subscribeMsg = messages.find((msg) => {
        const parsed = JSON.parse(msg);
        return parsed.action === 'subscribe' && parsed.spec_id === 'spec-001';
      });

      expect(subscribeMsg).toBeDefined();
    });

    it('should track subscriptions', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.subscribe('spec-001');
      client.subscribe('spec-002');

      const subscriptions = client.getSubscriptions();

      expect(subscriptions).toContain('spec-001');
      expect(subscriptions).toContain('spec-002');
      expect(subscriptions.length).toBe(2);
    });

    it('should not duplicate subscriptions', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.subscribe('spec-001');
      client.subscribe('spec-001');

      const subscriptions = client.getSubscriptions();

      expect(subscriptions.filter((s) => s === 'spec-001').length).toBe(1);
    });

    it('should warn if not connected', () => {
      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      client.subscribe('spec-001');

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Cannot send message: WebSocket not connected'
      );

      consoleWarnSpy.mockRestore();
    });
  });

  describe('unsubscribe', () => {
    it('should send unsubscribe message', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      client.subscribe('spec-001');
      ws?.clearSentMessages();

      client.unsubscribe('spec-001');

      const messages = ws?.getSentMessages() || [];
      const unsubscribeMsg = messages.find((msg) => {
        const parsed = JSON.parse(msg);
        return parsed.action === 'unsubscribe' && parsed.spec_id === 'spec-001';
      });

      expect(unsubscribeMsg).toBeDefined();
    });

    it('should remove subscription from tracking', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.subscribe('spec-001');
      client.subscribe('spec-002');

      client.unsubscribe('spec-001');

      const subscriptions = client.getSubscriptions();

      expect(subscriptions).not.toContain('spec-001');
      expect(subscriptions).toContain('spec-002');
      expect(subscriptions.length).toBe(1);
    });
  });

  describe('getSubscriptions', () => {
    it('should return list of active subscriptions', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      expect(client.getSubscriptions()).toEqual([]);

      client.subscribe('spec-001');
      client.subscribe('spec-002');
      client.subscribe('spec-003');

      expect(client.getSubscriptions().sort((a, b) => a.localeCompare(b))).toEqual(['spec-001', 'spec-002', 'spec-003']);
    });

    it('should return a copy of subscriptions array', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.subscribe('spec-001');

      const subs1 = client.getSubscriptions();
      const subs2 = client.getSubscriptions();

      expect(subs1).toEqual(subs2);
      expect(subs1).not.toBe(subs2); // Different arrays
    });
  });

  // ============================================
  // ERROR HANDLING TESTS
  // ============================================

  describe('Error Handling', () => {
    it('should handle WebSocket error event', () => {
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      client.connect();
      const ws = mockWsInstance;
      ws?.simulateError();

      expect(client.getState()).toBe('error');
      expect(stateHandler).toHaveBeenCalledWith('error');
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'WebSocket error:',
        expect.any(Event)
      );
    });

    it('should handle connection error', () => {
      const stateHandler = vi.fn();
      client.onStateChange(stateHandler);

      // Mock WebSocket constructor to throw
      websocketSpy.mockImplementationOnce(() => {
        throw new Error('Connection failed');
      });

      client.connect();

      expect(client.getState()).toBe('error');
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Error connecting to WebSocket:',
        expect.any(Error)
      );
    });

    it('should handle send error', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      // Force readyState to CLOSED
      if (ws) {
        ws.readyState = WebSocket.CLOSED;
      }

      const consoleWarnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});

      client.subscribe('spec-001');

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        'Cannot send message: WebSocket not connected'
      );

      consoleWarnSpy.mockRestore();
    });
  });

  // ============================================
  // PING/PONG TESTS
  // ============================================

  describe('Ping Interval', () => {
    it('should send periodic ping messages', () => {
      client.connect();
      const ws = mockWsInstance;
      ws?.simulateOpen();

      ws?.clearSentMessages();

      // Fast-forward to first ping
      vi.advanceTimersByTime(5000);

      const messages1 = ws?.getSentMessages() || [];
      expect(messages1.some((msg) => JSON.parse(msg).action === 'ping')).toBe(true);

      ws?.clearSentMessages();

      // Fast-forward to second ping
      vi.advanceTimersByTime(5000);

      const messages2 = ws?.getSentMessages() || [];
      expect(messages2.some((msg) => JSON.parse(msg).action === 'ping')).toBe(true);
    });

    it('should stop ping on disconnect', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      client.disconnect();

      mockWsInstance?.clearSentMessages();

      vi.advanceTimersByTime(10000);

      expect(mockWsInstance?.getSentMessages().length).toBe(0);
    });

    it('should restart ping on reconnection', () => {
      client.connect();
      let ws = mockWsInstance;
      ws?.simulateOpen();

      // Simulate disconnect and reconnect
      ws?.close();
      vi.advanceTimersByTime(1000);

      ws = mockWsInstance;
      ws?.simulateOpen();
      ws?.clearSentMessages();

      vi.advanceTimersByTime(5000);

      const messages = ws?.getSentMessages() || [];
      expect(messages.some((msg) => JSON.parse(msg).action === 'ping')).toBe(true);
    });
  });

  // ============================================
  // FACTORY FUNCTION TESTS
  // ============================================

  describe('createWebSocketClient', () => {
    it('should create a new client instance', () => {
      const newClient = createWebSocketClient({
        url: 'ws://factory-test.local',
      });

      expect(newClient).toBeInstanceOf(WebSocketClient);
      expect(newClient.getConfig().url).toBe('ws://factory-test.local');

      newClient.disconnect();
    });

    it('should create client with default config', () => {
      const newClient = createWebSocketClient();

      expect(newClient).toBeInstanceOf(WebSocketClient);
      expect(newClient.getConfig()).toBeDefined();

      newClient.disconnect();
    });
  });

  // ============================================
  // EDGE CASES
  // ============================================

  describe('Edge Cases', () => {
    it('should handle rapid connect/disconnect cycles', () => {
      for (let i = 0; i < 5; i++) {
        client.connect();
        mockWsInstance?.simulateOpen();
        client.disconnect();
      }

      expect(client.getState()).toBe('disconnected');
      expect(client.isConnected()).toBe(false);
    });

    it('should handle subscribe before connect', () => {
      client.subscribe('spec-001');

      // Should track subscription even if not connected
      expect(client.getSubscriptions()).toContain('spec-001');

      // Should send subscribe message after connection
      client.connect();

      // Need to access mockWsInstance AFTER connect() creates it
      expect(mockWsInstance).not.toBeNull();

      mockWsInstance?.simulateOpen();

      const messages = mockWsInstance?.getSentMessages() || [];
      expect(messages.some((msg) => {
        const parsed = JSON.parse(msg);
        return parsed.action === 'subscribe' && parsed.spec_id === 'spec-001';
      })).toBe(true);
    });

    it('should handle multiple event types in sequence', () => {
      const executionHandler = vi.fn();
      const logHandler = vi.fn();
      const errorHandler = vi.fn();

      client.on('execution', executionHandler);
      client.on('log', logHandler);
      client.on('error', errorHandler);

      client.connect();
      expect(mockWsInstance).not.toBeNull();

      mockWsInstance?.simulateOpen();

      const executionEvent: ExecutionEvent = {
        event_type: 'execution',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        data: { phase: 'coding', phase_progress: 50, overall_progress: 25 },
      };

      const logEvent: LogEvent = {
        event_type: 'log',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        log_line: 'Test log',
        level: 'info',
      };

      const errorEvent: ErrorEvent = {
        event_type: 'error',
        timestamp: '2024-01-01T00:00:00Z',
        spec_id: 'spec-001',
        error_message: 'Test error',
      };

      mockWsInstance?.simulateMessage(executionEvent);
      mockWsInstance?.simulateMessage(logEvent);
      mockWsInstance?.simulateMessage(errorEvent);

      expect(executionHandler).toHaveBeenCalledWith(executionEvent);
      expect(logHandler).toHaveBeenCalledWith(logEvent);
      expect(errorHandler).toHaveBeenCalledWith(errorEvent);
    });

    it('should handle empty subscriptions list', () => {
      client.connect();
      mockWsInstance?.simulateOpen();

      expect(client.getSubscriptions()).toEqual([]);

      // Unsubscribe from non-existent subscription should not error
      client.unsubscribe('non-existent');

      expect(client.getSubscriptions()).toEqual([]);
    });
  });
});
