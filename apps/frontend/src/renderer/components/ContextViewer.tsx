/**
 * Context Viewer
 *
 * Displays context window statistics, token usage, file prioritization,
 * and optimization metrics. Allows users to view and adjust which files
 * are prioritized in the AI context.
 */

import { useState, useEffect, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Database,
  FileText,
  TrendingUp,
  Zap,
  BarChart3,
  RefreshCw,
  Download,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';
import { useProjectStore } from '../stores/project-store';
import type {
  ContextStats,
  TokenBreakdown,
  PrioritizationScores,
  OptimizationReport
} from '../../preload/api/modules/context-viewer-api';

interface ContextViewerProps {
  specId?: string;
  task?: string;
}

export function ContextViewer({ specId, task }: ContextViewerProps) {
  const { t } = useTranslation(['common']);
  const projects = useProjectStore((state) => state.projects);
  const selectedProjectId = useProjectStore((state) => state.selectedProjectId);
  const selectedProject = projects.find((p) => p.id === selectedProjectId);

  const [stats, setStats] = useState<ContextStats | null>(null);
  const [breakdown, setBreakdown] = useState<TokenBreakdown | null>(null);
  const [, setScores] = useState<PrioritizationScores | null>(null);
  const [report, setReport] = useState<OptimizationReport | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['token-stats', 'files'])
  );

  // Load all context data
  const loadContextData = useCallback(async () => {
    if (!selectedProjectId || !selectedProject) {
      setError(t('errors:noProjectSelected'));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Load stats
      const statsResult = await window.electronAPI.getContextStats(
        selectedProjectId,
        specId
      );
      if (statsResult.success && statsResult.data) {
        setStats(statsResult.data);
      } else {
        setError(statsResult.error || t('errors.failedToLoadStats'));
      }

      // Load token breakdown
      const breakdownResult = await window.electronAPI.getTokenBreakdown(
        selectedProjectId,
        specId
      );
      if (breakdownResult.success && breakdownResult.data) {
        setBreakdown(breakdownResult.data);
      }

      // Load prioritization scores
      const scoresResult = await window.electronAPI.getPrioritizationScores(
        selectedProjectId,
        task
      );
      if (scoresResult.success && scoresResult.data) {
        setScores(scoresResult.data);
      }

      // Load optimization report (only if specId is provided)
      if (specId) {
        const reportResult = await window.electronAPI.getOptimizationReport(
          selectedProjectId,
          specId
        );
        if (reportResult.success && reportResult.data) {
          setReport(reportResult.data);
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('errors.unknownError'));
    } finally {
      setIsLoading(false);
    }
  }, [selectedProjectId, selectedProject, specId, task, t]);

  // Load data on mount and when dependencies change
  useEffect(() => {
    loadContextData();
  }, [loadContextData]);

  // Toggle section expansion
  const toggleSection = useCallback((section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  // Export context snapshot
  const handleExport = useCallback(async () => {
    if (!selectedProjectId || !specId) return;

    try {
      const result = await window.electronAPI.exportContextSnapshot(
        selectedProjectId,
        specId
      );
      if (result.success && result.data) {
        // Download the snapshot as JSON
        const blob = new Blob([JSON.stringify(result.data, null, 2)], {
          type: 'application/json'
        });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `context-snapshot-${specId}-${new Date().toISOString()}.json`;
        a.click();
        URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error('Failed to export snapshot:', err);
    }
  }, [selectedProjectId, specId]);

  const isExpanded = (section: string) => expandedSections.has(section);

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="border-b border-border p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-muted">
              <Database className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <h1 className="text-xl font-semibold text-foreground">
                {t('common:contextViewer.title')}
              </h1>
              <p className="text-sm text-muted-foreground">
                {t('common:contextViewer.description')}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadContextData}
              disabled={isLoading}
            >
              <RefreshCw className={cn('mr-2 h-4 w-4', isLoading && 'animate-spin')} />
              {t('common:actions.refresh')}
            </Button>
            {specId && (
              <Button
                variant="outline"
                size="sm"
                onClick={handleExport}
              >
                <Download className="mr-2 h-4 w-4" />
                {t('common:actions.export')}
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Error state */}
          {error && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4">
              <p className="text-sm text-destructive">{error}</p>
            </div>
          )}

          {/* Loading state */}
          {isLoading && !stats && (
            <div className="text-center py-8">
              <RefreshCw className="h-8 w-8 animate-spin mx-auto mb-3 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">
                {t('common:loading')}
              </p>
            </div>
          )}

          {/* Token Statistics */}
          {stats && (
            <Card>
              <button
                type="button"
                onClick={() => toggleSection('token-stats')}
                className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <BarChart3 className="h-4 w-4 text-muted-foreground" />
                  <h3 className="font-medium text-foreground">
                    {t('common:contextViewer.tokenStats')}
                  </h3>
                </div>
                {isExpanded('token-stats') ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>

              {isExpanded('token-stats') && (
                <CardContent className="pt-0">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    {/* Total Budget */}
                    <div className="rounded-lg border border-border bg-muted/30 p-4">
                      <div className="text-sm text-muted-foreground mb-1">
                        {t('common:contextViewer.totalBudget')}
                      </div>
                      <div className="text-2xl font-semibold text-foreground">
                        {stats.token_stats.total_budget.toLocaleString()}
                      </div>
                    </div>

                    {/* Used */}
                    <div className="rounded-lg border border-border bg-muted/30 p-4">
                      <div className="text-sm text-muted-foreground mb-1">
                        {t('common:contextViewer.used')}
                      </div>
                      <div className="text-2xl font-semibold text-foreground">
                        {stats.token_stats.used.toLocaleString()}
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">
                        {stats.token_stats.utilization_percent.toFixed(1)}%
                      </div>
                    </div>

                    {/* Remaining */}
                    <div className="rounded-lg border border-border bg-muted/30 p-4">
                      <div className="text-sm text-muted-foreground mb-1">
                        {t('common:contextViewer.remaining')}
                      </div>
                      <div className="text-2xl font-semibold text-foreground">
                        {stats.token_stats.remaining.toLocaleString()}
                      </div>
                    </div>
                  </div>

                  {/* Token usage bar */}
                  <div className="mt-4">
                    <div className="flex items-center justify-between text-xs text-muted-foreground mb-2">
                      <span>{t('common:contextViewer.utilization')}</span>
                      <span>{stats.token_stats.utilization_percent.toFixed(1)}%</span>
                    </div>
                    <div className="h-2 bg-muted rounded-full overflow-hidden">
                      <div
                        className={cn(
                          'h-full transition-all',
                          stats.token_stats.utilization_percent > 90
                            ? 'bg-destructive'
                            : stats.token_stats.utilization_percent > 70
                            ? 'bg-warning'
                            : 'bg-primary'
                        )}
                        style={{ width: `${stats.token_stats.utilization_percent}%` }}
                      />
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Session Statistics */}
          {stats && stats.session_stats.current_turn > 0 && (
            <Card>
              <button
                type="button"
                onClick={() => toggleSection('session-stats')}
                className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <TrendingUp className="h-4 w-4 text-muted-foreground" />
                  <h3 className="font-medium text-foreground">
                    {t('common:contextViewer.sessionStats')}
                  </h3>
                </div>
                {isExpanded('session-stats') ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>

              {isExpanded('session-stats') && (
                <CardContent className="pt-0">
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">
                        {t('common:contextViewer.currentTurn')}
                      </div>
                      <div className="text-lg font-semibold text-foreground">
                        {stats.session_stats.current_turn}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">
                        {t('common:contextViewer.totalTokensSent')}
                      </div>
                      <div className="text-lg font-semibold text-foreground">
                        {stats.session_stats.total_tokens_sent.toLocaleString()}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-muted-foreground mb-1">
                        {t('common:contextViewer.uniqueFilesSent')}
                      </div>
                      <div className="text-lg font-semibold text-foreground">
                        {stats.session_stats.unique_files_sent}
                      </div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Token Breakdown by File */}
          {breakdown && breakdown.total > 0 && (
            <Card>
              <button
                type="button"
                onClick={() => toggleSection('token-breakdown')}
                className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  <h3 className="font-medium text-foreground">
                    {t('common:contextViewer.tokenBreakdown')}
                  </h3>
                  <Badge variant="secondary" className="text-xs">
                    {Object.keys(breakdown.by_file).length} {t('common:contextViewer.files')}
                  </Badge>
                </div>
                {isExpanded('token-breakdown') ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>

              {isExpanded('token-breakdown') && (
                <CardContent className="pt-0">
                  <div className="space-y-2">
                    {Object.entries(breakdown.by_file)
                      .sort(([, a], [, b]) => b - a)
                      .slice(0, 20)
                      .map(([file, tokens]) => (
                        <div
                          key={file}
                          className="flex items-center justify-between py-2 px-3 rounded-lg bg-muted/30"
                        >
                          <div className="flex items-center gap-2 flex-1 min-w-0">
                            <FileText className="h-4 w-4 text-muted-foreground shrink-0" />
                            <span className="text-sm truncate" title={file}>
                              {file}
                            </span>
                          </div>
                          <div className="flex items-center gap-3">
                            <Badge variant="outline" className="text-xs">
                              {tokens.toLocaleString()} tokens
                            </Badge>
                            <div className="text-xs text-muted-foreground w-16 text-right">
                              {((tokens / breakdown.total) * 100).toFixed(1)}%
                            </div>
                          </div>
                        </div>
                      ))}
                  </div>

                  {/* Category breakdown */}
                  <div className="mt-4 pt-4 border-t border-border">
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                      <div>
                        <div className="text-muted-foreground">
                          {t('common:contextViewer.toModify')}
                        </div>
                        <div className="font-medium">
                          {breakdown.by_category.to_modify.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">
                          {t('common:contextViewer.toReference')}
                        </div>
                        <div className="font-medium">
                          {breakdown.by_category.to_reference.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">
                          {t('common:contextViewer.patterns')}
                        </div>
                        <div className="font-medium">
                          {breakdown.by_category.patterns.toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">
                          {t('common:contextViewer.summaries')}
                        </div>
                        <div className="font-medium">
                          {breakdown.by_category.summaries.toLocaleString()}
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Optimization Report */}
          {report && (
            <Card>
              <button
                type="button"
                onClick={() => toggleSection('optimization')}
                className="w-full flex items-center justify-between p-4 hover:bg-muted/50 transition-colors"
              >
                <div className="flex items-center gap-2">
                  <Zap className="h-4 w-4 text-muted-foreground" />
                  <h3 className="font-medium text-foreground">
                    {t('common:contextViewer.optimization')}
                  </h3>
                </div>
                {isExpanded('optimization') ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </button>

              {isExpanded('optimization') && (
                <CardContent className="pt-0">
                  <div className="space-y-4">
                    {/* Overall metrics */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="rounded-lg border border-border bg-muted/30 p-4">
                        <div className="text-sm text-muted-foreground mb-1">
                          {t('common:contextViewer.tokensSaved')}
                        </div>
                        <div className="text-2xl font-semibold text-emerald-600">
                          {report.overall.total_tokens_saved.toLocaleString()}
                        </div>
                      </div>
                      <div className="rounded-lg border border-border bg-muted/30 p-4">
                        <div className="text-sm text-muted-foreground mb-1">
                          {t('common:contextViewer.optimizationPercent')}
                        </div>
                        <div className="text-2xl font-semibold text-foreground">
                          {report.overall.optimization_percent.toFixed(1)}%
                        </div>
                      </div>
                      <div className="rounded-lg border border-border bg-muted/30 p-4">
                        <div className="text-sm text-muted-foreground mb-1">
                          {t('common:contextViewer.targetPercent')}
                        </div>
                        <div className="text-2xl font-semibold text-muted-foreground">
                          {report.overall.target_percent}%
                        </div>
                      </div>
                    </div>

                    {/* Deduplication stats */}
                    <div className="rounded-lg border border-border bg-muted/20 p-4">
                      <h4 className="text-sm font-medium mb-3">
                        {t('common:contextViewer.deduplication')}
                      </h4>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
                        <div>
                          <div className="text-muted-foreground">
                            {t('common:contextViewer.filesProcessed')}
                          </div>
                          <div className="font-medium">
                            {report.deduplication.files_processed}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">
                            {t('common:contextViewer.duplicatesFound')}
                          </div>
                          <div className="font-medium">
                            {report.deduplication.duplicates_found}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">
                            {t('common:contextViewer.tokensSaved')}
                          </div>
                          <div className="font-medium text-emerald-600">
                            {report.deduplication.tokens_saved.toLocaleString()}
                          </div>
                        </div>
                        <div>
                          <div className="text-muted-foreground">
                            {t('common:contextViewer.savings')}
                          </div>
                          <div className="font-medium">
                            {report.deduplication.savings_percent.toFixed(1)}%
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </CardContent>
              )}
            </Card>
          )}

          {/* Empty state */}
          {!isLoading && !stats && !error && (
            <div className="text-center py-12">
              <Database className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <h3 className="text-lg font-medium text-foreground mb-2">
                {t('common:contextViewer.noData')}
              </h3>
              <p className="text-sm text-muted-foreground mb-4">
                {t('common:contextViewer.noDataDescription')}
              </p>
              <Button onClick={loadContextData}>
                {t('common:actions.load')}
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
