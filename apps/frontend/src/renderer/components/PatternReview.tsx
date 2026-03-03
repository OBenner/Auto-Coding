import { useState, useMemo } from 'react';
import {
  CheckCircle,
  XCircle,
  Code,
  ThumbsUp,
  ThumbsDown,
  TrendingUp,
  Filter,
  AlertCircle
} from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { cn } from '../lib/utils';
import type { PatternSuggestion } from '../../shared/types';

interface PatternReviewProps {
  /** Project ID for the patterns */
  projectId: string;
  /** List of patterns to review */
  patterns: PatternSuggestion[];
  /** Loading state */
  loading?: boolean;
  /** Callback when pattern is approved */
  onApprove?: (pattern: PatternSuggestion) => void;
  /** Callback when pattern is deprecated */
  onDeprecate?: (pattern: PatternSuggestion) => void;
}

type CategoryFilter = 'all' | string;

// Pattern category colors for visual distinction
const categoryColors: Record<string, string> = {
  'api-design': 'bg-blue-500/10 text-blue-400 border-blue-500/30',
  'error-handling': 'bg-red-500/10 text-red-400 border-red-500/30',
  'state-management': 'bg-purple-500/10 text-purple-400 border-purple-500/30',
  'testing': 'bg-green-500/10 text-green-400 border-green-500/30',
  'performance': 'bg-orange-500/10 text-orange-400 border-orange-500/30',
  'security': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/30',
  'uncategorized': 'bg-gray-500/10 text-gray-400 border-gray-500/30'
};

// Get color class for a category
function getCategoryColor(category: string): string {
  return categoryColors[category] || categoryColors.uncategorized;
}

// Get confidence level label and color
function getConfidenceLevel(confidence: number): { label: string; color: string } {
  if (confidence >= 0.9) {
    return { label: 'High', color: 'text-green-400' };
  }
  if (confidence >= 0.7) {
    return { label: 'Medium', color: 'text-amber-400' };
  }
  return { label: 'Low', color: 'text-red-400' };
}

/**
 * PatternReview Component
 *
 * Displays learned code patterns with options to approve as team standards
 * or deprecate patterns that should not be followed.
 */
export function PatternReview({
  projectId: _projectId,
  patterns,
  loading = false,
  onApprove,
  onDeprecate
}: PatternReviewProps) {
  const { t } = useTranslation(['patterns', 'common']);
  const [activeFilter, setActiveFilter] = useState<CategoryFilter>('all');
  const [processingPatterns, setProcessingPatterns] = useState<Set<string>>(new Set());

  // Extract unique categories from patterns (normalizing falsy values)
  const categories = useMemo(() => {
    const uniqueCategories = new Set(
      patterns.map(p => (p.category && p.category.trim()) || 'uncategorized').filter(Boolean)
    );
    return ['all', ...Array.from(uniqueCategories).sort()];
  }, [patterns]);

  // Count patterns by category
  const categoryCounts = useMemo(() => {
    const counts: Record<string, number> = { all: patterns.length };
    for (const pattern of patterns) {
      const cat = (pattern.category && pattern.category.trim()) || 'uncategorized';
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }, [patterns]);

  // Filter patterns based on active category
  const filteredPatterns = useMemo(() => {
    if (activeFilter === 'all') return patterns;
    return patterns.filter(p => p.category === activeFilter);
  }, [patterns, activeFilter]);

  // Sort patterns by confidence (highest first)
  const sortedPatterns = useMemo(() => {
    return [...filteredPatterns].sort((a, b) => b.confidence - a.confidence);
  }, [filteredPatterns]);

  // Handle approve action
  const handleApprove = async (pattern: PatternSuggestion) => {
    const patternKey = `${pattern.category}:${pattern.pattern}`;
    setProcessingPatterns(prev => new Set(prev).add(patternKey));
    try {
      await onApprove?.(pattern);
    } finally {
      setProcessingPatterns(prev => {
        const next = new Set(prev);
        next.delete(patternKey);
        return next;
      });
    }
  };

  // Handle deprecate action
  const handleDeprecate = async (pattern: PatternSuggestion) => {
    const patternKey = `${pattern.category}:${pattern.pattern}`;
    setProcessingPatterns(prev => new Set(prev).add(patternKey));
    try {
      await onDeprecate?.(pattern);
    } finally {
      setProcessingPatterns(prev => {
        const next = new Set(prev);
        next.delete(patternKey);
        return next;
      });
    }
  };

  // Check if pattern is being processed
  const isProcessing = (pattern: PatternSuggestion): boolean => {
    const patternKey = `${pattern.category}:${pattern.pattern}`;
    return processingPatterns.has(patternKey);
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="space-y-2">
          <h2 className="text-2xl font-semibold flex items-center gap-2">
            <Code className="h-6 w-6" />
            {t('patterns:component.title')}
          </h2>
          <p className="text-sm text-muted-foreground">
            {t('patterns:component.description')}
          </p>
        </div>

        {/* Category Filters */}
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              {t('patterns:component.categories')}
            </h3>
          </div>
          <div className="flex flex-wrap gap-2">
            {categories.map(category => {
              const count = categoryCounts[category] || 0;
              const isActive = activeFilter === category;
              const isAll = category === 'all';

              return (
                <Button
                  key={category}
                  variant={isActive ? 'default' : 'outline'}
                  size="sm"
                  className={cn(
                    'gap-1.5 h-8',
                    isActive && 'bg-accent text-accent-foreground'
                  )}
                  onClick={() => setActiveFilter(category)}
                >
                  {isAll && <Code className="h-3.5 w-3.5" />}
                  <span className="capitalize">{category.replace('-', ' ')}</span>
                  {count > 0 && (
                    <Badge
                      variant="secondary"
                      className={cn(
                        'ml-1 px-1.5 py-0 text-xs',
                        isActive && 'bg-background/20'
                      )}
                    >
                      {count}
                    </Badge>
                  )}
                </Button>
              );
            })}
          </div>
        </div>

        {/* Patterns List */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              {t('patterns:component.patterns')}
            </h3>
            <span className="text-xs text-muted-foreground">
              {sortedPatterns.length} {sortedPatterns.length === 1 ? t('patterns:metadata.pattern') : t('patterns:metadata.patterns')}
            </span>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="flex items-center justify-center py-12">
              <div className="flex flex-col items-center gap-3">
                <Code className="h-8 w-8 animate-pulse text-muted-foreground" />
                <p className="text-sm text-muted-foreground">{t('patterns:component.loading')}</p>
              </div>
            </div>
          )}

          {/* Empty State */}
          {!loading && sortedPatterns.length === 0 && patterns.length === 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <Code className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-2">
                {t('patterns:component.empty')}
              </p>
              <p className="text-xs text-muted-foreground max-w-md">
                {t('patterns:component.emptyDescription')}
              </p>
            </div>
          )}

          {/* Empty Filter State */}
          {!loading && sortedPatterns.length === 0 && patterns.length > 0 && (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <AlertCircle className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-sm text-muted-foreground mb-2">
                {t('patterns:component.emptyFilter')}
              </p>
              <Button
                variant="link"
                size="sm"
                onClick={() => setActiveFilter('all')}
                className="mt-2"
              >
                {t('patterns:component.showAll')}
              </Button>
            </div>
          )}

          {/* Pattern Cards */}
          {sortedPatterns.length > 0 && (
            <div className="space-y-3">
              {sortedPatterns.map((pattern) => {
                const confidenceLevel = getConfidenceLevel(pattern.confidence);
                const processing = isProcessing(pattern);
                const stableKey = pattern.spec_id || `${pattern.category}:${pattern.pattern}`;

                return (
                  <Card key={stableKey} className="overflow-hidden">
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex-1 space-y-2">
                          <CardTitle className="text-base font-medium leading-snug">
                            {pattern.pattern}
                          </CardTitle>
                          <div className="flex flex-wrap items-center gap-2">
                            <Badge
                              variant="outline"
                              className={cn('text-xs', getCategoryColor(pattern.category))}
                            >
                              {pattern.category.replace('-', ' ')}
                            </Badge>
                            <Badge variant="outline" className="text-xs gap-1">
                              <TrendingUp className="h-3 w-3" />
                              <span className={confidenceLevel.color}>
                                {confidenceLevel.label}
                              </span>
                              <span className="text-muted-foreground">
                                ({(pattern.confidence * 100).toFixed(0)}%)
                              </span>
                            </Badge>
                          </div>
                        </div>
                      </div>
                    </CardHeader>

                    <CardContent className="space-y-3">
                      {/* Reasoning */}
                      {pattern.reasoning && (
                        <div className="space-y-1">
                          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
                            Reasoning
                          </p>
                          <p className="text-sm text-muted-foreground leading-relaxed">
                            {pattern.reasoning}
                          </p>
                        </div>
                      )}

                      {/* Metadata */}
                      <div className="flex flex-wrap items-center gap-3 text-xs text-muted-foreground">
                        {pattern.spec_id && (
                          <span className="flex items-center gap-1">
                            <Code className="h-3 w-3" />
                            {t('patterns:metadata.spec')}: {pattern.spec_id}
                          </span>
                        )}
                        {pattern.timestamp && (() => {
                          const date = new Date(pattern.timestamp);
                          return Number.isNaN(date.getTime()) ? null : (
                            <span>{date.toLocaleDateString()}</span>
                          );
                        })()}
                      </div>

                      {/* Actions */}
                      <div className="flex items-center gap-2 pt-2 border-t border-border/50">
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2 flex-1 hover:bg-green-500/10 hover:text-green-400 hover:border-green-500/30"
                          onClick={() => handleApprove(pattern)}
                          disabled={processing}
                        >
                          {processing ? (
                            <Code className="h-4 w-4 animate-pulse" />
                          ) : (
                            <>
                              <ThumbsUp className="h-4 w-4" />
                              {t('patterns:actions.approve')}
                            </>
                          )}
                        </Button>
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2 flex-1 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/30"
                          onClick={() => handleDeprecate(pattern)}
                          disabled={processing}
                        >
                          {processing ? (
                            <Code className="h-4 w-4 animate-pulse" />
                          ) : (
                            <>
                              <ThumbsDown className="h-4 w-4" />
                              {t('patterns:actions.deprecate')}
                            </>
                          )}
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>

        {/* Legend */}
        {sortedPatterns.length > 0 && (
          <Card className="bg-muted/30">
            <CardContent className="pt-4">
              <div className="flex items-start gap-3">
                <AlertCircle className="h-4 w-4 text-muted-foreground mt-0.5" />
                <div className="space-y-2 text-xs text-muted-foreground">
                  <p className="font-semibold">{t('patterns:legend.title')}</p>
                  <ul className="space-y-1 list-disc list-inside">
                    <li>{t('patterns:legend.high')}</li>
                    <li>{t('patterns:legend.medium')}</li>
                    <li>{t('patterns:legend.low')}</li>
                  </ul>
                  <p className="pt-2">
                    <CheckCircle className="h-3 w-3 inline mr-1 text-green-400" />
                    {t('patterns:legend.approved')}
                  </p>
                  <p>
                    <XCircle className="h-3 w-3 inline mr-1 text-red-400" />
                    {t('patterns:legend.deprecated')}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </ScrollArea>
  );
}
