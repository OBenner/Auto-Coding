import { motion } from 'motion/react';
import { useTranslation } from 'react-i18next';
import { memo, useRef, useState, useEffect } from 'react';
import { cn } from '../lib/utils';
import { Cpu, MemoryStick, Clock } from 'lucide-react';
import type { ExecutionProgress } from '../../shared/types';

interface ResourceUsageIndicatorProps {
  progress?: ExecutionProgress;
  isRunning?: boolean;
  className?: string;
}

/**
 * Resource usage threshold constants for color coding
 */
const THRESHOLD_CRITICAL = 90;  // Red: At or near limit
const THRESHOLD_WARNING = 75;   // Orange: High usage
const THRESHOLD_ELEVATED = 50;  // Yellow: Moderate usage
// Below 50 is considered normal (green)

/**
 * Get color class based on usage percentage
 */
const getColorClass = (percent: number): string => {
  if (percent >= THRESHOLD_CRITICAL) return 'bg-destructive';
  if (percent >= THRESHOLD_WARNING) return 'bg-orange-500';
  if (percent >= THRESHOLD_ELEVATED) return 'bg-warning';
  return 'bg-success';
};

/**
 * Get text color class based on usage percentage
 */
const getTextColorClass = (percent: number): string => {
  if (percent >= THRESHOLD_CRITICAL) return 'text-destructive';
  if (percent >= THRESHOLD_WARNING) return 'text-orange-500';
  if (percent >= THRESHOLD_ELEVATED) return 'text-warning';
  return 'text-success';
};

/**
 * Format elapsed time in human-readable format
 */
const formatElapsedTime = (seconds?: number): string => {
  if (!seconds || seconds < 1) return '—';

  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);

  if (hours > 0) {
    return `${hours}h ${minutes}m`;
  } else if (minutes > 0) {
    return `${minutes}m ${secs}s`;
  } else {
    return `${secs}s`;
  }
};

/**
 * Format memory in human-readable format
 */
const formatMemory = (mb?: number): string => {
  if (!mb || mb < 1) return '—';

  if (mb >= 1024) {
    return `${(mb / 1024).toFixed(1)} GB`;
  }
  return `${Math.round(mb)} MB`;
};

/**
 * Smart resource usage indicator showing CPU, memory, and elapsed time
 *
 * Features:
 * - Color-coded progress bars based on usage thresholds
 * - Real-time updates from ExecutionProgress
 * - Smooth animations with IntersectionObserver performance optimization
 * - Responsive layout with icons
 */
export const ResourceUsageIndicator = memo(function ResourceUsageIndicator({
  progress,
  isRunning = false,
  className,
}: ResourceUsageIndicatorProps) {
  const { t } = useTranslation('tasks');
  const containerRef = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(true);

  // Use IntersectionObserver to pause animations when component is not visible
  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 }
    );

    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  // Only animate when visible and running
  const shouldAnimate = isVisible && isRunning;

  // Extract resource metrics with defaults
  const cpuPercent = progress?.cpu_percent ?? 0;
  const memoryMb = progress?.memory_mb ?? 0;
  const memoryPercent = progress?.memory_percent ?? 0;
  const elapsedSeconds = progress?.elapsed_seconds ?? 0;

  // Determine which color classes to use
  const cpuColorClass = getColorClass(cpuPercent);
  const cpuTextColorClass = getTextColorClass(cpuPercent);
  const memoryColorClass = getColorClass(memoryPercent);
  const memoryTextColorClass = getTextColorClass(memoryPercent);

  return (
    <div ref={containerRef} className={cn('space-y-3', className)}>
      {/* CPU Usage */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Cpu className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {t('execution.resources.cpu', { defaultValue: 'CPU' })}
            </span>
          </div>
          <span className={cn('text-xs font-medium', cpuTextColorClass)}>
            {cpuPercent > 0 ? `${Math.round(cpuPercent)}%` : '—'}
          </span>
        </div>
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-border">
          <motion.div
            className={cn('h-full rounded-full', cpuColorClass)}
            initial={{ width: 0 }}
            animate={shouldAnimate ? { width: `${Math.min(cpuPercent, 100)}%` } : { width: `${Math.min(cpuPercent, 100)}%` }}
            transition={shouldAnimate ? { duration: 0.5, ease: 'easeOut' } : { duration: 0 }}
          />
        </div>
      </div>

      {/* Memory Usage */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <MemoryStick className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {t('execution.resources.memory', { defaultValue: 'Memory' })}
            </span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="text-xs text-muted-foreground">
              {formatMemory(memoryMb)}
            </span>
            <span className={cn('text-xs font-medium', memoryTextColorClass)}>
              {memoryPercent > 0 ? `${Math.round(memoryPercent)}%` : '—'}
            </span>
          </div>
        </div>
        <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-border">
          <motion.div
            className={cn('h-full rounded-full', memoryColorClass)}
            initial={{ width: 0 }}
            animate={shouldAnimate ? { width: `${Math.min(memoryPercent, 100)}%` } : { width: `${Math.min(memoryPercent, 100)}%` }}
            transition={shouldAnimate ? { duration: 0.5, ease: 'easeOut' } : { duration: 0 }}
          />
        </div>
      </div>

      {/* Elapsed Time */}
      <div className="space-y-1">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Clock className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-xs text-muted-foreground">
              {t('execution.resources.elapsed', { defaultValue: 'Elapsed' })}
            </span>
          </div>
          <span className="text-xs font-medium text-foreground">
            {formatElapsedTime(elapsedSeconds)}
          </span>
        </div>
      </div>
    </div>
  );
});
