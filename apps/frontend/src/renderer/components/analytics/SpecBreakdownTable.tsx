import { useState } from 'react';
import { Loader2, Search, FileText, CheckCircle2, Clock, XCircle, AlertCircle } from 'lucide-react';
import { Input } from '../ui/input';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { SpecMetrics } from '../../../shared/types/productivity-analytics';

interface SpecBreakdownTableProps {
  specs: SpecMetrics[];
  isLoading?: boolean;
}

type StatusFilter = 'all' | 'completed' | 'in_progress' | 'failed';
type ComplexityFilter = 'all' | 'simple' | 'standard' | 'complex';
type TypeFilter = 'all' | 'feature' | 'bug' | 'refactor' | 'other';

export function SpecBreakdownTable({ specs, isLoading = false }: SpecBreakdownTableProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');
  const [complexityFilter, setComplexityFilter] = useState<ComplexityFilter>('all');
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');

  // Filter specs based on all criteria
  const filteredSpecs = specs.filter((spec) => {
    const q = searchQuery.toLowerCase();

    // Apply search filter
    const matchesSearch =
      spec.spec_name.toLowerCase().includes(q) ||
      spec.spec_id.toLowerCase().includes(q) ||
      spec.workflow_type.toLowerCase().includes(q);

    // Apply status filter
    const matchesStatus =
      statusFilter === 'all' ||
      spec.status.toLowerCase() === statusFilter;

    // Apply complexity filter
    const matchesComplexity =
      complexityFilter === 'all' ||
      spec.complexity.toLowerCase() === complexityFilter;

    // Apply type filter
    const matchesType =
      typeFilter === 'all' ||
      spec.workflow_type.toLowerCase() === typeFilter;

    return matchesSearch && matchesStatus && matchesComplexity && matchesType;
  });

  // Format duration
  const formatDuration = (seconds: number): string => {
    if (seconds === 0) return '-';
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes}m`;
    const hours = Math.floor(minutes / 60);
    const remainingMinutes = minutes % 60;
    if (hours < 24) return `${hours}h ${remainingMinutes}m`;
    const days = Math.floor(hours / 24);
    const remainingHours = hours % 24;
    return `${days}d ${remainingHours}h`;
  };

  // Format date
  const formatDate = (dateString: string | null): string => {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // Get status icon and color
  const getStatusDisplay = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
        return {
          icon: CheckCircle2,
          color: 'text-success',
          variant: 'default' as const,
        };
      case 'in_progress':
        return {
          icon: Clock,
          color: 'text-warning',
          variant: 'secondary' as const,
        };
      case 'failed':
        return {
          icon: XCircle,
          color: 'text-destructive',
          variant: 'destructive' as const,
        };
      default:
        return {
          icon: AlertCircle,
          color: 'text-muted-foreground',
          variant: 'outline' as const,
        };
    }
  };

  // Get complexity color
  const getComplexityColor = (complexity: string): string => {
    switch (complexity.toLowerCase()) {
      case 'simple':
        return 'text-green-600';
      case 'standard':
        return 'text-blue-600';
      case 'complex':
        return 'text-orange-600';
      default:
        return 'text-muted-foreground';
    }
  };

  return (
    <div className="flex flex-col h-full rounded-lg border border-border bg-card">
      {/* Header */}
      <div className="p-4 border-b border-border space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-foreground flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Spec Breakdown ({filteredSpecs.length})
          </h3>
        </div>

        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-3 w-3 text-muted-foreground" />
          <Input
            placeholder="Search by spec name, ID, or type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="h-8 text-sm pl-9"
          />
        </div>

        {/* Filters */}
        <div className="flex flex-wrap gap-2">
          {/* Status Filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground mr-1">Status:</span>
            {(['all', 'completed', 'in_progress', 'failed'] as const).map((status) => (
              <Button
                key={status}
                variant={statusFilter === status ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setStatusFilter(status)}
                className="h-6 text-xs capitalize px-2"
              >
                {status === 'in_progress' ? 'In Progress' : status}
              </Button>
            ))}
          </div>

          {/* Complexity Filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground mr-1">Complexity:</span>
            {(['all', 'simple', 'standard', 'complex'] as const).map((complexity) => (
              <Button
                key={complexity}
                variant={complexityFilter === complexity ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setComplexityFilter(complexity)}
                className="h-6 text-xs capitalize px-2"
              >
                {complexity}
              </Button>
            ))}
          </div>

          {/* Type Filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground mr-1">Type:</span>
            {(['all', 'feature', 'bug', 'refactor'] as const).map((type) => (
              <Button
                key={type}
                variant={typeFilter === type ? 'default' : 'ghost'}
                size="sm"
                onClick={() => setTypeFilter(type)}
                className="h-6 text-xs capitalize px-2"
              >
                {type}
              </Button>
            ))}
          </div>
        </div>
      </div>

      {/* Table Content */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : filteredSpecs.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            {searchQuery || statusFilter !== 'all' || complexityFilter !== 'all' || typeFilter !== 'all'
              ? 'No matching specs found'
              : 'No specs available'}
          </div>
        ) : (
          <div className="p-2 space-y-1">
            {filteredSpecs.map((spec) => {
              const statusDisplay = getStatusDisplay(spec.status);
              const StatusIcon = statusDisplay.icon;

              return (
                <div
                  key={spec.spec_id}
                  className="p-3 rounded-lg border border-border hover:bg-muted/50 transition-colors"
                >
                  <div className="flex items-start gap-3">
                    <StatusIcon
                      className={cn('h-5 w-5 mt-0.5 shrink-0', statusDisplay.color)}
                    />
                    <div className="flex-1 min-w-0">
                      {/* Spec Name and Status */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-foreground truncate">
                          {spec.spec_name}
                        </span>
                        <Badge variant={statusDisplay.variant} className="text-xs">
                          {spec.status.replace('_', ' ')}
                        </Badge>
                      </div>

                      {/* Spec ID */}
                      <div className="text-xs text-muted-foreground font-mono mt-0.5">
                        {spec.spec_id}
                      </div>

                      {/* Type and Complexity */}
                      <div className="flex items-center gap-3 mt-2">
                        <div className="text-xs">
                          <span className="text-muted-foreground">Type: </span>
                          <span className="text-foreground capitalize font-medium">
                            {spec.workflow_type}
                          </span>
                        </div>
                        <div className="text-xs">
                          <span className="text-muted-foreground">Complexity: </span>
                          <span
                            className={cn(
                              'capitalize font-medium',
                              getComplexityColor(spec.complexity)
                            )}
                          >
                            {spec.complexity}
                          </span>
                        </div>
                      </div>

                      {/* Stats */}
                      <div className="flex flex-wrap items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <div className="flex items-center gap-1">
                          <span>Subtasks:</span>
                          <span className="text-foreground font-medium">
                            {spec.completed_subtasks}/{spec.total_subtasks}
                          </span>
                        </div>
                        {spec.qa_iterations > 0 && (
                          <div className="flex items-center gap-1">
                            <span>QA Iterations:</span>
                            <span className="text-foreground font-medium">
                              {spec.qa_iterations}
                            </span>
                          </div>
                        )}
                        {spec.duration_seconds > 0 && (
                          <div className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            <span>{formatDuration(spec.duration_seconds)}</span>
                          </div>
                        )}
                        {spec.unique_sessions > 0 && (
                          <div className="flex items-center gap-1">
                            <span>Sessions:</span>
                            <span className="text-foreground font-medium">
                              {spec.unique_sessions}
                            </span>
                          </div>
                        )}
                      </div>

                      {/* Timestamps */}
                      {spec.created_at && (
                        <div className="mt-2 text-xs text-muted-foreground">
                          <span>Created: {formatDate(spec.created_at)}</span>
                          {spec.completed_at && (
                            <span className="ml-3">
                              • Completed: {formatDate(spec.completed_at)}
                            </span>
                          )}
                        </div>
                      )}

                      {/* QA Status */}
                      {spec.qa_status && spec.qa_status !== 'pending' && (
                        <div className="mt-2">
                          <Badge
                            variant={
                              spec.qa_status === 'approved'
                                ? 'default'
                                : spec.qa_status === 'rejected'
                                  ? 'destructive'
                                  : 'secondary'
                            }
                            className="text-xs"
                          >
                            QA: {spec.qa_status}
                          </Badge>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </ScrollArea>
    </div>
  );
}
