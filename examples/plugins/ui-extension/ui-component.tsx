/**
 * Project Statistics Dashboard Widget
 *
 * Example React component for UI plugin that displays project statistics.
 * Demonstrates:
 * - React hooks (useState, useEffect)
 * - IPC communication with backend
 * - Auto-refresh with intervals
 * - Error handling and loading states
 * - Tailwind CSS styling
 */

import { useEffect, useState } from 'react';
import { RefreshCw, TrendingUp, CheckCircle2, Clock, AlertCircle, XCircle } from 'lucide-react';

interface ProjectStats {
  totalSpecs: number;
  completedSpecs: number;
  pendingSpecs: number;
  inProgressSpecs: number;
  failedSpecs: number;
  successRate: number;
  lastBuildTime: string | null;
  averageBuildTime: string | null;
}

interface ProjectStatsWidgetProps {
  projectDir: string;
  refreshInterval?: number;
  showCharts?: boolean;
}

/**
 * Project Statistics Widget Component
 *
 * Displays project statistics in a dashboard card with auto-refresh capability.
 */
export function ProjectStatsWidget({
  projectDir,
  refreshInterval = 30000,
  showCharts = true
}: ProjectStatsWidgetProps) {
  const [stats, setStats] = useState<ProjectStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  /**
   * Fetch project statistics from backend via IPC
   */
  const fetchStats = async (showLoadingState = true) => {
    if (showLoadingState) {
      setIsLoading(true);
    }
    setError(null);

    try {
      // Call IPC handler registered in plugin.py
      const result = await window.electronAPI.invoke('ui-extension:get-stats', projectDir);

      if (result.success) {
        setStats(result.data);
        setLastRefresh(new Date());
      } else {
        setError(result.error || 'Failed to fetch statistics');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Manually refresh statistics (clears cache on backend)
   */
  const handleRefresh = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.invoke('ui-extension:refresh-stats', projectDir);

      if (result.success) {
        setStats(result.data);
        setLastRefresh(new Date());
      } else {
        setError(result.error || 'Failed to refresh statistics');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error occurred');
    } finally {
      setIsLoading(false);
    }
  };

  // Fetch stats on mount
  useEffect(() => {
    fetchStats();
  }, [projectDir]);

  // Auto-refresh at specified interval
  useEffect(() => {
    if (!refreshInterval) return;

    const interval = setInterval(() => {
      fetchStats(false); // Don't show loading spinner for auto-refresh
    }, refreshInterval);

    return () => clearInterval(interval);
  }, [refreshInterval, projectDir]);

  // Loading state
  if (isLoading && !stats) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex items-center justify-center h-48">
          <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-border bg-card p-6">
        <div className="flex flex-col items-center justify-center h-48 space-y-4">
          <AlertCircle className="h-12 w-12 text-destructive" />
          <div className="text-center">
            <p className="text-sm font-medium text-foreground">Failed to load statistics</p>
            <p className="text-xs text-muted-foreground mt-1">{error}</p>
            <button
              onClick={() => fetchStats()}
              className="mt-4 px-4 py-2 bg-primary text-primary-foreground rounded-md text-sm hover:bg-primary/90"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  // No stats available
  if (!stats) {
    return null;
  }

  return (
    <div className="rounded-lg border border-border bg-card p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <TrendingUp className="h-5 w-5 text-primary" />
          <h3 className="text-lg font-semibold text-foreground">Project Statistics</h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isLoading}
          className="p-2 hover:bg-accent rounded-md transition-colors disabled:opacity-50"
          title="Refresh statistics"
        >
          <RefreshCw className={`h-4 w-4 text-muted-foreground ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {/* Total Specs */}
        <StatCard
          icon={<TrendingUp className="h-5 w-5" />}
          label="Total Specs"
          value={stats.totalSpecs}
          color="text-blue-500"
        />

        {/* Completed */}
        <StatCard
          icon={<CheckCircle2 className="h-5 w-5" />}
          label="Completed"
          value={stats.completedSpecs}
          color="text-green-500"
        />

        {/* In Progress */}
        <StatCard
          icon={<Clock className="h-5 w-5" />}
          label="In Progress"
          value={stats.inProgressSpecs}
          color="text-yellow-500"
        />

        {/* Failed */}
        <StatCard
          icon={<XCircle className="h-5 w-5" />}
          label="Failed"
          value={stats.failedSpecs}
          color="text-red-500"
        />
      </div>

      {/* Success Rate */}
      <div className="bg-accent/50 rounded-lg p-4 mb-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-muted-foreground">Success Rate</span>
          <span className="text-2xl font-bold text-foreground">{stats.successRate}%</span>
        </div>
        {/* Progress Bar */}
        <div className="w-full bg-muted rounded-full h-2">
          <div
            className="bg-green-500 h-2 rounded-full transition-all duration-300"
            style={{ width: `${stats.successRate}%` }}
          />
        </div>
      </div>

      {/* Last Refresh */}
      <div className="text-xs text-muted-foreground text-right">
        Last updated: {lastRefresh.toLocaleTimeString()}
      </div>
    </div>
  );
}

/**
 * Individual stat card component
 */
interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  color: string;
}

function StatCard({ icon, label, value, color }: StatCardProps) {
  return (
    <div className="bg-accent/30 rounded-lg p-4">
      <div className={`${color} mb-2`}>
        {icon}
      </div>
      <div className="text-2xl font-bold text-foreground mb-1">
        {value}
      </div>
      <div className="text-xs text-muted-foreground">
        {label}
      </div>
    </div>
  );
}

export default ProjectStatsWidget;
