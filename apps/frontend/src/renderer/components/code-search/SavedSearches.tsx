/**
 * SavedSearches component for managing saved code searches
 */

import { useState, useEffect, useCallback, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Bookmark,
  Loader2,
  Trash2,
  Edit,
  Play,
  Plus,
  X,
  Search,
  Calendar,
  Tag,
  AlertTriangle,
  Download
} from 'lucide-react';
import { Button } from '../ui/button';
import { ScrollArea } from '../ui/scroll-area';
import { Input } from '../ui/input';
import { Badge } from '../ui/badge';
import { Card, CardContent } from '../ui/card';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '../ui/dialog';
import { Label } from '../ui/label';
import { toast } from '../../hooks/use-toast';

/**
 * Saved search type matching the IPC handler
 */
export interface SavedSearch {
  name: string;
  query: string;
  search_type: string;
  filters: Record<string, unknown>;
  created_at: string;
  last_used: string | null;
  description: string | null;
  tags: string[];
}

interface SavedSearchesProps {
  projectId: string;
  onRunSearch?: (search: SavedSearch) => void;
}

/** Race a promise against a timeout so a hung IPC can never block the UI. */
function withTimeout<T>(promise: Promise<T>, ms = 5_000): Promise<T> {
  return Promise.race([
    promise,
    new Promise<never>((_, reject) =>
      setTimeout(() => reject(new Error('IPC request timed out')), ms)
    ),
  ]);
}

function formatDate(isoString: string | null, t: (key: string, options?: Record<string, unknown>) => string): string {
  if (!isoString) return t('code-search:savedSearches.dates.never');
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return t('code-search:savedSearches.dates.today');
  if (diffDays === 1) return t('code-search:savedSearches.dates.yesterday');
  if (diffDays < 7) return t('code-search:savedSearches.dates.daysAgo', { count: diffDays });
  if (diffDays < 30) return t('code-search:savedSearches.dates.weeksAgo', { count: Math.floor(diffDays / 7) });
  if (diffDays < 365) return t('code-search:savedSearches.dates.monthsAgo', { count: Math.floor(diffDays / 30) });
  return date.toLocaleDateString();
}

interface SearchFormData {
  name: string;
  query: string;
  search_type: string;
  description: string;
  tags: string[];
  filters: Record<string, unknown>;
}

interface SearchFormDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  idPrefix: string;
  formData: SearchFormData;
  setFormData: React.Dispatch<React.SetStateAction<SearchFormData>>;
  tagInput: string;
  setTagInput: (value: string) => void;
  onAddTag: () => void;
  onRemoveTag: (tag: string) => void;
  onSubmit: () => void;
  submitLabel: string;
}

function SearchFormDialog({
  open,
  onOpenChange,
  title,
  description: desc,
  idPrefix,
  formData,
  setFormData,
  tagInput,
  setTagInput,
  onAddTag,
  onRemoveTag,
  onSubmit,
  submitLabel,
}: SearchFormDialogProps) {
  const { t } = useTranslation(['code-search']);
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{desc}</DialogDescription>
        </DialogHeader>
        <div className="space-y-4 py-4">
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}name`}>{t('code-search:savedSearches.form.name')} *</Label>
            <Input
              id={`${idPrefix}name`}
              value={formData.name}
              onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
              placeholder={t('code-search:savedSearches.form.namePlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}query`}>{t('code-search:savedSearches.form.query')} *</Label>
            <Input
              id={`${idPrefix}query`}
              value={formData.query}
              onChange={(e) => setFormData(prev => ({ ...prev, query: e.target.value }))}
              placeholder={t('code-search:savedSearches.form.queryPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}search_type`}>{t('code-search:savedSearches.form.searchType')}</Label>
            <select
              id={`${idPrefix}search_type`}
              value={formData.search_type}
              onChange={(e) => setFormData(prev => ({ ...prev, search_type: e.target.value }))}
              className="w-full px-3 py-2 rounded-md border border-input bg-background"
            >
              <option value="unified">{t('code-search:savedSearches.searchTypes.unified')}</option>
              <option value="purpose">{t('code-search:savedSearches.searchTypes.purpose')}</option>
              <option value="patterns">{t('code-search:savedSearches.searchTypes.patterns')}</option>
              <option value="callers">{t('code-search:savedSearches.searchTypes.callers')}</option>
              <option value="callees">{t('code-search:savedSearches.searchTypes.callees')}</option>
            </select>
          </div>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}description`}>{t('code-search:savedSearches.form.description')}</Label>
            <Input
              id={`${idPrefix}description`}
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder={t('code-search:savedSearches.form.descriptionPlaceholder')}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor={`${idPrefix}tags`}>{t('code-search:savedSearches.form.tags')}</Label>
            <div className="flex gap-2">
              <Input
                id={`${idPrefix}tags`}
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyPress={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    onAddTag();
                  }
                }}
                placeholder={t('code-search:savedSearches.form.tagsPlaceholder')}
              />
              <Button type="button" variant="outline" onClick={onAddTag}>
                {t('code-search:savedSearches.form.addTag')}
              </Button>
            </div>
            {formData.tags.length > 0 && (
              <div className="flex flex-wrap gap-1 mt-2">
                {formData.tags.map((tag) => (
                  <Badge key={tag} variant="secondary" className="text-xs">
                    {tag}
                    <button
                      onClick={() => onRemoveTag(tag)}
                      className="ml-1 hover:text-destructive"
                    >
                      <X className="h-3 w-3" />
                    </button>
                  </Badge>
                ))}
              </div>
            )}
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('code-search:savedSearches.dialog.cancel')}
          </Button>
          <Button onClick={onSubmit} disabled={!formData.name || !formData.query}>
            {submitLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function SavedSearches({ projectId, onRunSearch }: SavedSearchesProps) {
  const { t } = useTranslation(['code-search']);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [_hasLoaded, setHasLoaded] = useState(false);

  // Dialog states
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [showEditDialog, setShowEditDialog] = useState(false);
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [selectedSearch, setSelectedSearch] = useState<SavedSearch | null>(null);

  // Form states
  const [formData, setFormData] = useState<SearchFormData>({
    name: '',
    query: '',
    search_type: 'unified',
    description: '',
    tags: [],
    filters: {},
  });
  const [tagInput, setTagInput] = useState('');

  const mountedRef = useRef(true);
  useEffect(() => {
    mountedRef.current = true;
    return () => { mountedRef.current = false; };
  }, []);

  const loadSavedSearches = useCallback(async (showRefreshToast = false) => {
    try {
      setIsLoading(true);
      setLoadError(null);

      if (!window.electronAPI?.search.searchSavedList) {
        throw new Error('electronAPI?.search.searchSavedList is not available');
      }

      const result = await withTimeout(
        window.electronAPI.search.searchSavedList(projectId)
      );

      if (!mountedRef.current) return;

      if (result.success && result.data) {
        setSavedSearches(result.data);
        if (showRefreshToast) {
          toast({
            title: t('code-search:savedSearches.toast.refreshed.title'),
            description: t('code-search:savedSearches.toast.refreshed.description'),
          });
        }
      } else {
        throw new Error(result.error || 'Failed to load saved searches');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : String(error);
      console.error('[SavedSearches] Error loading saved searches:', msg);
      if (mountedRef.current) {
        setLoadError(msg);
      }
    } finally {
      if (mountedRef.current) {
        setIsLoading(false);
        setIsRefreshing(false);
        setHasLoaded(true);
      }
    }
  }, [projectId]);

  useEffect(() => {
    loadSavedSearches();
  }, [loadSavedSearches]);

  const handleRefresh = useCallback(() => {
    setIsRefreshing(true);
    loadSavedSearches(true);
  }, [loadSavedSearches]);

  const handleRunSearch = useCallback((search: SavedSearch) => {
    if (onRunSearch) {
      onRunSearch(search);
    }
  }, [onRunSearch]);

  const handleCreate = useCallback(() => {
    setSelectedSearch(null);
    setFormData({
      name: '',
      query: '',
      search_type: 'unified',
      description: '',
      tags: [],
      filters: {},
    });
    setTagInput('');
    setShowCreateDialog(true);
  }, []);

  const handleEdit = useCallback((search: SavedSearch) => {
    setSelectedSearch(search);
    setFormData({
      name: search.name,
      query: search.query,
      search_type: search.search_type,
      description: search.description || '',
      tags: search.tags || [],
      filters: search.filters || {},
    });
    setTagInput('');
    setShowEditDialog(true);
  }, []);

  const handleDelete = useCallback((search: SavedSearch) => {
    setSelectedSearch(search);
    setShowDeleteDialog(true);
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (!selectedSearch || !window.electronAPI?.search.searchSavedDelete) return;

    try {
      const result = await withTimeout(
        window.electronAPI.search.searchSavedDelete(projectId, selectedSearch.name)
      );

      if (result.success) {
        toast({
          title: t('code-search:savedSearches.toast.deleted.title'),
          description: t('code-search:savedSearches.toast.deleted.description', { name: selectedSearch.name }),
        });
        await loadSavedSearches();
      } else {
        throw new Error(result.error || 'Failed to delete saved search');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : t('code-search:savedSearches.toast.deleteFailed.description');
      toast({
        title: t('code-search:savedSearches.toast.deleteFailed.title'),
        description: msg,
        variant: 'destructive',
      });
    } finally {
      setShowDeleteDialog(false);
      setSelectedSearch(null);
    }
  }, [projectId, selectedSearch, loadSavedSearches]);

  const handleSaveSearch = useCallback(async (isEdit = false) => {
    if (!window.electronAPI?.search.searchSavedSave && !window.electronAPI?.search.searchSavedUpdate) {
      toast({
        title: t('code-search:savedSearches.toast.error.title'),
        description: t('code-search:savedSearches.toast.error.description'),
        variant: 'destructive',
      });
      return;
    }

    try {
      const searchToSave = {
        ...formData,
        filters: formData.filters || {},
      };

      let result: { success: boolean; search?: SavedSearch; error?: string };
      if (isEdit && selectedSearch) {
        // Strip `name` — the update handler identifies the search by the
        // second positional arg (`selectedSearch.name`), not a `name` field
        // inside the updates payload.
        const { name: _name, ...updates } = searchToSave;
        result = await withTimeout(
          window.electronAPI.search.searchSavedUpdate?.(
            projectId,
            selectedSearch.name,
            updates
          )
        );
      } else {
        result = await withTimeout(
          window.electronAPI.search.searchSavedSave?.(projectId, searchToSave)
        );
      }

      if (result.success) {
        toast({
          title: isEdit
            ? t('code-search:savedSearches.toast.updated.title')
            : t('code-search:savedSearches.toast.created.title'),
          description: isEdit
            ? t('code-search:savedSearches.toast.updated.description', { name: formData.name })
            : t('code-search:savedSearches.toast.created.description', { name: formData.name }),
        });
        setShowCreateDialog(false);
        setShowEditDialog(false);
        await loadSavedSearches();
      } else {
        throw new Error(result.error || 'Failed to save search');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : t('code-search:savedSearches.toast.saveFailed.description');
      toast({
        title: t('code-search:savedSearches.toast.saveFailed.title'),
        description: msg,
        variant: 'destructive',
      });
    }
  }, [projectId, formData, selectedSearch, loadSavedSearches]);

  const handleExport = useCallback(async () => {
    if (!window.electronAPI?.search.searchSavedExport) return;

    try {
      const result = await withTimeout(
        window.electronAPI.search.searchSavedExport(projectId)
      );

      if (result.success && result.data) {
        toast({
          title: t('code-search:savedSearches.toast.exportSuccess.title'),
          description: t('code-search:savedSearches.toast.exportSuccess.description', { count: result.data.count, path: result.data.path }),
        });
      } else {
        throw new Error(result.error || 'Failed to export saved searches');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : t('code-search:savedSearches.toast.exportFailed.description');
      toast({
        title: t('code-search:savedSearches.toast.exportFailed.title'),
        description: msg,
        variant: 'destructive',
      });
    }
  }, [projectId]);

  const handleAddTag = useCallback(() => {
    const tag = tagInput.trim();
    if (tag && !formData.tags.includes(tag)) {
      setFormData(prev => ({
        ...prev,
        tags: [...prev.tags, tag],
      }));
      setTagInput('');
    }
  }, [tagInput, formData.tags]);

  const handleRemoveTag = useCallback((tag: string) => {
    setFormData(prev => ({
      ...prev,
      tags: prev.tags.filter(t => t !== tag),
    }));
  }, []);

  const getSearchTypeBadge = useCallback((searchType: string) => {
    const variants: Record<string, 'default' | 'secondary' | 'outline'> = {
      unified: 'default',
      purpose: 'secondary',
      patterns: 'outline',
      callers: 'secondary',
      callees: 'outline',
    };
    return variants[searchType] || 'outline';
  }, []);

  return (
    <div className="flex h-full flex-col overflow-hidden bg-background">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bookmark className="h-6 w-6 text-accent" />
            <div>
              <h1 className="text-2xl font-semibold text-foreground">{t('code-search:savedSearches.title')}</h1>
              <p className="text-sm text-muted-foreground">
                {t('code-search:savedSearches.description')}
              </p>
            </div>
            {isLoading && (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            )}
          </div>

          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleExport}
              disabled={savedSearches.length === 0}
            >
              <Download className="h-4 w-4 mr-1" />
              {t('code-search:savedSearches.actions.export')}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <Loader2 className={`h-4 w-4 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
              {t('code-search:savedSearches.actions.refresh')}
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleCreate}
            >
              <Plus className="h-4 w-4 mr-1" />
              {t('code-search:savedSearches.actions.newSearch')}
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-4">
          {/* Error Banner */}
          {loadError && (
            <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 flex items-start gap-3">
              <AlertTriangle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-destructive">{t('code-search:savedSearches.error.title')}</p>
                <p className="text-xs text-muted-foreground mt-1 break-all">{loadError}</p>
              </div>
              <Button variant="outline" size="sm" onClick={handleRefresh} className="shrink-0">
                <Loader2 className="h-3 w-3 mr-1" />
                {t('code-search:savedSearches.actions.retry')}
              </Button>
            </div>
          )}

          {/* Saved Searches List */}
          {savedSearches.length > 0 ? (
            <div className="space-y-3">
              {savedSearches.map((search) => (
                <Card key={search.name} className="bg-muted/30 border-border/50 hover:bg-muted/50 transition-colors">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-2">
                          <h3 className="text-sm font-semibold text-foreground truncate">
                            {search.name}
                          </h3>
                          <Badge variant={getSearchTypeBadge(search.search_type)} className="text-xs">
                            {search.search_type}
                          </Badge>
                        </div>

                        {search.description && (
                          <p className="text-xs text-muted-foreground mb-2 line-clamp-2">
                            {search.description}
                          </p>
                        )}

                        <div className="flex items-center gap-2 mb-2">
                          <Search className="h-3 w-3 text-muted-foreground" />
                          <code className="text-xs bg-muted px-2 py-1 rounded">
                            {search.query}
                          </code>
                        </div>

                        {search.tags && search.tags.length > 0 && (
                          <div className="flex items-center gap-1 flex-wrap mb-2">
                            <Tag className="h-3 w-3 text-muted-foreground" />
                            {search.tags.map((tag) => (
                              <Badge key={tag} variant="secondary" className="text-xs">
                                {tag}
                              </Badge>
                            ))}
                          </div>
                        )}

                        <div className="flex items-center gap-4 text-xs text-muted-foreground">
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>{t('code-search:savedSearches.dates.created')}: {formatDate(search.created_at, t)}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>{t('code-search:savedSearches.dates.lastUsed')}: {formatDate(search.last_used, t)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRunSearch(search)}
                          title={t('code-search:savedSearches.actions.runSearch')}
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(search)}
                          title={t('code-search:savedSearches.actions.editSearch')}
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(search)}
                          title={t('code-search:savedSearches.actions.deleteSearch')}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          ) : (
            /* Empty State */
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Bookmark className="h-16 w-16 text-muted-foreground/50 mb-4" />
              <p className="text-lg font-medium text-foreground">{t('code-search:savedSearches.empty.title')}</p>
              <p className="text-sm text-muted-foreground mb-4">
                {t('code-search:savedSearches.empty.description')}
              </p>
              <Button onClick={handleCreate}>
                <Plus className="h-4 w-4 mr-2" />
                {t('code-search:savedSearches.empty.action')}
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Create Dialog */}
      <SearchFormDialog
        open={showCreateDialog}
        onOpenChange={setShowCreateDialog}
        title={t('code-search:savedSearches.dialog.createTitle')}
        description={t('code-search:savedSearches.dialog.createDescription')}
        idPrefix=""
        formData={formData}
        setFormData={setFormData}
        tagInput={tagInput}
        setTagInput={setTagInput}
        onAddTag={handleAddTag}
        onRemoveTag={handleRemoveTag}
        onSubmit={() => handleSaveSearch(false)}
        submitLabel={t('code-search:savedSearches.dialog.save')}
      />

      {/* Edit Dialog */}
      <SearchFormDialog
        open={showEditDialog}
        onOpenChange={setShowEditDialog}
        title={t('code-search:savedSearches.dialog.editTitle')}
        description={t('code-search:savedSearches.dialog.editDescription')}
        idPrefix="edit-"
        formData={formData}
        setFormData={setFormData}
        tagInput={tagInput}
        setTagInput={setTagInput}
        onAddTag={handleAddTag}
        onRemoveTag={handleRemoveTag}
        onSubmit={() => handleSaveSearch(true)}
        submitLabel={t('code-search:savedSearches.dialog.update')}
      />

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('code-search:savedSearches.dialog.deleteTitle')}</DialogTitle>
            <DialogDescription>
              {t('code-search:savedSearches.dialog.deleteDescription', { name: selectedSearch?.name })}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              {t('code-search:savedSearches.dialog.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              {t('code-search:savedSearches.dialog.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
