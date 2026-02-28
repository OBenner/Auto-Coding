import { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, Clock, AlertCircle, CheckCircle2, XCircle, Loader2, Filter, FileText, ExternalLink } from 'lucide-react';
import { StatusBadge } from './StatusBadge';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../ui/select';
import type { WebhookLog, WebhookDeliveryStatus, WebhookEventType } from '../../../shared/types';

interface WebhookLogsViewerProps {
  logs: WebhookLog[];
  loading?: boolean;
}

/**
 * Component for viewing webhook delivery logs
 *
 * Displays a list of webhook delivery attempts with filtering and expandable details.
 * Each log entry shows the event type, status, timestamp, and duration.
 * Expanding a log entry reveals full request/response details including headers and bodies.
 *
 * Features:
 * - Filter by delivery status (success, failed, retrying, pending)
 * - Filter by event type (build_started, build_completed, etc.)
 * - Expandable log entries for detailed inspection
 * - Status badges with color coding
 * - Timestamp formatting with relative time
 * - Empty state handling
 * - External link to request URLs
 *
 * @example
 * ```tsx
 * <WebhookLogsViewer
 *   logs={webhookLogs}
 *   loading={isLoadingLogs}
 * />
 * ```
 */
export function WebhookLogsViewer({ logs, loading = false }: WebhookLogsViewerProps) {
  const [statusFilter, setStatusFilter] = useState<WebhookDeliveryStatus | 'all'>('all');
  const [eventTypeFilter, setEventTypeFilter] = useState<WebhookEventType | 'all'>('all');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  // Get unique event types from logs for filter dropdown
  const availableEventTypes = useMemo(() => {
    const types = new Set<WebhookEventType>();
    logs.forEach((log) => types.add(log.event_type));
    return Array.from(types).sort();
  }, [logs]);

  // Filter logs based on selected filters
  const filteredLogs = useMemo(() => {
    return logs.filter((log) => {
      if (statusFilter !== 'all' && log.status !== statusFilter) {
        return false;
      }
      if (eventTypeFilter !== 'all' && log.event_type !== eventTypeFilter) {
        return false;
      }
      return true;
    });
  }, [logs, statusFilter, eventTypeFilter]);

  // Format timestamp for display
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return date.toLocaleDateString();
  };

  // Format duration for display
  const formatDuration = (durationMs: number | null) => {
    if (durationMs === null) return 'N/A';
    if (durationMs < 1000) return `${durationMs}ms`;
    return `${(durationMs / 1000).toFixed(2)}s`;
  };

  // Get status badge props
  const getStatusBadge = (status: WebhookDeliveryStatus) => {
    switch (status) {
      case 'success':
        return { status: 'success' as const, label: 'Success', icon: CheckCircle2 };
      case 'failed':
        return { status: 'warning' as const, label: 'Failed', icon: XCircle };
      case 'retrying':
        return { status: 'info' as const, label: 'Retrying', icon: Loader2 };
      case 'pending':
        return { status: 'info' as const, label: 'Pending', icon: Clock };
      default:
        return { status: 'info' as const, label: status, icon: Clock };
    }
  };

  // Get event type display name
  const getEventTypeName = (eventType: WebhookEventType): string => {
    return eventType
      .split('_')
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  };

  const toggleLogExpansion = (logId: string) => {
    setExpandedLogId((prev) => (prev === logId ? null : logId));
  };

  return (
    <div className="space-y-4">
      {/* Header with filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-medium text-foreground">Webhook Delivery Logs</h3>
          {logs.length > 0 && (
            <Badge variant="secondary" className="text-xs">
              {filteredLogs.length} / {logs.length}
            </Badge>
          )}
        </div>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 flex-1">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <Select value={statusFilter} onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="success">Success</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="retrying">Retrying</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
            </SelectContent>
          </Select>

          <Select value={eventTypeFilter} onValueChange={(value) => setEventTypeFilter(value as typeof eventTypeFilter)}>
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder="Filter by event" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Events</SelectItem>
              {availableEventTypes.map((eventType) => (
                <SelectItem key={eventType} value={eventType}>
                  {getEventTypeName(eventType)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Loading state */}
      {loading && (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading logs...</span>
        </div>
      )}

      {/* Empty state */}
      {!loading && logs.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-50" />
          <p className="text-sm text-muted-foreground">No webhook logs yet</p>
          <p className="text-xs text-muted-foreground mt-1">
            Webhook delivery logs will appear here once webhooks are triggered
          </p>
        </div>
      )}

      {/* No filtered results */}
      {!loading && logs.length > 0 && filteredLogs.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <Filter className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-50" />
          <p className="text-sm text-muted-foreground">No logs match the selected filters</p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => {
              setStatusFilter('all');
              setEventTypeFilter('all');
            }}
          >
            Clear Filters
          </Button>
        </div>
      )}

      {/* Logs list */}
      {!loading && filteredLogs.length > 0 && (
        <div className="space-y-2">
          {filteredLogs.map((log) => {
            const statusInfo = getStatusBadge(log.status);
            const StatusIcon = statusInfo.icon;
            const isExpanded = expandedLogId === log.id;

            return (
              <div
                key={log.id}
                className="rounded-lg border border-border overflow-hidden"
              >
                {/* Log summary */}
                <div
                  className="p-3 cursor-pointer hover:bg-muted/30 transition-colors"
                  onClick={() => toggleLogExpansion(log.id)}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      {/* Status icon */}
                      <div className={`flex-shrink-0 ${log.status === 'retrying' ? 'animate-spin' : ''}`}>
                        <StatusIcon className="h-4 w-4 text-muted-foreground" />
                      </div>

                      {/* Event type and details */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground truncate">
                            {getEventTypeName(log.event_type)}
                          </span>
                          <StatusBadge status={statusInfo.status} label={statusInfo.label} />
                          {log.attempt_number > 1 && (
                            <Badge variant="outline" className="text-xs">
                              Attempt {log.attempt_number}/{log.max_retries}
                            </Badge>
                          )}
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-muted-foreground">
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {formatTimestamp(log.created_at)}
                          </span>
                          {log.duration_ms != null && (
                            <span>{formatDuration(log.duration_ms)}</span>
                          )}
                          {log.request_url && (
                            <span className="truncate">{log.request_method} {log.request_url}</span>
                          )}
                        </div>
                      </div>

                      {/* Expand/collapse icon */}
                      <Button variant="ghost" size="sm" className="h-6 w-6 p-0 flex-shrink-0">
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </Button>
                    </div>
                  </div>

                  {/* Error message (if any) */}
                  {log.status === 'failed' && log.error_message && (
                    <div className="mt-2 flex items-start gap-2 text-xs text-warning bg-warning/5 p-2 rounded">
                      <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                      <span className="flex-1">{log.error_message}</span>
                    </div>
                  )}
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <>
                    <Separator />
                    <div className="p-3 space-y-3 bg-muted/20">
                      {/* Request details */}
                      {log.request_url && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-foreground">Request</p>
                          <div className="text-xs space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">URL:</span>
                              <span className="font-mono text-info">{log.request_method} {log.request_url}</span>
                              {log.request_url.startsWith('http') && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="h-5 px-1.5 py-0 text-xs"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    if (window.electronAPI?.openExternal) {
                                      window.electronAPI.openExternal(log.request_url!);
                                    }
                                  }}
                                >
                                  <ExternalLink className="h-3 w-3" />
                                </Button>
                              )}
                            </div>
                            {Object.keys(log.request_headers).length > 0 && (
                              <div>
                                <span className="text-muted-foreground">Headers:</span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto">
                                  {JSON.stringify(log.request_headers, null, 2)}
                                </pre>
                              </div>
                            )}
                            {log.request_body && (
                              <div>
                                <span className="text-muted-foreground">Body:</span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                                  {JSON.stringify(log.request_body, null, 2)}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Response details */}
                      {log.response_status_code && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-foreground">Response</p>
                          <div className="text-xs space-y-1">
                            <div>
                              <span className="text-muted-foreground">Status:</span>
                              <span className={`ml-2 font-mono ${
                                log.response_status_code >= 200 && log.response_status_code < 300
                                  ? 'text-success'
                                  : log.response_status_code >= 400
                                  ? 'text-warning'
                                  : 'text-info'
                              }`}>
                                {log.response_status_code}
                              </span>
                            </div>
                            {Object.keys(log.response_headers).length > 0 && (
                              <div>
                                <span className="text-muted-foreground">Headers:</span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto">
                                  {JSON.stringify(log.response_headers, null, 2)}
                                </pre>
                              </div>
                            )}
                            {log.response_body && (
                              <div>
                                <span className="text-muted-foreground">Body:</span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                                  {log.response_body}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Event data */}
                      {Object.keys(log.event_data).length > 0 && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-foreground">Event Data</p>
                          <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {JSON.stringify(log.event_data, null, 2)}
                          </pre>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border">
                        <span>ID: {log.id}</span>
                        <span>Webhook ID: {log.webhook_id}</span>
                        {log.completed_at && (
                          <span>Completed: {formatTimestamp(log.completed_at)}</span>
                        )}
                      </div>
                    </div>
                  </>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
