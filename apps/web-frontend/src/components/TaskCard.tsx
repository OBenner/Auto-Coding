/**
 * TaskCard Component (Web Version)
 * Adapted from Electron frontend - simplified for web without IPC calls
 */

import { useMemo, memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Play, Target, Bug, Wrench, FileCode, Shield, Gauge, Palette, Clock } from 'lucide-react';
import { Card, CardContent } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { cn, formatRelativeTime, sanitizeMarkdownForDisplay } from '../lib/utils';
import {
  TASK_CATEGORY_LABELS,
  TASK_CATEGORY_COLORS,
  TASK_COMPLEXITY_COLORS,
  TASK_COMPLEXITY_LABELS,
  TASK_IMPACT_COLORS,
  TASK_IMPACT_LABELS,
  TASK_PRIORITY_COLORS,
  TASK_PRIORITY_LABELS,
  EXECUTION_PHASE_LABELS,
  EXECUTION_PHASE_BADGE_COLORS,
  JSON_ERROR_PREFIX,
  JSON_ERROR_TITLE_SUFFIX
} from '../shared/constants';
import type { Task, TaskCategory, TaskStatus } from '../shared/types';

// Category icon mapping
const CategoryIcon: Record<TaskCategory, typeof Target> = {
  feature: Target,
  bug_fix: Bug,
  refactoring: Wrench,
  documentation: FileCode,
  security: Shield,
  performance: Gauge,
  ui_ux: Palette,
  infrastructure: Wrench,
  testing: FileCode
};

interface TaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (newStatus: TaskStatus) => unknown;
  isSelectable?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
}

// Custom comparator for React.memo - only re-render when relevant task data changes
function taskCardPropsAreEqual(prevProps: TaskCardProps, nextProps: TaskCardProps): boolean {
  const prevTask = prevProps.task;
  const nextTask = nextProps.task;

  // Fast path: same reference
  if (
    prevTask === nextTask &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onStatusChange === nextProps.onStatusChange &&
    prevProps.isSelectable === nextProps.isSelectable &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onToggleSelect === nextProps.onToggleSelect
  ) {
    return true;
  }

  // Check selectable props
  if (
    prevProps.isSelectable !== nextProps.isSelectable ||
    prevProps.isSelected !== nextProps.isSelected
  ) {
    return false;
  }

  // Compare only the fields that affect rendering
  return (
    prevTask.id === nextTask.id &&
    prevTask.status === nextTask.status &&
    prevTask.title === nextTask.title &&
    prevTask.description === nextTask.description &&
    prevTask.updatedAt === nextTask.updatedAt &&
    prevTask.executionProgress?.phase === nextTask.executionProgress?.phase &&
    prevTask.executionProgress?.phaseProgress === nextTask.executionProgress?.phaseProgress &&
    prevTask.subtasks.length === nextTask.subtasks.length &&
    prevTask.metadata?.category === nextTask.metadata?.category &&
    prevTask.metadata?.complexity === nextTask.metadata?.complexity &&
    prevTask.subtasks.every((s, i) => s.status === nextTask.subtasks[i]?.status)
  );
}

export const TaskCard = memo(function TaskCard({
  task,
  onClick,
}: TaskCardProps) {
  const { t } = useTranslation(['tasks', 'errors']);

  const isRunning = task.status === 'in_progress';
  const executionPhase = task.executionProgress?.phase;

  // Memoize expensive computations
  const sanitizedDescription = useMemo(() => {
    if (!task.description) return null;
    // Check for JSON error marker and use i18n
    if (task.description.startsWith(JSON_ERROR_PREFIX)) {
      const errorMessage = task.description.slice(JSON_ERROR_PREFIX.length);
      const translatedDesc = t('errors:task.jsonError.description', { error: errorMessage, defaultValue: `Failed to parse task data: ${errorMessage}` });
      return sanitizeMarkdownForDisplay(translatedDesc, 120);
    }
    return sanitizeMarkdownForDisplay(task.description, 120);
  }, [task.description, t]);

  // Memoize title with JSON error suffix handling
  const displayTitle = useMemo(() => {
    if (task.title.endsWith(JSON_ERROR_TITLE_SUFFIX)) {
      const baseName = task.title.slice(0, -JSON_ERROR_TITLE_SUFFIX.length);
      return `${baseName} ${t('errors:task.jsonError.titleSuffix', { defaultValue: '(Parse Error)' })}`;
    }
    return task.title;
  }, [task.title, t]);

  // Memoize relative time
  const relativeTime = useMemo(
    () => formatRelativeTime(task.updatedAt),
    [task.updatedAt]
  );

  // Calculate subtask progress
  const completedSubtasks = task.subtasks.filter((s) => s.status === 'completed').length;
  const totalSubtasks = task.subtasks.length;
  const progress = totalSubtasks > 0 ? (completedSubtasks / totalSubtasks) * 100 : 0;

  // Get category icon and metadata
  const category = task.metadata?.category;
  const Icon = category ? CategoryIcon[category] : Target;

  return (
    <Card
      className={cn(
        'group cursor-pointer transition-all hover:shadow-md',
        isRunning && 'border-primary ring-2 ring-primary/20'
      )}
      onClick={onClick}
    >
      <CardContent className="p-4">
        {/* Header: Title and Status */}
        <div className="flex items-start justify-between gap-2 mb-2">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {category && (
              <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
            )}
            <h3 className="font-semibold text-sm truncate">{displayTitle}</h3>
          </div>
          {isRunning && (
            <Button variant="ghost" size="icon" className="h-6 w-6 shrink-0">
              <Play className="h-3 w-3" />
            </Button>
          )}
        </div>

        {/* Description */}
        {sanitizedDescription && (
          <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
            {sanitizedDescription}
          </p>
        )}

        {/* Metadata Badges */}
        <div className="flex flex-wrap gap-2 mb-3">
          {category && (
            <Badge variant="outline" className={cn('text-xs', TASK_CATEGORY_COLORS[category])}>
              {TASK_CATEGORY_LABELS[category]}
            </Badge>
          )}
          {task.metadata?.complexity && (
            <Badge variant="outline" className={cn('text-xs', TASK_COMPLEXITY_COLORS[task.metadata.complexity])}>
              {TASK_COMPLEXITY_LABELS[task.metadata.complexity]}
            </Badge>
          )}
          {task.metadata?.priority && (
            <Badge variant="outline" className={cn('text-xs', TASK_PRIORITY_COLORS[task.metadata.priority])}>
              {TASK_PRIORITY_LABELS[task.metadata.priority]}
            </Badge>
          )}
          {task.metadata?.impact && (
            <Badge variant="outline" className={cn('text-xs', TASK_IMPACT_COLORS[task.metadata.impact])}>
              {TASK_IMPACT_LABELS[task.metadata.impact]}
            </Badge>
          )}
        </div>

        {/* Execution Phase */}
        {executionPhase && executionPhase !== 'idle' && (
          <div className="mb-3">
            <Badge variant="outline" className={cn('text-xs', EXECUTION_PHASE_BADGE_COLORS[executionPhase])}>
              {EXECUTION_PHASE_LABELS[executionPhase]}
            </Badge>
          </div>
        )}

        {/* Progress Bar */}
        {totalSubtasks > 0 && (
          <div className="space-y-1 mb-3">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Progress</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-muted rounded-full overflow-hidden">
              <div
                className="h-full bg-primary transition-all duration-300"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Footer: Updated Time */}
        <div className="flex items-center gap-1 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>{relativeTime}</span>
        </div>
      </CardContent>
    </Card>
  );
}, taskCardPropsAreEqual);
