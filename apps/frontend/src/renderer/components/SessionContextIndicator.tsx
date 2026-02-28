import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Database,
  CheckCircle,
  AlertCircle,
  Loader2,
  MessageSquare,
  FileText
} from 'lucide-react';
import { Button } from './ui/button';
import { Popover, PopoverContent, PopoverTrigger } from './ui/popover';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import type { SessionContextSummary } from '../../shared/types';

interface SessionContextIndicatorProps {
  projectId?: string;
  taskId?: string;
  className?: string;
}

type StatusType = 'loading' | 'persisting' | 'error' | 'no-data';

// Check every 30 seconds for session context updates
const CHECK_INTERVAL_MS = 30 * 1000;

/**
 * Session Context Indicator for the sidebar.
 * Shows whether session context is being persisted and displays context size.
 */
export function SessionContextIndicator({
  projectId,
  taskId,
  className
}: SessionContextIndicatorProps) {
  const { t } = useTranslation(['common', 'navigation']);
  const [status, setStatus] = useState<StatusType>('loading');
  const [sessions, setSessions] = useState<SessionContextSummary[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  // Load session context data
  const loadSessionData = async () => {
    if (!projectId || !taskId) {
      setStatus('no-data');
      return;
    }

    try {
      setStatus('loading');

      // Get session summaries from electronAPI
      // TODO: Type assertion needed until TypeScript picks up the SessionContextAPI type
      const result = await (window.electronAPI as any).getSessionSummaries(
        projectId,
        taskId,
        10 // Get last 10 sessions
      );

      if (result.success && result.data) {
        setSessions(result.data);
        setStatus(result.data.length > 0 ? 'persisting' : 'no-data');
        setLastChecked(new Date());
      } else {
        setStatus('error');
      }
    } catch (err) {
      console.error('Failed to load session context:', err);
      setStatus('error');
    }
  };

  // Initial load and periodic refresh
  useEffect(() => {
    loadSessionData();

    const interval = setInterval(loadSessionData, CHECK_INTERVAL_MS);
    return () => clearInterval(interval);
  }, [projectId, taskId]);

  // Calculate totals
  const totalRounds = sessions.reduce((sum, s) => sum + s.total_rounds, 0);
  const totalTokens = sessions.reduce((sum, s) => sum + s.total_input_tokens + s.total_output_tokens, 0);
  const totalCodeRefs = sessions.reduce((sum, s) => sum + s.code_references.length, 0);

  // Format token count for display
  const formatTokens = (tokens: number): string => {
    if (tokens >= 1000000) {
      return `${(tokens / 1000000).toFixed(1)}M`;
    }
    if (tokens >= 1000) {
      return `${(tokens / 1000).toFixed(1)}K`;
    }
    return tokens.toString();
  };

  // Render status icon
  const renderStatusIcon = () => {
    switch (status) {
      case 'loading':
        return <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />;
      case 'persisting':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-destructive" />;
      case 'no-data':
        return <Database className="h-4 w-4 text-muted-foreground" />;
      default:
        return <Database className="h-4 w-4 text-muted-foreground" />;
    }
  };

  // Get status tooltip text
  const getStatusTooltip = () => {
    switch (status) {
      case 'loading':
        return t('sessionContext.status.loading');
      case 'persisting':
        return t('sessionContext.status.persisting');
      case 'error':
        return t('sessionContext.status.error');
      case 'no-data':
        return t('sessionContext.status.noData');
      default:
        return '';
    }
  };

  return (
    <Popover open={isOpen} onOpenChange={setIsOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className={cn(
            'w-full justify-start px-2 py-1.5 h-auto',
            status === 'error' && 'text-destructive',
            status === 'persisting' && 'text-green-600 dark:text-green-400',
            className
          )}
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <div className="flex items-center gap-2 w-full">
                {renderStatusIcon()}
                <div className="flex items-center gap-1.5 text-xs">
                  <Database className="h-3 w-3" />
                  <span className="font-medium truncate">
                    {t('sessionContext.label')}
                  </span>
                </div>
                {status === 'persisting' && totalRounds > 0 && (
                  <Badge variant="secondary" className="ml-auto text-xs">
                    {totalRounds}
                  </Badge>
                )}
              </div>
            </TooltipTrigger>
            <TooltipContent side="right" className="max-w-xs">
              <p>{getStatusTooltip()}</p>
              {status === 'persisting' && lastChecked && (
                <p className="text-xs text-muted-foreground mt-1">
                  {t('sessionContext.lastChecked', { time: lastChecked.toLocaleTimeString() })}
                </p>
              )}
            </TooltipContent>
          </Tooltip>
        </Button>
      </PopoverTrigger>
      <PopoverContent side="right" className="w-80">
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Database className="h-4 w-4" />
              <h3 className="font-semibold text-sm">{t('sessionContext.title')}</h3>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2"
              onClick={(e) => {
                e.stopPropagation();
                loadSessionData();
              }}
            >
              {status === 'loading' ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                t('common:buttons.refresh', { ns: 'common' })
              )}
            </Button>
          </div>

          {/* Status message */}
          {status === 'error' && (
            <div className="flex items-center gap-2 text-sm text-destructive">
              <AlertCircle className="h-4 w-4" />
              <span>{t('sessionContext.error.loadFailed')}</span>
            </div>
          )}

          {status === 'no-data' && (
            <div className="text-sm text-muted-foreground">
              {t('sessionContext.noSessions')}
            </div>
          )}

          {/* Session stats */}
          {status === 'persisting' && sessions.length > 0 && (
            <>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-muted/50">
                  <MessageSquare className="h-3.5 w-3.5 text-muted-foreground" />
                  <div>
                    <div className="font-medium">{totalRounds}</div>
                    <div className="text-muted-foreground">
                      {t('sessionContext.stats.rounds')}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-1.5 p-2 rounded-lg bg-muted/50">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                  <div>
                    <div className="font-medium">{formatTokens(totalTokens)}</div>
                    <div className="text-muted-foreground">
                      {t('sessionContext.stats.tokens')}
                    </div>
                  </div>
                </div>
              </div>

              {/* Recent sessions list */}
              <div className="space-y-1.5">
                <div className="text-xs font-medium text-muted-foreground">
                  {t('sessionContext.recentSessions')}
                </div>
                <div className="space-y-1 max-h-40 overflow-y-auto">
                  {sessions.slice(0, 5).map((session) => (
                    <div
                      key={session.session_id}
                      className="flex items-center justify-between p-2 rounded-lg bg-muted/30 text-xs"
                    >
                      <div className="flex items-center gap-2">
                        <CheckCircle className="h-3 w-3 text-green-500" />
                        <span className="text-muted-foreground">
                          {new Date(session.session_start).toLocaleTimeString()}
                        </span>
                      </div>
                      <Badge variant="secondary" className="text-xs">
                        {session.total_rounds} {t('sessionContext.stats.rounds')}
                      </Badge>
                    </div>
                  ))}
                </div>
              </div>

              {/* Footer */}
              <div className="pt-2 border-t text-xs text-muted-foreground">
                {t('sessionContext.summary', {
                  sessions: sessions.length,
                  rounds: totalRounds,
                  codeRefs: totalCodeRefs
                })}
              </div>
            </>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
