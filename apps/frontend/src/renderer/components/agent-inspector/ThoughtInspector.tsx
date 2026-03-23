/**
 * ThoughtInspector Component
 *
 * Main component for displaying agent thoughts and tool calls in real-time.
 * Provides timeline view, filtering, and performance insights.
 */

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Brain,
  Wrench,
  List,
  RefreshCw,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Card, CardContent } from '../ui/card';
import { cn } from '../../lib/utils';
import { ThoughtBlock, type AgentThinkingBlock } from './ThoughtBlock';
import { ToolCallBlock, type AgentToolCall } from './ToolCallBlock';

/** View modes for the inspector */
type InspectorView = 'timeline' | 'thoughts' | 'tools';

/** Combined timeline entry */
interface TimelineEntry {
  id: string;
  timestamp: string;
  type: 'thought' | 'tool';
  data: AgentThinkingBlock | AgentToolCall;
}

interface ThoughtInspectorProps {
  /** Path to the project directory */
  projectPath: string;
  /** Spec ID to load thoughts for (optional, loads all if not provided) */
  specId?: string;
  /** Optional session ID to filter by */
  sessionId?: string;
  /** Callback when thought is selected */
  onThoughtSelect?: (thought: AgentThinkingBlock) => void;
  /** Callback when tool call is selected */
  onToolCallSelect?: (toolCall: AgentToolCall) => void;
}

/**
 * Main ThoughtInspector component
 */
export function ThoughtInspector({
  projectPath,
  specId,
  sessionId,
  onThoughtSelect,
  onToolCallSelect,
}: ThoughtInspectorProps) {
  const { t } = useTranslation(['agent-inspector', 'common']);

  // State
  const [currentView, setCurrentView] = useState<InspectorView>('timeline');
  const [thoughts, setThoughts] = useState<AgentThinkingBlock[]>([]);
  const [toolCalls, setToolCalls] = useState<AgentToolCall[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Load thoughts and tool calls from backend
  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // Use electronAPI if available (Electron), otherwise use mock data (browser)
      if (!window.electronAPI?.agentInspector || !specId) {
        // In browser mode or without specId, use empty arrays
        setThoughts([]);
        setToolCalls([]);
        setLoading(false);
        setRefreshing(false);
        return;
      }

      // Get combined inspector data from backend
      const result = await window.electronAPI.agentInspector.getInspectorData(
        projectPath,
        specId,
        sessionId
      );

      if (!result.success || !result.data) {
        throw new Error(result.error || 'Failed to load inspector data');
      }

      setThoughts(result.data.thoughts);
      setToolCalls(result.data.toolCalls);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [projectPath, specId, sessionId]);

  // Initial load
  useEffect(() => {
    loadData();
  }, [loadData]);

  // Refresh handler
  const handleRefresh = useCallback(() => {
    setRefreshing(true);
    loadData();
  }, [loadData]);

  // Combine thoughts and tool calls into timeline
  const timeline = useMemo((): TimelineEntry[] => {
    const entries: TimelineEntry[] = [
      ...thoughts.map((thought) => ({
        id: thought.id,
        timestamp: thought.timestamp,
        type: 'thought' as const,
        data: thought,
      })),
      ...toolCalls.map((toolCall) => ({
        id: toolCall.id,
        timestamp: toolCall.timestamp,
        type: 'tool' as const,
        data: toolCall,
      })),
    ];

    // Sort by timestamp (newest first)
    return entries.sort((a, b) =>
      new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
  }, [thoughts, toolCalls]);

  // Filter entries based on current view
  const filteredEntries = useMemo(() => {
    if (currentView === 'thoughts') {
      return timeline.filter((entry) => entry.type === 'thought');
    }
    if (currentView === 'tools') {
      return timeline.filter((entry) => entry.type === 'tool');
    }
    return timeline;
  }, [timeline, currentView]);

  // Count statistics
  const stats = useMemo(() => ({
    totalThoughts: thoughts.length,
    totalToolCalls: toolCalls.length,
    totalEntries: timeline.length,
  }), [thoughts.length, toolCalls.length, timeline.length]);

  // Render loading state
  if (loading && !thoughts.length && !toolCalls.length) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground">
            {t('agent-inspector:loading')}
          </p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error && !thoughts.length && !toolCalls.length) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
              <div>
                <h3 className="font-semibold text-lg">
                  {t('agent-inspector:errors.loadFailed')}
                </h3>
                <p className="text-sm text-muted-foreground mt-2">{error}</p>
              </div>
              <Button onClick={handleRefresh} variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                {t('common:actions.retry')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-none border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold">
              {t('agent-inspector:title', 'Agent Inspector')}
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t('agent-inspector:subtitle', 'View agent reasoning and tool calls in real-time')}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="text-sm text-muted-foreground mr-4">
              {stats.totalEntries} {t('agent-inspector:totalSteps', 'total steps')}
            </div>
            <Button
              onClick={handleRefresh}
              disabled={refreshing}
              variant="outline"
              size="sm"
            >
              <RefreshCw className={cn('w-4 h-4 mr-2', refreshing && 'animate-spin')} />
              {t('common:actions.refresh')}
            </Button>
          </div>
        </div>

        {/* View Tabs */}
        <div className="flex gap-2 px-6 pb-4">
          <Button
            variant={currentView === 'timeline' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('timeline')}
          >
            <List className="w-4 h-4 mr-2" />
            {t('agent-inspector:views.timeline')}
            <span className="ml-2 text-xs opacity-70">({stats.totalEntries})</span>
          </Button>
          <Button
            variant={currentView === 'thoughts' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('thoughts')}
          >
            <Brain className="w-4 h-4 mr-2" />
            {t('agent-inspector:views.thoughts')}
            <span className="ml-2 text-xs opacity-70">({stats.totalThoughts})</span>
          </Button>
          <Button
            variant={currentView === 'tools' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('tools')}
          >
            <Wrench className="w-4 h-4 mr-2" />
            {t('agent-inspector:views.toolCalls')}
            <span className="ml-2 text-xs opacity-70">({stats.totalToolCalls})</span>
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6">
          {filteredEntries.length === 0 ? (
            // Empty state
            <Card>
              <CardContent className="pt-6">
                <div className="text-center space-y-4 py-8">
                  <div className="mx-auto w-12 h-12 rounded-full bg-muted flex items-center justify-center">
                    {currentView === 'thoughts' && <Brain className="w-6 h-6 text-muted-foreground" />}
                    {currentView === 'tools' && <Wrench className="w-6 h-6 text-muted-foreground" />}
                    {currentView === 'timeline' && <List className="w-6 h-6 text-muted-foreground" />}
                  </div>
                  <div>
                    <h3 className="font-semibold text-lg">
                      {t('agent-inspector:noThoughtsYet')}
                    </h3>
                    <p className="text-sm text-muted-foreground mt-2">
                      {t('agent-inspector:noThoughtsDescription')}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          ) : (
            // Timeline entries
            <div className="space-y-4">
              {filteredEntries.map((entry) => {
                if (entry.type === 'thought') {
                  const thought = entry.data as AgentThinkingBlock;
                  return (
                    <ThoughtBlock
                      key={entry.id}
                      thought={thought}
                      defaultExpanded={false}
                    />
                  );
                }

                const toolCall = entry.data as AgentToolCall;
                return (
                  <ToolCallBlock
                    key={entry.id}
                    toolCall={toolCall}
                    defaultExpanded={false}
                  />
                );
              })}
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
