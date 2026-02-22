/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useInsightsStore } from '../insights-store';
import type { InsightsChatMessage, InsightsSession } from '../../../shared/types';

function makeMessage(overrides: Partial<InsightsChatMessage> = {}): InsightsChatMessage {
  return {
    id: 'msg-1',
    role: 'user',
    content: 'Hello',
    timestamp: new Date(),
    ...overrides,
  } as InsightsChatMessage;
}

function makeSession(messages: InsightsChatMessage[] = []): InsightsSession {
  return {
    id: 'session-1',
    projectId: 'proj-1',
    messages,
    createdAt: new Date(),
    updatedAt: new Date(),
  };
}

describe('insights-store', () => {
  beforeEach(() => {
    useInsightsStore.getState().clearSession();
  });

  describe('initial state', () => {
    it('should have correct defaults', () => {
      const state = useInsightsStore.getState();
      expect(state.session).toBeNull();
      expect(state.sessions).toEqual([]);
      expect(state.status.phase).toBe('idle');
      expect(state.pendingMessage).toBe('');
      expect(state.streamingContent).toBe('');
      expect(state.currentTool).toBeNull();
      expect(state.toolsUsed).toEqual([]);
      expect(state.isLoadingSessions).toBe(false);
    });
  });

  describe('addMessage', () => {
    it('should create session if none exists', () => {
      const msg = makeMessage({ content: 'First message' });
      useInsightsStore.getState().addMessage(msg);

      const session = useInsightsStore.getState().session;
      expect(session).not.toBeNull();
      expect(session!.messages).toHaveLength(1);
      expect(session!.messages[0].content).toBe('First message');
    });

    it('should append to existing session', () => {
      useInsightsStore.setState({
        session: makeSession([makeMessage({ id: 'm1' })]),
      });

      useInsightsStore.getState().addMessage(makeMessage({ id: 'm2', content: 'Second' }));

      expect(useInsightsStore.getState().session!.messages).toHaveLength(2);
    });
  });

  describe('updateLastAssistantMessage', () => {
    it('should update content of last assistant message', () => {
      const session = makeSession([
        makeMessage({ id: 'm1', role: 'user' }),
        makeMessage({ id: 'm2', role: 'assistant', content: 'Old content' }),
      ]);
      useInsightsStore.setState({ session });

      useInsightsStore.getState().updateLastAssistantMessage('New content');

      const messages = useInsightsStore.getState().session!.messages;
      expect(messages[1].content).toBe('New content');
    });

    it('should not modify if last message is not assistant', () => {
      const session = makeSession([
        makeMessage({ id: 'm1', role: 'assistant', content: 'Assistant' }),
        makeMessage({ id: 'm2', role: 'user', content: 'User' }),
      ]);
      useInsightsStore.setState({ session });

      useInsightsStore.getState().updateLastAssistantMessage('Attempted update');

      const messages = useInsightsStore.getState().session!.messages;
      expect(messages[1].content).toBe('User');
    });

    it('should not modify when no session', () => {
      useInsightsStore.getState().updateLastAssistantMessage('test');
      expect(useInsightsStore.getState().session).toBeNull();
    });
  });

  describe('streaming', () => {
    it('should append streaming content', () => {
      useInsightsStore.getState().appendStreamingContent('Hello ');
      useInsightsStore.getState().appendStreamingContent('World');
      expect(useInsightsStore.getState().streamingContent).toBe('Hello World');
    });

    it('should clear streaming content', () => {
      useInsightsStore.setState({ streamingContent: 'some content' });
      useInsightsStore.getState().clearStreamingContent();
      expect(useInsightsStore.getState().streamingContent).toBe('');
    });
  });

  describe('tool tracking', () => {
    it('should set current tool', () => {
      useInsightsStore.getState().setCurrentTool({ name: 'search', input: 'query' });
      expect(useInsightsStore.getState().currentTool).toEqual({ name: 'search', input: 'query' });
    });

    it('should clear current tool', () => {
      useInsightsStore.setState({ currentTool: { name: 'search' } });
      useInsightsStore.getState().setCurrentTool(null);
      expect(useInsightsStore.getState().currentTool).toBeNull();
    });

    it('should add tool usage with timestamp', () => {
      useInsightsStore.getState().addToolUsage({ name: 'read_file', input: '/path' });

      const tools = useInsightsStore.getState().toolsUsed;
      expect(tools).toHaveLength(1);
      expect(tools[0].name).toBe('read_file');
      expect(tools[0].timestamp).toBeDefined();
    });

    it('should clear tools used', () => {
      useInsightsStore.setState({
        toolsUsed: [{ name: 'test', timestamp: new Date() }],
      });
      useInsightsStore.getState().clearToolsUsed();
      expect(useInsightsStore.getState().toolsUsed).toEqual([]);
    });
  });

  describe('finalizeStreamingMessage', () => {
    it('should create assistant message from streaming content', () => {
      useInsightsStore.setState({
        streamingContent: 'Streamed response',
        toolsUsed: [{ name: 'search', timestamp: new Date() }],
      });

      useInsightsStore.getState().finalizeStreamingMessage();

      const state = useInsightsStore.getState();
      expect(state.streamingContent).toBe('');
      expect(state.toolsUsed).toEqual([]);
      expect(state.session).not.toBeNull();
      expect(state.session!.messages).toHaveLength(1);
      expect(state.session!.messages[0].role).toBe('assistant');
      expect(state.session!.messages[0].content).toBe('Streamed response');
      expect(state.session!.messages[0].toolsUsed).toHaveLength(1);
    });

    it('should include suggested task when provided', () => {
      useInsightsStore.setState({ streamingContent: 'Here is a suggestion' });

      const suggestedTask = { title: 'Task', description: 'Description' };
      useInsightsStore.getState().finalizeStreamingMessage(suggestedTask as any);

      const msg = useInsightsStore.getState().session!.messages[0];
      expect(msg.suggestedTask).toEqual(suggestedTask);
    });

    it('should not create message when no content and no suggestion', () => {
      useInsightsStore.setState({ streamingContent: '', toolsUsed: [] });
      useInsightsStore.getState().finalizeStreamingMessage();
      expect(useInsightsStore.getState().session).toBeNull();
    });

    it('should append to existing session', () => {
      useInsightsStore.setState({
        session: makeSession([makeMessage({ role: 'user' })]),
        streamingContent: 'Response',
      });

      useInsightsStore.getState().finalizeStreamingMessage();

      expect(useInsightsStore.getState().session!.messages).toHaveLength(2);
    });
  });

  describe('session management', () => {
    it('should set sessions list', () => {
      const summaries = [{ id: 's1', title: 'Session 1' }];
      useInsightsStore.getState().setSessions(summaries as any);
      expect(useInsightsStore.getState().sessions).toEqual(summaries);
    });

    it('should set loading sessions state', () => {
      useInsightsStore.getState().setLoadingSessions(true);
      expect(useInsightsStore.getState().isLoadingSessions).toBe(true);
    });
  });

  describe('clearSession', () => {
    it('should reset all session state', () => {
      useInsightsStore.setState({
        session: makeSession([makeMessage()]),
        status: { phase: 'streaming', message: 'test' },
        pendingMessage: 'pending',
        streamingContent: 'content',
        currentTool: { name: 'search' },
        toolsUsed: [{ name: 'test', timestamp: new Date() }],
      });

      useInsightsStore.getState().clearSession();

      const state = useInsightsStore.getState();
      expect(state.session).toBeNull();
      expect(state.status.phase).toBe('idle');
      expect(state.pendingMessage).toBe('');
      expect(state.streamingContent).toBe('');
      expect(state.currentTool).toBeNull();
      expect(state.toolsUsed).toEqual([]);
    });
  });
});
