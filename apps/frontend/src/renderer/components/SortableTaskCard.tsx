import { memo, useCallback } from 'react';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { useTranslation } from 'react-i18next';
import { motion } from 'motion/react';
import { TaskCard } from './TaskCard';
import { Tooltip, TooltipContent, TooltipTrigger } from './ui/tooltip';
import { cn } from '../lib/utils';
import type { Task, TaskStatus } from '../../shared/types';

interface SortableTaskCardProps {
  task: Task;
  onClick: () => void;
  onStatusChange?: (newStatus: TaskStatus) => unknown;
  // Optional selection props for multi-selection in Human Review column
  isSelectable?: boolean;
  isSelected?: boolean;
  onToggleSelect?: () => void;
  // Drag disabled when auto-sort is active
  isDragDisabled?: boolean;
}

// Custom comparator - only re-render when task or onClick actually changed
function sortableTaskCardPropsAreEqual(
  prevProps: SortableTaskCardProps,
  nextProps: SortableTaskCardProps
): boolean {
  // TaskCard has its own memo, so we just need to check reference equality
  // for the task object and onClick handler
  return (
    prevProps.task === nextProps.task &&
    prevProps.onClick === nextProps.onClick &&
    prevProps.onStatusChange === nextProps.onStatusChange &&
    prevProps.isSelectable === nextProps.isSelectable &&
    prevProps.isSelected === nextProps.isSelected &&
    prevProps.onToggleSelect === nextProps.onToggleSelect &&
    prevProps.isDragDisabled === nextProps.isDragDisabled
  );
}

export const SortableTaskCard = memo(function SortableTaskCard({ task, onClick, onStatusChange, isSelectable, isSelected, onToggleSelect, isDragDisabled }: SortableTaskCardProps) {
  const { t } = useTranslation(['tasks']);
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
    isOver
  } = useSortable({
    id: task.id,
    disabled: isDragDisabled
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    // Prevent z-index stacking issues during drag
    zIndex: isDragging ? 50 : undefined
  };

  // Memoize onClick to prevent unnecessary TaskCard re-renders
  const handleClick = useCallback(() => {
    onClick();
  }, [onClick]);

  const cardContent = (
    <motion.div
      ref={setNodeRef}
      style={style}
      className={cn(
        !isDragDisabled && 'touch-none',
        isDragDisabled && 'cursor-not-allowed',
        isOver && !isDragging && 'ring-2 ring-primary/30 ring-offset-2 ring-offset-background rounded-xl'
      )}
      animate={{
        scale: isDragging ? 1.05 : 1,
        opacity: isDragging ? 0.8 : 1,
        boxShadow: isDragging
          ? '0 10px 40px -10px rgba(0, 0, 0, 0.3), 0 0 0 1px rgba(0, 0, 0, 0.05)'
          : '0 0 0 0 rgba(0, 0, 0, 0)',
      }}
      transition={{
        type: 'spring',
        stiffness: 300,
        damping: 25,
        mass: 0.5,
      }}
      {...attributes}
      {...(isDragDisabled ? {} : listeners)}
    >
      <TaskCard
        task={task}
        onClick={handleClick}
        onStatusChange={onStatusChange}
        isSelectable={isSelectable}
        isSelected={isSelected}
        onToggleSelect={onToggleSelect}
      />
    </motion.div>
  );

  // Wrap in tooltip when drag is disabled
  if (isDragDisabled) {
    return (
      <Tooltip delayDuration={200}>
        <TooltipTrigger asChild>
          {cardContent}
        </TooltipTrigger>
        <TooltipContent>
          {t('kanban.dragDisabledAutoSort')}
        </TooltipContent>
      </Tooltip>
    );
  }

  return cardContent;
}, sortableTaskCardPropsAreEqual);
