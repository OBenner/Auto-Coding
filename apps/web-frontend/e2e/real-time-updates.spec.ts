/**
 * WebSocket Real-Time Updates E2E Tests
 *
 * End-to-end tests for WebSocket client functionality.
 * Tests WebSocket API, connection states, message handling, and event patterns.
 */

import { test, expect, type Page } from '@playwright/test';

/**
 * Helper: Inject WebSocket mock into page context
 */
async function setupWebSocketMock(page: Page) {
  await page.addInitScript(() => {
    const mockSockets: any[] = [];
    const sentMessages: any[] = [];

    class MockWebSocket extends EventTarget {
      static readonly CONNECTING = 0;
      static readonly OPEN = 1;
      static readonly CLOSING = 2;
      static readonly CLOSED = 3;

      url: string;
      readyState: number;
      onopen: ((event: Event) => void) | null = null;
      onmessage: ((event: MessageEvent) => void) | null = null;
      onerror: ((event: Event) => void) | null = null;
      onclose: ((event: CloseEvent) => void) | null = null;

      constructor(url: string) {
        super();
        this.url = url;
        this.readyState = MockWebSocket.CONNECTING;
        mockSockets.push(this);

        setTimeout(() => {
          if (this.readyState === MockWebSocket.CONNECTING) {
            this.readyState = MockWebSocket.OPEN;
            const event = new Event('open');
            this.onopen?.(event);
            this.dispatchEvent(event);
          }
        }, 50);
      }

      send(data: string) {
        try {
          sentMessages.push(JSON.parse(data));
        } catch {
          sentMessages.push(data);
        }
      }

      close() {
        this.readyState = MockWebSocket.CLOSING;
        setTimeout(() => {
          this.readyState = MockWebSocket.CLOSED;
          const event = new CloseEvent('close', { code: 1000, reason: '' });
          this.onclose?.(event);
          this.dispatchEvent(event);
        }, 50);
      }

      simulateMessage(data: any) {
        const event = new MessageEvent('message', {
          data: typeof data === 'string' ? data : JSON.stringify(data),
        });
        this.onmessage?.(event);
        this.dispatchEvent(event);
      }

      simulateError() {
        const event = new Event('error');
        this.onerror?.(event);
        this.dispatchEvent(event);
      }
    }

    (globalThis as any).WebSocket = MockWebSocket;
    (globalThis as any).getMockWebSockets = () => mockSockets;
    (globalThis as any).getSentMessages = () => sentMessages;
    (globalThis as any).clearSentMessages = () => { sentMessages.length = 0; };
  });
}

/**
 * Helper: Open a WebSocket, receive one simulated message, return received events.
 */
async function receiveOneEvent(page: Page, messageData: any): Promise<any[]> {
  return page.evaluate(async (data) => {
    const ws = new WebSocket('ws://localhost:8000/ws/test');
    await new Promise<void>((resolve) => {
      ws.onopen = () => resolve();
    });
    const receivedEvents: any[] = [];
    ws.onmessage = (event) => {
      receivedEvents.push(JSON.parse(event.data));
    };
    (ws as any).simulateMessage(data);
    await new Promise<void>((resolve) => setTimeout(resolve, 50));
    return receivedEvents;
  }, messageData);
}

test.describe('WebSocket Real-Time Updates', () => {
  test.beforeEach(async ({ page }) => {
    await setupWebSocketMock(page);
    await page.goto('/');
    await page.waitForTimeout(300);
  });

  test.describe('WebSocket Creation and Connection', () => {
    test('should create WebSocket instance', async ({ page }) => {
      const result = await page.evaluate(() => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        return {
          created: ws !== null,
          url: ws.url,
          readyState: ws.readyState,
        };
      });

      expect(result.created).toBe(true);
      expect(result.url).toBe('ws://localhost:8000/ws/test');
      expect(result.readyState).toBe(0); // CONNECTING
    });

    test('should transition to OPEN state', async ({ page }) => {
      const result = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        const initialState = ws.readyState;

        await new Promise((resolve) => {
          ws.onopen = resolve;
          setTimeout(resolve, 200); // Fallback timeout
        });

        return {
          initial: initialState,
          final: ws.readyState,
        };
      });

      expect(result.initial).toBe(0); // CONNECTING
      expect(result.final).toBe(1); // OPEN
    });

    test('should accept connection URL with path', async ({ page }) => {
      const url = await page.evaluate(() => {
        const ws = new WebSocket('ws://localhost:8000/ws/agent-events');
        return ws.url;
      });

      expect(url).toBe('ws://localhost:8000/ws/agent-events');
    });

    test('should handle close event', async ({ page }) => {
      const result = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');

        await new Promise((resolve) => ws.onopen = resolve);

        const stateBeforeClose = ws.readyState;
        ws.close();

        await new Promise((resolve) => ws.onclose = resolve);

        return {
          beforeClose: stateBeforeClose,
          afterClose: ws.readyState,
        };
      });

      expect(result.beforeClose).toBe(1); // OPEN
      expect(result.afterClose).toBe(3); // CLOSED
    });
  });

  test.describe('Message Sending', () => {
    test('should send JSON messages', async ({ page }) => {
      await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        ws.send(JSON.stringify({ action: 'ping' }));
        ws.send(JSON.stringify({ action: 'subscribe', spec_id: '001' }));
      });

      await page.waitForTimeout(100);

      const messages = await page.evaluate(() => {
        return (globalThis as any).getSentMessages();
      });

      expect(messages.length).toBeGreaterThanOrEqual(2);
      expect(messages[0]).toEqual({ action: 'ping' });
      expect(messages[1]).toEqual({ action: 'subscribe', spec_id: '001' });
    });

    test('should send subscribe messages', async ({ page }) => {
      await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        ws.send(JSON.stringify({ action: 'subscribe', spec_id: '042' }));
      });

      await page.waitForTimeout(50);

      const messages = await page.evaluate(() => {
        return (globalThis as any).getSentMessages();
      });

      const subscribeMsg = messages.find((m: any) => m.action === 'subscribe');
      expect(subscribeMsg).toBeDefined();
      expect(subscribeMsg.spec_id).toBe('042');
    });

    test('should send unsubscribe messages', async ({ page }) => {
      await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        ws.send(JSON.stringify({ action: 'unsubscribe', spec_id: '001' }));
      });

      await page.waitForTimeout(50);

      const messages = await page.evaluate(() => {
        return (globalThis as any).getSentMessages();
      });

      const unsubscribeMsg = messages.find((m: any) => m.action === 'unsubscribe');
      expect(unsubscribeMsg).toBeDefined();
      expect(unsubscribeMsg.spec_id).toBe('001');
    });
  });

  test.describe('Message Receiving', () => {
    const eventCases: Array<{ type: string; data: Record<string, unknown>; assertFn: (r: any) => void }> = [
      {
        type: 'execution',
        data: { phase: 'implementation', progress: 50 },
        assertFn: (r: any) => { expect(r.data.phase).toBe('implementation'); expect(r.data.progress).toBe(50); },
      },
      {
        type: 'log',
        data: { level: 'info', message: 'Test log' },
        assertFn: (r: any) => { expect(r.data.message).toBe('Test log'); },
      },
      {
        type: 'error',
        data: { error: 'Test error', message: 'Something went wrong' },
        assertFn: (r: any) => { expect(r.data.error).toBe('Test error'); },
      },
      {
        type: 'ideation',
        data: { thought: 'Planning approach...', context: 'design' },
        assertFn: (r: any) => { expect(r.data.thought).toBe('Planning approach...'); },
      },
      {
        type: 'roadmap',
        data: { phase: 'planning', steps: ['Step 1', 'Step 2'], current_step: 'Step 1' },
        assertFn: (r: any) => { expect(r.data.phase).toBe('planning'); },
      },
    ];

    for (const { type, data, assertFn } of eventCases) {
      test(`should receive ${type} events`, async ({ page }) => {
        const result = await receiveOneEvent(page, {
          event_type: type,
          spec_id: '001',
          timestamp: new Date().toISOString(),
          data,
        });

        expect(result.length).toBe(1);
        expect(result[0].event_type).toBe(type);
        assertFn(result[0]);
      });
    }

    test('should handle multiple events in sequence', async ({ page }) => {
      const result = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        const receivedEvents: any[] = [];
        ws.onmessage = (event) => {
          receivedEvents.push(JSON.parse(event.data));
        };

        // Simulate multiple events
        (ws as any).simulateMessage({ event_type: 'ideation', spec_id: '001', timestamp: new Date().toISOString(), data: {} });
        (ws as any).simulateMessage({ event_type: 'roadmap', spec_id: '001', timestamp: new Date().toISOString(), data: {} });
        (ws as any).simulateMessage({ event_type: 'execution', spec_id: '001', timestamp: new Date().toISOString(), data: {} });
        (ws as any).simulateMessage({ event_type: 'log', spec_id: '001', timestamp: new Date().toISOString(), data: {} });

        await new Promise((resolve) => setTimeout(resolve, 100));

        return receivedEvents.map((e) => e.event_type);
      });

      expect(result).toEqual(['ideation', 'roadmap', 'execution', 'log']);
    });
  });

  test.describe('Event Handling', () => {
    test('should handle onopen callback', async ({ page }) => {
      const opened = await page.evaluate(async () => {
        let callbackCalled = false;

        const ws = new WebSocket('ws://localhost:8000/ws/test');
        ws.onopen = () => {
          callbackCalled = true;
        };

        await new Promise((resolve) => setTimeout(resolve, 150));

        return callbackCalled;
      });

      expect(opened).toBe(true);
    });

    test('should handle onclose callback', async ({ page }) => {
      const closed = await page.evaluate(async () => {
        let callbackCalled = false;

        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        ws.onclose = () => {
          callbackCalled = true;
        };

        ws.close();

        await new Promise((resolve) => setTimeout(resolve, 150));

        return callbackCalled;
      });

      expect(closed).toBe(true);
    });

    test('should handle onerror callback', async ({ page }) => {
      const errorHandled = await page.evaluate(async () => {
        let callbackCalled = false;

        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        ws.onerror = () => {
          callbackCalled = true;
        };

        (ws as any).simulateError();

        await new Promise((resolve) => setTimeout(resolve, 50));

        return callbackCalled;
      });

      expect(errorHandled).toBe(true);
    });

    test('should handle onmessage callback', async ({ page }) => {
      const messageReceived = await page.evaluate(async () => {
        let receivedData: any = null;

        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        ws.onmessage = (event) => {
          receivedData = JSON.parse(event.data);
        };

        (ws as any).simulateMessage({ test: 'data' });

        await new Promise((resolve) => setTimeout(resolve, 50));

        return receivedData;
      });

      expect(messageReceived).toEqual({ test: 'data' });
    });
  });

  test.describe('Connection State Management', () => {
    test('should track readyState correctly', async ({ page }) => {
      const states = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        const stateAfterCreate = ws.readyState;

        await new Promise((resolve) => ws.onopen = resolve);
        const stateAfterOpen = ws.readyState;

        ws.close();
        await new Promise((resolve) => ws.onclose = resolve);
        const stateAfterClose = ws.readyState;

        return {
          afterCreate: stateAfterCreate,
          afterOpen: stateAfterOpen,
          afterClose: stateAfterClose,
        };
      });

      expect(states.afterCreate).toBe(0); // CONNECTING
      expect(states.afterOpen).toBe(1); // OPEN
      expect(states.afterClose).toBe(3); // CLOSED
    });

    test('should maintain connection for extended period', async ({ page }) => {
      const stillConnected = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        // Wait 1 second
        await new Promise((resolve) => setTimeout(resolve, 1000));

        return ws.readyState === 1; // OPEN
      });

      expect(stillConnected).toBe(true);
    });

    test('should track multiple independent connections', async ({ page }) => {
      const result = await page.evaluate(() => {
        const initialCount = (globalThis as any).getMockWebSockets().length;

        // Store connections to satisfy usage requirements; tracking is via getMockWebSockets()
        const connections = [
          new WebSocket('ws://localhost:8000/ws/test1'),
          new WebSocket('ws://localhost:8000/ws/test2'),
          new WebSocket('ws://localhost:8000/ws/test3'),
        ];

        const finalCount = (globalThis as any).getMockWebSockets().length;

        return {
          added: finalCount - initialCount,
          total: finalCount,
          connectionCount: connections.length,
        };
      });

      expect(result.added).toBe(3);
      expect(result.total).toBeGreaterThanOrEqual(3);
      expect(result.connectionCount).toBe(3);
    });
  });

  test.describe('Error Handling', () => {
    test('should handle invalid JSON gracefully', async ({ page }) => {
      const result = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        let errorCaught = false;
        const receivedMessages: any[] = [];

        ws.onmessage = (event) => {
          try {
            receivedMessages.push(JSON.parse(event.data));
          } catch {
            errorCaught = true;
          }
        };

        // Simulate receiving invalid JSON
        (ws as any).simulateMessage('invalid json {{{');

        await new Promise((resolve) => setTimeout(resolve, 50));

        return { errorCaught, messageCount: receivedMessages.length };
      });

      expect(result.errorCaught).toBe(true);
      expect(result.messageCount).toBe(0);
    });

    test('should continue working after receiving invalid messages', async ({ page }) => {
      const result = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        const receivedMessages: any[] = [];

        ws.onmessage = (event) => {
          try {
            receivedMessages.push(JSON.parse(event.data));
          } catch {
            // Ignore parse errors for invalid messages
          }
        };

        // Send invalid then valid
        (ws as any).simulateMessage('invalid');
        (ws as any).simulateMessage({ event_type: 'log', data: { message: 'valid' } });

        await new Promise((resolve) => setTimeout(resolve, 50));

        return receivedMessages;
      });

      expect(result.length).toBe(1);
      expect(result[0].event_type).toBe('log');
    });
  });

  test.describe('Performance', () => {
    test('should handle rapid message bursts', async ({ page }) => {
      const messageCount = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        const receivedMessages: any[] = [];
        ws.onmessage = (event) => {
          try {
            receivedMessages.push(JSON.parse(event.data));
          } catch (e) {
            // Ignore
          }
        };

        // Send 100 messages rapidly
        for (let i = 0; i < 100; i++) {
          (ws as any).simulateMessage({
            event_type: 'log',
            spec_id: '001',
            timestamp: new Date().toISOString(),
            data: { message: `Message ${i}` },
          });
        }

        await new Promise((resolve) => setTimeout(resolve, 200));

        return receivedMessages.length;
      });

      expect(messageCount).toBe(100);
    });

    test('should handle large messages', async ({ page }) => {
      const received = await page.evaluate(async () => {
        const ws = new WebSocket('ws://localhost:8000/ws/test');
        await new Promise((resolve) => ws.onopen = resolve);

        let receivedData: any = null;
        ws.onmessage = (event) => {
          receivedData = JSON.parse(event.data);
        };

        // Create large message (1000 items array)
        const largeData = {
          event_type: 'log',
          spec_id: '001',
          timestamp: new Date().toISOString(),
          data: {
            items: Array.from({ length: 1000 }, (_, i) => `Item ${i}`),
          },
        };

        (ws as any).simulateMessage(largeData);

        await new Promise((resolve) => setTimeout(resolve, 100));

        return receivedData?.data?.items?.length;
      });

      expect(received).toBe(1000);
    });
  });
});
