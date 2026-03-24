import { useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  FileText,
  CheckCircle2,
  Clock,
  GitBranch,
  RefreshCw,
  BarChart3
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { ProductivitySummary } from '../../../shared/types/productivity-analytics';

interface SpecSummaryCardProps {
  readonly analytics: ProductivitySummary | null;
  readonly isLoading?: boolean;
}

interface StatCardProps {
  readonly icon: React.ComponentType<{ className?: string }>;
  readonly label: string;
  readonly value: string | number;
  readonly subValue?: string;
  readonly variant?: 'default' | 'success' | 'warning' | 'error';
}

interface WorkflowBreakdownProps {
  readonly specsByType: Record<string, number>;
}

function getCompletionVariant(rate: number): 'success' | 'warning' | 'default' {
  if (rate >= 0.8) return 'success';
  if (rate >= 0.5) return 'warning';
  return 'default';
}

function getQAVariant(iterations: number): 'success' | 'warning' | 'error' {
  if (iterations <= 1) return 'success';
  if (iterations <= 2) return 'warning';
  return 'error';
}

function StatCard({ icon: Icon, label, value, subValue, variant = 'default' }: StatCardProps) {
  const variantStyles = {
    default: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    error: 'bg-destructive/10 text-destructive'
  };

  return (
    <div className="flex items-start gap-3 p-4 rounded-lg bg-muted/30 border border-border/50">
      <div className={`p-2 rounded-lg ${variantStyles[variant]}`}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm text-muted-foreground mb-1">{label}</div>
        <div className="flex items-baseline gap-2">
          <div className="text-2xl font-semibold text-foreground">{value}</div>
          {subValue && (
            <div className="text-xs text-muted-foreground">
              {subValue}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function WorkflowBreakdown({ specsByType }: WorkflowBreakdownProps) {
  const { t } = useTranslation('analytics');
  const workflowEntries = Object.entries(specsByType).sort(([, a], [, b]) => b - a);

  if (workflowEntries.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 p-4 rounded-lg bg-muted/30 border border-border/50">
      <div className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-accent" />
        {t('specSummary.workflowBreakdown')}
      </div>
      <div className="flex flex-wrap gap-2">
        {workflowEntries.map(([type, count]) => (
          <Badge key={type} variant="outline" className="text-xs">
            {type}: {count}
          </Badge>
        ))}
      </div>
    </div>
  );
}

function formatPercentage(rate: number): string {
  return `${(rate * 100).toFixed(1)}%`;
}

export function SpecSummaryCard({ analytics, isLoading = false }: SpecSummaryCardProps) {
  const { t } = useTranslation('analytics');

  const stats = useMemo(() => {
    if (!analytics) {
      return {
        totalSpecs: 0,
        completedSpecs: 0,
        inProgressSpecs: 0,
        completionRate: 0,
        averageQAIterations: 0,
        specsByType: {}
      };
    }

    const completionRate = analytics.total_specs > 0
      ? analytics.completed_specs / analytics.total_specs
      : 0;

    return {
      totalSpecs: analytics.total_specs,
      completedSpecs: analytics.completed_specs,
      inProgressSpecs: analytics.in_progress_specs,
      completionRate,
      averageQAIterations: analytics.average_qa_iterations,
      specsByType: analytics.specs_by_type || {}
    };
  }, [analytics]);

  const hasData = analytics && analytics.total_specs > 0;
  const completionVariant = getCompletionVariant(stats.completionRate);
  const qaVariant = getQAVariant(stats.averageQAIterations);

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-accent" />
            {t('specSummary.title')}
          </CardTitle>
          {hasData && (
            <Badge variant="outline" className="text-xs">
              {t('specSummary.specCount', { count: stats.totalSpecs })}
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Clock className="h-5 w-5 animate-spin mr-2" />
            {t('specSummary.loading')}
          </div>
        ) : hasData ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              <StatCard
                icon={BarChart3}
                label={t('specSummary.totalSpecs')}
                value={stats.totalSpecs}
                variant="default"
              />
              <StatCard
                icon={CheckCircle2}
                label={t('specSummary.completed')}
                value={stats.completedSpecs}
                subValue={formatPercentage(stats.completionRate)}
                variant={completionVariant}
              />
              <StatCard
                icon={Clock}
                label={t('specSummary.inProgress')}
                value={stats.inProgressSpecs}
                variant={stats.inProgressSpecs > 0 ? 'warning' : 'default'}
              />
              <StatCard
                icon={RefreshCw}
                label={t('specSummary.avgQAIterations')}
                value={stats.averageQAIterations.toFixed(1)}
                variant={qaVariant}
              />
            </div>
            <WorkflowBreakdown specsByType={stats.specsByType} />
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileText className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">{t('specSummary.noData')}</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              {t('specSummary.noDataHint')}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
