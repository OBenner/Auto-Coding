/**
 * AuditLogViewer - Security audit log viewer component
 *
 * Displays security-relevant operations that have been logged, including
 * command executions, filesystem access, API calls, and permission changes.
 * Provides filtering, search, and detailed view of audit events.
 *
 * Features:
 * - View all audit log entries with timestamps
 * - Filter by category, severity, and status (allowed/blocked)
 * - Search logs by message, command, or file path
 * - View detailed event information
 * - Export logs for compliance
 */
import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  AlertTriangle,
  AlertCircle,
  Info,
  CheckCircle2,
  XCircle,
  Search,
  Filter,
  FileText,
  Terminal,
  HardDrive,
  Globe,
  Settings as SettingsIcon,
  Download,
  RefreshCw,
  ChevronRight,
  Clock,
  Bot,
  FolderOpen,
  X
} from 'lucide-react';
import { cn } from '../../../lib/utils';
import { Button } from '../../ui/button';
import { Input } from '../../ui/input';
import { Badge } from '../../ui/badge';
import { ScrollArea } from '../../ui/scroll-area';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '../../ui/tooltip';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '../../ui/dialog';
import type {
  SecurityAuditLog,
  SecurityEventCategory,
  SecurityEventSeverity
} from '../../../../shared/types';

interface AuditLogViewerProps {
  /** Audit log entries to display */
  logs: SecurityAuditLog[];
  /** Whether logs are being loaded */
  isLoading?: boolean;
  /** Whether to show export button */
  showExport?: boolean;
  /** Callback to refresh logs */
  onRefresh?: () => void;
  /** Callback to export logs */
  onExport?: () => void;
  /** Maximum number of logs to display (null for unlimited) */
  maxLogs?: number | null;
}

/**
 * Filter options for audit logs
 */
type FilterCategory = 'all' | SecurityEventCategory;
type FilterSeverity = 'all' | SecurityEventSeverity;
type FilterStatus = 'all' | 'allowed' | 'blocked';

/**
 * Get icon and color for event category
 */
function getCategoryIcon(category: SecurityEventCategory) {
  switch (category) {
    case 'command_execution':
      return { Icon: Terminal, color: 'text-blue-500', label: 'Command' };
    case 'filesystem_access':
      return { Icon: HardDrive, color: 'text-green-500', label: 'Filesystem' };
    case 'api_call':
      return { Icon: Globe, color: 'text-purple-500', label: 'API Call' };
    case 'permission_change':
      return { Icon: SettingsIcon, color: 'text-orange-500', label: 'Permission' };
    case 'sandbox_violation':
      return { Icon: ShieldAlert, color: 'text-red-500', label: 'Sandbox' };
    case 'profile_loaded':
      return { Icon: ShieldCheck, color: 'text-emerald-500', label: 'Profile' };
    case 'profile_exported':
      return { Icon: FileText, color: 'text-cyan-500', label: 'Export' };
    case 'risk_detected':
      return { Icon: AlertTriangle, color: 'text-red-600', label: 'Risk' };
    default:
      return { Icon: Info, color: 'text-gray-500', label: 'Unknown' };
  }
}

/**
 * Get icon and color for event severity
 */
function getSeverityIcon(severity: SecurityEventSeverity) {
  switch (severity) {
    case 'critical':
      return { Icon: AlertCircle, color: 'text-red-600', bgColor: 'bg-red-50' };
    case 'warning':
      return { Icon: AlertTriangle, color: 'text-orange-600', bgColor: 'bg-orange-50' };
    case 'info':
      return { Icon: Info, color: 'text-blue-600', bgColor: 'bg-blue-50' };
    default:
      return { Icon: Info, color: 'text-gray-600', bgColor: 'bg-gray-50' };
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: number): string {
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
}

/**
 * Format full timestamp for detailed view
 */
function formatFullTimestamp(timestamp: number): string {
  const date = new Date(timestamp);
  return date.toLocaleString();
}

/**
 * AuditLogViewer Component
 */
export function AuditLogViewer({
  logs,
  isLoading = false,
  showExport = true,
  onRefresh,
  onExport,
  maxLogs = null
}: AuditLogViewerProps) {
  const { t } = useTranslation(['security', 'common']);
  const { t: tCommon } = useTranslation('common');

  // Filter and search state
  const [categoryFilter, setCategoryFilter] = useState<FilterCategory>('all');
  const [severityFilter, setSeverityFilter] = useState<FilterSeverity>('all');
  const [statusFilter, setStatusFilter] = useState<FilterStatus>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Detail view state
  const [selectedLog, setSelectedLog] = useState<SecurityAuditLog | null>(null);

  /**
   * Filter and search audit logs
   */
  const filteredLogs = useMemo(() => {
    let result = logs;

    // Apply category filter
    if (categoryFilter !== 'all') {
      result = result.filter(log => log.category === categoryFilter);
    }

    // Apply severity filter
    if (severityFilter !== 'all') {
      result = result.filter(log => log.severity === severityFilter);
    }

    // Apply status filter
    if (statusFilter !== 'all') {
      if (statusFilter === 'allowed') {
        result = result.filter(log => log.allowed);
      } else {
        result = result.filter(log => !log.allowed);
      }
    }

    // Apply search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter(log => {
        return (
          log.message.toLowerCase().includes(query) ||
          log.command?.toLowerCase().includes(query) ||
          log.filePath?.toLowerCase().includes(query) ||
          log.apiEndpoint?.toLowerCase().includes(query) ||
          log.agentType?.toLowerCase().includes(query)
        );
      });
    }

    // Limit logs if maxLogs is set
    if (maxLogs !== null && maxLogs > 0) {
      result = result.slice(0, maxLogs);
    }

    return result;
  }, [logs, categoryFilter, severityFilter, statusFilter, searchQuery, maxLogs]);

  /**
   * Calculate statistics
   */
  const stats = useMemo(() => {
    const total = logs.length;
    const critical = logs.filter(l => l.severity === 'critical').length;
    const blocked = logs.filter(l => !l.allowed).length;
    const byCategory: Record<string, number> = {};

    logs.forEach(log => {
      byCategory[log.category] = (byCategory[log.category] || 0) + 1;
    });

    return { total, critical, blocked, byCategory };
  }, [logs]);

  /**
   * Clear all filters
   */
  const clearFilters = useCallback(() => {
    setCategoryFilter('all');
    setSeverityFilter('all');
    setStatusFilter('all');
    setSearchQuery('');
  }, []);

  const hasActiveFilters =
    categoryFilter !== 'all' ||
    severityFilter !== 'all' ||
    statusFilter !== 'all' ||
    searchQuery.length > 0;

  return (
    <div className="flex flex-col gap-4">
      {/* Header with stats and actions */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <Shield className="h-5 w-5 text-primary" />
            <h3 className="text-lg font-semibold">{t('security:audit.title')}</h3>
          </div>
          <Badge variant="secondary" className="text-xs">
            {filteredLogs.length} / {stats.total} {tCommon('events')}
          </Badge>
        </div>

        <div className="flex items-center gap-2">
          {/* Refresh button */}
          {onRefresh && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={onRefresh}
                  disabled={isLoading}
                >
                  <RefreshCw className={cn('h-4 w-4', isLoading && 'animate-spin')} />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{tCommon('refresh')}</p>
              </TooltipContent>
            </Tooltip>
          )}

          {/* Export button */}
          {showExport && onExport && (
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={onExport}>
                  <Download className="h-4 w-4" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>{tCommon('export')}</p>
              </TooltipContent>
            </Tooltip>
          )}
        </div>
      </div>

      {/* Stats summary */}
      <div className="flex items-center gap-4 text-sm text-muted-foreground">
        {stats.critical > 0 && (
          <div className="flex items-center gap-1">
            <AlertCircle className="h-3.5 w-3.5 text-red-600" />
            <span>{stats.critical} critical</span>
          </div>
        )}
        {stats.blocked > 0 && (
          <div className="flex items-center gap-1">
            <XCircle className="h-3.5 w-3.5 text-orange-600" />
            <span>{stats.blocked} blocked</span>
          </div>
        )}
      </div>

      {/* Filters and search */}
      <div className="flex flex-col gap-3">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('security:audit.searchPlaceholder') || 'Search by message, command, file path...'}
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-8"
          />
        </div>

        {/* Filter buttons */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Category filter */}
          <div className="flex items-center gap-1">
            <Filter className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">{tCommon('filter')}:</span>
          </div>

          {/* Category badges */}
          <Button
            variant={categoryFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs"
            onClick={() => setCategoryFilter('all')}
          >
            {tCommon('all')}
          </Button>
          {(['command_execution', 'filesystem_access', 'api_call', 'permission_change', 'risk_detected'] as SecurityEventCategory[]).map(cat => {
            const { Icon, label } = getCategoryIcon(cat);
            return (
              <Button
                key={cat}
                variant={categoryFilter === cat ? 'default' : 'outline'}
                size="sm"
                className="h-7 text-xs"
                onClick={() => setCategoryFilter(cat)}
              >
                <Icon className="h-3 w-3 mr-1" />
                {label}
              </Button>
            );
          })}

          {/* Severity filter */}
          <div className="h-4 w-px bg-border mx-1" />

          <Button
            variant={severityFilter === 'all' ? 'outline' : 'secondary'}
            size="sm"
            className="h-7 text-xs"
            onClick={() => setSeverityFilter(severityFilter === 'critical' ? 'all' : 'critical')}
          >
            <AlertCircle className={cn('h-3 w-3 mr-1', severityFilter === 'critical' && 'text-red-600')} />
            Critical
          </Button>

          {/* Status filter */}
          <Button
            variant={statusFilter === 'blocked' ? 'destructive' : statusFilter === 'allowed' ? 'default' : 'outline'}
            size="sm"
            className="h-7 text-xs"
            onClick={() => setStatusFilter(statusFilter === 'all' ? 'blocked' : statusFilter === 'blocked' ? 'allowed' : 'all')}
          >
            {statusFilter === 'blocked' && <XCircle className="h-3 w-3 mr-1" />}
            {statusFilter === 'allowed' && <CheckCircle2 className="h-3 w-3 mr-1" />}
            {statusFilter === 'all' && tCommon('status')}
            {statusFilter === 'blocked' && tCommon('blocked')}
            {statusFilter === 'allowed' && tCommon('allowed')}
          </Button>

          {/* Clear filters */}
          {hasActiveFilters && (
            <Button
              variant="ghost"
              size="sm"
              className="h-7 text-xs"
              onClick={clearFilters}
            >
              <X className="h-3 w-3 mr-1" />
              {tCommon('clear')}
            </Button>
          )}
        </div>
      </div>

      {/* Logs list */}
      {filteredLogs.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-12 text-center">
          <Shield className="h-12 w-12 text-muted-foreground/50 mb-3" />
          <p className="text-sm text-muted-foreground">
            {hasActiveFilters
              ? (t('security:audit.noMatchingEvents') || 'No matching security events')
              : (t('security:audit.noEvents') || 'No security events logged yet')
            }
          </p>
          {hasActiveFilters && (
            <Button variant="link" size="sm" onClick={clearFilters}>
              {tCommon('clearFilters')}
            </Button>
          )}
        </div>
      ) : (
        <ScrollArea className="h-[400px] w-full border rounded-md">
          <div className="p-2">
            {filteredLogs.map((log) => {
              const { Icon: CategoryIcon, color: categoryColor } = getCategoryIcon(log.category);
              const { Icon: SeverityIcon, color: severityColor, bgColor } = getSeverityIcon(log.severity);

              return (
                <button
                  type="button"
                  key={log.id}
                  className={cn(
                    'w-full text-left group flex items-start gap-3 p-3 rounded-md border border-transparent',
                    'hover:bg-muted/50 hover:border-border transition-colors cursor-pointer',
                    !log.allowed && 'bg-orange-50/30 hover:bg-orange-50/50'
                  )}
                  onClick={() => setSelectedLog(log)}
                >
                  {/* Status indicator */}
                  <div className="flex-shrink-0 mt-0.5">
                    {log.allowed ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600" />
                    ) : (
                      <XCircle className="h-4 w-4 text-orange-600" />
                    )}
                  </div>

                  {/* Category icon */}
                  <div className={cn('flex-shrink-0 mt-0.5', categoryColor)}>
                    <CategoryIcon className="h-4 w-4" />
                  </div>

                  {/* Content */}
                  <div className="flex-1 min-w-0 space-y-1">
                    {/* Message and timestamp */}
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-sm font-medium line-clamp-2">{log.message}</p>
                      <span className="flex-shrink-0 text-xs text-muted-foreground flex items-center gap-1">
                        <Clock className="h-3 w-3" />
                        {formatTimestamp(log.timestamp)}
                      </span>
                    </div>

                    {/* Metadata */}
                    <div className="flex items-center gap-2 text-xs text-muted-foreground flex-wrap">
                      {/* Severity badge */}
                      <Badge variant="secondary" className={cn('text-xs', bgColor)}>
                        <SeverityIcon className={cn('h-2.5 w-2.5 mr-1', severityColor)} />
                        {log.severity}
                      </Badge>

                      {/* Command */}
                      {log.command && (
                        <span className="flex items-center gap-0.5">
                          <Terminal className="h-2.5 w-2.5" />
                          <code className="text-xs">{log.command}</code>
                        </span>
                      )}

                      {/* File path */}
                      {log.filePath && (
                        <span className="flex items-center gap-0.5 max-w-[200px] truncate">
                          <FolderOpen className="h-2.5 w-2.5 flex-shrink-0" />
                          <span className="truncate">{log.filePath}</span>
                        </span>
                      )}

                      {/* API endpoint */}
                      {log.apiEndpoint && (
                        <span className="flex items-center gap-0.5 max-w-[200px] truncate">
                          <Globe className="h-2.5 w-2.5 flex-shrink-0" />
                          <span className="truncate">{log.apiEndpoint}</span>
                        </span>
                      )}

                      {/* Agent type */}
                      {log.agentType && (
                        <span className="flex items-center gap-0.5">
                          <Bot className="h-2.5 w-2.5" />
                          {log.agentType}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Expand indicator */}
                  <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
              );
            })}
          </div>
        </ScrollArea>
      )}

      {/* Detail dialog */}
      <Dialog open={!!selectedLog} onOpenChange={() => setSelectedLog(null)}>
        <DialogContent className="max-w-2xl">
          {selectedLog && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-2">
                  {(() => {
                    const { Icon } = getCategoryIcon(selectedLog.category);
                    return <Icon className="h-5 w-5" />;
                  })()}
                  <DialogTitle>{t('security:audit.eventDetails') || 'Event Details'}</DialogTitle>
                </div>
                <DialogDescription>
                  {selectedLog.message}
                </DialogDescription>
              </DialogHeader>

              <div className="space-y-4">
                {/* Status and severity */}
                <div className="flex items-center gap-3">
                  {selectedLog.allowed ? (
                    <Badge variant="default" className="bg-green-600">
                      <CheckCircle2 className="h-3 w-3 mr-1" />
                      {tCommon('allowed')}
                    </Badge>
                  ) : (
                    <Badge variant="destructive">
                      <XCircle className="h-3 w-3 mr-1" />
                      {tCommon('blocked')}
                    </Badge>
                  )}

                  <Badge variant="secondary">
                    {selectedLog.category}
                  </Badge>

                  {(() => {
                    const { Icon, color, bgColor } = getSeverityIcon(selectedLog.severity);
                    return (
                      <Badge variant="secondary" className={cn(bgColor)}>
                        <Icon className={cn('h-3 w-3 mr-1', color)} />
                        {selectedLog.severity}
                      </Badge>
                    );
                  })()}
                </div>

                {/* Timestamp */}
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{formatFullTimestamp(selectedLog.timestamp)}</span>
                </div>

                {/* Details grid */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  {selectedLog.command && (
                    <div className="space-y-1">
                      <span className="text-xs text-muted-foreground">{tCommon('command')}</span>
                      <div className="flex items-center gap-1.5">
                        <Terminal className="h-3.5 w-3.5 text-muted-foreground" />
                        <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                          {selectedLog.command}
                        </code>
                      </div>
                    </div>
                  )}

                  {selectedLog.filePath && (
                    <div className="space-y-1">
                      <span className="text-xs text-muted-foreground">{tCommon('path')}</span>
                      <div className="flex items-center gap-1.5">
                        <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs bg-muted px-1.5 py-0.5 rounded truncate">
                          {selectedLog.filePath}
                        </span>
                      </div>
                    </div>
                  )}

                  {selectedLog.apiEndpoint && (
                    <div className="space-y-1">
                      <span className="text-xs text-muted-foreground">API Endpoint</span>
                      <div className="flex items-center gap-1.5">
                        <Globe className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs bg-muted px-1.5 py-0.5 rounded truncate">
                          {selectedLog.apiEndpoint}
                        </span>
                      </div>
                    </div>
                  )}

                  {selectedLog.agentType && (
                    <div className="space-y-1">
                      <span className="text-xs text-muted-foreground">{tCommon('agent')}</span>
                      <div className="flex items-center gap-1.5">
                        <Bot className="h-3.5 w-3.5 text-muted-foreground" />
                        <span className="text-xs bg-muted px-1.5 py-0.5 rounded">
                          {selectedLog.agentType}
                        </span>
                      </div>
                    </div>
                  )}

                  {selectedLog.projectId && (
                    <div className="space-y-1">
                      <span className="text-xs text-muted-foreground">{tCommon('project')}</span>
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
                        {selectedLog.projectId}
                      </span>
                    </div>
                  )}

                  {selectedLog.sessionId && (
                    <div className="space-y-1">
                      <span className="text-xs text-muted-foreground">{tCommon('session')}</span>
                      <span className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono">
                        {selectedLog.sessionId}
                      </span>
                    </div>
                  )}
                </div>

                {/* Additional context */}
                {selectedLog.context && (
                  <div className="space-y-1">
                    <span className="text-xs text-muted-foreground">{tCommon('context')}</span>
                    <pre className="text-xs bg-muted p-2 rounded overflow-x-auto">
                      {selectedLog.context}
                    </pre>
                  </div>
                )}

                {/* Rule ID */}
                {selectedLog.ruleId && (
                  <div className="text-xs text-muted-foreground">
                    Rule ID: <code className="font-mono">{selectedLog.ruleId}</code>
                  </div>
                )}
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
