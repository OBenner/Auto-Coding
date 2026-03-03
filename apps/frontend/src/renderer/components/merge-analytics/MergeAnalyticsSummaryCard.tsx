import { useMemo } from 'react';
import {
  GitMerge,
  CheckCircle2,
  Clock,
  Zap,
  TrendingUp,
  TrendingDown,
  Minus
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { MergeAnalytics } from '../../../shared/types/merge-analytics';

interface MergeAnalyticsSummaryCardProps {
  analytics: MergeAnalytics | null;
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

function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = Math.floor(seconds % 60);
  return `${minutes}m ${remainingSeconds}s`;
}

function formatPercentage(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function MergeAnalyticsSummaryCard({ analytics, isLoading = false }: MergeAnalyticsSummaryCardProps) {
  const stats = useMemo(() => {
    if (!analytics) {
      return {
        totalMerges: 0,
        successRate: 0,
        autoMergeRate: 0,
        avgDuration: 0
      };
    }

    return {
      totalMerges: analytics.total_operations,
      successRate: analytics.success_rate,
      autoMergeRate: analytics.auto_merge_rate,
      avgDuration: analytics.average_duration_seconds
    };
  }, [analytics]);

  const hasData = analytics && analytics.total_operations > 0;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <GitMerge className="h-5 w-5 text-accent" />
            Merge Analytics Summary
          </CardTitle>
          {hasData && (
            <Badge variant="outline" className="text-xs">
              {stats.totalMerges} {stats.totalMerges === 1 ? 'operation' : 'operations'}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Clock className="h-5 w-5 animate-spin mr-2" />
            Loading analytics...
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <GitMerge className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">No merge operations recorded yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Analytics will appear here after your first merge
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={GitMerge}
              label="Total Merges"
              value={stats.totalMerges}
              variant="default"
            />
            <StatCard
              icon={CheckCircle2}
              label="Success Rate"
              value={formatPercentage(stats.successRate)}
              variant={stats.successRate >= 0.8 ? 'success' : stats.successRate >= 0.5 ? 'warning' : 'error'}
            />
            <StatCard
              icon={Zap}
              label="Auto-Merge Rate"
              value={formatPercentage(stats.autoMergeRate)}
              variant={stats.autoMergeRate >= 0.6 ? 'success' : 'default'}
            />
            <StatCard
              icon={Clock}
              label="Avg Duration"
              value={formatDuration(stats.avgDuration)}
              variant="default"
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
