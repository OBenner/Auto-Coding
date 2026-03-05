import { useMemo } from 'react';
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
  analytics: ProductivitySummary | null;
  isLoading?: boolean;
}

interface StatCardProps {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  subValue?: string;
  variant?: 'default' | 'success' | 'warning' | 'error';
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

interface WorkflowBreakdownProps {
  specsByType: Record<string, number>;
}

function WorkflowBreakdown({ specsByType }: WorkflowBreakdownProps) {
  const workflowEntries = Object.entries(specsByType).sort(([, a], [, b]) => b - a);

  if (workflowEntries.length === 0) {
    return null;
  }

  return (
    <div className="mt-4 p-4 rounded-lg bg-muted/30 border border-border/50">
      <div className="text-sm font-medium text-foreground mb-3 flex items-center gap-2">
        <GitBranch className="h-4 w-4 text-accent" />
        Workflow Type Breakdown
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

  // Determine completion rate variant
  const completionVariant = stats.completionRate >= 0.8
    ? 'success'
    : stats.completionRate >= 0.5
      ? 'warning'
      : 'default';

  // Determine QA iterations variant (lower is better)
  const qaVariant = stats.averageQAIterations <= 1
    ? 'success'
    : stats.averageQAIterations <= 2
      ? 'warning'
      : 'error';

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5 text-accent" />
            Spec Overview
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
            Loading spec data...
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <FileText className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">No specs tracked yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Spec statistics will appear here after creating your first spec
            </p>
          </div>
        ) : (
          <>
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
                subValue={formatPercentage(stats.completionRate)}
                variant={completionVariant}
              />
              <StatCard
                icon={Clock}
                label="In Progress"
                value={stats.inProgressSpecs}
                variant={stats.inProgressSpecs > 0 ? 'warning' : 'default'}
              />
              <StatCard
                icon={RefreshCw}
                label="Avg QA Iterations"
                value={stats.averageQAIterations.toFixed(1)}
                variant={qaVariant}
              />
            </div>
            <WorkflowBreakdown specsByType={stats.specsByType} />
          </>
        )}
      </CardContent>
    </Card>
  );
}
