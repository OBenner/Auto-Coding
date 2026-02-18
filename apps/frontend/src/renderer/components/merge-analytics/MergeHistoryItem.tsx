import { CheckCircle2, XCircle, Clock, Files, GitMerge } from 'lucide-react';
import { cn } from '../../lib/utils';
import { Badge } from '../ui/badge';
import type { MergeOperationRecord } from '../../../shared/types/merge-analytics';

interface MergeHistoryItemProps {
  operation: MergeOperationRecord;
  isSelected: boolean;
  onClick: () => void;
}

export function MergeHistoryItem({ operation, isSelected, onClick }: MergeHistoryItemProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const formatDuration = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds.toFixed(1)}s`;
    }
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}m ${remainingSeconds}s`;
  };

  const StatusIcon = operation.success ? CheckCircle2 : XCircle;
  const statusColor = operation.success ? 'text-success' : 'text-destructive';

  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'w-full text-left p-3 rounded-lg border transition-colors',
        isSelected
          ? 'border-primary bg-primary/5'
          : 'border-transparent hover:bg-muted/50'
      )}
    >
      <div className="flex items-start gap-3">
        <StatusIcon className={cn('h-5 w-5 mt-0.5 shrink-0', statusColor)} />
        <div className="flex-1 min-w-0">
          {/* Operation ID and Status */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground font-mono">
              {operation.operation_id.slice(0, 8)}
            </span>
            <Badge variant={operation.success ? 'default' : 'destructive'} className="text-xs">
              {operation.success ? 'Success' : 'Failed'}
            </Badge>
          </div>

          {/* Tasks Merged */}
          <div className="flex items-center gap-2 mt-1">
            <GitMerge className="h-3 w-3 text-muted-foreground" />
            <span className="text-sm text-foreground">
              {operation.tasks_merged.length > 0
                ? operation.tasks_merged.join(', ')
                : 'No tasks specified'}
            </span>
          </div>

          {/* Stats */}
          <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Files className="h-3 w-3" />
              <span>{operation.stats.files_processed} files</span>
            </div>
            {operation.stats.conflicts_detected > 0 && (
              <div className="flex items-center gap-1">
                <span className="text-warning">⚠</span>
                <span>{operation.stats.conflicts_detected} conflicts</span>
              </div>
            )}
            {operation.stats.ai_calls_made > 0 && (
              <div className="flex items-center gap-1">
                <span>🤖</span>
                <span>{operation.stats.ai_calls_made} AI calls</span>
              </div>
            )}
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              <span>{formatDuration(operation.duration_seconds)}</span>
            </div>
          </div>

          {/* Timestamp */}
          <div className="mt-2 text-xs text-muted-foreground">
            {formatDate(operation.timestamp)}
          </div>

          {/* Error message if failed */}
          {!operation.success && operation.error && (
            <div className="mt-2 text-xs text-destructive bg-destructive/10 p-2 rounded">
              {operation.error}
            </div>
          )}
        </div>
      </div>
    </button>
  );
}
