import { useMemo } from 'react';
import {
  Activity,
  CheckCircle2,
  Shield,
  Package,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import type { ProjectHealth, HealthStatus, TrendDirection } from '../../../shared/types/health';

const TEST_COVERAGE_BASELINE = 70;

interface HealthSummaryCardProps {
  health: ProjectHealth | null;
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

function getStatusBadgeVariant(status: HealthStatus): 'default' | 'success' | 'warning' | 'destructive' {
  switch (status) {
    case 'excellent':
      return 'success';
    case 'good':
      return 'default';
    case 'fair':
      return 'warning';
    case 'poor':
      return 'destructive';
    default:
      return 'default';
  }
}

function getStatusLabel(status: HealthStatus): string {
  return status.charAt(0).toUpperCase() + status.slice(1);
}

function formatPercentage(value: number): string {
  return `${value.toFixed(1)}%`;
}

function getTestCoverageVariant(coverage: number): 'default' | 'success' | 'warning' | 'error' {
  if (coverage >= 80) return 'success';
  if (coverage >= 60) return 'warning';
  return 'error';
}

function getCodeQualityVariant(score: number): 'default' | 'success' | 'warning' | 'error' {
  if (score >= 80) return 'success';
  if (score >= 60) return 'warning';
  return 'error';
}

function getSecurityVariant(criticalCount: number, highCount: number): 'default' | 'success' | 'warning' | 'error' {
  if (criticalCount > 0) return 'error';
  if (highCount > 0) return 'warning';
  return 'success';
}

function getDependencyVariant(freshnessScore: number): 'default' | 'success' | 'warning' | 'error' {
  if (freshnessScore >= 80) return 'success';
  if (freshnessScore >= 60) return 'warning';
  return 'error';
}

function getTrendFromDirection(direction: TrendDirection): 'up' | 'down' | 'neutral' {
  if (direction === 'improving') return 'up';
  if (direction === 'declining') return 'down';
  return 'neutral';
}

export function HealthSummaryCard({ health, isLoading = false }: HealthSummaryCardProps) {
  const stats = useMemo(() => {
    if (!health) {
      return {
        overallScore: 0,
        testCoverage: 0,
        codeQuality: 0,
        securityScore: 0,
        dependencyHealth: 0,
        testCoverageTrend: 'neutral' as 'up' | 'down' | 'neutral',
        criticalVulns: 0,
        highVulns: 0
      };
    }

    // Calculate security score (0-100, inverted from vulnerability count)
    const totalVulns = health.security.vulnerability_count;
    const securityScore = Math.max(0, 100 - (totalVulns * 5)); // Each vuln reduces score by 5

    return {
      overallScore: health.overall_score,
      testCoverage: health.test_coverage.percentage,
      codeQuality: health.code_quality.maintainability_index,
      securityScore,
      dependencyHealth: health.dependencies.freshness_score,
      testCoverageTrend: getTrendFromDirection(health.test_coverage.trend),
      criticalVulns: health.security.critical_count,
      highVulns: health.security.high_count
    };
  }, [health]);

  const hasData = health !== null;

  return (
    <Card className="bg-muted/30 border-border/50">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Activity className="h-5 w-5 text-accent" />
            Project Health Summary
          </CardTitle>
          {hasData && health && (
            <Badge variant={getStatusBadgeVariant(health.status)} className="text-xs">
              {getStatusLabel(health.status)} ({stats.overallScore}/100)
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Activity className="h-5 w-5 animate-spin mr-2" />
            Loading health data...
          </div>
        ) : !hasData ? (
          <div className="flex flex-col items-center justify-center py-8 text-center">
            <Activity className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">No health data available yet</p>
            <p className="text-xs text-muted-foreground/70 mt-1">
              Health metrics will appear here after analysis
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
              icon={CheckCircle2}
              label="Test Coverage"
              value={formatPercentage(stats.testCoverage)}
              variant={getTestCoverageVariant(stats.testCoverage)}
              trend={stats.testCoverageTrend}
              trendValue={stats.testCoverageTrend !== 'neutral' ? formatPercentage(Math.abs(stats.testCoverage - TEST_COVERAGE_BASELINE)) : undefined}
            />
            <StatCard
              icon={Activity}
              label="Code Quality"
              value={stats.codeQuality.toFixed(0)}
              variant={getCodeQualityVariant(stats.codeQuality)}
            />
            <StatCard
              icon={Shield}
              label="Security"
              value={stats.securityScore.toFixed(0)}
              variant={getSecurityVariant(stats.criticalVulns, stats.highVulns)}
            />
            <StatCard
              icon={Package}
              label="Dependencies"
              value={formatPercentage(stats.dependencyHealth)}
              variant={getDependencyVariant(stats.dependencyHealth)}
            />
          </div>
        )}
        {hasData && health && (stats.criticalVulns > 0 || stats.highVulns > 0) && (
          <div className="mt-4 p-3 rounded-lg bg-destructive/10 border border-destructive/20 flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-destructive mt-0.5 flex-shrink-0" />
            <div className="text-sm text-destructive">
              <span className="font-semibold">Security Alert:</span> {stats.criticalVulns} critical and {stats.highVulns} high severity vulnerabilities detected
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
