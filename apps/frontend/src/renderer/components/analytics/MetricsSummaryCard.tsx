import { useMemo } from 'react';
import {
  BarChart3,
  CheckCircle2,
  Clock,
  TrendingUp,
  TrendingDown,
  Minus,
  Target
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { ProductivitySummary } from '../../../shared/types/productivity-analytics';

interface MetricsSummaryCardProps {
  analytics: ProductivitySummary | null;
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

function formatHours(hours: number): string {
  if (hours < 1) {
    return `${(hours * 60).toFixed(0)}m`;
  }
  if (hours < 24) {
    return `${hours.toFixed(1)}h`;
  }
  const days = Math.floor(hours / 24);
  const remainingHours = Math.floor(hours % 24);
  return `${days}d ${remainingHours}h`;
}

function formatPercentage(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function MetricsSummaryCard({ analytics, isLoading = false }: MetricsSummaryCardProps) {
  const stats = useMemo(() => {
    if (!analytics) {
      return {
        totalSpecs: 0,
        completedSpecs: 0,
        timeSaved: 0,
        successRate: 0
      };
    }

    return {
      totalSpecs: analytics.total_specs,
      completedSpecs: analytics.completed_specs,
      timeSaved: analytics.total_time_saved_hours,
      successRate: analytics.average_success_rate
    };
  }, [analytics]);

  const hasData = analytics && analytics.total_specs > 0;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Target className="h-5 w-5 text-accent" />
            Productivity Summary
          </CardTitle>
          {hasData && (
            <Badge variant="outline" className="text-xs">
              {stats.totalSpecs} {stats.totalSpecs === 1 ? 'spec' : 'specs'}
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
            <BarChart3 className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">No productivity data recorded yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Analytics will appear here after your first completed spec
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={BarChart3}
              label="Total Specs"
              value={stats.totalSpecs}
              variant="default"
            />
            <StatCard
              icon={CheckCircle2}
              label="Completed"
              value={stats.completedSpecs}
              variant={stats.completedSpecs >= stats.totalSpecs * 0.8 ? 'success' : stats.completedSpecs >= stats.totalSpecs * 0.5 ? 'warning' : 'default'}
            />
            <StatCard
              icon={Clock}
              label="Time Saved"
              value={formatHours(stats.timeSaved)}
              variant={stats.timeSaved >= 10 ? 'success' : 'default'}
            />
            <StatCard
              icon={TrendingUp}
              label="Success Rate"
              value={formatPercentage(stats.successRate)}
              variant={stats.successRate >= 0.8 ? 'success' : stats.successRate >= 0.5 ? 'warning' : 'error'}
            />
          </div>
        )}
      </CardContent>
    </Card>
  );
}
