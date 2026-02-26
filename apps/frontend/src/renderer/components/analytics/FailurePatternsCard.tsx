import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  AlertTriangle,
  Bug,
  FileWarning,
  TrendingDown,
  TrendingUp,
  Minus,
  ShieldAlert
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { FailureMetrics } from '../../../shared/types/productivity-analytics';

interface FailurePatternsCardProps {
  failureMetrics: FailureMetrics | null;
  isLoading?: boolean;
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  trend?: 'up' | 'down' | 'neutral';
  trendValue?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

function StatCard({ icon: Icon, label, value, trend, trendValue, variant = 'default' }: StatCardProps) {
  const variantStyles = {
    default: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-destructive/10 text-destructive'
  };

  const TrendIcon = trend === 'up' ? TrendingUp : trend === 'down' ? TrendingDown : Minus;
  const trendColor = trend === 'up' ? 'text-success' : trend === 'down' ? 'text-destructive' : 'text-muted-foreground';

  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
      <div className={`p-2 rounded-lg ${variantStyles[variant]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-muted-foreground mb-1">{label}</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-semibold text-foreground">{value}</div>
          {trend && trendValue && (
            <div className={`flex items-center gap-1 text-xs ${trendColor}`}>
              <TrendIcon className="h-3 w-3" />
              <span>{trendValue}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

interface CategoryItemProps {
  category: string;
  count: number;
  total: number;
}

function CategoryItem({ category, count, total }: CategoryItemProps) {
  const percentage = total > 0 ? Math.round((count / total) * 100) : 0;

  return (
    <div className="flex items-center justify-between py-2 px-3 rounded-md bg-muted/20 border border-border/30">
      <div className="flex items-center gap-2 flex-1 min-w-0">
        <Bug className="h-4 w-4 text-destructive/70 flex-shrink-0" />
        <span className="text-sm font-medium text-foreground truncate">{category}</span>
      </div>
      <div className="flex items-center gap-3 flex-shrink-0">
        <div className="text-xs text-muted-foreground">{percentage}%</div>
        <Badge variant="outline" className="text-xs min-w-[2.5rem] justify-center">
          {count}
        </Badge>
      </div>
    </div>
  );
}

function formatPercentage(rate: number | undefined): string {
  return `${((rate ?? 0) * 100).toFixed(1)}%`;
}

export function FailurePatternsCard({ failureMetrics, isLoading = false }: FailurePatternsCardProps) {
  const { t } = useTranslation(['common']);

  const stats = useMemo(() => {
    if (!failureMetrics) {
      return {
        totalFailures: 0,
        rootCauseRate: 0,
        patternDetectionRate: 0,
        recurrenceRate: 0,
        topCategories: []
      };
    }

    return {
      totalFailures: failureMetrics.total_failures,
      rootCauseRate: failureMetrics.root_cause_rate ?? 0,
      patternDetectionRate: failureMetrics.pattern_detection_rate ?? 0,
      recurrenceRate: failureMetrics.recurrence_rate ?? 0,
      topCategories: failureMetrics.top_failure_categories ?? []
    };
  }, [failureMetrics]);

  const hasData = failureMetrics && failureMetrics.total_failures > 0;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <ShieldAlert className="h-5 w-5 text-destructive" />
            {t('common:failurePatterns.title')}
          </CardTitle>
          {hasData && (
            <Badge variant="outline" className="text-xs">
              {t('common:failurePatterns.failureCount', { count: stats.totalFailures })}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <AlertTriangle className="h-5 w-5 animate-pulse mr-2" />
            {t('common:failurePatterns.loading')}
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <ShieldAlert className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">{t('common:failurePatterns.noData')}</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              {t('common:failurePatterns.noDataHint')}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Metrics Summary */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={AlertTriangle}
                label={t('common:failurePatterns.totalFailures')}
                value={stats.totalFailures}
                variant={stats.totalFailures > 10 ? 'error' : stats.totalFailures > 5 ? 'warning' : 'default'}
              />
              <StatCard
                icon={Bug}
                label={t('common:failurePatterns.rootCauseRate')}
                value={formatPercentage(stats.rootCauseRate)}
                variant={stats.rootCauseRate >= 0.8 ? 'success' : stats.rootCauseRate >= 0.5 ? 'warning' : 'error'}
              />
              <StatCard
                icon={FileWarning}
                label={t('common:failurePatterns.patternDetection')}
                value={formatPercentage(stats.patternDetectionRate)}
                variant={stats.patternDetectionRate >= 0.8 ? 'success' : stats.patternDetectionRate >= 0.5 ? 'warning' : 'error'}
              />
              <StatCard
                icon={TrendingDown}
                label={t('common:failurePatterns.recurrenceRate')}
                value={formatPercentage(stats.recurrenceRate)}
                variant={stats.recurrenceRate <= 0.2 ? 'success' : stats.recurrenceRate <= 0.5 ? 'warning' : 'error'}
              />
            </div>

            {/* Top Failure Categories */}
            {stats.topCategories.length > 0 && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <Bug className="h-4 w-4 text-muted-foreground" />
                  <h3 className="text-sm font-semibold text-foreground">{t('common:failurePatterns.commonCategories')}</h3>
                </div>
                <div className="space-y-2">
                  {stats.topCategories.map((item) => (
                    <CategoryItem
                      key={item.category}
                      category={item.category}
                      count={item.count}
                      total={stats.totalFailures}
                    />
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
