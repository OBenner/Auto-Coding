import { useState, useMemo, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
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

const SENSITIVE_PATTERNS = [
  'authorization',
  'x-api-key',
  'x-auth-token',
  'cookie',
  'token',
  'secret',
  'password',
  'api_key',
  'apikey',
  'access_token',
  'ssn',
  'credential',
];

function redactSensitiveHeaders(headers: Record<string, string>): Record<string, string> {
  const redacted: Record<string, string> = {};
  for (const [key, value] of Object.entries(headers)) {
    const keyLower = key.toLowerCase();
    const isSensitive = SENSITIVE_PATTERNS.some(
      (pattern) => keyLower === pattern || keyLower.includes(pattern),
    );
    redacted[key] = isSensitive ? '***REDACTED***' : value;
  }
  return redacted;
}

function redactSensitiveFields(data: unknown): unknown {
  if (data === null || data === undefined) return data;
  if (typeof data === 'string') return data;
  if (typeof data === 'number' || typeof data === 'boolean') return data;

  if (Array.isArray(data)) {
    return data.map(redactSensitiveFields);
  }

  if (typeof data === 'object') {
    const result: Record<string, unknown> = {};
    for (const [key, value] of Object.entries(data as Record<string, unknown>)) {
      const keyLower = key.toLowerCase();
      const isSensitive = SENSITIVE_PATTERNS.some(
        (pattern) => keyLower === pattern || keyLower.includes(pattern),
      );
      result[key] = isSensitive ? '***REDACTED***' : redactSensitiveFields(value);
    }
    return result;
  }

  return data;
}

export function WebhookLogsViewer({ logs, loading = false }: WebhookLogsViewerProps) {
  const { t } = useTranslation(['settings']);
  const [statusFilter, setStatusFilter] = useState<WebhookDeliveryStatus | 'all'>('all');
  const [eventTypeFilter, setEventTypeFilter] = useState<WebhookEventType | 'all'>('all');
  const [expandedLogId, setExpandedLogId] = useState<string | null>(null);

  const availableEventTypes = useMemo(() => {
    const types = new Set<WebhookEventType>();
    logs.forEach((log) => types.add(log.event_type));
    return Array.from(types).sort((a, b) => a.localeCompare(b));
  }, [logs]);

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

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return t('settings:webhooks.logs.timeAgo.justNow');
    if (diffMins < 60)
      return t('settings:webhooks.logs.timeAgo.minutesAgo', { count: diffMins });
    if (diffHours < 24)
      return t('settings:webhooks.logs.timeAgo.hoursAgo', { count: diffHours });
    if (diffDays < 7)
      return t('settings:webhooks.logs.timeAgo.daysAgo', { count: diffDays });

    return date.toLocaleDateString();
  };

  const formatDuration = (durationMs: number | null) => {
    if (durationMs === null) return t('settings:webhooks.logs.duration.unavailable');
    if (durationMs < 1000) return `${durationMs}ms`;
    return `${(durationMs / 1000).toFixed(2)}s`;
  };

  const getStatusBadge = (status: WebhookDeliveryStatus) => {
    const labels = t('settings:webhooks.logs.statusBadge', {
      returnObjects: true,
    }) as Record<string, string>;

    switch (status) {
      case 'success':
        return { status: 'success' as const, label: labels.success, icon: CheckCircle2 };
      case 'failed':
        return { status: 'warning' as const, label: labels.failed, icon: XCircle };
      case 'retrying':
        return { status: 'info' as const, label: labels.retrying, icon: Loader2 };
      case 'pending':
        return { status: 'info' as const, label: labels.pending, icon: Clock };
      default:
        return { status: 'info' as const, label: status, icon: Clock };
    }
  };

  const getEventTypeName = useCallback(
    (eventType: WebhookEventType): string => {
      const key = `settings:webhooks.events.${eventType}`;
      const translated = t(key, { defaultValue: '' });
      if (translated && translated !== key) return translated;
      // Fallback: snake_case to Title Case
      return eventType
        .split('_')
        .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');
    },
    [t],
  );

  const toggleLogExpansion = (logId: string) => {
    setExpandedLogId((prev) => (prev === logId ? null : logId));
  };

  const handleRowKeyDown = (e: React.KeyboardEvent, logId: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleLogExpansion(logId);
    }
  };

  return (
    <div className="space-y-4">
      {/* Header with filters */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <FileText className="h-4 w-4 text-muted-foreground" />
          <h3 className="text-sm font-medium text-foreground">
            {t('settings:webhooks.logs.title')}
          </h3>
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
          <Select
            value={statusFilter}
            onValueChange={(value) => setStatusFilter(value as typeof statusFilter)}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder={t('settings:webhooks.logs.filterByStatus')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('settings:webhooks.logs.allStatuses')}</SelectItem>
              <SelectItem value="success">
                {t('settings:webhooks.logs.statusBadge.success')}
              </SelectItem>
              <SelectItem value="failed">
                {t('settings:webhooks.logs.statusBadge.failed')}
              </SelectItem>
              <SelectItem value="retrying">
                {t('settings:webhooks.logs.statusBadge.retrying')}
              </SelectItem>
              <SelectItem value="pending">
                {t('settings:webhooks.logs.statusBadge.pending')}
              </SelectItem>
            </SelectContent>
          </Select>

          <Select
            value={eventTypeFilter}
            onValueChange={(value) => setEventTypeFilter(value as typeof eventTypeFilter)}
          >
            <SelectTrigger className="h-8 text-xs">
              <SelectValue placeholder={t('settings:webhooks.logs.filterByEvent')} />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">{t('settings:webhooks.logs.allEvents')}</SelectItem>
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
          <span className="ml-2 text-sm text-muted-foreground">
            {t('settings:webhooks.logs.loading')}
          </span>
        </div>
      )}

      {/* Empty state */}
      {!loading && logs.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <FileText className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-50" />
          <p className="text-sm text-muted-foreground">{t('settings:webhooks.logs.empty')}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {t('settings:webhooks.logs.emptyDescription')}
          </p>
        </div>
      )}

      {/* No filtered results */}
      {!loading && logs.length > 0 && filteredLogs.length === 0 && (
        <div className="rounded-lg border border-dashed border-border p-8 text-center">
          <Filter className="h-8 w-8 text-muted-foreground mx-auto mb-3 opacity-50" />
          <p className="text-sm text-muted-foreground">
            {t('settings:webhooks.logs.noMatch')}
          </p>
          <Button
            variant="outline"
            size="sm"
            className="mt-3"
            onClick={() => {
              setStatusFilter('all');
              setEventTypeFilter('all');
            }}
          >
            {t('settings:webhooks.logs.clearFilters')}
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
            const detailsPanelId = `log-details-${log.id}`;

            return (
              <div key={log.id} className="rounded-lg border border-border overflow-hidden">
                {/* Log summary - accessible interactive row */}
                <div
                  className="p-3 cursor-pointer hover:bg-muted/30 transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  onClick={() => toggleLogExpansion(log.id)}
                  onKeyDown={(e) => handleRowKeyDown(e, log.id)}
                  role="button"
                  tabIndex={0}
                  aria-expanded={isExpanded}
                  aria-controls={detailsPanelId}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3 flex-1 min-w-0">
                      <div
                        className={`flex-shrink-0 ${log.status === 'retrying' ? 'animate-spin' : ''}`}
                      >
                        <StatusIcon className="h-4 w-4 text-muted-foreground" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2">
                          <span className="text-sm font-medium text-foreground truncate">
                            {getEventTypeName(log.event_type)}
                          </span>
                          <StatusBadge status={statusInfo.status} label={statusInfo.label} />
                          {log.attempt_number > 1 && (
                            <Badge variant="outline" className="text-xs">
                              {t('settings:webhooks.logs.attempt', {
                                current: log.attempt_number,
                                max: log.max_retries,
                              })}
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
                            <span className="truncate">
                              {log.request_method} {log.request_url}
                            </span>
                          )}
                        </div>
                      </div>

                      <div className="h-6 w-6 flex items-center justify-center flex-shrink-0">
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4" />
                        )}
                      </div>
                    </div>
                  </div>

                  {log.status === 'failed' && log.error_message && (
                    <div className="mt-2 flex items-start gap-2 text-xs text-warning bg-warning/5 p-2 rounded">
                      <AlertCircle className="h-3 w-3 flex-shrink-0 mt-0.5" />
                      <span className="flex-1">{log.error_message}</span>
                    </div>
                  )}
                </div>

                {/* Expanded details */}
                {isExpanded && (
                  <div id={detailsPanelId} role="region">
                    <Separator />
                    <div className="p-3 space-y-3 bg-muted/20">
                      {/* Request details */}
                      {log.request_url && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-foreground">
                            {t('settings:webhooks.logs.request')}
                          </p>
                          <div className="text-xs space-y-1">
                            <div className="flex items-center gap-2">
                              <span className="text-muted-foreground">
                                {t('settings:webhooks.logs.url')}
                              </span>
                              <span className="font-mono text-info">
                                {log.request_method} {log.request_url}
                              </span>
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
                                <span className="text-muted-foreground">
                                  {t('settings:webhooks.logs.headers')}
                                </span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto">
                                  {JSON.stringify(
                                    redactSensitiveHeaders(log.request_headers),
                                    null,
                                    2,
                                  )}
                                </pre>
                              </div>
                            )}
                            {log.request_body && (
                              <div>
                                <span className="text-muted-foreground">
                                  {t('settings:webhooks.logs.body')}
                                </span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                                  {JSON.stringify(
                                    redactSensitiveFields(log.request_body),
                                    null,
                                    2,
                                  )}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Response details */}
                      {log.response_status_code && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-foreground">
                            {t('settings:webhooks.logs.response')}
                          </p>
                          <div className="text-xs space-y-1">
                            <div>
                              <span className="text-muted-foreground">
                                {t('settings:webhooks.logs.statusLabel')}
                              </span>
                              <span
                                className={`ml-2 font-mono ${
                                  log.response_status_code >= 200 &&
                                  log.response_status_code < 300
                                    ? 'text-success'
                                    : log.response_status_code >= 400
                                      ? 'text-warning'
                                      : 'text-info'
                                }`}
                              >
                                {log.response_status_code}
                              </span>
                            </div>
                            {Object.keys(log.response_headers).length > 0 && (
                              <div>
                                <span className="text-muted-foreground">
                                  {t('settings:webhooks.logs.headers')}
                                </span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto">
                                  {JSON.stringify(
                                    redactSensitiveHeaders(log.response_headers),
                                    null,
                                    2,
                                  )}
                                </pre>
                              </div>
                            )}
                            {log.response_body && (
                              <div>
                                <span className="text-muted-foreground">
                                  {t('settings:webhooks.logs.body')}
                                </span>
                                <pre className="mt-1 text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                                  {typeof log.response_body === 'string'
                                    ? log.response_body
                                    : JSON.stringify(
                                        redactSensitiveFields(log.response_body),
                                        null,
                                        2,
                                      )}
                                </pre>
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {/* Event data */}
                      {Object.keys(log.event_data).length > 0 && (
                        <div className="space-y-1">
                          <p className="text-xs font-medium text-foreground">
                            {t('settings:webhooks.logs.eventData')}
                          </p>
                          <pre className="text-xs bg-muted p-2 rounded overflow-x-auto max-h-40 overflow-y-auto">
                            {JSON.stringify(
                              redactSensitiveFields(log.event_data),
                              null,
                              2,
                            )}
                          </pre>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border">
                        <span>
                          {t('settings:webhooks.logs.id')} {log.id}
                        </span>
                        <span>
                          {t('settings:webhooks.logs.webhookId')} {log.webhook_id}
                        </span>
                        {log.completed_at && (
                          <span>
                            {t('settings:webhooks.logs.completed')}{' '}
                            {formatTimestamp(log.completed_at)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
