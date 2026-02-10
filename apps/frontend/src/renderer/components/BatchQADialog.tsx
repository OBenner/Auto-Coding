import { useState, useEffect, useCallback, useRef } from 'react';
import {
  CheckCircle2,
  Loader2,
  XCircle,
  AlertTriangle,
  MinusCircle,
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from './ui/dialog';
import { Button } from './ui/button';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import type { Task } from '../../shared/types';
import { useQuickActionsStore } from '../stores/quick-actions-store';
import { useProjectStore } from '../stores/project-store';

/**
 * Check if an error message indicates a task-related issue (no worktree, not started, etc.)
 * This is used to show 'skipped' status instead of 'error' for tasks that can't be QA'd.
 */
function isTaskNotReadyForQA(errorMsg: string): boolean {
  const lowerMsg = errorMsg.toLowerCase();
  return lowerMsg.includes('not started') ||
         lowerMsg.includes('no implementation') ||
         lowerMsg.includes('not found') ||
         lowerMsg.includes('worktree');
}

/**
 * Result for a single task in the batch QA run
 */
interface TaskQAResult {
  taskId: string;
  taskTitle: string;
  status: 'pending' | 'running' | 'success' | 'skipped' | 'error';
  error?: string;
  issuesFound?: number;
}

interface BatchQADialogProps {
  open: boolean;
  tasks: Task[];
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}

/**
 * Dialog for running QA validation on multiple tasks in bulk
 * Shows progress tracking and results per task
 */
export function BatchQADialog({
  open,
  tasks,
  onOpenChange,
  onComplete
}: BatchQADialogProps) {
  const { t } = useTranslation(['taskReview', 'common', 'tasks']);
  const addRecentAction = useQuickActionsStore((state) => state.addRecentAction);
  const selectedProjectId = useProjectStore((state) => (state.activeProjectId || state.selectedProjectId) ?? undefined);

  // Progress tracking
  const [step, setStep] = useState<'confirm' | 'running' | 'results'>('confirm');
  const [taskResults, setTaskResults] = useState<TaskQAResult[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const isCancelledRef = useRef(false);

  const prevOpenRef = useRef(open);

  // Only reset when transitioning closed→open (not on tasks array changes during async operation)
  useEffect(() => {
    const wasOpen = prevOpenRef.current;
    prevOpenRef.current = open;

    if (open && !wasOpen) {
      setStep('confirm');
      setCurrentIndex(0);
      isCancelledRef.current = false;
      setTaskResults(tasks.map(task => ({
        taskId: task.id,
        taskTitle: task.title,
        status: 'pending'
      })));
    }
  }, [open, tasks]);

  const handleRunQA = useCallback(async () => {
    setStep('running');
    isCancelledRef.current = false;

    const results: TaskQAResult[] = tasks.map(task => ({
      taskId: task.id,
      taskTitle: task.title,
      status: 'pending' as const
    }));
    setTaskResults(results);

    for (let i = 0; i < tasks.length; i++) {
      if (isCancelledRef.current) break;

      setCurrentIndex(i);

      setTaskResults(prev => prev.map((r, idx) =>
        idx === i ? { ...r, status: 'running' as const } : r
      ));

      try {
        // Call the batch QA IPC handler (will be implemented in subtask-2-4)
        const qaResult = await window.electronAPI?.batchRunQA?.(tasks[i].id);

        if (isCancelledRef.current) break;

        if (qaResult?.success) {
          setTaskResults(prev => prev.map((r, idx) =>
            idx === i ? {
              ...r,
              status: 'success' as const,
              issuesFound: qaResult.data?.issues?.length || 0
            } : r
          ));
        } else {
          const errorMsg = qaResult?.error || '';
          setTaskResults(prev => prev.map((r, idx) =>
            idx === i ? {
              ...r,
              status: isTaskNotReadyForQA(errorMsg) ? 'skipped' as const : 'error' as const,
              error: isTaskNotReadyForQA(errorMsg)
                ? t('taskReview:batchQA.notReady')
                : (qaResult?.error || t('taskReview:batchQA.unknownError'))
            } : r
          ));
        }
      } catch (err) {
        if (isCancelledRef.current) break;

        const errorMsg = err instanceof Error ? err.message : '';
        setTaskResults(prev => prev.map((r, idx) =>
          idx === i ? {
            ...r,
            status: isTaskNotReadyForQA(errorMsg) ? 'skipped' as const : 'error' as const,
            error: isTaskNotReadyForQA(errorMsg)
              ? t('taskReview:batchQA.notReady')
              : (err instanceof Error ? err.message : t('taskReview:batchQA.unknownError'))
          } : r
        ));
      }
    }

    if (!isCancelledRef.current) {
      // Add to recent actions when batch QA completes
      addRecentAction({
        type: 'batch_qa',
        label: 'Batch QA',
        itemCount: tasks.length,
        projectId: selectedProjectId
      });

      setStep('results');
    }
  }, [tasks, t, addRecentAction, selectedProjectId]);

  const handleClose = () => {
    isCancelledRef.current = true;
    if (step === 'results' && onComplete) {
      onComplete();
    }
    onOpenChange(false);
  };

  // Calculate progress
  const completedCount = taskResults.filter(r => r.status === 'success' || r.status === 'error' || r.status === 'skipped').length;
  const successCount = taskResults.filter(r => r.status === 'success').length;
  const errorCount = taskResults.filter(r => r.status === 'error').length;
  const skippedCount = taskResults.filter(r => r.status === 'skipped').length;
  const progress = tasks.length > 0 ? (completedCount / tasks.length) * 100 : 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CheckCircle2 className="h-5 w-5 text-primary" />
            {t('taskReview:batchQA.title')}
          </DialogTitle>
          <DialogDescription>
            {step === 'confirm' && t('taskReview:batchQA.description', { count: tasks.length })}
            {step === 'running' && t('taskReview:batchQA.running', { current: currentIndex + 1, total: tasks.length })}
            {step === 'results' && (skippedCount > 0
              ? t('taskReview:batchQA.resultsDescriptionWithSkipped', { success: successCount, skipped: skippedCount, failed: errorCount })
              : t('taskReview:batchQA.resultsDescription', { success: successCount, failed: errorCount })
            )}
          </DialogDescription>
        </DialogHeader>

        {/* Confirm Step */}
        {step === 'confirm' && (
          <div className="space-y-4">
            {/* Task List Preview */}
            <div className="space-y-2">
              <ScrollArea className="h-64 rounded-md border border-border p-2">
                <div className="space-y-1">
                  {tasks.map((task, idx) => (
                    <div
                      key={task.id}
                      className="flex items-center gap-2 text-sm py-2 px-3 rounded hover:bg-muted/50"
                    >
                      <span className="text-muted-foreground">{idx + 1}.</span>
                      <span className="truncate font-medium">{task.title}</span>
                      {task.qaReport?.status === 'passed' && (
                        <CheckCircle2 className="h-4 w-4 text-success ml-auto flex-shrink-0" />
                      )}
                      {task.qaReport?.status === 'failed' && (
                        <XCircle className="h-4 w-4 text-destructive ml-auto flex-shrink-0" />
                      )}
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                {t('common:buttons.cancel')}
              </Button>
              <Button onClick={handleRunQA} disabled={tasks.length === 0 || step !== 'confirm'}>
                <CheckCircle2 className="mr-2 h-4 w-4" />
                {t('taskReview:batchQA.runAll', { count: tasks.length })}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Running Step */}
        {step === 'running' && (
          <div className="space-y-4">
            <div className="flex flex-col items-center justify-center py-4 space-y-4">
              <Loader2 className="h-10 w-10 text-primary animate-spin" />
              <div className="text-center space-y-1">
                <p className="text-sm font-medium">
                  {t('taskReview:batchQA.runningQA', { current: currentIndex + 1, total: tasks.length })}
                </p>
                <p className="text-xs text-muted-foreground truncate max-w-[400px]">
                  {tasks[currentIndex]?.title}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Progress value={progress} />
              <p className="text-xs text-center text-muted-foreground">
                {completedCount} / {tasks.length} {t('taskReview:batchQA.completed')}
              </p>
            </div>

            {/* Task Status List */}
            <ScrollArea className="h-40 rounded-md border border-border">
              <div className="p-2 space-y-1">
                {taskResults.map((result, idx) => (
                  <TaskQAResultRow key={result.taskId} result={result} index={idx} />
                ))}
              </div>
            </ScrollArea>
          </div>
        )}

        {/* Results Step */}
        {step === 'results' && (
          <div className="space-y-4">
            {/* Summary */}
            <div className="flex items-center justify-center gap-6 py-4">
              {successCount > 0 && (
                <div className="flex items-center gap-2 text-success">
                  <CheckCircle2 className="h-5 w-5" />
                  <span className="font-medium">{successCount} {t('taskReview:batchQA.succeeded')}</span>
                </div>
              )}
              {skippedCount > 0 && (
                <div className="flex items-center gap-2 text-muted-foreground">
                  <MinusCircle className="h-5 w-5" />
                  <span className="font-medium">{skippedCount} {t('taskReview:batchQA.skipped')}</span>
                </div>
              )}
              {errorCount > 0 && (
                <div className="flex items-center gap-2 text-destructive">
                  <XCircle className="h-5 w-5" />
                  <span className="font-medium">{errorCount} {t('taskReview:batchQA.failed')}</span>
                </div>
              )}
            </div>

            {/* Results List */}
            <ScrollArea className="h-56 rounded-md border border-border">
              <div className="p-2 space-y-2">
                {taskResults.map((result, idx) => (
                  <TaskQAResultRow
                    key={result.taskId}
                    result={result}
                    index={idx}
                    showDetails
                  />
                ))}
              </div>
            </ScrollArea>

            <DialogFooter>
              <Button onClick={handleClose}>
                {t('common:buttons.close')}
              </Button>
            </DialogFooter>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

/**
 * Individual task QA result row component
 */
interface TaskQAResultRowProps {
  result: TaskQAResult;
  index: number;
  showDetails?: boolean;
}

function TaskQAResultRow({ result, index, showDetails }: TaskQAResultRowProps) {
  const { t } = useTranslation(['taskReview']);

  const getStatusIcon = () => {
    switch (result.status) {
      case 'pending':
        return <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />;
      case 'running':
        return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case 'skipped':
        return <MinusCircle className="h-4 w-4 text-muted-foreground" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  return (
    <div
      className={`flex items-start gap-2 p-2 rounded text-sm ${
        result.status === 'running' ? 'bg-primary/5' : ''
      }`}
    >
      <div className="flex-shrink-0 mt-0.5">
        {getStatusIcon()}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-muted-foreground text-xs">{index + 1}.</span>
          <span className="truncate font-medium">{result.taskTitle}</span>
        </div>

        {showDetails && result.status === 'success' && (
          <div className="flex items-center gap-1 mt-1">
            <CheckCircle2 className="h-3 w-3 text-success flex-shrink-0" />
            <span className="text-xs text-success">
              {result.issuesFound === 0
                ? t('taskReview:batchQA.noIssues')
                : t('taskReview:batchQA.issuesFound', { count: result.issuesFound })
              }
            </span>
          </div>
        )}

        {showDetails && result.status === 'skipped' && result.error && (
          <div className="flex items-start gap-1 mt-1">
            <MinusCircle className="h-3 w-3 text-muted-foreground flex-shrink-0 mt-0.5" />
            <span className="text-xs text-muted-foreground">{result.error}</span>
          </div>
        )}

        {showDetails && result.status === 'error' && result.error && (
          <div className="flex items-start gap-1 mt-1">
            <AlertTriangle className="h-3 w-3 text-destructive flex-shrink-0 mt-0.5" />
            <span className="text-xs text-destructive">{result.error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
