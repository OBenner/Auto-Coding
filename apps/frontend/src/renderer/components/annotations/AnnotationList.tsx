/**
 * AnnotationList - Display and manage session annotations
 *
 * This component provides a list view of all annotations created in the current session.
 * Users can view, filter, select, edit, and delete annotations. Features include:
 *
 * - Group annotations by status (draft, submitted, processing, completed, failed)
 * - Filter by status using dropdown
 * - Multi-select mode for bulk operations
 * - Inline editing of annotation descriptions
 * - Screenshot thumbnail preview
 * - Severity indicator with color coding
 * - Delete confirmation dialog
 *
 * @pattern Follows ChatHistorySidebar.tsx structure and conventions
 */

import { useState, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Trash2,
  Pencil,
  Check,
  X,
  MoreVertical,
  Loader2,
  Image as ImageIcon,
  AlertCircle,
  CheckCircle,
  Clock,
  FileText,
  Filter,
  CheckSquare
} from 'lucide-react';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Textarea } from '../ui/textarea';
import { ScrollArea } from '../ui/scroll-area';
import { Badge } from '../ui/badge';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator
} from '../ui/dropdown-menu';
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue
} from '../ui/select';
import { cn } from '../../lib/utils';
import type { Annotation, AnnotationSeverity, AnnotationStatus } from '../../../shared/types/annotation';

/**
 * Props for the AnnotationList component
 */
interface AnnotationListProps {
  /** List of annotations to display */
  annotations: Annotation[];
  /** Currently active annotation ID (for highlighting) */
  activeAnnotationId?: string | null;
  /** Loading state indicator */
  isLoading?: boolean;
  /** Callback when an annotation is selected */
  onSelectAnnotation?: (annotationId: string) => void;
  /** Callback when an annotation is deleted */
  onDeleteAnnotation?: (annotationId: string) => Promise<boolean>;
  /** Callback when annotation description is edited */
  onEditAnnotation?: (annotationId: string, newDescription: string) => Promise<boolean>;
  /** Callback when multiple annotations are deleted */
  onDeleteAnnotations?: (annotationIds: string[]) => Promise<void>;
  /** Callback when annotations are regenerated as specs */
  onRegenerateSpec?: (annotationId: string) => Promise<void>;
  /** Current status filter */
  statusFilter?: AnnotationStatus | 'all';
  /** Callback when status filter changes */
  onStatusFilterChange?: (status: AnnotationStatus | 'all') => void;
}

/**
 * Get severity color class for badge styling
 */
function getSeverityColorClass(severity: AnnotationSeverity): string {
  switch (severity) {
    case 'low':
      return 'bg-blue-500/10 text-blue-600 border-blue-500/20 hover:bg-blue-500/15';
    case 'medium':
      return 'bg-yellow-500/10 text-yellow-600 border-yellow-500/20 hover:bg-yellow-500/15';
    case 'high':
      return 'bg-orange-500/10 text-orange-600 border-orange-500/20 hover:bg-orange-500/15';
    case 'critical':
      return 'bg-red-500/10 text-red-600 border-red-500/20 hover:bg-red-500/15';
    default:
      return 'bg-muted text-muted-foreground border-border';
  }
}

/**
 * Get status icon for annotation workflow state
 */
function getStatusIcon(status: AnnotationStatus) {
  switch (status) {
    case 'draft':
      return <FileText className="h-3.5 w-3.5" />;
    case 'submitted':
      return <Clock className="h-3.5 w-3.5" />;
    case 'processing':
      return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
    case 'completed':
      return <CheckCircle className="h-3.5 w-3.5 text-success" />;
    case 'failed':
      return <AlertCircle className="h-3.5 w-3.5 text-destructive" />;
    default:
      return null;
  }
}

/**
 * Format timestamp for display
 */
function formatTimestamp(timestamp: string, t: (key: string, options?: { defaultValue?: string; count?: number }) => string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffMins < 1) {
    return t('annotationList:justNow', { defaultValue: 'Just now' });
  } else if (diffMins < 60) {
    return t('annotationList:minutesAgo', { defaultValue: '{{count}}m ago', count: diffMins }).replace('{{count}}', String(diffMins));
  } else if (diffHours < 24) {
    return t('annotationList:hoursAgo', { defaultValue: '{{count}}h ago', count: diffHours }).replace('{{count}}', String(diffHours));
  } else if (diffDays === 1) {
    return t('annotationList:yesterday', { defaultValue: 'Yesterday' });
  } else if (diffDays < 7) {
    return t('annotationList:daysAgo', { defaultValue: '{{count}}d ago', count: diffDays }).replace('{{count}}', String(diffDays));
  } else {
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }
}

/**
 * AnnotationList component
 *
 * Displays a scrollable list of annotations with filtering, selection,
 * editing, and deletion capabilities.
 */
export function AnnotationList({
  annotations,
  activeAnnotationId,
  isLoading = false,
  onSelectAnnotation,
  onDeleteAnnotation,
  onEditAnnotation,
  onDeleteAnnotations,
  onRegenerateSpec,
  statusFilter = 'all',
  onStatusFilterChange
}: AnnotationListProps) {
  const { t } = useTranslation(['common', 'annotationList']);

  // Local state
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editDescription, setEditDescription] = useState('');
  const [deleteAnnotationId, setDeleteAnnotationId] = useState<string | null>(null);
  const [isSelectionMode, setIsSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);

  /**
   * Filter annotations by status
   */
  const filteredAnnotations = useMemo(() => {
    if (statusFilter === 'all') {
      return annotations;
    }
    return annotations.filter((a) => a.status === statusFilter);
  }, [annotations, statusFilter]);

  /**
   * Group annotations by status for sectioned display
   */
  const groupedAnnotations = useMemo(() => {
    const groups: Record<string, Annotation[]> = {};
    filteredAnnotations.forEach((annotation) => {
      const status = annotation.status;
      if (!groups[status]) {
        groups[status] = [];
      }
      groups[status].push(annotation);
    });
    return groups;
  }, [filteredAnnotations]);

  /**
   * Clear selection when exiting selection mode
   */
  const handleToggleSelectionMode = useCallback(() => {
    setIsSelectionMode((prev) => {
      if (prev) {
        setSelectedIds(new Set());
      }
      return !prev;
    });
  }, []);

  /**
   * Toggle selection of a single annotation
   */
  const handleToggleSelect = useCallback((annotationId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(annotationId)) {
        next.delete(annotationId);
      } else {
        next.add(annotationId);
      }
      return next;
    });
  }, []);

  /**
   * Select all visible annotations
   */
  const handleSelectAll = useCallback(() => {
    setSelectedIds(new Set(filteredAnnotations.map((a) => a.id)));
  }, [filteredAnnotations]);

  /**
   * Clear all selections
   */
  const handleClearSelection = useCallback(() => {
    setSelectedIds(new Set());
  }, []);

  /**
   * Start editing an annotation description
   */
  const handleStartEdit = (annotation: Annotation) => {
    setEditingId(annotation.id);
    setEditDescription(annotation.description);
  };

  /**
   * Save edited description
   */
  const handleSaveEdit = async () => {
    if (editingId && editDescription.trim() && onEditAnnotation) {
      await onEditAnnotation(editingId, editDescription.trim());
    }
    setEditingId(null);
    setEditDescription('');
  };

  /**
   * Cancel editing
   */
  const handleCancelEdit = () => {
    setEditingId(null);
    setEditDescription('');
  };

  /**
   * Delete a single annotation
   */
  const handleDelete = async () => {
    if (deleteAnnotationId && onDeleteAnnotation) {
      await onDeleteAnnotation(deleteAnnotationId);
      setDeleteAnnotationId(null);
    }
  };

  /**
   * Bulk delete selected annotations
   */
  const handleBulkDelete = async () => {
    if (selectedIds.size > 0 && onDeleteAnnotations) {
      try {
        await onDeleteAnnotations(Array.from(selectedIds));
        setSelectedIds(new Set());
      } catch (error) {
        console.error('Failed to delete annotations:', error);
      } finally {
        setBulkDeleteOpen(false);
      }
    }
  };

  /**
   * Regenerate spec for a failed annotation
   */
  const handleRegenerate = async (annotationId: string) => {
    if (onRegenerateSpec) {
      await onRegenerateSpec(annotationId);
    }
  };

  // Get display labels for status values
  const statusLabels: Record<AnnotationStatus | 'all', string> = {
    all: t('annotationList:statusFilter.all', { defaultValue: 'All Annotations' }),
    draft: t('annotationList:status.draft', { defaultValue: 'Draft' }),
    submitted: t('annotationList:status.submitted', { defaultValue: 'Submitted' }),
    processing: t('annotationList:status.processing', { defaultValue: 'Processing' }),
    completed: t('annotationList:status.completed', { defaultValue: 'Completed' }),
    failed: t('annotationList:status.failed', { defaultValue: 'Failed' })
  };

  // Annotations selected for bulk delete preview
  const annotationsToDelete = filteredAnnotations.filter((a) => selectedIds.has(a.id));

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border px-4 py-3">
        <h3 className="text-sm font-medium text-foreground">
          {t('annotationList:title', { defaultValue: 'Annotations' })}
          <span className="ml-2 text-xs text-muted-foreground">
            ({annotations.length})
          </span>
        </h3>
        <div className="flex items-center gap-1">
          {/* Status filter */}
          {onStatusFilterChange && (
            <Select value={statusFilter} onValueChange={(value) => onStatusFilterChange(value as AnnotationStatus | 'all')}>
              <Tooltip>
                <TooltipTrigger asChild>
                  <SelectTrigger className="h-7 w-[140px] text-xs">
                    <Filter className="h-3.5 w-3.5 mr-1.5" />
                    <SelectValue />
                  </SelectTrigger>
                </TooltipTrigger>
                <TooltipContent>
                  {t('annotationList:filterTooltip', { defaultValue: 'Filter by status' })}
                </TooltipContent>
              </Tooltip>
              <SelectContent>
                <SelectItem value="all">{statusLabels.all}</SelectItem>
                <SelectItem value="draft">{statusLabels.draft}</SelectItem>
                <SelectItem value="submitted">{statusLabels.submitted}</SelectItem>
                <SelectItem value="processing">{statusLabels.processing}</SelectItem>
                <SelectItem value="completed">{statusLabels.completed}</SelectItem>
                <SelectItem value="failed">{statusLabels.failed}</SelectItem>
              </SelectContent>
            </Select>
          )}

          {/* Selection mode toggle */}
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant={isSelectionMode ? 'secondary' : 'ghost'}
                size="icon"
                className="h-7 w-7"
                onClick={handleToggleSelectionMode}
                aria-label={
                  isSelectionMode
                    ? t('annotationList:exitSelectMode', { defaultValue: 'Exit selection mode' })
                    : t('annotationList:selectMode', { defaultValue: 'Enter selection mode' })
                }
              >
                <CheckSquare className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              {isSelectionMode
                ? t('annotationList:exitSelectMode', { defaultValue: 'Exit selection mode' })
                : t('annotationList:selectMode', { defaultValue: 'Enter selection mode' })}
            </TooltipContent>
          </Tooltip>
        </div>
      </div>

      {/* Select All / Clear links */}
      {isSelectionMode && filteredAnnotations.length > 0 && (
        <div className="flex items-center justify-between border-b border-border px-4 py-1.5">
          <button
            type="button"
            className="text-xs text-primary hover:underline"
            onClick={handleSelectAll}
          >
            {t('common:accessibility.selectAllAriaLabel', { defaultValue: 'Select all' })}
          </button>
          <button
            type="button"
            className="text-xs text-muted-foreground hover:underline"
            onClick={handleClearSelection}
          >
            {t('common:accessibility.clearSelectionAriaLabel', { defaultValue: 'Clear selection' })}
          </button>
        </div>
      )}

      {/* Annotation list */}
      <ScrollArea className="flex-1">
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          </div>
        ) : filteredAnnotations.length === 0 ? (
          <div className="px-4 py-8 text-center text-sm text-muted-foreground">
            {annotations.length === 0
              ? t('annotationList:noAnnotations', { defaultValue: 'No annotations yet' })
              : t('annotationList:noMatchingAnnotations', { defaultValue: 'No annotations match the filter' })}
          </div>
        ) : (
          <div className="py-2">
            {Object.entries(groupedAnnotations).map(([status, statusAnnotations]) => (
              <div key={status} className="mb-3">
                {/* Status header */}
                <div className="px-4 py-1.5 flex items-center gap-1.5 text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
                  {getStatusIcon(status as AnnotationStatus)}
                  <span>{statusLabels[status as AnnotationStatus]}</span>
                  <span className="text-muted-foreground/50">({statusAnnotations.length})</span>
                </div>
                {/* Annotations for this status */}
                <div className="space-y-1 px-2">
                  {statusAnnotations.map((annotation) => (
                    <AnnotationItem
                      key={annotation.id}
                      annotation={annotation}
                      isActive={annotation.id === activeAnnotationId}
                      isEditing={editingId === annotation.id}
                      editDescription={editDescription}
                      onSelect={() => onSelectAnnotation?.(annotation.id)}
                      onStartEdit={() => handleStartEdit(annotation)}
                      onSaveEdit={handleSaveEdit}
                      onCancelEdit={handleCancelEdit}
                      onEditDescriptionChange={setEditDescription}
                      onDelete={() => setDeleteAnnotationId(annotation.id)}
                      onRegenerate={() => handleRegenerate(annotation.id)}
                      isSelectionMode={isSelectionMode}
                      isSelected={selectedIds.has(annotation.id)}
                      onToggleSelect={() => handleToggleSelect(annotation.id)}
                    />
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </ScrollArea>

      {/* Bulk action toolbar */}
      {isSelectionMode && selectedIds.size > 0 && (
        <div className="flex items-center gap-2 border-t border-border px-4 py-2">
          <Button
            variant="destructive"
            size="sm"
            className="flex-1 text-xs"
            onClick={() => setBulkDeleteOpen(true)}
          >
            <Trash2 className="mr-1.5 h-3.5 w-3.5" />
            {t('selection.deleteSelected', { defaultValue: 'Delete selected' })} ({selectedIds.size})
          </Button>
        </div>
      )}

      {/* Single delete confirmation dialog */}
      <AlertDialog open={!!deleteAnnotationId} onOpenChange={() => setDeleteAnnotationId(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('annotationList:deleteTitle', { defaultValue: 'Delete annotation?' })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('annotationList:deleteDescription', { defaultValue: 'This will permanently delete this annotation. This action cannot be undone.' })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:buttons.cancel', { defaultValue: 'Cancel' })}</AlertDialogCancel>
            <AlertDialogAction onClick={handleDelete}>
              {t('common:accessibility.deleteAriaLabel', { defaultValue: 'Delete' })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Bulk delete confirmation dialog */}
      <AlertDialog open={bulkDeleteOpen} onOpenChange={setBulkDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              {t('annotationList:bulkDeleteTitle', { defaultValue: 'Delete annotations?' })}
            </AlertDialogTitle>
            <AlertDialogDescription>
              {t('annotationList:bulkDeleteDescription', { defaultValue: 'This will permanently delete {{count}} annotation(s). This action cannot be undone.', count: selectedIds.size })}
            </AlertDialogDescription>
          </AlertDialogHeader>
          {annotationsToDelete.length > 0 && (
            <div className="max-h-32 overflow-y-auto rounded border border-border p-2">
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                {t('annotationList:annotationsToDelete', { defaultValue: 'Annotations to delete' })}:
              </p>
              <ul className="space-y-0.5">
                {annotationsToDelete.map((a) => (
                  <li key={a.id} className="truncate text-xs text-foreground/80">
                    {a.description.slice(0, 50)}{a.description.length > 50 ? '...' : ''}
                  </li>
                ))}
              </ul>
            </div>
          )}
          <AlertDialogFooter>
            <AlertDialogCancel>{t('common:buttons.cancel', { defaultValue: 'Cancel' })}</AlertDialogCancel>
            <AlertDialogAction onClick={handleBulkDelete}>
              {t('annotationList:bulkDeleteConfirm', { defaultValue: 'Delete {{count}}', count: selectedIds.size })}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

/**
 * Props for individual annotation item
 */
interface AnnotationItemProps {
  annotation: Annotation;
  isActive: boolean;
  isEditing: boolean;
  editDescription: string;
  onSelect: () => void;
  onStartEdit: () => void;
  onSaveEdit: () => void;
  onCancelEdit: () => void;
  onEditDescriptionChange: (desc: string) => void;
  onDelete: () => void;
  onRegenerate?: () => void;
  isSelectionMode: boolean;
  isSelected: boolean;
  onToggleSelect: () => void;
}

/**
 * AnnotationItem component
 *
 * Renders a single annotation in the list with support for
 * viewing, editing, selecting, and actions.
 */
function AnnotationItem({
  annotation,
  isActive,
  isEditing,
  editDescription,
  onSelect,
  onStartEdit,
  onSaveEdit,
  onCancelEdit,
  onEditDescriptionChange,
  onDelete,
  onRegenerate,
  isSelectionMode,
  isSelected,
  onToggleSelect
}: AnnotationItemProps) {
  const { t } = useTranslation(['common', 'annotationList']);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      onSaveEdit();
    } else if (e.key === 'Escape') {
      onCancelEdit();
    }
  };

  if (isEditing) {
    return (
      <div className="group flex items-start gap-2 rounded-md border border-primary/50 bg-primary/5 px-3 py-2">
        <div className="flex-1 space-y-2">
          <Textarea
            value={editDescription}
            onChange={(e) => onEditDescriptionChange(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[60px] resize-none text-sm"
            autoFocus
          />
          <div className="flex items-center justify-end gap-1">
            <Button
              variant="ghost"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onCancelEdit}
            >
              <X className="mr-1 h-3.5 w-3.5" />
              {t('common:buttons.cancel', { defaultValue: 'Cancel' })}
            </Button>
            <Button
              variant="default"
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={onSaveEdit}
            >
              <Check className="mr-1 h-3.5 w-3.5" />
              {t('common:buttons.save', { defaultValue: 'Save' })}
            </Button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div
      role={isSelectionMode ? 'checkbox' : 'button'}
      aria-checked={isSelectionMode ? isSelected : undefined}
      tabIndex={0}
      className={cn(
        'group relative rounded-md border transition-colors hover:bg-muted/50',
        'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-1',
        isActive && 'border-primary bg-primary/5',
        !isActive && 'border-border'
      )}
      onClick={isSelectionMode ? onToggleSelect : onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          isSelectionMode ? onToggleSelect() : onSelect();
        }
      }}
    >
      {/* Content with reserved space for the menu button */}
      <div className="flex items-start gap-2 pr-7 p-3">
        {/* Checkbox in selection mode, or severity badge otherwise */}
        {isSelectionMode ? (
          <div className="shrink-0 pt-1">
            <input
              type="checkbox"
              checked={isSelected}
              onChange={onToggleSelect}
              className="h-4 w-4 cursor-pointer"
              aria-hidden
              tabIndex={-1}
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        ) : (
          <Badge
            variant="outline"
            className={cn(
              'mt-0.5 shrink-0 text-[10px] font-medium uppercase tracking-wide',
              getSeverityColorClass(annotation.severity)
            )}
          >
            {t(`annotationList:severity.${annotation.severity}`, { defaultValue: annotation.severity })}
          </Badge>
        )}

        {/* Main content */}
        <div className="min-w-0 flex-1">
          {/* Description */}
          <p
            className={cn(
              'text-sm leading-snug break-words',
              isActive ? 'font-medium text-foreground' : 'text-foreground/90'
            )}
          >
            {annotation.description}
          </p>

          {/* Metadata row */}
          <div className="mt-1.5 flex flex-wrap items-center gap-2 text-[11px] text-muted-foreground">
            {/* Timestamp */}
            <span>{formatTimestamp(annotation.timestamp, t)}</span>

            {/* Separator */}
            <span>•</span>

            {/* Status with icon */}
            <span className="flex items-center gap-1">
              {getStatusIcon(annotation.status)}
              {t(`annotationList:status.${annotation.status}`, { defaultValue: annotation.status })}
            </span>

            {/* Component if available */}
            {annotation.component && (
              <>
                <span>•</span>
                <span className="font-mono">{annotation.component}</span>
              </>
            )}

            {/* Route if available */}
            {annotation.route && (
              <>
                <span>•</span>
                <span className="font-mono">{annotation.route}</span>
              </>
            )}

            {/* Spec ID if completed */}
            {annotation.specId && (
              <>
                <span>•</span>
                <span className="text-success">{annotation.specId}</span>
              </>
            )}
          </div>

          {/* Screenshot thumbnail */}
          {annotation.screenshot && (
            <div className="mt-2 flex items-center gap-2">
              <div className="relative inline-flex items-center gap-1 rounded border border-border bg-muted/30 px-2 py-1 text-xs text-muted-foreground">
                <ImageIcon className="h-3 w-3" />
                <span>
                  {annotation.coordinates.width} × {annotation.coordinates.height}
                </span>
              </div>
            </div>
          )}

          {/* Error message if failed */}
          {annotation.status === 'failed' && annotation.error && (
            <div className="mt-2 flex items-start gap-1.5 text-xs text-destructive">
              <AlertCircle className="h-3.5 w-3.5 mt-0.5 shrink-0" />
              <span className="line-clamp-2">{annotation.error}</span>
            </div>
          )}
        </div>
      </div>

      {/* Dropdown menu - hidden in selection mode */}
      {!isSelectionMode && (
        <DropdownMenu modal={false}>
          <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
            <Button
              variant="ghost"
              size="icon"
              className="absolute right-1 top-3 h-6 w-6 opacity-0 group-hover:opacity-100 data-[state=open]:opacity-100 hover:bg-muted-foreground/20 transition-opacity"
              aria-label={t('common:accessibility.moreOptionsAriaLabel', { defaultValue: 'More options' })}
            >
              <MoreVertical className="h-3.5 w-3.5" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" sideOffset={5} className="w-40 z-[100]">
            <DropdownMenuItem onSelect={onStartEdit}>
              <Pencil className="mr-2 h-3.5 w-3.5" />
              {t('common:accessibility.renameAriaLabel', { defaultValue: 'Edit' })}
            </DropdownMenuItem>
            {annotation.status === 'failed' && onRegenerate && (
              <>
                <DropdownMenuItem onSelect={onRegenerate}>
                  <Loader2 className="mr-2 h-3.5 w-3.5" />
                  {t('annotationList:regenerateSpec', { defaultValue: 'Regenerate spec' })}
                </DropdownMenuItem>
                <DropdownMenuSeparator />
              </>
            )}
            <DropdownMenuItem
              onSelect={onDelete}
              className="text-destructive focus:text-destructive"
            >
              <Trash2 className="mr-2 h-3.5 w-3.5" />
              {t('common:accessibility.deleteAriaLabel', { defaultValue: 'Delete' })}
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      )}
    </div>
  );
}
