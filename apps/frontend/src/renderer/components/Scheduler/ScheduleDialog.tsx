/**
 * ScheduleDialog - Dialog for scheduling builds
 *
 * Allows users to schedule task builds for specific times with priority and dependency management.
 * Follows the same dialog pattern as AddFeatureDialog for consistency.
 *
 * Features:
 * - Task/spec selection dropdown
 * - Scheduled time picker (supports ISO datetime and natural language)
 * - Priority selection
 * - Dependencies management (multi-select from other tasks)
 * - Form validation
 *
 * @example
 * ```tsx
 * <ScheduleDialog
 *   projectId={project.id}
 *   tasks={tasks}
 *   open={isScheduleDialogOpen}
 *   onOpenChange={setIsScheduleDialogOpen}
 *   onScheduled={(buildId) => console.log('Build scheduled:', buildId)}
 * />
 * ```
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Loader2, X, Clock, AlertCircle } from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle
} from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { Checkbox } from '../ui/checkbox';
import type { SchedulePriority } from '../../../shared/types/scheduler';
import type { Task } from '../../../shared/types/task';

/**
 * Props for the ScheduleDialog component
 */
interface ScheduleDialogProps {
  /** Project ID for the build */
  projectId: string;
  /** Available tasks to schedule */
  tasks: Task[];
  /** Whether the dialog is open */
  open: boolean;
  /** Callback when the dialog open state changes */
  onOpenChange: (open: boolean) => void;
  /** Optional callback when build is successfully scheduled, receives the new build ID */
  onScheduled?: (buildId: string) => void;
  /** Optional default task ID to pre-select */
  defaultTaskId?: string;
}

/**
 * Priority options with descriptions
 */
const PRIORITY_OPTIONS: Array<{
  value: SchedulePriority;
  labelKey: string;
  descriptionKey: string;
}> = [
  {
    value: 'critical',
    labelKey: 'scheduler:priority.critical',
    descriptionKey: 'scheduler:priority.criticalDescription'
  },
  {
    value: 'high',
    labelKey: 'scheduler:priority.high',
    descriptionKey: 'scheduler:priority.highDescription'
  },
  {
    value: 'normal',
    labelKey: 'scheduler:priority.normal',
    descriptionKey: 'scheduler:priority.normalDescription'
  },
  {
    value: 'low',
    labelKey: 'scheduler:priority.low',
    descriptionKey: 'scheduler:priority.lowDescription'
  },
  {
    value: 'background',
    labelKey: 'scheduler:priority.background',
    descriptionKey: 'scheduler:priority.backgroundDescription'
  }
];

/**
 * Quick time suggestions for scheduling
 */
const TIME_SUGGESTIONS: Array<{
  labelKey: string;
  value: string;
}> = [
  { labelKey: 'scheduler:time.now', value: 'now' },
  { labelKey: 'scheduler:time.tonight', value: 'tonight 10pm' },
  { labelKey: 'scheduler:time.tomorrowMorning', value: 'tomorrow 9am' },
  { labelKey: 'scheduler:time.tomorrowEvening', value: 'tomorrow 6pm' },
  { labelKey: 'scheduler:time.mondayMorning', value: 'Monday 9am' }
];

export function ScheduleDialog({
  projectId,
  tasks,
  open,
  onOpenChange,
  onScheduled,
  defaultTaskId
}: ScheduleDialogProps) {
  const { t } = useTranslation(['dialogs', 'common', 'tasks']);

  // Form state
  const [selectedTaskId, setSelectedTaskId] = useState<string>('');
  const [scheduledTime, setScheduledTime] = useState<string>('now');
  const [priority, setPriority] = useState<SchedulePriority>('normal');
  const [dependencies, setDependencies] = useState<string[]>([]);

  // UI state
  const [isScheduling, setIsScheduling] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when dialog opens/closes
  useEffect(() => {
    if (open) {
      setSelectedTaskId(defaultTaskId || (tasks.length > 0 ? tasks[0].id : ''));
      setScheduledTime('now');
      setPriority('normal');
      setDependencies([]);
      setError(null);
    }
  }, [open, defaultTaskId, tasks]);

  /**
   * Toggle dependency selection
   */
  const toggleDependency = (taskId: string) => {
    setDependencies((prev) =>
      prev.includes(taskId)
        ? prev.filter((id) => id !== taskId)
        : [...prev, taskId]
    );
  };

  /**
   * Set scheduled time from suggestion
   */
  const setTimeSuggestion = (value: string) => {
    setScheduledTime(value);
  };

  const handleSchedule = async () => {
    // Validate required fields
    if (!selectedTaskId) {
      setError(t('dialogs:scheduler.taskRequired'));
      return;
    }

    setIsScheduling(true);
    setError(null);

    try {
      // Parse natural language time if not 'now' or ISO format
      let scheduledTimeValue = scheduledTime;
      if (scheduledTime === 'now') {
        scheduledTimeValue = null; // null means immediate
      }

      // Schedule build via API
      const result = await window.electronAPI.scheduler.scheduleBuild(
        selectedTaskId,
        scheduledTimeValue,
        priority,
        dependencies
      );

      if (!result.success) {
        throw new Error(result.error || t('dialogs:scheduler.failedToSchedule'));
      }

      // Success - close dialog and notify parent
      onOpenChange(false);
      onScheduled?.(result.data.buildId);
    } catch (err) {
      setError(err instanceof Error ? err.message : t('dialogs:scheduler.failedToSchedule'));
    } finally {
      setIsScheduling(false);
    }
  };

  const handleClose = () => {
    if (!isScheduling) {
      onOpenChange(false);
    }
  };

  // Form validation
  const isValid = selectedTaskId.length > 0;

  // Get selected task for display
  const selectedTask = tasks.find((task) => task.id === selectedTaskId);

  // Filter available dependencies (exclude selected task and already dependent tasks)
  const availableDependencies = tasks.filter(
    (task) => task.id !== selectedTaskId && !dependencies.includes(task.id)
  );

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="sm:max-w-[600px] max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="text-foreground">{t('dialogs:scheduler.title')}</DialogTitle>
          <DialogDescription>
            {t('dialogs:scheduler.description')}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-5 py-4">
          {/* Task Selection (Required) */}
          <div className="space-y-2">
            <Label htmlFor="schedule-task" className="text-sm font-medium text-foreground">
              {t('dialogs:scheduler.taskLabel')} <span className="text-destructive">*</span>
            </Label>
            <Select
              value={selectedTaskId}
              onValueChange={setSelectedTaskId}
              disabled={isScheduling}
            >
              <SelectTrigger id="schedule-task" aria-required="true">
                <SelectValue placeholder={t('dialogs:scheduler.selectTask')} />
              </SelectTrigger>
              <SelectContent>
                {tasks.map((task) => (
                  <SelectItem key={task.id} value={task.id}>
                    <div className="flex flex-col">
                      <span className="font-medium">{task.title}</span>
                      <span className="text-xs text-muted-foreground">
                        {t('tasks:status.' + task.status)}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            {selectedTask && (
              <p className="text-xs text-muted-foreground">
                {selectedTask.description}
              </p>
            )}
          </div>

          {/* Scheduled Time */}
          <div className="space-y-2">
            <Label htmlFor="schedule-time" className="text-sm font-medium text-foreground">
              {t('dialogs:scheduler.scheduledTime')}
            </Label>
            <div className="flex gap-2">
              <Input
                id="schedule-time"
                placeholder={t('dialogs:scheduler.timePlaceholder')}
                value={scheduledTime}
                onChange={(e) => setScheduledTime(e.target.value)}
                disabled={isScheduling}
                className="flex-1"
              />
              <Clock className="h-4 w-4 mt-3 text-muted-foreground" />
            </div>

            {/* Quick Time Suggestions */}
            <div className="flex flex-wrap gap-2 mt-2">
              {TIME_SUGGESTIONS.map((suggestion) => (
                <Button
                  key={suggestion.value}
                  type="button"
                  variant={scheduledTime === suggestion.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => setTimeSuggestion(suggestion.value)}
                  disabled={isScheduling}
                  className="text-xs"
                >
                  {t(suggestion.labelKey)}
                </Button>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {t('dialogs:scheduler.timeHelp')}
            </p>
          </div>

          {/* Priority Selection */}
          <div className="space-y-2">
            <Label htmlFor="schedule-priority" className="text-sm font-medium text-foreground">
              {t('dialogs:scheduler.priorityLabel')}
            </Label>
            <Select
              value={priority}
              onValueChange={(value) => setPriority(value as SchedulePriority)}
              disabled={isScheduling}
            >
              <SelectTrigger id="schedule-priority">
                <SelectValue placeholder={t('dialogs:scheduler.selectPriority')} />
              </SelectTrigger>
              <SelectContent>
                {PRIORITY_OPTIONS.map(({ value, labelKey, descriptionKey }) => (
                  <SelectItem key={value} value={value}>
                    <div className="flex flex-col">
                      <span className="font-medium">{t(labelKey)}</span>
                      <span className="text-xs text-muted-foreground">
                        {t(descriptionKey)}
                      </span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Dependencies */}
          {availableDependencies.length > 0 && (
            <div className="space-y-2">
              <Label className="text-sm font-medium text-foreground">
                {t('dialogs:scheduler.dependenciesLabel')}{' '}
                <span className="text-muted-foreground font-normal">
                  ({t('dialogs:scheduler.optional')})
                </span>
              </Label>
              <div className="space-y-2 max-h-40 overflow-y-auto border rounded-md p-3">
                {availableDependencies.map((task) => (
                  <div key={task.id} className="flex items-start space-x-2">
                    <Checkbox
                      id={`dep-${task.id}`}
                      checked={dependencies.includes(task.id)}
                      onCheckedChange={() => toggleDependency(task.id)}
                      disabled={isScheduling}
                    />
                    <label
                      htmlFor={`dep-${task.id}`}
                      className="text-sm cursor-pointer flex-1"
                    >
                      <span className="font-medium">{task.title}</span>
                      <p className="text-xs text-muted-foreground">
                        {task.description.slice(0, 60)}
                        {task.description.length > 60 ? '...' : ''}
                      </p>
                    </label>
                  </div>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">
                {t('dialogs:scheduler.dependenciesHelp')}
              </p>
            </div>
          )}

          {/* Selected Dependencies Summary */}
          {dependencies.length > 0 && (
            <div className="flex items-start gap-2 rounded-lg bg-blue-500/10 border border-blue-500/30 p-3 text-sm">
              <AlertCircle className="h-4 w-4 mt-0.5 shrink-0 text-blue-500" />
              <div className="flex-1">
                <p className="font-medium text-blue-500 dark:text-blue-400">
                  {t('dialogs:scheduler.dependenciesSelected', { count: dependencies.length })}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {dependencies
                    .map((id) => tasks.find((t) => t.id === id)?.title)
                    .filter(Boolean)
                    .join(', ')}
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-destructive/10 border border-destructive/30 p-3 text-sm text-destructive" role="alert">
              <X className="h-4 w-4 mt-0.5 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={isScheduling}>
            {t('common:buttons.cancel')}
          </Button>
          <Button
            onClick={handleSchedule}
            disabled={isScheduling || !isValid}
          >
            {isScheduling ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                {t('dialogs:scheduler.scheduling')}
              </>
            ) : (
              t('dialogs:scheduler.scheduleBuild')
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
