import { useState, useEffect, useCallback } from 'react';
import { Activity, Loader2, RefreshCw, Shield, Package, Code2, TestTube2, Bug, TrendingUp } from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { useToast } from '../../hooks/use-toast';
import { HealthSummaryCard } from './HealthSummaryCard';
import { MetricCard } from './MetricCard';
import type { ProjectHealth } from '../../../shared/types/health';

interface HealthDashboardProps {
  projectId: string;
}

export function HealthDashboard({ projectId }: HealthDashboardProps) {
  const { toast } = useToast();

  // State
  const [health, setHealth] = useState<ProjectHealth | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Load health data
  const loadHealthData = useCallback(async (showRefreshToast = false) => {
    try {
      const loadingState = showRefreshToast ? setIsRefreshing : setIsLoading;
      loadingState(true);

      // Load comprehensive health data
      const result = await window.electronAPI.getProjectHealth(projectId);
      if (result.success && result.data) {
        setHealth(result.data);
      } else {
        setHealth(null);
        toast({
          title: 'Error',
          description: result.error || 'Failed to load project health data.',
          variant: 'destructive',
        });
      }

      if (showRefreshToast) {
        toast({
          title: 'Health Data Refreshed',
          description: 'Project health metrics have been updated.',
        });
      }
    } catch (error) {
      setHealth(null);
      toast({
        title: 'Error',
        description: 'Failed to load project health data.',
        variant: 'destructive',
      });
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [projectId, toast]);

  // Initial load
  useEffect(() => {
    loadHealthData();
  }, [loadHealthData]);

  // Handle refresh
  const handleRefresh = useCallback(() => {
    loadHealthData(true);
  }, [loadHealthData]);

  // Helper functions for formatting and variants
  const formatPercentage = (value: number): string => {
    return `${value.toFixed(1)}%`;
  };

  const formatScore = (value: number): string => {
    return value.toFixed(0);
  };

  const getTestCoverageVariant = (coverage: number): 'default' | 'success' | 'warning' | 'error' => {
    if (coverage >= 80) return 'success';
    if (coverage >= 60) return 'warning';
    return 'error';
  };

  const getCodeQualityVariant = (score: number): 'default' | 'success' | 'warning' | 'error' => {
    if (score >= 80) return 'success';
    if (score >= 60) return 'warning';
    return 'error';
  };

  const getSecurityVariant = (criticalCount: number, highCount: number): 'default' | 'success' | 'warning' | 'error' => {
    if (criticalCount > 0) return 'error';
    if (highCount > 0) return 'warning';
    return 'success';
  };

  const getDependencyVariant = (freshnessScore: number): 'default' | 'success' | 'warning' | 'error' => {
    if (freshnessScore >= 80) return 'success';
    if (freshnessScore >= 60) return 'warning';
    return 'error';
  };

  const getTrendFromDirection = (direction: string): 'up' | 'down' | 'neutral' => {
    if (direction === 'improving') return 'up';
    if (direction === 'declining') return 'down';
    return 'neutral';
  };

  if (isLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          <p className="text-sm text-muted-foreground">Loading project health...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Activity className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">Project Health</h1>
              <p className="text-sm text-muted-foreground">
                Monitor test coverage, code quality, security, and dependencies
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Summary Card */}
          <HealthSummaryCard health={health} isLoading={false} />

          {/* Detailed Metrics */}
          {health && (
            <>
              {/* Test Coverage Section */}
              <div>
                <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <TestTube2 className="h-5 w-5 text-accent" />
                  Test Coverage
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <MetricCard
                    title="Coverage"
                    value={formatPercentage(health.test_coverage.percentage)}
                    description={`${health.test_coverage.covered_lines} of ${health.test_coverage.total_lines} lines covered`}
                    icon={TestTube2}
                    variant={getTestCoverageVariant(health.test_coverage.percentage)}
                    trend={getTrendFromDirection(health.test_coverage.trend)}
                  />
                  <MetricCard
                    title="Test Count"
                    value={health.test_coverage.test_count}
                    description="Total number of tests"
                    icon={TestTube2}
                    variant="default"
                  />
                  <MetricCard
                    title="Covered Lines"
                    value={health.test_coverage.covered_lines.toLocaleString()}
                    description="Lines covered by tests"
                    icon={TestTube2}
                    variant="default"
                  />
                  <MetricCard
                    title="Total Lines"
                    value={health.test_coverage.total_lines.toLocaleString()}
                    description="Total testable lines"
                    icon={TestTube2}
                    variant="default"
                  />
                </div>
              </div>

              {/* Code Quality Section */}
              <div>
                <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <Code2 className="h-5 w-5 text-accent" />
                  Code Quality
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  <MetricCard
                    title="Maintainability Index"
                    value={formatScore(health.code_quality.maintainability_index)}
                    description="Overall maintainability score"
                    icon={Code2}
                    variant={getCodeQualityVariant(health.code_quality.maintainability_index)}
                  />
                  <MetricCard
                    title="Complexity Score"
                    value={formatScore(health.code_quality.complexity_score)}
                    description="Cyclomatic complexity"
                    icon={Code2}
                    variant="default"
                  />
                  <MetricCard
                    title="Duplication"
                    value={formatPercentage(health.code_quality.duplication_percentage)}
                    description="Percentage of duplicated code"
                    icon={Code2}
                    variant={health.code_quality.duplication_percentage > 10 ? 'warning' : 'success'}
                  />
                  <MetricCard
                    title="Issues"
                    value={health.code_quality.issues_count}
                    description="Code quality issues detected"
                    icon={Bug}
                    variant={health.code_quality.issues_count > 0 ? 'warning' : 'success'}
                  />
                </div>
              </div>

              {/* Security Section */}
              <div>
                <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <Shield className="h-5 w-5 text-accent" />
                  Security
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                  <MetricCard
                    title="Total Vulnerabilities"
                    value={health.security.vulnerability_count}
                    description={`Scanned on ${new Date(health.security.scan_date).toLocaleDateString()}`}
                    icon={Shield}
                    variant={getSecurityVariant(health.security.critical_count, health.security.high_count)}
                  />
                  <MetricCard
                    title="Critical"
                    value={health.security.critical_count}
                    description="Critical severity"
                    icon={Shield}
                    variant={health.security.critical_count > 0 ? 'error' : 'success'}
                  />
                  <MetricCard
                    title="High"
                    value={health.security.high_count}
                    description="High severity"
                    icon={Shield}
                    variant={health.security.high_count > 0 ? 'warning' : 'success'}
                  />
                  <MetricCard
                    title="Medium"
                    value={health.security.medium_count}
                    description="Medium severity"
                    icon={Shield}
                    variant="default"
                  />
                  <MetricCard
                    title="Low"
                    value={health.security.low_count}
                    description="Low severity"
                    icon={Shield}
                    variant="default"
                  />
                </div>
              </div>

              {/* Dependencies Section */}
              <div>
                <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <Package className="h-5 w-5 text-accent" />
                  Dependencies
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
                  <MetricCard
                    title="Freshness Score"
                    value={formatPercentage(health.dependencies.freshness_score)}
                    description="Overall dependency health"
                    icon={Package}
                    variant={getDependencyVariant(health.dependencies.freshness_score)}
                  />
                  <MetricCard
                    title="Total Dependencies"
                    value={health.dependencies.total_dependencies}
                    description="All project dependencies"
                    icon={Package}
                    variant="default"
                  />
                  <MetricCard
                    title="Outdated"
                    value={health.dependencies.outdated_count}
                    description="Dependencies with updates"
                    icon={Package}
                    variant={health.dependencies.outdated_count > 0 ? 'warning' : 'success'}
                  />
                  <MetricCard
                    title="Major Updates"
                    value={health.dependencies.major_updates_available}
                    description="Breaking changes"
                    icon={Package}
                    variant={health.dependencies.major_updates_available > 0 ? 'error' : 'success'}
                  />
                  <MetricCard
                    title="Minor/Patch Updates"
                    value={health.dependencies.minor_updates_available + health.dependencies.patch_updates_available}
                    description="Non-breaking updates"
                    icon={Package}
                    variant="default"
                  />
                </div>
              </div>

              {/* Agent Activity Section */}
              <div>
                <h2 className="text-lg font-semibold text-foreground mb-4 flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-accent" />
                  Agent Activity
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  <MetricCard
                    title="Total Iterations"
                    value={health.agent_activity.total_iterations}
                    description="Agent execution count"
                    icon={Activity}
                    variant="default"
                  />
                  <MetricCard
                    title="Success Rate"
                    value={formatPercentage(health.agent_activity.success_rate)}
                    description="Successful completions"
                    icon={Activity}
                    variant={health.agent_activity.success_rate >= 80 ? 'success' : health.agent_activity.success_rate >= 60 ? 'warning' : 'error'}
                  />
                  <MetricCard
                    title="Average Fix Time"
                    value={`${health.agent_activity.average_fix_time.toFixed(1)}m`}
                    description="Time to complete tasks"
                    icon={Activity}
                    variant="default"
                  />
                </div>
              </div>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
