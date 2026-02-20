/**
 * PatternReviewPanel - UI for reviewing and managing learned codebase patterns
 *
 * Allows users to:
 * - View patterns learned from the codebase
 * - Filter by category (naming-conventions, error-handling, code-organization)
 * - Approve, override, or delete patterns
 * - See pattern details (confidence, reasoning)
 */
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Sparkles,
  Filter,
  Check,
  Edit,
  Trash2,
  Info,
  AlertCircle,
  Loader2,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { useProjectStore } from '../../stores/project-store';
import { useTaskStore } from '../../stores/task-store';
import type { Pattern } from '../../../preload/api/modules/pattern-api';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Card } from '../ui/card';
import { Label } from '../ui/label';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '../../lib/utils';
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger
} from '../ui/tooltip';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle
} from '../ui/alert-dialog';

type CategoryFilter = 'all' | Pattern['category'];

/**
 * Main pattern review panel component
 */
export function PatternReviewPanel() {
  const { t } = useTranslation('common');

  // State
  const [patterns, setPatterns] = useState<Pattern[]>([]);
  const [categoryFilter, setCategoryFilter] = useState<CategoryFilter>('all');
  const [expandedPatternIndex, setExpandedPatternIndex] = useState<number | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [deleteConfirmPattern, setDeleteConfirmPattern] = useState<Pattern | null>(null);
  const [editingPatternIndex, setEditingPatternIndex] = useState<number | null>(null);
  const [editText, setEditText] = useState('');

  // Get current project and spec
  const { projects, getActiveProject } = useProjectStore();
  const currentProject = getActiveProject() ?? projects[0];
  const selectedTask = useTaskStore((s) => s.getSelectedTask());
  const currentSpecId = selectedTask?.specId ?? currentProject?.id;

  /**
   * Load patterns from backend
   */
  const loadPatterns = async () => {
    if (!currentProject) {
      setError(t('patternReview.noProject'));
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const categoryFilterParam = categoryFilter === 'all' ? undefined : categoryFilter;
      const result = await window.electronAPI.pattern.listPatterns(
        currentProject.id,
        currentSpecId,
        categoryFilterParam
      );

      if (result.success && result.data) {
        setPatterns(result.data);
      } else {
        setError(result.error || t('patternReview.failedToLoad'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('patternReview.unknownError'));
    } finally {
      setIsLoading(false);
    }
  };

  /**
   * Load patterns on component mount and when category filter or project changes
   */
  useEffect(() => {
    loadPatterns();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [categoryFilter, currentProject?.id, currentSpecId]);

  // Filter patterns by category
  const filteredPatterns = categoryFilter === 'all'
    ? patterns
    : patterns.filter(p => p.category === categoryFilter);

  // Group patterns by category for display
  const groupedPatterns = filteredPatterns
    .filter(p => p.category)  // Remove patterns without category
    .reduce((acc, pattern) => {
      const cat = pattern.category!;  // Non-null assertion (safe after filter)
      if (!acc[cat]) {
        acc[cat] = [];
      }
      acc[cat].push(pattern);
      return acc;
    }, {} as Record<string, Pattern[]>);

  // Handlers
  const handleApprove = async (patternIndex: number) => {
    if (!currentProject) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.pattern.approvePattern(
        currentProject.id,
        currentSpecId,
        patternIndex
      );

      if (result.success) {
        await loadPatterns();
      } else {
        setError(result.error || t('patternReview.failedToApprove'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('patternReview.unknownError'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleStartEdit = (pattern: Pattern) => {
    setEditingPatternIndex(pattern.index);
    setEditText(pattern.text);
  };

  const handleSaveEdit = async (patternIndex: number) => {
    if (!currentProject || !editText.trim()) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.pattern.overridePattern(
        currentProject.id,
        currentSpecId,
        patternIndex,
        editText
      );

      if (result.success) {
        await loadPatterns();
        setEditingPatternIndex(null);
        setEditText('');
      } else {
        setError(result.error || t('patternReview.failedToOverride'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('patternReview.unknownError'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancelEdit = () => {
    setEditingPatternIndex(null);
    setEditText('');
  };

  const handleDelete = async () => {
    if (!deleteConfirmPattern || !currentProject) return;

    setIsLoading(true);
    setError(null);

    try {
      const result = await window.electronAPI.pattern.deletePattern(
        currentProject.id,
        currentSpecId,
        deleteConfirmPattern.index
      );

      if (result.success) {
        await loadPatterns();
        setDeleteConfirmPattern(null);
      } else {
        setError(result.error || t('patternReview.failedToDelete'));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : t('patternReview.unknownError'));
    } finally {
      setIsLoading(false);
    }
  };

  const toggleExpanded = (patternIndex: number) => {
    setExpandedPatternIndex(expandedPatternIndex === patternIndex ? null : patternIndex);
  };

  // Get confidence badge color
  const getConfidenceBadgeVariant = (confidence: Pattern['confidence']) => {
    switch (confidence) {
      case 'high':
        return 'default';
      case 'medium':
        return 'secondary';
      case 'low':
        return 'outline';
      default:
        return 'outline';
    }
  };

  // Get category display name
  const getCategoryName = (category: Pattern['category']) => {
    switch (category) {
      case 'naming-conventions':
        return t('patternReview.categoryNaming');
      case 'error-handling':
        return t('patternReview.categoryErrorHandling');
      case 'code-organization':
        return t('patternReview.categoryOrganization');
      default:
        return category;
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold flex items-center gap-2">
            <Sparkles className="h-6 w-6 text-primary" />
            {t('patternReview.title')}
          </h2>
          <p className="text-sm text-muted-foreground mt-1">
            {t('patternReview.subtitle')}
          </p>
        </div>
        {error && (
          <div className="text-sm text-destructive bg-destructive/10 px-3 py-1.5 rounded-md">
            {error}
          </div>
        )}
      </div>

      {/* Filter Bar */}
      <div className="flex items-center gap-4 mb-6 p-4 bg-muted/30 rounded-lg border border-border">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Label className="text-sm font-medium">{t('patternReview.filterLabel')}</Label>
        <div className="flex gap-2">
          <Button
            variant={categoryFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCategoryFilter('all')}
          >
            {t('patternReview.filterAll')}
          </Button>
          <Button
            variant={categoryFilter === 'naming-conventions' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCategoryFilter('naming-conventions')}
          >
            {t('patternReview.filterNaming')}
          </Button>
          <Button
            variant={categoryFilter === 'error-handling' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCategoryFilter('error-handling')}
          >
            {t('patternReview.filterErrorHandling')}
          </Button>
          <Button
            variant={categoryFilter === 'code-organization' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setCategoryFilter('code-organization')}
          >
            {t('patternReview.filterOrganization')}
          </Button>
        </div>
      </div>

      {/* Patterns List */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredPatterns.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-12 px-4 border border-dashed rounded-lg">
            <Info className="h-12 w-12 text-muted-foreground mb-4" />
            <h4 className="text-lg font-medium mb-2">{t('patternReview.emptyTitle')}</h4>
            <p className="text-sm text-muted-foreground text-center max-w-sm">
              {t('patternReview.emptyDescription')}
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {Object.entries(groupedPatterns).map(([category, categoryPatterns]) => (
              <div key={category}>
                <h3 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3">
                  {getCategoryName(category as Pattern['category'])}
                </h3>
                <div className="space-y-2">
                  {categoryPatterns.map((pattern) => {
                    const isExpanded = expandedPatternIndex === pattern.index;
                    const isEditing = editingPatternIndex === pattern.index;

                    return (
                      <Card key={pattern.index} className={cn(
                        "transition-colors",
                        pattern.approved ? "border-primary/50 bg-primary/5" : ""
                      )}>
                        <div className="p-4">
                          {/* Pattern Header */}
                          <div className="flex items-start justify-between gap-4">
                            <div className="flex-1 min-w-0">
                              {isEditing ? (
                                <Input
                                  value={editText}
                                  onChange={(e) => setEditText(e.target.value)}
                                  className="mb-2"
                                  autoFocus
                                />
                              ) : (
                                <p className="text-sm font-medium mb-2">{pattern.text}</p>
                              )}

                              <div className="flex items-center gap-2 flex-wrap">
                                <Badge variant={getConfidenceBadgeVariant(pattern.confidence)}>
                                  {t('patternReview.confidence', { level: pattern.confidence })}
                                </Badge>
                                <Badge variant="outline">
                                  {getCategoryName(pattern.category)}
                                </Badge>
                                {pattern.approved && (
                                  <Badge variant="default" className="bg-success/20 text-success border-success/30">
                                    <Check className="h-3 w-3 mr-1" />
                                    {t('patternReview.approved')}
                                  </Badge>
                                )}
                              </div>
                            </div>

                            {/* Action Buttons */}
                            <div className="flex items-center gap-1">
                              {isEditing ? (
                                <>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={() => handleSaveEdit(pattern.index)}
                                    className="h-8 gap-1"
                                  >
                                    <Check className="h-4 w-4" />
                                    {t('patternReview.save')}
                                  </Button>
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    onClick={handleCancelEdit}
                                    className="h-8"
                                  >
                                    {t('patternReview.cancel')}
                                  </Button>
                                </>
                              ) : (
                                <>
                                  {!pattern.approved && (
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => handleApprove(pattern.index)}
                                          className="h-8 w-8 p-0"
                                        >
                                          <Check className="h-4 w-4" />
                                        </Button>
                                      </TooltipTrigger>
                                      <TooltipContent>{t('patternReview.tooltipApprove')}</TooltipContent>
                                    </Tooltip>
                                  )}

                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => handleStartEdit(pattern)}
                                        className="h-8 w-8 p-0"
                                      >
                                        <Edit className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>{t('patternReview.tooltipEdit')}</TooltipContent>
                                  </Tooltip>

                                  <Tooltip>
                                    <TooltipTrigger asChild>
                                      <Button
                                        variant="ghost"
                                        size="sm"
                                        onClick={() => setDeleteConfirmPattern(pattern)}
                                        className="h-8 w-8 p-0 text-destructive hover:text-destructive hover:bg-destructive/10"
                                      >
                                        <Trash2 className="h-4 w-4" />
                                      </Button>
                                    </TooltipTrigger>
                                    <TooltipContent>{t('patternReview.tooltipDelete')}</TooltipContent>
                                  </Tooltip>

                                  {pattern.reasoning && (
                                    <Tooltip>
                                      <TooltipTrigger asChild>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          onClick={() => toggleExpanded(pattern.index)}
                                          className="h-8 w-8 p-0"
                                        >
                                          {isExpanded ? (
                                            <ChevronDown className="h-4 w-4" />
                                          ) : (
                                            <ChevronRight className="h-4 w-4" />
                                          )}
                                        </Button>
                                      </TooltipTrigger>
                                      <TooltipContent>
                                        {isExpanded ? t('patternReview.tooltipHideDetails') : t('patternReview.tooltipShowDetails')}
                                      </TooltipContent>
                                    </Tooltip>
                                  )}
                                </>
                              )}
                            </div>
                          </div>

                          {/* Expanded Details */}
                          {isExpanded && pattern.reasoning && (
                            <div className="mt-4 pt-4 border-t border-border">
                              <div className="flex items-start gap-2 text-sm">
                                <AlertCircle className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                                <div>
                                  <p className="font-medium text-muted-foreground mb-1">{t('patternReview.reasoning')}</p>
                                  <p className="text-foreground">{pattern.reasoning}</p>
                                </div>
                              </div>
                            </div>
                          )}
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Delete Confirmation Dialog */}
      <AlertDialog
        open={deleteConfirmPattern !== null}
        onOpenChange={() => setDeleteConfirmPattern(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>{t('patternReview.deleteTitle')}</AlertDialogTitle>
            <AlertDialogDescription>
              {t('patternReview.deleteDescription')}
              <div className="mt-4 p-3 bg-muted rounded-md">
                <p className="text-sm font-medium text-foreground">
                  {deleteConfirmPattern?.text}
                </p>
              </div>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('patternReview.cancel')}</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              {t('patternReview.deleteConfirm')}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
