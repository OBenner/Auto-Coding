import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Clock,
  MessageSquare,
  FileCode,
  RefreshCw,
  AlertCircle,
  Loader2,
  User,
  Bot,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import type { ConversationHistory, ConversationRound } from '../../shared/types';

interface SessionContextViewerProps {
  projectId: string;
}

export function SessionContextViewer({ projectId }: SessionContextViewerProps) {
  const { t } = useTranslation(['common', 'navigation']);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [conversationHistories, setConversationHistories] = useState<ConversationHistory[]>([]);
  const [expandedRounds, setExpandedRounds] = useState<Set<string>>(new Set());

  // Load session context data via IPC
  useEffect(() => {
    loadSessionData();
  }, [projectId]);

  const loadSessionData = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // TODO: Get taskId from props or route params
      // For now, using a placeholder task ID
      const taskId = '119-extended-context-session-manager';

      // Get conversation history from electronAPI
      // TODO: Type assertion needed until TypeScript picks up the SessionContextAPI type
      const result = await (window.electronAPI as any).getConversationHistory(
        projectId,
        taskId
      );

      if (result.success && result.data) {
        setConversationHistories(result.data);
      } else if (result.error) {
        setError(result.error);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load session data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRefresh = () => {
    loadSessionData();
  };

  const toggleRoundExpansion = (roundId: string) => {
    setExpandedRounds(prev => {
      const newSet = new Set(prev);
      if (newSet.has(roundId)) {
        newSet.delete(roundId);
      } else {
        newSet.add(roundId);
      }
      return newSet;
    });
  };

  // Calculate session overview stats
  const totalRounds = conversationHistories.reduce((sum, hist) => sum + hist.rounds.length, 0);
  const totalCodeRefs = conversationHistories.reduce(
    (sum, hist) => sum + (hist.all_code_references?.length || 0),
    0
  );

  // Calculate session duration (from first session start to now)
  const sessionDuration = conversationHistories.length > 0
    ? calculateDuration(conversationHistories[conversationHistories.length - 1].session_start)
    : '0h';

  function calculateDuration(startTime: string): string {
    const start = new Date(startTime);
    const now = new Date();
    const diffMs = now.getTime() - start.getTime();
    const hours = Math.floor(diffMs / (1000 * 60 * 60));
    const minutes = Math.floor((diffMs % (1000 * 60 * 60)) / (1000 * 60));

    if (hours > 0) {
      return `${hours}h ${minutes}m`;
    }
    return `${minutes}m`;
  }

  function formatTimestamp(timestamp: string): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / (1000 * 60));

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffMins < 1440) return `${Math.floor(diffMins / 60)}h ago`;
    return date.toLocaleDateString();
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{t('navigation:items.sessionContext')}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {t('common:sessionContext.description')}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', isLoading && 'animate-spin')} />
            {t('common:accessibility.refreshAriaLabel')}
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Error State */}
          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  <p className="text-sm">{error}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Loading State */}
          {isLoading && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Session Overview */}
          {!isLoading && !error && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      {t('common:sessionContext.conversationRounds')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{totalRounds}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <FileCode className="h-4 w-4 text-muted-foreground" />
                      {t('common:sessionContext.codeReferences')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{totalCodeRefs}</div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      {t('common:sessionContext.sessionDuration')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">{sessionDuration}</div>
                  </CardContent>
                </Card>
              </div>

              {/* Session Timeline */}
              <Card>
                <CardHeader>
                  <CardTitle>{t('common:sessionContext.timeline')}</CardTitle>
                  <CardDescription>
                    {t('common:sessionContext.timelineDescription')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {conversationHistories.length === 0 ? (
                    <div className="text-center py-8 text-muted-foreground">
                      <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                      <p className="text-sm">
                        {t('common:sessionContext.noSessionData')}
                      </p>
                      <p className="text-xs mt-1">
                        {t('common:sessionContext.startAgentSession')}
                      </p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      {conversationHistories.map((history) => (
                        <div key={history.session_id} className="space-y-4">
                          {/* Session Header */}
                          <div className="flex items-center gap-2 text-sm">
                            <Badge variant="outline" className="text-xs">
                              {history.session_id.slice(0, 8)}
                            </Badge>
                            <span className="text-muted-foreground">
                              {formatTimestamp(history.session_start)}
                            </span>
                            <span className="text-muted-foreground">•</span>
                            <span className="text-muted-foreground">
                              {history.rounds.length} rounds
                            </span>
                          </div>

                          {/* Conversation Rounds Timeline */}
                          <div className="space-y-3">
                            {history.rounds.map((round, roundIndex) => {
                              const roundId = `${history.session_id}-${round.round_number}`;
                              const isExpanded = expandedRounds.has(roundId);

                              return (
                                <div
                                  key={roundId}
                                  className="border border-border rounded-lg overflow-hidden"
                                >
                                  {/* Round Header */}
                                  <button
                                    type="button"
                                    onClick={() => toggleRoundExpansion(roundId)}
                                    className="w-full px-4 py-3 flex items-start gap-3 hover:bg-accent/50 transition-colors text-left"
                                  >
                                    <div className="flex items-center gap-2 mt-0.5 shrink-0">
                                      {roundIndex % 2 === 0 ? (
                                        <User className="h-4 w-4 text-muted-foreground" />
                                      ) : (
                                        <Bot className="h-4 w-4 text-primary" />
                                      )}
                                      <span className="text-sm font-medium text-muted-foreground">
                                        #{round.round_number}
                                      </span>
                                    </div>

                                    <div className="flex-1 min-w-0">
                                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                                        <Badge variant="secondary" className="text-xs">
                                          {round.phase}
                                        </Badge>
                                        <span className="text-xs text-muted-foreground">
                                          {formatTimestamp(round.timestamp)}
                                        </span>
                                        {round.code_references.length > 0 && (
                                          <>
                                            <FileCode className="h-3 w-3 text-muted-foreground" />
                                            <span className="text-xs text-muted-foreground">
                                              {round.code_references.length} ref
                                              {round.code_references.length > 1 ? 's' : ''}
                                            </span>
                                          </>
                                        )}
                                      </div>

                                      <p className="text-sm truncate">
                                        {round.user_message || round.assistant_response}
                                      </p>
                                    </div>

                                    <div className="shrink-0">
                                      {isExpanded ? (
                                        <ChevronUp className="h-4 w-4 text-muted-foreground" />
                                      ) : (
                                        <ChevronDown className="h-4 w-4 text-muted-foreground" />
                                      )}
                                    </div>
                                  </button>

                                  {/* Expanded Content */}
                                  {isExpanded && (
                                    <div className="border-t border-border bg-muted/30 p-4 space-y-4">
                                      {/* User Message */}
                                      {round.user_message && (
                                        <div className="space-y-2">
                                          <div className="flex items-center gap-2 text-sm font-medium">
                                            <User className="h-4 w-4 text-muted-foreground" />
                                            <span>User Message</span>
                                          </div>
                                          <div className="pl-6 text-sm text-muted-foreground whitespace-pre-wrap">
                                            {round.user_message}
                                          </div>
                                        </div>
                                      )}

                                      {/* Assistant Response */}
                                      {round.assistant_response && (
                                        <div className="space-y-2">
                                          <div className="flex items-center gap-2 text-sm font-medium">
                                            <Bot className="h-4 w-4 text-primary" />
                                            <span>Assistant Response</span>
                                          </div>
                                          <div className="pl-6 text-sm text-muted-foreground whitespace-pre-wrap">
                                            {round.assistant_response}
                                          </div>
                                        </div>
                                      )}

                                      {/* Code References */}
                                      {round.code_references.length > 0 && (
                                        <div className="space-y-2">
                                          <div className="flex items-center gap-2 text-sm font-medium">
                                            <FileCode className="h-4 w-4 text-primary" />
                                            <span>Code References</span>
                                          </div>
                                          <div className="pl-6 space-y-1">
                                            {round.code_references.map((ref, idx) => (
                                              <div
                                                key={idx}
                                                className="text-xs font-mono bg-background border border-border rounded px-2 py-1 text-primary"
                                              >
                                                {ref}
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Tool Calls */}
                                      {round.tool_calls.length > 0 && (
                                        <div className="space-y-2">
                                          <div className="flex items-center gap-2 text-sm font-medium">
                                            <RefreshCw className="h-4 w-4 text-muted-foreground" />
                                            <span>Tool Calls ({round.tool_calls.length})</span>
                                          </div>
                                          <div className="pl-6 space-y-1">
                                            {round.tool_calls.map((tool, idx) => (
                                              <div
                                                key={idx}
                                                className="text-xs font-mono bg-background border border-border rounded px-2 py-1"
                                              >
                                                <span className="font-medium text-primary">
                                                  {tool.name}
                                                </span>
                                              </div>
                                            ))}
                                          </div>
                                        </div>
                                      )}

                                      {/* Token Usage */}
                                      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border">
                                        <span>Input: {round.input_tokens.toLocaleString()} tokens</span>
                                        <span>Output: {round.output_tokens.toLocaleString()} tokens</span>
                                      </div>
                                    </div>
                                  )}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
