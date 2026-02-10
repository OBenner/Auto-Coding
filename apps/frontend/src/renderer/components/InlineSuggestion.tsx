import { Check, X, Lightbulb } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { cn } from '../lib/utils';

/**
 * Suggestion data structure
 */
export interface SuggestionData {
  suggestion: string;
  context?: string;
  confidence?: number;
}

/**
 * Props for InlineSuggestion component
 */
export interface InlineSuggestionProps {
  suggestion: SuggestionData;
  onAccept: () => void;
  onReject: () => void;
  className?: string;
}

/**
 * InlineSuggestion component
 * Displays AI-generated code suggestions inline with accept/reject actions
 */
export function InlineSuggestion({
  suggestion,
  onAccept,
  onReject,
  className
}: InlineSuggestionProps) {
  const { t } = useTranslation(['pairProgramming']);

  /**
   * Get confidence level badge color and label
   */
  const getConfidenceBadge = (confidence?: number) => {
    if (confidence === undefined) return null;

    const percentage = Math.round(confidence * 100);
    let color = 'bg-muted text-muted-foreground';
    let label = 'low';

    if (percentage >= 80) {
      color = 'bg-green-500/10 text-green-600 dark:text-green-500';
      label = 'high';
    } else if (percentage >= 60) {
      color = 'bg-yellow-500/10 text-yellow-600 dark:text-yellow-500';
      label = 'medium';
    } else {
      color = 'bg-orange-500/10 text-orange-600 dark:text-orange-500';
      label = 'low';
    }

    return (
      <span className={cn('inline-flex items-center rounded-md px-2 py-0.5 text-xs font-medium', color)}>
        {t(`pairProgramming:confidence.${label}`)}: {percentage}%
      </span>
    );
  };

  return (
    <div
      className={cn(
        'group relative rounded-lg border border-primary/20 bg-primary/5 p-4 transition-all duration-200',
        'hover:border-primary/40 hover:shadow-md',
        className
      )}
    >
      {/* Header with icon and confidence */}
      <div className="mb-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary/10">
            <Lightbulb className="h-4 w-4 text-primary" />
          </div>
          <span className="text-sm font-medium text-foreground">
            {t('pairProgramming:suggestion.title')}
          </span>
        </div>
        {getConfidenceBadge(suggestion.confidence)}
      </div>

      {/* Context information (if available) */}
      {suggestion.context && (
        <div className="mb-3 rounded-md bg-muted/50 px-3 py-2">
          <p className="text-xs text-muted-foreground">
            <span className="font-medium">{t('pairProgramming:suggestion.context')}:</span>{' '}
            {suggestion.context}
          </p>
        </div>
      )}

      {/* Suggestion content */}
      <div className="mb-4 rounded-md bg-background p-3">
        <pre className="overflow-x-auto text-sm text-foreground">
          <code>{suggestion.suggestion}</code>
        </pre>
      </div>

      {/* Action buttons */}
      <div className="flex items-center gap-2">
        <button
          onClick={onAccept}
          className={cn(
            'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors',
            'bg-primary text-primary-foreground hover:bg-primary/90',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2'
          )}
        >
          <Check className="h-4 w-4" />
          {t('pairProgramming:suggestion.accept')}
        </button>
        <button
          onClick={onReject}
          className={cn(
            'flex items-center gap-2 rounded-md px-4 py-2 text-sm font-medium transition-colors',
            'border border-border bg-background text-foreground hover:bg-muted',
            'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2'
          )}
        >
          <X className="h-4 w-4" />
          {t('pairProgramming:suggestion.reject')}
        </button>
      </div>
    </div>
  );
}
