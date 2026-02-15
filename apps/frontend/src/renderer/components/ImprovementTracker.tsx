import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  TrendingUp,
  TrendingDown,
  Minus,
  Calendar,
  FileText,
  CheckCircle2,
  AlertCircle,
  Lightbulb,
  Search,
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { Input } from './ui/input';
import { useToast } from '../hooks/use-toast';
import { cn } from '../lib/utils';
import {
  type TimeRange,
  getDaysFromTimeRange,
  TimeRangeFilter,
  RefreshButton,
  LoadingSpinner,
  EmptyState,
} from './feedback/shared';

// =============================================================================
// TYPES
// =============================================================================

interface MetricChange {
  before: number;
  after: number;
  delta: number;
  percent_change: number;
}

interface ImprovementData {
  improvement_id: string;
  improvement_description: string;
  feedback_ids: string[];
  agent_type?: string;
  created_at?: string;
  improvement_delta: Record<string, MetricChange>;
  context?: Record<string, unknown>;
}

interface ImprovementTrackerProps {
  projectId?: string;
}

type FilterType = 'all' | 'planner' | 'coder' | 'qa_reviewer' | 'qa_fixer';

// =============================================================================
// METRIC CHANGE CARD COMPONENT
// =============================================================================

interface MetricChangeCardProps {
  metricName: string;
  change: MetricChange;
}

function MetricChangeCard({ metricName, change }: MetricChangeCardProps) {
  const { t } = useTranslation(['feedback']);

  const isPositive = change.delta > 0;
  const isNeutral = change.delta === 0;

  const Icon = isNeutral ? Minus : isPositive ? TrendingUp : TrendingDown;

  // Determine variant based on metric name and delta direction
  // For error rates, lower is better; for success rates, higher is better
  const isErrorMetric =
    metricName.toLowerCase().includes('error') ||
    metricName.toLowerCase().includes('fail');

  const isImprovement = isErrorMetric ? change.delta < 0 : change.delta > 0;

  const variant = isNeutral
    ? 'default'
    : isImprovement
    ? 'success'
    : 'warning';

  const variantStyles = {
    default: 'bg-muted/50 text-muted-foreground',
    success: 'bg-success/10 text-success border-success/20',
    warning: 'bg-warning/10 text-warning border-warning/20',
  };

  return (
    <div
      className={cn(
        'p-4 rounded-lg border',
        variantStyles[variant]
      )}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4" />
          <span className="text-sm font-medium capitalize">
            {metricName.replace(/_/g, ' ')}
          </span>
        </div>
        {!isNeutral && (
          <Badge variant={isImprovement ? 'default' : 'secondary'} className="text-xs">
            {change.percent_change > 0 ? '+' : ''}
            {change.percent_change.toFixed(1)}%
          </Badge>
        )}
      </div>

      <div className="grid grid-cols-3 gap-3 text-sm">
        <div>
          <div className="text-xs text-muted-foreground mb-1">
            {t('feedback:improvement.before')}
          </div>
          <div className="font-semibold">{change.before.toFixed(2)}</div>
        </div>

        <div>
          <div className="text-xs text-muted-foreground mb-1">
            {t('feedback:improvement.after')}
          </div>
          <div className="font-semibold">{change.after.toFixed(2)}</div>
        </div>

        <div>
          <div className="text-xs text-muted-foreground mb-1">
            {t('feedback:improvement.delta')}
          </div>
          <div className="font-semibold">
            {change.delta > 0 ? '+' : ''}
            {change.delta.toFixed(2)}
          </div>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// IMPROVEMENT ITEM COMPONENT
// =============================================================================

interface ImprovementItemProps {
  improvement: ImprovementData;
}

function ImprovementItem({ improvement }: ImprovementItemProps) {
  const { t } = useTranslation(['feedback']);

  const formatDate = (dateString?: string): string => {
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

  const metricCount = Object.keys(improvement.improvement_delta).length;
  const feedbackCount = improvement.feedback_ids.length;

  return (
    <Card className="bg-card border-border">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1">
            <CardTitle className="text-base font-semibold flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-accent flex-shrink-0" />
              <span className="line-clamp-2">{improvement.improvement_description}</span>
            </CardTitle>
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
              {improvement.agent_type && (
                <Badge variant="outline" className="text-xs capitalize">
                  {improvement.agent_type}
                </Badge>
              )}
              {feedbackCount > 0 && (
                <span className="flex items-center gap-1">
                  <FileText className="h-3 w-3" />
                  {t('feedback:improvement.basedOnFeedback', { count: feedbackCount })}
                </span>
              )}
              {improvement.created_at && (
                <span className="flex items-center gap-1">
                  <Calendar className="h-3 w-3" />
                  {formatDate(improvement.created_at)}
                </span>
              )}
            </div>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {metricCount > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {Object.entries(improvement.improvement_delta).map(([metric, change]) => (
              <MetricChangeCard key={metric} metricName={metric} change={change} />
            ))}
          </div>
        ) : (
          <div className="flex items-center justify-center py-6 text-muted-foreground">
            <p className="text-sm">No metrics tracked for this improvement</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

// =============================================================================
// MAIN IMPROVEMENT TRACKER COMPONENT
// =============================================================================

export function ImprovementTracker({ projectId = '.' }: ImprovementTrackerProps) {
  const { t } = useTranslation(['feedback', 'common']);
  const { toast } = useToast();

  // State
  const [improvements, setImprovements] = useState<ImprovementData[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');
  const [agentFilter, setAgentFilter] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');

  // Load improvements data
  const loadImprovementsData = useCallback(
    async (showRefreshToast = false) => {
      try {
        const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
        loadingState(true);

        const days = getDaysFromTimeRange(timeRange);

        // Call backend API to get improvements
        const result = await window.electronAPI.getImprovements?.(projectId, days);

        if (result?.success && result?.data) {
          setImprovements(result.data);
          if (showRefreshToast) {
            toast({
              title: t('common:success'),
              description: 'Improvements refreshed',
            });
          }
        } else {
          console.error('Failed to load improvements:', result?.error);
          // Don't show error toast on first load, just log it
          if (showRefreshToast) {
            toast({
              title: t('common:warning'),
              description: result?.error || 'Failed to load improvements',
              variant: 'destructive',
            });
          }
          // Set empty array if no data
          setImprovements([]);
        }
      } catch (error) {
        console.error('Error loading improvements data:', error);
        if (showRefreshToast) {
          toast({
            title: t('common:error'),
            description: 'Failed to load improvements data.',
            variant: 'destructive',
          });
        }
        setImprovements([]);
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [projectId, timeRange, toast, t]
  );

  // Initial load
  useEffect(() => {
    loadImprovementsData();
  }, [loadImprovementsData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadImprovementsData(true);
  }, [loadImprovementsData]);

  // Handle time range change
  const handleTimeRangeChange = useCallback((range: TimeRange) => {
    setTimeRange(range);
  }, []);

  // Filter improvements
  const filteredImprovements = useMemo(() => {
    return improvements.filter((improvement) => {
      // Apply agent filter
      if (agentFilter !== 'all' && improvement.agent_type !== agentFilter) {
        return false;
      }

      // Apply search filter
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        const matchesDescription = (improvement.improvement_description ?? '')
          .toLowerCase()
          .includes(q);
        const matchesAgent = (improvement.agent_type ?? '').toLowerCase().includes(q);
        const matchesMetrics = Object.keys(improvement.improvement_delta).some((metric) =>
          metric.toLowerCase().includes(q)
        );

        return matchesDescription || matchesAgent || matchesMetrics;
      }

      return true;
    });
  }, [improvements, agentFilter, searchQuery]);

  // Calculate summary stats
  const stats = useMemo(() => {
    const totalImprovements = filteredImprovements.length;
    const totalFeedbackAddressed = filteredImprovements.reduce(
      (sum, imp) => sum + imp.feedback_ids.length,
      0
    );
    const totalMetricsImproved = filteredImprovements.reduce(
      (sum, imp) => sum + Object.keys(imp.improvement_delta).length,
      0
    );

    return {
      totalImprovements,
      totalFeedbackAddressed,
      totalMetricsImproved,
    };
  }, [filteredImprovements]);

  // Loading state
  if (isLoading) {
    return <LoadingSpinner message={t('feedback:improvement.description')} />;
  }

  const hasData = filteredImprovements.length > 0;

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <TrendingUp className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">
                {t('feedback:improvement.title')}
              </h1>
              <p className="text-sm text-muted-foreground">
                {t('feedback:improvement.description')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <TimeRangeFilter value={timeRange} onChange={handleTimeRangeChange} />
            <RefreshButton onClick={handleRefresh} isRefreshing={isRefreshing} />
          </div>
        </div>
      </div>

      {/* Filters and Stats */}
      <div className="border-b border-border px-6 py-3 space-y-3">
        {/* Search and Agent Filter */}
        <div className="flex items-center gap-3">
          {/* Search */}
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-3 w-3 text-muted-foreground" />
            <Input
              placeholder="Search improvements, metrics, or agent types..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="h-8 text-sm pl-9"
            />
          </div>

          {/* Agent Filter */}
          <div className="flex items-center gap-1">
            <span className="text-xs text-muted-foreground mr-1">Agent:</span>
            {(['all', 'planner', 'coder', 'qa_reviewer', 'qa_fixer'] as const).map(
              (agent) => (
                <Button
                  key={agent}
                  variant={agentFilter === agent ? 'default' : 'ghost'}
                  size="sm"
                  onClick={() => setAgentFilter(agent)}
                  className="h-6 text-xs capitalize px-2"
                >
                  {agent === 'qa_reviewer'
                    ? 'QA'
                    : agent === 'qa_fixer'
                    ? 'Fixer'
                    : agent}
                </Button>
              )
            )}
          </div>
        </div>

        {/* Stats */}
        {hasData && (
          <div className="grid grid-cols-3 gap-3">
            <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30 border border-border/50">
              <CheckCircle2 className="h-4 w-4 text-success" />
              <div>
                <div className="text-xs text-muted-foreground">Improvements</div>
                <div className="text-lg font-semibold">{stats.totalImprovements}</div>
              </div>
            </div>

            <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30 border border-border/50">
              <FileText className="h-4 w-4 text-accent" />
              <div>
                <div className="text-xs text-muted-foreground">Feedback Addressed</div>
                <div className="text-lg font-semibold">{stats.totalFeedbackAddressed}</div>
              </div>
            </div>

            <div className="flex items-center gap-2 p-2 rounded-lg bg-muted/30 border border-border/50">
              <TrendingUp className="h-4 w-4 text-warning" />
              <div>
                <div className="text-xs text-muted-foreground">Metrics Improved</div>
                <div className="text-lg font-semibold">{stats.totalMetricsImproved}</div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-4">
          {hasData ? (
            <>
              {filteredImprovements.map((improvement) => (
                <ImprovementItem key={improvement.improvement_id} improvement={improvement} />
              ))}
            </>
          ) : (
            <EmptyState
              icon={AlertCircle}
              title={t('feedback:improvement.noImprovements')}
              description={t('feedback:improvement.noImprovementsDescription')}
            />
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
