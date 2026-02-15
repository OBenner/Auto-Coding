/**
 * SessionComparison Component
 *
 * Side-by-side comparison view for analyzing two sessions.
 * Displays metrics, common/unique subtasks, tool usage, and decision points.
 */

import { useState, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import {
  ArrowLeft,
  Clock,
  CheckCircle2,
  TrendingUp,
  Wrench,
  Lightbulb,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '../ui/card';
import type {
  SessionComparisonData,
  SessionApproachComparison,
  SessionMetadata,
} from '../../../shared/types';

interface SessionComparisonProps {
  /** Comparison data between sessions */
  comparisonData: SessionComparisonData;
  /** Optional detailed approach comparison */
  approachComparison?: SessionApproachComparison;
  /** Callback to navigate back to list */
  onBack?: () => void;
  /** Callback to select a session for detailed view */
  onSelectSession?: (sessionId: string) => void;
}

/**
 * Format duration for display (seconds to human-readable)
 */
function formatDuration(seconds: number | null): string {
  if (seconds === null) return '—';
  if (seconds < 60) return `${seconds}s`;
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }
  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
}

/**
 * Get status badge variant
 */
function getStatusBadgeVariant(status: string): 'success' | 'warning' {
  return status === 'completed' ? 'success' : 'warning';
}

/**
 * Main SessionComparison component
 */
export function SessionComparison({
  comparisonData,
  approachComparison,
  onBack,
  onSelectSession,
}: SessionComparisonProps) {
  const { t } = useTranslation('session-replay');

  // Local state for expandable sections
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['metrics', 'subtasks', 'tools', 'decisions'])
  );

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

  const sessions = comparisonData.sessions;

  // Early return if sessions array doesn't have at least 2 entries
  if (!sessions || sessions.length < 2) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        <span className="text-sm">{t('sessionComparison.selectSessions')}</span>
      </div>
    );
  }

  const session1 = sessions[0];
  const session2 = sessions[1];

  const isMetricsExpanded = expandedSections.has('metrics');
  const isSubtasksExpanded = expandedSections.has('subtasks');
  const isToolsExpanded = expandedSections.has('tools');
  const isDecisionsExpanded = expandedSections.has('decisions');

  // Calculate efficiency difference
  const efficiency1 = comparisonData.metrics.efficiency?.[session1.session_id];
  const efficiency2 = comparisonData.metrics.efficiency?.[session2.session_id];
  const efficiencyDiff =
    efficiency1 !== null && efficiency1 !== undefined &&
    efficiency2 !== null && efficiency2 !== undefined
      ? efficiency2 - efficiency1
      : null;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-border/40 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="flex items-center gap-3">
          {onBack && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onBack}
              className="h-8 w-8 p-0"
              aria-label={t('sessionComparison.back')}
            >
              <ArrowLeft className="h-4 w-4" />
            </Button>
          )}
          <div className="flex-1">
            <h2 className="text-sm font-medium">{t('sessionComparison.title')}</h2>
            <div className="text-xs text-muted-foreground mt-0.5">
              {t('sessionComparison.comparing')}: {t('sessionComparison.session')} #{session1.session_number} {t('sessionComparison.vs')} #{session2.session_number}
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
        {/* Metrics Comparison */}
        <Card>
          <CardHeader
            className="cursor-pointer select-none"
            onClick={() => toggleSection('metrics')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <TrendingUp className="h-4 w-4" />
                {t('sessionComparison.metrics')}
              </CardTitle>
              {isMetricsExpanded ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
          {isMetricsExpanded && (
            <CardContent className="space-y-3">
              {/* Duration */}
              <div className="grid grid-cols-3 gap-3">
                <div className="text-sm text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3.5 w-3.5" />
                  {t('sessionComparison.duration')}
                </div>
                <div className="text-sm font-medium text-center">
                  {formatDuration(comparisonData.metrics?.durations?.[session1.session_id] ?? null)}
                </div>
                <div className="text-sm font-medium text-center">
                  {formatDuration(comparisonData.metrics?.durations?.[session2.session_id] ?? null)}
                </div>
              </div>

              {/* Subtasks */}
              <div className="grid grid-cols-3 gap-3">
                <div className="text-sm text-muted-foreground">
                  {t('sessionComparison.subtasks')}
                </div>
                <div className="text-sm font-medium text-center">
                  {comparisonData.metrics?.subtask_counts?.[session1.session_id] ?? 0}
                </div>
                <div className="text-sm font-medium text-center">
                  {comparisonData.metrics?.subtask_counts?.[session2.session_id] ?? 0}
                </div>
              </div>

              {/* Efficiency */}
              {comparisonData.metrics.efficiency && (
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-sm text-muted-foreground">
                    {t('sessionComparison.efficiency')}
                  </div>
                  <div className="text-sm font-medium text-center">
                    {efficiency1 !== null ? `${efficiency1}/h` : '—'}
                  </div>
                  <div className="text-sm font-medium text-center">
                    {efficiency2 !== null ? `${efficiency2}/h` : '—'}
                    {efficiencyDiff !== null && efficiencyDiff !== 0 && (
                      <Badge
                        variant={efficiencyDiff > 0 ? 'success' : 'warning'}
                        className="ml-2 text-xs"
                      >
                        {efficiencyDiff > 0 ? '+' : ''}
                        {efficiencyDiff.toFixed(2)}
                      </Badge>
                    )}
                  </div>
                </div>
              )}

              {/* Completion Status */}
              <div className="grid grid-cols-3 gap-3">
                <div className="text-sm text-muted-foreground">
                  {t('sessionList.status')}
                </div>
                <div className="flex justify-center">
                  <Badge
                    variant={getStatusBadgeVariant(
                      comparisonData.metrics?.completion_status?.[session1.session_id] ?? 'in-progress'
                    )}
                    className="gap-1"
                  >
                    <span className="text-xs">
                      {t(
                        `sessionList.status${comparisonData.metrics?.completion_status?.[session1.session_id] === 'completed' ? 'Completed' : 'InProgress'}`
                      )}
                    </span>
                  </Badge>
                </div>
                <div className="flex justify-center">
                  <Badge
                    variant={getStatusBadgeVariant(
                      comparisonData.metrics?.completion_status?.[session2.session_id] ?? 'in-progress'
                    )}
                    className="gap-1"
                  >
                    <span className="text-xs">
                      {t(
                        `sessionList.status${comparisonData.metrics?.completion_status?.[session2.session_id] === 'completed' ? 'Completed' : 'InProgress'}`
                      )}
                    </span>
                  </Badge>
                </div>
              </div>
            </CardContent>
          )}
        </Card>

        {/* Subtasks Comparison */}
        <Card>
          <CardHeader
            className="cursor-pointer select-none"
            onClick={() => toggleSection('subtasks')}
          >
            <div className="flex items-center justify-between">
              <CardTitle className="text-sm flex items-center gap-2">
                <CheckCircle2 className="h-4 w-4" />
                {t('sessionComparison.subtasks')}
              </CardTitle>
              {isSubtasksExpanded ? (
                <ChevronUp className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              )}
            </div>
          </CardHeader>
          {isSubtasksExpanded && (
            <CardContent className="space-y-3">
              {/* Common Subtasks */}
              {comparisonData.common_subtasks.length > 0 && (
                <div>
                  <div className="text-xs text-muted-foreground mb-2">
                    {t('sessionComparison.commonSubtasks')}
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {comparisonData.common_subtasks.map((subtask) => (
                      <Badge
                        key={subtask}
                        variant="outline"
                        className="text-xs bg-primary/5"
                      >
                        {subtask}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}

              {/* Unique Subtasks */}
              <div className="grid grid-cols-2 gap-4">
                {/* Session 1 Unique */}
                {comparisonData.unique_subtasks[session1.session_id]?.length > 0 && (
                  <div>
                    <div className="text-xs text-muted-foreground mb-2">
                      {t('sessionComparison.uniqueToSession1')} (#{session1.session_number})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {comparisonData.unique_subtasks[session1.session_id].map((subtask) => (
                        <Badge
                          key={subtask}
                          variant="secondary"
                          className="text-xs"
                        >
                          {subtask}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}

                {/* Session 2 Unique */}
                {comparisonData.unique_subtasks[session2.session_id]?.length > 0 && (
                  <div>
                    <div className="text-xs text-muted-foreground mb-2">
                      {t('sessionComparison.uniqueToSession2')} (#{session2.session_number})
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {comparisonData.unique_subtasks[session2.session_id].map((subtask) => (
                        <Badge
                          key={subtask}
                          variant="secondary"
                          className="text-xs"
                        >
                          {subtask}
                        </Badge>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </CardContent>
          )}
        </Card>

        {/* Tool Usage Comparison */}
        {approachComparison?.tool_usage_comparison && Object.keys(approachComparison.tool_usage_comparison).length > 0 && (
          <Card>
            <CardHeader
              className="cursor-pointer select-none"
              onClick={() => toggleSection('tools')}
            >
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Wrench className="h-4 w-4" />
                  {t('sessionComparison.toolComparison')}
                </CardTitle>
                {isToolsExpanded ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            {isToolsExpanded && (
              <CardContent>
                <div className="space-y-2">
                  {Object.entries(approachComparison.tool_usage_comparison).map(([tool, usage]) => (
                    <div key={tool} className="grid grid-cols-3 gap-3 items-center">
                      <div className="text-sm">{tool}</div>
                      <div className="text-sm font-medium text-center">
                        {usage[session1.session_id] || 0}
                      </div>
                      <div className="text-sm font-medium text-center">
                        {usage[session2.session_id] || 0}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            )}
          </Card>
        )}

        {/* Decision Points Comparison */}
        {approachComparison?.decision_points && Object.keys(approachComparison.decision_points).length > 0 && (
          <Card>
            <CardHeader
              className="cursor-pointer select-none"
              onClick={() => toggleSection('decisions')}
            >
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm flex items-center gap-2">
                  <Lightbulb className="h-4 w-4" />
                  {t('sessionComparison.decisionComparison')}
                </CardTitle>
                {isDecisionsExpanded ? (
                  <ChevronUp className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                )}
              </div>
            </CardHeader>
            {isDecisionsExpanded && (
              <CardContent className="space-y-4">
                {/* Session 1 Decision Points */}
                <div>
                  <div className="text-xs text-muted-foreground mb-2">
                    {t('sessionComparison.session')} #{session1.session_number}
                  </div>
                  <div className="space-y-2">
                    {approachComparison.decision_points[session1.session_id]?.length > 0 ? (
                      approachComparison.decision_points[session1.session_id].map((dp) => (
                        <div
                          key={dp.id}
                          className="p-2 rounded border border-primary/20 bg-primary/5"
                        >
                          <div className="text-xs font-medium mb-1">{dp.reasoning?.slice(0, 80)}...</div>
                          <div className="text-xs text-muted-foreground">
                            {t('sessionPlayer.chosen')}: {dp.chosen_approach?.slice(0, 60)}...
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-muted-foreground italic">
                        {t('sessionList.noDecisionPoints')}
                      </div>
                    )}
                  </div>
                </div>

                <Separator />

                {/* Session 2 Decision Points */}
                <div>
                  <div className="text-xs text-muted-foreground mb-2">
                    {t('sessionComparison.session')} #{session2.session_number}
                  </div>
                  <div className="space-y-2">
                    {approachComparison.decision_points[session2.session_id]?.length > 0 ? (
                      approachComparison.decision_points[session2.session_id].map((dp) => (
                        <div
                          key={dp.id}
                          className="p-2 rounded border border-primary/20 bg-primary/5"
                        >
                          <div className="text-xs font-medium mb-1">{dp.reasoning?.slice(0, 80)}...</div>
                          <div className="text-xs text-muted-foreground">
                            {t('sessionPlayer.chosen')}: {dp.chosen_approach?.slice(0, 60)}...
                          </div>
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-muted-foreground italic">
                        {t('sessionList.noDecisionPoints')}
                      </div>
                    )}
                  </div>
                </div>
              </CardContent>
            )}
          </Card>
        )}

        {/* Session Details Buttons */}
        <div className="flex gap-3 pt-2">
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onSelectSession?.(String(session1.session_id))}
          >
            {t('sessionComparison.viewSession1')} #{session1.session_number}
          </Button>
          <Button
            variant="outline"
            size="sm"
            className="flex-1"
            onClick={() => onSelectSession?.(String(session2.session_id))}
          >
            {t('sessionComparison.viewSession2')} #{session2.session_number}
          </Button>
        </div>
      </div>
    </div>
  );
}
