import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import type { TFunction } from 'i18next';
import {
  BarChart3,
  TrendingUp,
  Users,
  CheckCircle2,
  XCircle,
  Clock,
  DollarSign,
  AlertCircle,
  Loader2,
  RefreshCw
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';
import type {
  AnalyticsReport,
  AnalyticsView,
  AgentStats as AgentStatsType,
  MetricsSummary,
  QAStats as QAStatsType,
  TrendDataPoint
} from '../../shared/types';

// Reuse a single formatter to avoid repeated Intl.NumberFormat allocation
const usdFormatter = new Intl.NumberFormat('en-US', {
  style: 'currency',
  currency: 'USD',
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
});

const numberFormatter = new Intl.NumberFormat('en-US');

interface AnalyticsProps {
  projectId: string;
}

export function Analytics({ projectId }: AnalyticsProps) {
  const { t } = useTranslation(['analytics', 'common']);

  const [currentView, setCurrentView] = useState<AnalyticsView>('overview');
  const [report, setReport] = useState<AnalyticsReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Load analytics data
  const loadAnalytics = async () => {
    try {
      setLoading(true);
      setError(null);

      const result = await window.electronAPI.analytics.getReport(projectId);

      if (result.success && result.data) {
        setReport(result.data);
      } else {
        setError(result.error || t('analytics:errors.loadFailed'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  useEffect(() => {
    loadAnalytics();
  }, [projectId]);

  const handleRefresh = () => {
    setRefreshing(true);
    loadAnalytics();
  };

  // Format helpers (using memoized formatters)
  const formatCurrency = useCallback((amount: number) => usdFormatter.format(amount), []);
  const formatPercentage = useCallback((value: number) => `${value.toFixed(1)}%`, []);
  const formatDuration = useCallback((seconds: number) => {
    if (seconds < 60) return `${seconds.toFixed(0)}s`;
    if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
    return `${(seconds / 3600).toFixed(1)}h`;
  }, []);
  const formatNumber = useCallback((num: number) => numberFormatter.format(num), []);

  // Render loading state
  if (loading && !report) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center space-y-4">
          <Loader2 className="w-8 h-8 animate-spin text-primary mx-auto" />
          <p className="text-sm text-muted-foreground">{t('analytics:loading')}</p>
        </div>
      </div>
    );
  }

  // Render error state
  if (error || !report) {
    return (
      <div className="flex h-full items-center justify-center p-8">
        <Card className="max-w-md">
          <CardContent className="pt-6">
            <div className="text-center space-y-4">
              <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
              <div>
                <h3 className="font-semibold text-lg">{t('analytics:errors.title')}</h3>
                <p className="text-sm text-muted-foreground mt-2">
                  {error || t('analytics:errors.noData')}
                </p>
              </div>
              <Button onClick={handleRefresh} variant="outline">
                <RefreshCw className="w-4 h-4 mr-2" />
                {t('common:actions.retry')}
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    );
  }

  const { summary, trends } = report;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex-none border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center justify-between px-6 py-4">
          <div>
            <h1 className="text-2xl font-bold">{t('analytics:title')}</h1>
            <p className="text-sm text-muted-foreground mt-1">
              {t('analytics:subtitle')}
            </p>
          </div>
          <Button
            onClick={handleRefresh}
            disabled={refreshing}
            variant="outline"
            size="sm"
          >
            <RefreshCw className={cn('w-4 h-4 mr-2', refreshing && 'animate-spin')} />
            {t('common:actions.refresh')}
          </Button>
        </div>

        {/* View Tabs */}
        <div className="flex gap-2 px-6 pb-4">
          <Button
            variant={currentView === 'overview' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('overview')}
          >
            <BarChart3 className="w-4 h-4 mr-2" />
            {t('analytics:views.overview')}
          </Button>
          <Button
            variant={currentView === 'agents' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('agents')}
          >
            <Users className="w-4 h-4 mr-2" />
            {t('analytics:views.agents')}
          </Button>
          <Button
            variant={currentView === 'trends' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('trends')}
          >
            <TrendingUp className="w-4 h-4 mr-2" />
            {t('analytics:views.trends')}
          </Button>
          <Button
            variant={currentView === 'qa' ? 'default' : 'ghost'}
            size="sm"
            onClick={() => setCurrentView('qa')}
          >
            <CheckCircle2 className="w-4 h-4 mr-2" />
            {t('analytics:views.qa')}
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {currentView === 'overview' && (
            <OverviewView
              summary={summary}
              formatCurrency={formatCurrency}
              formatPercentage={formatPercentage}
              formatNumber={formatNumber}
              t={t}
            />
          )}
          {currentView === 'agents' && (
            <AgentsView
              agentStats={summary.agent_stats}
              formatCurrency={formatCurrency}
              formatPercentage={formatPercentage}
              formatDuration={formatDuration}
              formatNumber={formatNumber}
              t={t}
            />
          )}
          {currentView === 'trends' && (
            <TrendsView
              trends={trends}
              formatCurrency={formatCurrency}
              formatPercentage={formatPercentage}
              formatNumber={formatNumber}
              t={t}
            />
          )}
          {currentView === 'qa' && (
            <QAView
              qaStats={summary.qa_stats}
              formatPercentage={formatPercentage}
              formatNumber={formatNumber}
              t={t}
            />
          )}
        </div>
      </ScrollArea>

      {/* Footer with last updated */}
      <div className="flex-none border-t px-6 py-3 bg-muted/50">
        <p className="text-xs text-muted-foreground">
          {t('analytics:lastUpdated')}: {new Date(summary.last_updated).toLocaleString()}
        </p>
      </div>
    </div>
  );
}

// Overview View Component
interface OverviewViewProps {
  summary: MetricsSummary;
  formatCurrency: (amount: number) => string;
  formatPercentage: (value: number) => string;
  formatNumber: (value: number) => string;
  t: TFunction;
}

function OverviewView({
  summary,
  formatCurrency,
  formatPercentage,
  formatNumber,
  t
}: OverviewViewProps) {
  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('analytics:overview.totalSpecs')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{summary.total_specs}</div>
            <div className="flex gap-2 mt-2 text-xs">
              <Badge variant="success" className="gap-1">
                <CheckCircle2 className="w-3 h-3" />
                {summary.completed_specs} {t('common:status.completed')}
              </Badge>
              {summary.failed_specs > 0 && (
                <Badge variant="destructive" className="gap-1">
                  <XCircle className="w-3 h-3" />
                  {summary.failed_specs} {t('common:status.failed')}
                </Badge>
              )}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('analytics:overview.successRate')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatPercentage(summary.overall_success_rate)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {t('analytics:overview.successRateDesc')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <DollarSign className="w-4 h-4" />
              {t('analytics:overview.totalCost')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatCurrency(summary.total_cost)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {formatNumber(summary.total_tokens)} {t('analytics:overview.tokens')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('analytics:overview.avgCostPerSpec')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">
              {formatCurrency(summary.total_specs > 0 ? summary.total_cost / summary.total_specs : 0)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {t('analytics:overview.perSpec')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Complexity Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:overview.complexityBreakdown')}</CardTitle>
          <CardDescription>{t('analytics:overview.complexityDesc')}</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Object.entries(summary.complexity_stats).map(([complexity, stats]) => (
              <div key={complexity} className="space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Badge variant="outline">{complexity}</Badge>
                    <span className="text-sm text-muted-foreground">
                      {stats.total_tasks} {t('analytics:overview.tasks')}
                    </span>
                  </div>
                  <div className="text-sm font-medium">
                    {formatPercentage(stats.success_rate)} {t('analytics:overview.successRate')}
                  </div>
                </div>
                <div className="flex gap-4 text-xs text-muted-foreground">
                  <span>
                    <Clock className="w-3 h-3 inline mr-1" />
                    {(stats.avg_completion_time / 60).toFixed(1)}m {t('analytics:overview.avgTime')}
                  </span>
                  <span>
                    <DollarSign className="w-3 h-3 inline mr-1" />
                    {formatCurrency(stats.avg_cost)} {t('analytics:overview.avgCost')}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

// Agents View Component
interface AgentsViewProps {
  agentStats: Record<string, AgentStatsType>;
  formatCurrency: (amount: number) => string;
  formatPercentage: (value: number) => string;
  formatDuration: (seconds: number) => string;
  formatNumber: (value: number) => string;
  t: TFunction;
}

function AgentsView({
  agentStats,
  formatCurrency,
  formatPercentage,
  formatDuration,
  formatNumber,
  t
}: AgentsViewProps) {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-6">
        {Object.entries(agentStats).map(([agentType, stats]) => (
          <Card key={agentType}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>{agentType}</span>
                <Badge variant={stats.success_rate >= 80 ? 'success' : stats.success_rate >= 60 ? 'warning' : 'destructive'}>
                  {formatPercentage(stats.success_rate)}
                </Badge>
              </CardTitle>
              <CardDescription>
                {stats.total_attempts} {t('analytics:agents.totalAttempts')}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <div>
                  <div className="text-sm text-muted-foreground">{t('analytics:agents.successful')}</div>
                  <div className="text-2xl font-bold text-green-600">{stats.successful_attempts}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">{t('analytics:agents.failed')}</div>
                  <div className="text-2xl font-bold text-red-600">{stats.failed_attempts}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">{t('analytics:agents.totalCost')}</div>
                  <div className="text-2xl font-bold">{formatCurrency(stats.total_cost)}</div>
                  <div className="text-xs text-muted-foreground">{formatNumber(stats.total_tokens)} {t('analytics:overview.tokens')}</div>
                </div>
                <div>
                  <div className="text-sm text-muted-foreground">{t('analytics:agents.avgTime')}</div>
                  <div className="text-2xl font-bold">{formatDuration(stats.avg_completion_time)}</div>
                </div>
              </div>

              {/* Error Patterns */}
              {Object.keys(stats.error_patterns).length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-semibold mb-2">{t('analytics:agents.errorPatterns')}</h4>
                  <div className="space-y-2">
                    {Object.entries(stats.error_patterns)
                      .sort(([, a], [, b]) => (b as number) - (a as number))
                      .slice(0, 5)
                      .map(([error, count]) => (
                        <div key={error} className="flex items-center justify-between text-sm">
                          <span className="text-muted-foreground truncate flex-1">{error}</span>
                          <Badge variant="outline">{count}</Badge>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {Object.keys(agentStats).length === 0 && (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
            <p className="text-muted-foreground">{t('analytics:agents.noData')}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// Trends View Component
interface TrendsViewProps {
  trends: TrendDataPoint[];
  formatCurrency: (amount: number) => string;
  formatPercentage: (value: number) => string;
  formatNumber: (value: number) => string;
  t: TFunction;
}

function TrendsView({
  trends,
  formatCurrency,
  formatPercentage,
  formatNumber,
  t
}: TrendsViewProps) {
  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:trends.title')}</CardTitle>
          <CardDescription>{t('analytics:trends.description')}</CardDescription>
        </CardHeader>
        <CardContent>
          {trends.length > 0 ? (
            <div className="space-y-4">
              {trends.slice().reverse().map((point: TrendDataPoint) => (
                <div key={point.date} className="flex items-center justify-between pb-3 border-b last:border-0">
                  <div>
                    <div className="font-medium">{new Date(point.date).toLocaleDateString()}</div>
                    <div className="text-sm text-muted-foreground">
                      {point.total_tasks} {t('analytics:trends.tasks')}
                    </div>
                  </div>
                  <div className="text-right space-y-1">
                    <div className="font-semibold">{formatPercentage(point.success_rate)}</div>
                    <div className="text-xs text-muted-foreground">{formatCurrency(point.total_cost)}</div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <TrendingUp className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">{t('analytics:trends.noData')}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

// QA View Component
interface QAViewProps {
  qaStats: QAStatsType;
  formatPercentage: (value: number) => string;
  formatNumber: (value: number) => string;
  t: TFunction;
}

function QAView({
  qaStats,
  formatPercentage,
  formatNumber,
  t
}: QAViewProps) {
  return (
    <div className="space-y-6">
      {/* QA Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('analytics:qa.totalReviews')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold">{qaStats.total_reviews}</div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('analytics:qa.approved')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-3xl font-bold text-green-600">{qaStats.approved}</div>
            <p className="text-xs text-muted-foreground mt-2">
              {qaStats.total_reviews > 0
                ? formatPercentage((qaStats.approved / qaStats.total_reviews) * 100)
                : formatPercentage(0)
              } {t('analytics:qa.approvalRate')}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground">
              {t('analytics:qa.rejectionRate')}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className={cn(
              'text-3xl font-bold',
              qaStats.rejection_rate > 30 ? 'text-red-600' : qaStats.rejection_rate > 15 ? 'text-yellow-600' : 'text-green-600'
            )}>
              {formatPercentage(qaStats.rejection_rate)}
            </div>
            <p className="text-xs text-muted-foreground mt-2">
              {qaStats.rejected} {t('analytics:qa.rejected')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Common Issues */}
      <Card>
        <CardHeader>
          <CardTitle>{t('analytics:qa.commonIssues')}</CardTitle>
          <CardDescription>{t('analytics:qa.issuesDescription')}</CardDescription>
        </CardHeader>
        <CardContent>
          {Object.keys(qaStats.common_issues).length > 0 ? (
            <div className="space-y-3">
              {Object.entries(qaStats.common_issues)
                .sort(([, a]: any, [, b]: any) => b - a)
                .map(([issue, count]) => (
                  <div key={issue} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 flex-1">
                      <AlertCircle className="w-4 h-4 text-muted-foreground" />
                      <span className="text-sm">{issue}</span>
                    </div>
                    <Badge variant="secondary">{count}</Badge>
                  </div>
                ))}
            </div>
          ) : (
            <div className="py-12 text-center">
              <CheckCircle2 className="w-12 h-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground">{t('analytics:qa.noIssues')}</p>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
