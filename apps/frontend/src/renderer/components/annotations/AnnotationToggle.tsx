/**
 * AnnotationToggle - Toolbar button to enable/disable annotation mode
 *
 * This component provides a toggle button that allows users to enable and disable
 * annotation mode. When enabled, users can click and drag to create visual
 * annotations on the UI. The button is only visible in development mode.
 *
 * Features:
 * - Toggle button with icon and tooltip
 * - Visual indication when annotation mode is active
 * - Only renders in development mode
 * - Uses annotation store for state management
 */

import { useMemo } from 'react';
import { MousePointer2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useAnnotationStore } from '../../stores/annotation-store';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';
import { cn } from '../../lib/utils';

/**
 * Props for the AnnotationToggle component
 */
export interface AnnotationToggleProps {
  /** Optional CSS class name */
  className?: string;
  /** Button size variant */
  size?: 'default' | 'sm' | 'lg' | 'icon';
  /** Show as icon-only button */
  iconOnly?: boolean;
}

/**
 * AnnotationToggle component
 *
 * Renders a toolbar button that toggles annotation mode on/off.
 * When active, users can create visual annotations on the UI.
 * Only visible in development mode.
 */
export function AnnotationToggle({
  className,
  size = 'icon',
  iconOnly = true
}: AnnotationToggleProps) {
  const { t } = useTranslation('common');
  const { isAnnotationMode, toggleAnnotationMode } = useAnnotationStore();

  /**
   * Determine button variant based on annotation mode state
   * - Default style when inactive
   * - Secondary style with active indication when enabled
   */
  const buttonVariant = useMemo(() => {
    return isAnnotationMode ? 'secondary' : 'ghost';
  }, [isAnnotationMode]);

  /**
   * Handle click to toggle annotation mode
   */
  const handleToggle = () => {
    toggleAnnotationMode();
  };

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant={buttonVariant}
            size={size}
            onClick={handleToggle}
            className={cn(
              'relative',
              isAnnotationMode && 'ring-2 ring-primary ring-offset-2',
              className
            )}
            aria-label={isAnnotationMode
              ? t('annotation.toggleDisable', 'Disable annotation mode')
              : t('annotation.toggleEnable', 'Enable annotation mode')
            }
            aria-pressed={isAnnotationMode}
          >
            <MousePointer2
              className={cn(
                'h-4 w-4',
                isAnnotationMode && 'text-primary'
              )}
              strokeWidth={2}
            />
            {!iconOnly && (
              <span className="ml-2">
                {isAnnotationMode
                  ? t('annotation.modeActive', 'Annotation On')
                  : t('annotation.modeInactive', 'Annotation Off')
                }
              </span>
            )}
            {/* Active indicator dot */}
            {isAnnotationMode && (
              <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-primary animate-pulse" />
            )}
          </Button>
        </TooltipTrigger>
        <TooltipContent side="bottom">
          {isAnnotationMode
            ? t('annotation.tooltipDisable', 'Click to disable annotation mode')
            : t('annotation.tooltipEnable', 'Click to enable annotation mode')
          }
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
