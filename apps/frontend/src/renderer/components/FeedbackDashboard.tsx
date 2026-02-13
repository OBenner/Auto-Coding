import { useState, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ThumbsUp,
  ThumbsDown,
  MessageSquare,
  TrendingUp,
  AlertTriangle,
  Calendar,
  Smile,
  Frown,
  Meh,
  Download,
  RefreshCw,
  BarChart3,
  FileText,
} from 'lucide-react';
import { Button } from './ui/button';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { ScrollArea } from './ui/scroll-area';
import { useToast } from '../hooks/use-toast';

// =============================================================================
// TYPES
// =============================================================================

interface FeedbackMetrics {
  feedback_id: string;
  spec_id?: string;
  spec_name?: string;
  feedback_type: 'accepted' | 'rejected' | 'modified';
  agent_type: string;
  task_description: string;
  rating?: number;
  sentiment?: 'positive' | 'negative' | 'neutral';
  sentiment_confidence: number;
  category?: string;
  severity?: 'low' | 'medium' | 'high' | 'critical';
  created_at?: string;
  context?: Record<string, unknown>;
}

interface FeedbackSummary {
  period_start: string;
  period_end: string;
  total_feedback: number;
  accepted_count: number;
  rejected_count: number;
  modified_count: number;
  average_rating?: number;
  total_ratings: number;
  positive_sentiment_count: number;
  negative_sentiment_count: number;
  neutral_sentiment_count: number;
  feedback_by_agent: Record<string, number>;
  ratings_by_agent: Record<string, number>;
  top_issues: Array<{
    task: string;
    agent_type: string;
    severity?: string;
    category?: string;
    created_at?: string;
  }>;
  feedback_by_category: Record<string, number>;
  satisfaction_rate: number;
  net_promoter_score?: number;
  feedback_items: FeedbackMetrics[];
}

interface FeedbackDashboardProps {
  projectId?: string;
}

type TimeRange = 'all' | '7d' | '30d' | '90d';

// =============================================================================
// STAT CARD COMPONENT
// =============================================================================

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  variant?: 'default' | 'success' | 'warning' | 'error';
  subtitle?: string;
}

function StatCard({ icon: Icon, label, value, variant = 'default', subtitle }: StatCardProps) {
  const variantStyles = {
    default: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-destructive/10 text-destructive',
  };

  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
      <div className={`p-2 rounded-lg ${variantStyles[variant]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-muted-foreground mb-1">{label}</div>
        <div className="text-2xl font-semibold text-foreground">{value}</div>
        {subtitle && <div className="text-xs text-muted-foreground mt-1">{subtitle}</div>}
      </div>
    </div>
  );
}

// =============================================================================
// SENTIMENT DISTRIBUTION COMPONENT
// =============================================================================

interface SentimentDistributionProps {
  positive: number;
  negative: number;
  neutral: number;
  total: number;
}

function SentimentDistribution({ positive, negative, neutral, total }: SentimentDistributionProps) {
  const { t } = useTranslation(['feedback']);

  if (total === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground">
        <p className="text-sm">{t('feedback:dashboard.noFeedback')}</p>
      </div>
    );
  }

  const positivePercent = (positive / total) * 100;
  const negativePercent = (negative / total) * 100;
  const neutralPercent = (neutral / total) * 100;

  return (
    <div className="space-y-4">
      {/* Positive */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <Smile className="h-4 w-4 text-success" />
            <span className="text-foreground">Positive</span>
          </div>
          <span className="font-semibold text-foreground">
            {positive} ({positivePercent.toFixed(1)}%)
          </span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-success transition-all"
            style={{ width: `${positivePercent}%` }}
          />
        </div>
      </div>

      {/* Neutral */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <Meh className="h-4 w-4 text-muted-foreground" />
            <span className="text-foreground">Neutral</span>
          </div>
          <span className="font-semibold text-foreground">
            {neutral} ({neutralPercent.toFixed(1)}%)
          </span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-muted-foreground transition-all"
            style={{ width: `${neutralPercent}%` }}
          />
        </div>
      </div>

      {/* Negative */}
      <div className="space-y-2">
        <div className="flex items-center justify-between text-sm">
          <div className="flex items-center gap-2">
            <Frown className="h-4 w-4 text-destructive" />
            <span className="text-foreground">Negative</span>
          </div>
          <span className="font-semibold text-foreground">
            {negative} ({negativePercent.toFixed(1)}%)
          </span>
        </div>
        <div className="h-2 bg-muted rounded-full overflow-hidden">
          <div
            className="h-full bg-destructive transition-all"
            style={{ width: `${negativePercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// TOP ISSUES COMPONENT
// =============================================================================

interface TopIssuesProps {
  issues: Array<{
    task: string;
    agent_type: string;
    severity?: string;
    category?: string;
    created_at?: string;
  }>;
}

function TopIssues({ issues }: TopIssuesProps) {
  const { t } = useTranslation(['feedback']);

  if (issues.length === 0) {
    return (
      <div className="flex items-center justify-center h-32 text-muted-foreground">
        <p className="text-sm">No issues reported</p>
      </div>
    );
  }

  const getSeverityVariant = (severity?: string) => {
    switch (severity) {
      case 'critical':
        return 'destructive';
      case 'high':
        return 'destructive';
      case 'medium':
        return 'secondary';
      case 'low':
        return 'outline';
      default:
        return 'outline';
    }
  };

  return (
    <div className="space-y-3">
      {issues.slice(0, 5).map((issue, index) => (
        <div
          key={index}
          className="flex items-start gap-3 p-3 rounded-lg bg-muted/30 border border-border/50"
        >
          <AlertTriangle className="h-4 w-4 text-warning mt-1 flex-shrink-0" />
          <div className="flex-1 min-w-0">
            <div className="flex items-start justify-between gap-2 mb-1">
              <p className="text-sm font-medium text-foreground line-clamp-2">
                {issue.task}
              </p>
              {issue.severity && (
                <Badge variant={getSeverityVariant(issue.severity)} className="text-xs flex-shrink-0">
                  {issue.severity}
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <span className="capitalize">{issue.agent_type}</span>
              {issue.category && (
                <>
                  <span>•</span>
                  <span className="capitalize">{issue.category}</span>
                </>
              )}
              {issue.created_at && (
                <>
                  <span>•</span>
                  <span>{new Date(issue.created_at).toLocaleDateString()}</span>
                </>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

// =============================================================================
// MAIN FEEDBACK DASHBOARD COMPONENT
// =============================================================================

export function FeedbackDashboard({ projectId = '.' }: FeedbackDashboardProps) {
  const { t } = useTranslation(['feedback', 'common']);
  const { toast } = useToast();

  // State
  const [summary, setSummary] = useState<FeedbackSummary | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [timeRange, setTimeRange] = useState<TimeRange>('30d');

  // Calculate days from time range
  const getDaysFromTimeRange = useCallback((): number => {
    switch (timeRange) {
      case '7d':
        return 7;
      case '30d':
        return 30;
      case '90d':
        return 90;
      case 'all':
        return 365; // Default to 1 year for "all"
      default:
        return 30;
    }
  }, [timeRange]);

  // Load feedback data
  const loadFeedbackData = useCallback(
    async (showRefreshToast = false) => {
      try {
        const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
        loadingState(true);

        const days = getDaysFromTimeRange();

        // Call backend API to get feedback summary
        // Note: This assumes a window.electronAPI.getFeedbackSummary method exists
        // If not, we'll need to add it to the IPC handlers
        const result = await window.electronAPI.getFeedbackSummary?.(projectId, days);

        if (result?.success && result?.data) {
          setSummary(result.data);
        } else {
          console.error('Failed to load feedback summary:', result?.error);
          // Don't show error toast on first load, just log it
          if (showRefreshToast) {
            toast({
              title: t('common:warning'),
              description: result?.error || t('feedback:messages.notAvailable'),
              variant: 'destructive',
            });
          }
        }

        if (showRefreshToast) {
          toast({
            title: t('common:success'),
            description: t('feedback:messages.submitted'),
          });
        }
      } catch (error) {
        console.error('Error loading feedback data:', error);
        if (showRefreshToast) {
          toast({
            title: t('common:error'),
            description: 'Failed to load feedback data.',
            variant: 'destructive',
          });
        }
      } finally {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    },
    [projectId, timeRange, getDaysFromTimeRange, toast, t]
  );

  // Initial load
  useEffect(() => {
    loadFeedbackData();
  }, [loadFeedbackData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadFeedbackData(true);
  }, [loadFeedbackData]);

  // Handle export
  const handleExport = useCallback(
    async (format: 'json' | 'csv') => {
      try {
        setIsExporting(true);

        const days = getDaysFromTimeRange();

        // Call backend API to export feedback
        const result = await window.electronAPI.exportFeedbackData?.(projectId, format, days);

        if (result?.success && result?.data) {
          toast({
            title: t('common:success'),
            description: `Feedback exported to ${result.data}`,
          });
        } else {
          toast({
            title: t('common:error'),
            description: result?.error || 'Failed to export feedback',
            variant: 'destructive',
          });
        }
      } catch (error) {
        console.error('Error exporting feedback:', error);
        toast({
          title: t('common:error'),
          description: 'An error occurred while exporting feedback.',
          variant: 'destructive',
        });
      } finally {
        setIsExporting(false);
      }
    },
    [projectId, getDaysFromTimeRange, toast, t]
  );

  // Handle time range change
  const handleTimeRangeChange = useCallback((range: TimeRange) => {
    setTimeRange(range);
  }, []);

  // Calculate metrics
  const metrics = useMemo(() => {
    if (!summary) {
      return {
        totalFeedback: 0,
        satisfactionRate: 0,
        averageRating: 0,
        positiveRate: 0,
      };
    }

    return {
      totalFeedback: summary.total_feedback,
      satisfactionRate: summary.satisfaction_rate * 100,
      averageRating: summary.average_rating || 0,
      positiveRate: summary.total_feedback > 0
        ? (summary.positive_sentiment_count / summary.total_feedback) * 100
        : 0,
    };
  }, [summary]);

  // Loading state
  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-border border-t-accent" />
          <p className="text-sm text-muted-foreground">
            {t('feedback:dashboard.description')}
          </p>
        </div>
      </div>
    );
  }

  const hasData = summary && summary.total_feedback > 0;

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <MessageSquare className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">
                {t('feedback:dashboard.title')}
              </h1>
              <p className="text-sm text-muted-foreground">
                {t('feedback:dashboard.description')}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Time Range Filter */}
            <div className="flex items-center gap-1 border border-border rounded-md p-1">
              <Button
                variant={timeRange === '7d' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('7d')}
                className="h-7"
              >
                <Calendar className="h-3 w-3 mr-1" />
                7d
              </Button>
              <Button
                variant={timeRange === '30d' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('30d')}
                className="h-7"
              >
                <Calendar className="h-3 w-3 mr-1" />
                30d
              </Button>
              <Button
                variant={timeRange === '90d' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('90d')}
                className="h-7"
              >
                <Calendar className="h-3 w-3 mr-1" />
                90d
              </Button>
              <Button
                variant={timeRange === 'all' ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handleTimeRangeChange('all')}
                className="h-7"
              >
                All
              </Button>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={isExporting}
            >
              <FileText className="h-4 w-4 mr-2" />
              Export JSON
            </Button>

            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={isExporting}
            >
              <Download className="h-4 w-4 mr-2" />
              Export CSV
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {hasData ? (
            <>
              {/* Summary Metrics */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                  icon={MessageSquare}
                  label={t('feedback:dashboard.totalFeedback')}
                  value={metrics.totalFeedback}
                  variant="default"
                />
                <StatCard
                  icon={TrendingUp}
                  label={t('feedback:dashboard.satisfactionScore')}
                  value={`${metrics.satisfactionRate.toFixed(1)}%`}
                  variant={
                    metrics.satisfactionRate >= 80
                      ? 'success'
                      : metrics.satisfactionRate >= 50
                      ? 'warning'
                      : 'error'
                  }
                />
                <StatCard
                  icon={ThumbsUp}
                  label={t('feedback:dashboard.positiveRate')}
                  value={`${metrics.positiveRate.toFixed(1)}%`}
                  variant={metrics.positiveRate >= 70 ? 'success' : 'default'}
                />
                <StatCard
                  icon={BarChart3}
                  label={t('feedback:dashboard.averageRating')}
                  value={metrics.averageRating > 0 ? metrics.averageRating.toFixed(1) : 'N/A'}
                  subtitle={metrics.averageRating > 0 ? 'out of 5' : undefined}
                  variant={
                    metrics.averageRating >= 4
                      ? 'success'
                      : metrics.averageRating >= 3
                      ? 'default'
                      : 'warning'
                  }
                />
              </div>

              {/* Sentiment Distribution & Top Issues */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Sentiment Distribution */}
                <Card className="bg-muted/30 border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                      <Smile className="h-5 w-5 text-accent" />
                      {t('feedback:analytics.sentimentDistribution')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <SentimentDistribution
                      positive={summary.positive_sentiment_count}
                      negative={summary.negative_sentiment_count}
                      neutral={summary.neutral_sentiment_count}
                      total={summary.total_feedback}
                    />
                  </CardContent>
                </Card>

                {/* Top Issues */}
                <Card className="bg-muted/30 border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold flex items-center gap-2">
                      <AlertTriangle className="h-5 w-5 text-warning" />
                      {t('feedback:dashboard.topIssues')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <TopIssues issues={summary.top_issues} />
                  </CardContent>
                </Card>
              </div>

              {/* Feedback by Agent Type */}
              {Object.keys(summary.feedback_by_agent).length > 0 && (
                <Card className="bg-muted/30 border-border/50">
                  <CardHeader>
                    <CardTitle className="text-lg font-semibold">Feedback by Agent Type</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      {Object.entries(summary.feedback_by_agent).map(([agent, count]) => (
                        <div
                          key={agent}
                          className="p-3 rounded-lg bg-muted/30 border border-border/50"
                        >
                          <p className="text-sm text-muted-foreground capitalize mb-1">{agent}</p>
                          <p className="text-xl font-semibold text-foreground">{count}</p>
                          {summary.ratings_by_agent[agent] && (
                            <p className="text-xs text-muted-foreground mt-1">
                              Avg: {summary.ratings_by_agent[agent].toFixed(1)}/5
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}
            </>
          ) : (
            /* Empty State */
            <div className="flex flex-col items-center justify-center h-[60vh] text-center">
              <MessageSquare className="h-16 w-16 text-muted-foreground/50 mb-4" />
              <h2 className="text-xl font-semibold text-foreground mb-2">
                {t('feedback:dashboard.noFeedback')}
              </h2>
              <p className="text-sm text-muted-foreground max-w-md">
                {t('feedback:dashboard.noFeedbackDescription')}
              </p>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
