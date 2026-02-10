import { useState, useEffect, useCallback, useRef } from 'react';
import {
  Loader2,
  CheckCircle2,
  XCircle,
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
import { Label } from './ui/label';
import { Progress } from './ui/progress';
import { ScrollArea } from './ui/scroll-area';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from './ui/select';
import type { Task, TaskStatus } from '../../shared/types';
import { useQuickActionsStore } from '../stores/quick-actions-store';
import { useProjectStore } from '../stores/project-store';

/**
 * Result for a single task in the bulk status update
 */
interface TaskStatusResult {
  taskId: string;
  taskTitle: string;
  status: 'pending' | 'updating' | 'success' | 'error';
  error?: string;
}

interface BatchStatusUpdateDialogProps {
  open: boolean;
  tasks: Task[];
  onOpenChange: (open: boolean) => void;
  onComplete?: () => void;
}

/**
 * Dialog for updating status of multiple tasks in bulk
 * Shows progress tracking and results per task
 */
export function BatchStatusUpdateDialog({
  open,
  tasks,
  onOpenChange,
  onComplete
}: BatchStatusUpdateDialogProps) {
  const { t } = useTranslation(['tasks', 'common']);
  const addRecentAction = useQuickActionsStore((state) => state.addRecentAction);
  const selectedProjectId = useProjectStore((state) => state.activeProjectId || state.selectedProjectId);

  // Common options for all status updates
  const [newStatus, setNewStatus] = useState<TaskStatus | ''>('');

  // Progress tracking
  const [step, setStep] = useState<'options' | 'updating' | 'results'>('options');
  const [taskResults, setTaskResults] = useState<TaskStatusResult[]>([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const isCancelledRef = useRef(false);

  const prevOpenRef = useRef(open);

  // Only reset when transitioning closed→open (not on tasks array changes during async operation)
  useEffect(() => {
    const wasOpen = prevOpenRef.current;
    prevOpenRef.current = open;

    if (open && !wasOpen) {
      setNewStatus('');
      setStep('options');
      setCurrentIndex(0);
      isCancelledRef.current = false;
      setTaskResults(tasks.map(task => ({
        taskId: task.id,
        taskTitle: task.title,
        status: 'pending'
      })));
    }
  }, [open, tasks]);

  const handleStatusUpdate = useCallback(async () => {
    if (!newStatus) {
      return;
    }

    setStep('updating');
    isCancelledRef.current = false;

    const results: TaskStatusResult[] = tasks.map(task => ({
      taskId: task.id,
      taskTitle: task.title,
      status: 'pending' as const
    }));
    setTaskResults(results);

    for (let i = 0; i < tasks.length; i++) {
      if (isCancelledRef.current) break;

      setCurrentIndex(i);

      setTaskResults(prev => prev.map((r, idx) =>
        idx === i ? { ...r, status: 'updating' as const } : r
      ));

      try {
        const updateResult = await window.electronAPI?.updateTaskStatus(tasks[i].id, newStatus);

        if (isCancelledRef.current) break;

        if (updateResult?.success) {
          setTaskResults(prev => prev.map((r, idx) =>
            idx === i ? {
              ...r,
              status: 'success' as const
            } : r
          ));
        } else {
          setTaskResults(prev => prev.map((r, idx) =>
            idx === i ? {
              ...r,
              status: 'error' as const,
              error: updateResult?.error || t('tasks:batchStatusUpdate.errors.unknown')
            } : r
          ));
        }
      } catch (err) {
        if (isCancelledRef.current) break;

        setTaskResults(prev => prev.map((r, idx) =>
          idx === i ? {
            ...r,
            status: 'error' as const,
            error: err instanceof Error ? err.message : t('tasks:batchStatusUpdate.errors.unknown')
          } : r
        ));
      }
    }

    if (!isCancelledRef.current) {
      // Add to recent actions when batch status update completes
      addRecentAction({
        type: 'batch_status_update',
        label: 'Batch Status Update',
        itemCount: tasks.length,
        targetStatus: newStatus,
        projectId: selectedProjectId
      });

      setStep('results');
    }
  }, [tasks, newStatus, t, addRecentAction, selectedProjectId]);

  const handleClose = () => {
    isCancelledRef.current = true;
    if (step === 'results' && onComplete) {
      onComplete();
    }
    onOpenChange(false);
  };

  // Calculate progress
  const completedCount = taskResults.filter(r => r.status === 'success' || r.status === 'error').length;
  const successCount = taskResults.filter(r => r.status === 'success').length;
  const errorCount = taskResults.filter(r => r.status === 'error').length;
  const progress = tasks.length > 0 ? (completedCount / tasks.length) * 100 : 0;

  // Available status options (exclude 'error' as it's set automatically)
  const statusOptions: { value: TaskStatus; label: string }[] = [
    { value: 'backlog', label: t('tasks:status.backlog') },
    { value: 'queue', label: t('tasks:status.queue') },
    { value: 'in_progress', label: t('tasks:status.in_progress') },
    { value: 'ai_review', label: t('tasks:status.ai_review') },
    { value: 'human_review', label: t('tasks:status.human_review') },
    { value: 'done', label: t('tasks:status.done') },
    { value: 'pr_created', label: t('tasks:status.pr_created') }
  ];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {t('tasks:batchStatusUpdate.title')}
          </DialogTitle>
          <DialogDescription>
            {step === 'options' && t('tasks:batchStatusUpdate.description', { count: tasks.length })}
            {step === 'updating' && t('tasks:batchStatusUpdate.updating', { current: currentIndex + 1, total: tasks.length })}
            {step === 'results' && t('tasks:batchStatusUpdate.resultsDescription', { success: successCount, failed: errorCount })}
          </DialogDescription>
        </DialogHeader>

        {/* Options Step */}
        {step === 'options' && (
          <div className="space-y-4">
            {/* Task List Preview */}
            <div className="space-y-2">
              <Label>{t('tasks:batchStatusUpdate.tasksToUpdate')}</Label>
              <ScrollArea className="h-32 rounded-md border border-border p-2">
                <div className="space-y-1">
                  {tasks.map((task, idx) => (
                    <div
                      key={task.id}
                      className="flex items-center gap-2 text-sm py-1 px-2 rounded hover:bg-muted/50"
                    >
                      <span className="text-muted-foreground">{idx + 1}.</span>
                      <span className="truncate">{task.title}</span>
                    </div>
                  ))}
                </div>
              </ScrollArea>
            </div>

            {/* Status Selection */}
            <div className="space-y-4 pt-2">
              <div className="space-y-2">
                <Label htmlFor="batchStatus">{t('tasks:batchStatusUpdate.newStatus')}</Label>
                <Select value={newStatus} onValueChange={(value) => setNewStatus(value as TaskStatus)}>
                  <SelectTrigger id="batchStatus">
                    <SelectValue placeholder={t('tasks:batchStatusUpdate.selectStatus')} />
                  </SelectTrigger>
                  <SelectContent>
                    {statusOptions.map(option => (
                      <SelectItem key={option.value} value={option.value}>
                        {option.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                <p className="text-xs text-muted-foreground">
                  {t('tasks:batchStatusUpdate.statusHint')}
                </p>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={handleClose}>
                {t('common:buttons.cancel')}
              </Button>
              <Button onClick={handleStatusUpdate} disabled={tasks.length === 0 || !newStatus || step !== 'options'}>
                {t('tasks:batchStatusUpdate.updateAll', { count: tasks.length })}
              </Button>
            </DialogFooter>
          </div>
        )}

        {/* Updating Step */}
        {step === 'updating' && (
          <div className="space-y-4">
            <div className="flex flex-col items-center justify-center py-4 space-y-4">
              <Loader2 className="h-10 w-10 text-primary animate-spin" />
              <div className="text-center space-y-1">
                <p className="text-sm font-medium">
                  {t('tasks:batchStatusUpdate.updatingStatus', { current: currentIndex + 1, total: tasks.length })}
                </p>
                <p className="text-xs text-muted-foreground truncate max-w-[400px]">
                  {tasks[currentIndex]?.title}
                </p>
              </div>
            </div>

            <div className="space-y-2">
              <Progress value={progress} />
              <p className="text-xs text-center text-muted-foreground">
                {completedCount} / {tasks.length} {t('tasks:batchStatusUpdate.completed')}
              </p>
            </div>

            {/* Task Status List */}
            <ScrollArea className="h-40 rounded-md border border-border">
              <div className="p-2 space-y-1">
                {taskResults.map((result, idx) => (
                  <StatusResultRow key={result.taskId} result={result} index={idx} />
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
                  <span className="font-medium">{successCount} {t('tasks:batchStatusUpdate.succeeded')}</span>
                </div>
              )}
              {errorCount > 0 && (
                <div className="flex items-center gap-2 text-destructive">
                  <XCircle className="h-5 w-5" />
                  <span className="font-medium">{errorCount} {t('tasks:batchStatusUpdate.failed')}</span>
                </div>
              )}
            </div>

            {/* Results List */}
            <ScrollArea className="h-56 rounded-md border border-border">
              <div className="p-2 space-y-2">
                {taskResults.map((result, idx) => (
                  <StatusResultRow
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
 * Individual task result row component
 */
interface StatusResultRowProps {
  result: TaskStatusResult;
  index: number;
  showDetails?: boolean;
}

function StatusResultRow({ result, index, showDetails }: StatusResultRowProps) {
  const { t } = useTranslation(['tasks']);

  const getStatusIcon = () => {
    switch (result.status) {
      case 'pending':
        return <div className="h-4 w-4 rounded-full border-2 border-muted-foreground/30" />;
      case 'updating':
        return <Loader2 className="h-4 w-4 text-primary animate-spin" />;
      case 'success':
        return <CheckCircle2 className="h-4 w-4 text-success" />;
      case 'error':
        return <XCircle className="h-4 w-4 text-destructive" />;
    }
  };

  return (
    <div
      className={`flex items-start gap-2 p-2 rounded text-sm ${
        result.status === 'updating' ? 'bg-primary/5' : ''
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

        {showDetails && result.status === 'error' && result.error && (
          <div className="flex items-start gap-1 mt-1">
            <XCircle className="h-3 w-3 text-destructive flex-shrink-0 mt-0.5" />
            <span className="text-xs text-destructive">{result.error}</span>
          </div>
        )}
      </div>
    </div>
  );
}
