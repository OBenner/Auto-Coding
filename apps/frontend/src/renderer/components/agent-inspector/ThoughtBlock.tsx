/**
 * ThoughtBlock Component
 *
 * Displays agent thinking blocks (extended_thinking) with collapsible sections
 * for debugging and understanding agent reasoning process.
 */

import { useState, useCallback, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, Brain, Clock } from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';

/**
 * Agent thinking block data structure
 */
export interface AgentThinkingBlock {
  /** Unique identifier */
  id: string;
  /** Timestamp of when thinking occurred */
  timestamp: string;
  /** Current phase (planning, coding, validation, etc.) */
  phase: string;
  /** Subtask context (optional) */
  subtask?: string;
  /** Thinking content from extended_thinking block */
  content: string;
  /** Session number (optional) */
  session?: number;
}

interface ThoughtBlockProps {
  /** Thinking block data to display */
  thought: AgentThinkingBlock;
  /** Whether the details are expanded by default */
  defaultExpanded?: boolean;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Custom comparator for React.memo - only re-render when thought content changes
 */
function thoughtBlockPropsAreEqual(prevProps: ThoughtBlockProps, nextProps: ThoughtBlockProps): boolean {
  const prevThought = prevProps.thought;
  const nextThought = nextProps.thought;

  // Fast path: same reference
  if (prevThought === nextThought && prevProps.className === nextProps.className) {
    return true;
  }

  // Compare only the fields that affect rendering
  return (
    prevProps.className === nextProps.className &&
    prevThought.id === nextThought.id &&
    prevThought.content === nextThought.content &&
    prevThought.phase === nextThought.phase &&
    prevThought.timestamp === nextThought.timestamp &&
    prevThought.subtask === nextThought.subtask &&
    prevThought.session === nextThought.session
  );
}

/**
 * ThoughtBlock component with expandable thinking content
 * Shows agent internal reasoning process from extended_thinking blocks
 */
export const ThoughtBlock = memo(function ThoughtBlock({
  thought,
  defaultExpanded = false,
  className,
}: ThoughtBlockProps) {
  const { t } = useTranslation('agent-inspector');
  const [isExpanded, setIsExpanded] = useState(defaultExpanded);

  // Memoize toggle callback to avoid recreating on every render
  const toggleExpanded = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  // Memoize phase badge color
  const phaseBadgeColor = useMemo(() => {
    const phaseColors: Record<string, string> = {
      planning: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
      coding: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
      validation: 'bg-green-500/20 text-green-400 border-green-500/30',
      debugging: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
      recovery: 'bg-red-500/20 text-red-400 border-red-500/30',
    };
    return phaseColors[thought.phase] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  }, [thought.phase]);

  // Memoize content preview (first 100 characters)
  const contentPreview = useMemo(() => {
    const content = thought.content ?? '';
    return content.length > 100 ? `${content.slice(0, 100)}...` : content;
  }, [thought.content]);

  return (
    <div className={cn('border border-primary/30 rounded-lg bg-primary/5 overflow-hidden', className)}>
      {/* Header - Always Visible */}
      <button
        type="button"
        onClick={toggleExpanded}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-primary/10 transition-colors text-left"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? t('collapseThought') : t('expandThought')}
      >
        {/* Icon */}
        <div className="shrink-0">
          <Brain className="h-5 w-5 text-primary" />
        </div>

        {/* Title and Metadata */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className={cn('gap-1 text-xs', phaseBadgeColor)}>
              {thought.phase}
            </Badge>
            {thought.subtask && (
              <span className="text-xs text-muted-foreground truncate">
                {thought.subtask}
              </span>
            )}
          </div>
          <div className="text-sm font-medium line-clamp-1">
            {contentPreview}
          </div>
        </div>

        {/* Expand/Collapse Icon */}
        <div className="shrink-0">
          {isExpanded ? (
            <ChevronUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {/* Expandable Details */}
      {isExpanded && (
        <div className="px-4 pb-4 space-y-4 border-t border-primary/20 pt-4">
          {/* Full Thinking Content */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Brain className="h-4 w-4 text-primary" />
              <h4 className="text-sm font-medium">{t('thinkingContent')}</h4>
            </div>
            <div className="text-sm text-muted-foreground pl-6 whitespace-pre-wrap bg-background/50 border border-border rounded-md p-3">
              {thought.content ?? ''}
            </div>
          </div>

          {/* Metadata Footer */}
          <div className="pt-2 border-t border-border">
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                <Clock className="h-3 w-3" />
                <span>{new Date(thought.timestamp).toLocaleString()}</span>
              </div>
              {thought.session && (
                <div>
                  {t('session')}: {thought.session}
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}, thoughtBlockPropsAreEqual);
