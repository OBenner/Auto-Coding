/**
 * DecisionPoint Component
 *
 * Displays agent decision points with annotated reasoning, alternatives considered,
 * and the chosen approach. Provides expandable details for deep learning.
 */

import { useState, useCallback, memo, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ChevronDown, ChevronUp, Lightbulb, CheckCircle2 } from 'lucide-react';
import { Badge } from '../ui/badge';
import { cn } from '../../lib/utils';
import type { ReplayDecisionPoint } from '../../../shared/types/session-replay';

interface DecisionPointProps {
  /** Decision point data to display */
  decision: ReplayDecisionPoint;
  /** Whether the details are expanded by default */
  defaultExpanded?: boolean;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Custom comparator for React.memo - only re-render when decision content changes
 */
function decisionPointPropsAreEqual(prevProps: DecisionPointProps, nextProps: DecisionPointProps): boolean {
  const prevDecision = prevProps.decision;
  const nextDecision = nextProps.decision;

  // Fast path: same reference
  if (prevDecision === nextDecision && prevProps.className === nextProps.className) {
    return true;
  }

  // Compare only the fields that affect rendering
  return (
    prevDecision.id === nextDecision.id &&
    prevDecision.reasoning === nextDecision.reasoning &&
    prevDecision.chosen_approach === nextDecision.chosen_approach &&
    prevDecision.expected_outcome === nextDecision.expected_outcome &&
    JSON.stringify(prevDecision.options_considered) === JSON.stringify(nextDecision.options_considered)
  );
}

/**
 * DecisionPoint component with expandable reasoning details
 * Shows agent thought process, alternatives considered, and chosen approach
 */
export const DecisionPoint = memo(function DecisionPoint({
  decision,
  defaultExpanded = false,
  className,
}: DecisionPointProps) {
  const { t } = useTranslation('session-replay');
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
    };
    return phaseColors[decision.phase] || 'bg-gray-500/20 text-gray-400 border-gray-500/30';
  }, [decision.phase]);

  return (
    <div className={cn('border border-primary/30 rounded-lg bg-primary/5 overflow-hidden', className)}>
      {/* Header - Always Visible */}
      <button
        onClick={toggleExpanded}
        className="w-full px-4 py-3 flex items-center gap-3 hover:bg-primary/10 transition-colors text-left"
        aria-expanded={isExpanded}
        aria-label={isExpanded ? t('sessionPlayer.collapseDetails') : t('sessionPlayer.expandDetails')}
      >
        {/* Icon */}
        <div className="shrink-0">
          <Lightbulb className="h-5 w-5 text-primary" />
        </div>

        {/* Title and Metadata */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline" className={cn('gap-1 text-xs', phaseBadgeColor)}>
              {decision.phase}
            </Badge>
            {decision.subtask && (
              <span className="text-xs text-muted-foreground truncate">
                {decision.subtask}
              </span>
            )}
          </div>
          <div className="text-sm font-medium line-clamp-1">
            {(decision.reasoning ?? '').slice(0, 100)}
            {(decision.reasoning ?? '').length > 100 && '...'}
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
          {/* Full Reasoning */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Lightbulb className="h-4 w-4 text-primary" />
              <h4 className="text-sm font-medium">{t('sessionPlayer.reasoning')}</h4>
            </div>
            <p className="text-sm text-muted-foreground pl-6">
              {decision.reasoning ?? ''}
            </p>
          </div>

          {/* Options Considered */}
          {decision.options_considered && decision.options_considered.length > 0 && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h4 className="text-sm font-medium">{t('sessionPlayer.options')}</h4>
                <Badge variant="secondary" className="text-xs">
                  {decision.options_considered.length}
                </Badge>
              </div>
              <ul className="space-y-2 pl-4">
                {decision.options_considered.map((option, index) => (
                  <li key={index} className="flex items-start gap-2">
                    <span className="text-xs text-muted-foreground mt-0.5 shrink-0">
                      {index + 1}.
                    </span>
                    <span className="text-sm text-muted-foreground">
                      {option}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Chosen Approach */}
          <div>
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle2 className="h-4 w-4 text-green-500" />
              <h4 className="text-sm font-medium">{t('sessionPlayer.chosen')}</h4>
            </div>
            <p className="text-sm pl-6 bg-green-500/10 border border-green-500/20 rounded-md p-3">
              {decision.chosen_approach}
            </p>
          </div>

          {/* Expected Outcome */}
          {decision.expected_outcome && (
            <div>
              <div className="flex items-center gap-2 mb-2">
                <h4 className="text-sm font-medium">{t('sessionPlayer.expectedOutcome')}</h4>
              </div>
              <p className="text-sm text-muted-foreground pl-6">
                {decision.expected_outcome}
              </p>
            </div>
          )}

          {/* Timestamp */}
          <div className="pt-2 border-t border-border">
            <div className="text-xs text-muted-foreground">
              {new Date(decision.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}, decisionPointPropsAreEqual);
