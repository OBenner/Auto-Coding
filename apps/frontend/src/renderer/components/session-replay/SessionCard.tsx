/**
 * SessionCard Component
 *
 * Displays a session preview card with metadata.
 * Shows session status, duration, subtask count, and relative time.
 */

import { memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { Clock, CheckCircle2, Loader2 } from 'lucide-react';
import { Card, CardContent } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { cn, formatRelativeTime } from '../lib/utils';
import type { SessionMetadata } from '../../../shared/types';

interface SessionCardProps {
  /** Session data to display */
  session: SessionMetadata;
  /** Callback when card is clicked */
  onClick?: () => void;
}

// Custom comparator for React.memo - only re-render when relevant session data changes
function sessionCardPropsAreEqual(prevProps: SessionCardProps, nextProps: SessionCardProps): boolean {
  const prevSession = prevProps.session;
  const nextSession = nextProps.session;

  // Fast path: same reference
  if (prevSession === nextSession && prevProps.onClick === nextProps.onClick) {
    return true;
  }

  // Compare only the fields that affect rendering
  return (
    prevSession.session_id === nextSession.session_id &&
    prevSession.started_at === nextSession.started_at &&
    prevSession.completed_at === nextSession.completed_at &&
    prevSession.duration_seconds === nextSession.duration_seconds &&
    prevSession.session_number === nextSession.session_number &&
    prevSession.subtasks.length === nextSession.subtasks.length
  );
}

export const SessionCard = memo(function SessionCard({
  session,
  onClick
}: SessionCardProps) {
  const { t } = useTranslation('session-replay');

  // Memoize computed values to avoid recalculating on every render
  const isCompleted = useMemo(() => session.completed_at !== null, [session.completed_at]);

  const duration = useMemo(() => {
    if (!session.duration_seconds) return null;
    const minutes = Math.floor(session.duration_seconds / 60);
    return `${minutes}m`;
  }, [session.duration_seconds]);

  const relativeTime = useMemo(
    () => formatRelativeTime(session.started_at),
    [session.started_at]
  );

  const hasSubtasks = useMemo(() => session.subtasks.length > 0, [session.subtasks.length]);

  return (
    <Card
      className={cn(
        "hover:border-primary/50 hover:bg-accent/5 transition-all cursor-pointer",
        onClick && "hover:shadow-md"
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          {/* Session Info */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Badge
                variant={isCompleted ? "success" : "warning"}
                className="gap-1"
              >
                {isCompleted ? (
                  <CheckCircle2 className="h-3 w-3" />
                ) : (
                  <Loader2 className="h-3 w-3 animate-spin" />
                )}
                <span className="text-xs">
                  {isCompleted
                    ? t('sessionList.statusCompleted')
                    : t('sessionList.statusInProgress')}
                </span>
              </Badge>
              <span className="text-xs text-muted-foreground">
                {t('sessionList.title')} #{session.session_number}
              </span>
            </div>

            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{relativeTime}</span>
              </div>
              {duration && (
                <>
                  <span className="w-px h-3 bg-border" />
                  <div className="flex items-center gap-1">
                    <span>{duration}</span>
                  </div>
                </>
              )}
              {hasSubtasks && (
                <>
                  <span className="w-px h-3 bg-border" />
                  <div className="flex items-center gap-1">
                    <span>
                      {session.subtasks.length} {t('sessionList.subtasks')}
                    </span>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* View Button */}
          {onClick && (
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onClick();
              }}
            >
              {t('sessionList.viewSession')}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}, sessionCardPropsAreEqual);
