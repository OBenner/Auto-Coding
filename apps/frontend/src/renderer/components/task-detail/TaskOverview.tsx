import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import {
  ListTree,
  CheckCircle2,
  Clock,
  AlertCircle,
  FileText,
  AlertTriangle,
  ChevronRight,
  ChevronDown,
  Loader2
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Separator } from '../ui/separator';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '../../lib/utils';
import type {
  Task,
  ImplementationPlan,
  Phase,
  SubtaskStatus,
  QAEscalation,
  GenericEditArtifactManifest
} from '../../../shared/types';
import { GenericEditArtifactsPanel } from './GenericEditArtifactsPanel';

interface TaskOverviewProps {
  task: Task;
}

export function TaskOverview({ task }: TaskOverviewProps) {
  const { t } = useTranslation(['tasks', 'common']);
  const [implementationPlan, setImplementationPlan] = useState<ImplementationPlan | null>(null);
  const [genericEditManifest, setGenericEditManifest] = useState<GenericEditArtifactManifest | null>(null);
  const [qaReport, setQAReport] = useState<string | null>(null);
  const [qaEscalation, setQAEscalation] = useState<QAEscalation | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [expandedPhases, setExpandedPhases] = useState<Set<number>>(new Set());

  useEffect(() => {
    loadTaskOverviewData();
  }, [task.id]);

  const loadTaskOverviewData = async () => {
    setIsLoading(true);
    setError(null);
    setImplementationPlan(null);
    setGenericEditManifest(null);
    setQAReport(null);
    setQAEscalation(null);
    try {
      // Load implementation plan
      const planResult = await window.electronAPI.getImplementationPlan(task.id);
      if (planResult.success && planResult.data) {
        setImplementationPlan(planResult.data);
        // Auto-expand phases with in-progress or failed subtasks
        const phasesToExpand = new Set<number>();
        planResult.data.phases.forEach((phase: Phase) => {
          const hasActiveWork = phase.subtasks.some(
            (st: { status: SubtaskStatus }) => st.status === 'in_progress' || st.status === 'failed'
          );
          if (hasActiveWork) {
            phasesToExpand.add(phase.phase);
          }
        });
        setExpandedPhases(phasesToExpand);
      }

      // Load Generic Edit v2 runtime artifacts if this task was executed by a generic provider.
      const manifestResult = await window.electronAPI.getGenericEditArtifactManifest(task.id);
      if (manifestResult.success && manifestResult.data) {
        setGenericEditManifest(manifestResult.data);
      }

      // Load QA report if available
      const qaResult = await window.electronAPI.getQAReport(task.id);
      if (qaResult.success && qaResult.data) {
        setQAReport(qaResult.data);
      }

      // Load QA escalation if available
      const escalationResult = await window.electronAPI.getQAEscalation(task.id);
      if (escalationResult.success && escalationResult.data) {
        setQAEscalation(escalationResult.data);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load task overview data');
    } finally {
      setIsLoading(false);
    }
  };

  const togglePhase = (phaseNumber: number) => {
    setExpandedPhases((prev) => {
      const next = new Set(prev);
      if (next.has(phaseNumber)) {
        next.delete(phaseNumber);
      } else {
        next.add(phaseNumber);
      }
      return next;
    });
  };

  const getSubtaskStatusBadge = (status: SubtaskStatus) => {
    switch (status) {
      case 'completed':
        return <Badge variant="success" className="text-xs">{t('common:status.completed')}</Badge>;
      case 'in_progress':
        return <Badge variant="info" className="text-xs status-running">{t('common:status.inProgress')}</Badge>;
      case 'failed':
        return <Badge variant="destructive" className="text-xs">{t('common:status.failed')}</Badge>;
      default:
        return <Badge variant="muted" className="text-xs">{t('common:status.pending')}</Badge>;
    }
  };

  const getPhaseStatusIcon = (phase: Phase) => {
    const allCompleted = phase.subtasks.every((st) => st.status === 'completed');
    const hasInProgress = phase.subtasks.some((st) => st.status === 'in_progress');
    const hasFailed = phase.subtasks.some((st) => st.status === 'failed');

    if (allCompleted) {
      return <CheckCircle2 className="h-4 w-4 text-success" />;
    }
    if (hasFailed) {
      return <AlertCircle className="h-4 w-4 text-destructive" />;
    }
    if (hasInProgress) {
      return <Loader2 className="h-4 w-4 text-info animate-spin" />;
    }
    return <Clock className="h-4 w-4 text-muted-foreground" />;
  };

  const getPhaseProgress = (phase: Phase) => {
    const completed = phase.subtasks.filter((st) => st.status === 'completed').length;
    const total = phase.subtasks.length;
    return { completed, total };
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-5">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 inline mr-2" />
          {error}
        </div>
      </div>
    );
  }

  return (
    <div className="p-5 space-y-5">
      {/* Implementation Plan Section */}
      {implementationPlan && (
        <div>
          <div className="section-divider mb-4">
            <ListTree className="h-3 w-3" />
            {t('tasks:overview.implementationPlan')}
          </div>

          {/* Plan Metadata */}
          {implementationPlan.description && (
            <p className="text-sm text-muted-foreground mb-4">{implementationPlan.description}</p>
          )}

          {/* Phases */}
          <div className="space-y-2">
            {implementationPlan.phases.map((phase) => {
              const { completed, total } = getPhaseProgress(phase);
              const isExpanded = expandedPhases.has(phase.phase);
              const isActive = phase.subtasks.some(
                (st) => st.status === 'in_progress' || st.status === 'failed'
              );

              return (
                <div
                  key={phase.phase}
                  className={cn(
                    'rounded-lg border transition-colors',
                    isActive && 'border-info/50 bg-info/5'
                  )}
                >
                  {/* Phase Header */}
                  <button
                    type="button"
                    onClick={() => togglePhase(phase.phase)}
                    className="w-full px-4 py-3 flex items-center gap-3 hover:bg-muted/50 transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 shrink-0 text-muted-foreground" />
                    ) : (
                      <ChevronRight className="h-4 w-4 shrink-0 text-muted-foreground" />
                    )}
                    {getPhaseStatusIcon(phase)}
                    <div className="flex-1 text-left min-w-0">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium">
                          {t('tasks:overview.phaseNumber', { number: phase.phase })}: {phase.name}
                        </span>
                        <Badge variant="outline" className="text-xs">
                          {phase.type}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {completed}/{total} {t('tasks:overview.subtasksCompleted')}
                      </div>
                    </div>
                  </button>

                  {/* Phase Subtasks */}
                  {isExpanded && (
                    <div className="px-4 pb-3 space-y-2">
                      <Separator className="mb-3" />
                      {phase.subtasks.map((subtask) => (
                        <div
                          key={subtask.id}
                          className={cn(
                            'flex items-start gap-3 p-2 rounded-md',
                            subtask.status === 'in_progress' && 'bg-info/10'
                          )}
                        >
                          <div className="mt-0.5">{getSubtaskStatusBadge(subtask.status)}</div>
                          <div className="flex-1 min-w-0">
                            <p className="text-sm">{subtask.description}</p>
                            {subtask.verification && (
                              <p className="text-xs text-muted-foreground mt-1">
                                {t('tasks:overview.verification')}: {subtask.verification.type}
                              </p>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Generic Edit Runtime Artifacts Section */}
      {genericEditManifest && (
        <>
          {implementationPlan && <Separator />}
          <GenericEditArtifactsPanel manifest={genericEditManifest} />
        </>
      )}

      {/* QA Report Section */}
      {qaReport && (
        <>
          <Separator />
          <div>
            <div className="section-divider mb-4">
              <FileText className="h-3 w-3" />
              {t('tasks:overview.qaReport')}
            </div>
            <div className="prose prose-sm dark:prose-invert max-w-none">
              <ReactMarkdown remarkPlugins={[remarkGfm]} skipHtml>{qaReport}</ReactMarkdown>
            </div>
          </div>
        </>
      )}

      {/* QA Escalation Section */}
      {qaEscalation && (
        <>
          <Separator />
          <div>
            <div className="section-divider mb-4">
              <AlertTriangle className="h-3 w-3" />
              {t('tasks:overview.qaEscalation')}
            </div>

            {/* Escalation Summary */}
            <div className="rounded-lg border border-warning/50 bg-warning/10 p-4 mb-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="h-5 w-5 text-warning shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-medium mb-2">{qaEscalation.reason}</p>
                  <div className="grid grid-cols-2 gap-3 text-xs">
                    <div>
                      <span className="text-muted-foreground">{t('tasks:overview.totalIterations')}:</span>{' '}
                      <span className="font-semibold">{qaEscalation.summary.totalIterations}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('tasks:overview.totalIssues')}:</span>{' '}
                      <span className="font-semibold">{qaEscalation.summary.totalIssues}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('tasks:overview.uniqueIssues')}:</span>{' '}
                      <span className="font-semibold">{qaEscalation.summary.uniqueIssues}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">{t('tasks:overview.fixSuccessRate')}:</span>{' '}
                      <span className="font-semibold">
                        {Math.round(qaEscalation.summary.fixSuccessRate * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recurring Issues */}
            {qaEscalation.recurringIssues.length > 0 && (
              <div className="mb-4">
                <h4 className="text-sm font-semibold mb-2">{t('tasks:overview.recurringIssues')}</h4>
                <div className="space-y-2">
                  {qaEscalation.recurringIssues.map((issue, idx) => (
                    <div key={idx} className="rounded-lg border p-3">
                      <div className="flex items-start gap-2 mb-1">
                        <Badge variant="destructive" className="text-xs">
                          {issue.occurrences}x
                        </Badge>
                        <p className="text-sm font-medium flex-1">{issue.title}</p>
                      </div>
                      {issue.file && (
                        <p className="text-xs text-muted-foreground mb-1">
                          {issue.file}
                          {issue.line && `:${issue.line}`}
                        </p>
                      )}
                      <p className="text-xs text-muted-foreground">{issue.description}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Common Issues */}
            {qaEscalation.mostCommonIssues.length > 0 && (
              <div>
                <h4 className="text-sm font-semibold mb-2">{t('tasks:overview.commonIssues')}</h4>
                <div className="space-y-2">
                  {qaEscalation.mostCommonIssues.map((issue, idx) => (
                    <div key={idx} className="flex items-center gap-2 p-2 rounded-md border">
                      <Badge variant="warning" className="text-xs">
                        {issue.occurrences}x
                      </Badge>
                      <span className="text-sm flex-1">{issue.title}</span>
                      {issue.file && (
                        <span className="text-xs text-muted-foreground">{issue.file}</span>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </>
      )}

      {/* No Data Available */}
      {!implementationPlan && !genericEditManifest && !qaReport && !qaEscalation && (
        <div className="text-center py-12 text-muted-foreground">
          <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
          <p className="text-sm">{t('tasks:overview.noDataAvailable')}</p>
        </div>
      )}
    </div>
  );
}
