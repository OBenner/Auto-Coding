/**
 * SavedSearches component for managing saved code searches
 */

import { useState, useEffect, useCallback, useRef } from 'react';
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

function formatDate(isoString: string | null): string {
  if (!isoString) return 'Never';
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return date.toLocaleDateString();
}

export function SavedSearches({ projectId, onRunSearch }: SavedSearchesProps) {
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
  const [formData, setFormData] = useState({
    name: '',
    query: '',
    search_type: 'unified',
    description: '',
    tags: [] as string[],
    filters: {} as Record<string, unknown>,
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
            title: 'Saved Searches Refreshed',
            description: 'Your saved searches have been updated.',
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
          title: 'Search Deleted',
          description: `"${selectedSearch.name}" has been removed from your saved searches.`,
        });
        await loadSavedSearches();
      } else {
        throw new Error(result.error || 'Failed to delete saved search');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to delete saved search';
      toast({
        title: 'Delete Failed',
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
        title: 'Error',
        description: 'Saved search functionality is not available',
        variant: 'destructive',
      });
      return;
    }

    try {
      const searchToSave = {
        ...formData,
        filters: formData.filters || {},
      };

      let result: any ;
      if (isEdit && selectedSearch) {
        result = await withTimeout(
          window.electronAPI.search.searchSavedUpdate?.(
            projectId,
            selectedSearch.name,
            searchToSave
          )
        );
      } else {
        result = await withTimeout(
          window.electronAPI.search.searchSavedSave?.(projectId, searchToSave)
        );
      }

      if (result.success) {
        toast({
          title: isEdit ? 'Search Updated' : 'Search Saved',
          description: `"${formData.name}" has been ${isEdit ? 'updated' : 'saved'}.`,
        });
        setShowCreateDialog(false);
        setShowEditDialog(false);
        await loadSavedSearches();
      } else {
        throw new Error(result.error || 'Failed to save search');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to save search';
      toast({
        title: 'Save Failed',
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
          title: 'Export Successful',
          description: `Exported ${result.data.count} saved search(es) to ${result.data.path}`,
        });
      } else {
        throw new Error(result.error || 'Failed to export saved searches');
      }
    } catch (error) {
      const msg = error instanceof Error ? error.message : 'Failed to export saved searches';
      toast({
        title: 'Export Failed',
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
              <h1 className="text-2xl font-semibold text-foreground">Saved Searches</h1>
              <p className="text-sm text-muted-foreground">
                Manage and reuse your code search queries
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
              Export
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleRefresh}
              disabled={isRefreshing}
            >
              <Loader2 className={`h-4 w-4 mr-1 ${isRefreshing ? 'animate-spin' : ''}`} />
              Refresh
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={handleCreate}
            >
              <Plus className="h-4 w-4 mr-1" />
              New Search
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
                <p className="text-sm font-medium text-destructive">Failed to load saved searches</p>
                <p className="text-xs text-muted-foreground mt-1 break-all">{loadError}</p>
              </div>
              <Button variant="outline" size="sm" onClick={handleRefresh} className="shrink-0">
                <Loader2 className="h-3 w-3 mr-1" />
                Retry
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
                            <span>Created: {formatDate(search.created_at)}</span>
                          </div>
                          <div className="flex items-center gap-1">
                            <Calendar className="h-3 w-3" />
                            <span>Last used: {formatDate(search.last_used)}</span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRunSearch(search)}
                          title="Run search"
                        >
                          <Play className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleEdit(search)}
                          title="Edit search"
                        >
                          <Edit className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDelete(search)}
                          title="Delete search"
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
              <p className="text-lg font-medium text-foreground">No saved searches yet</p>
              <p className="text-sm text-muted-foreground mb-4">
                Save your frequently used search queries to quickly access them later
              </p>
              <Button onClick={handleCreate}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Saved Search
              </Button>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Create Dialog */}
      <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Create Saved Search</DialogTitle>
            <DialogDescription>
              Save a search query to quickly access it later
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="name">Name *</Label>
              <Input
                id="name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="My search query"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="query">Query *</Label>
              <Input
                id="query"
                value={formData.query}
                onChange={(e) => setFormData(prev => ({ ...prev, query: e.target.value }))}
                placeholder="function authentication"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="search_type">Search Type</Label>
              <select
                id="search_type"
                value={formData.search_type}
                onChange={(e) => setFormData(prev => ({ ...prev, search_type: e.target.value }))}
                className="w-full px-3 py-2 rounded-md border border-input bg-background"
              >
                <option value="unified">Unified</option>
                <option value="purpose">Purpose</option>
                <option value="patterns">Patterns</option>
                <option value="callers">Callers</option>
                <option value="callees">Callees</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Input
                id="description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Find authentication-related functions"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="tags">Tags</Label>
              <div className="flex gap-2">
                <Input
                  id="tags"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  placeholder="Add a tag"
                />
                <Button type="button" variant="outline" onClick={handleAddTag}>
                  Add
                </Button>
              </div>
              {formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {formData.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
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
            <Button variant="outline" onClick={() => setShowCreateDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => handleSaveSearch(false)} disabled={!formData.name || !formData.query}>
              Save Search
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Dialog */}
      <Dialog open={showEditDialog} onOpenChange={setShowEditDialog}>
        <DialogContent className="sm:max-w-[600px]">
          <DialogHeader>
            <DialogTitle>Edit Saved Search</DialogTitle>
            <DialogDescription>
              Update your saved search query
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="edit-name">Name *</Label>
              <Input
                id="edit-name"
                value={formData.name}
                onChange={(e) => setFormData(prev => ({ ...prev, name: e.target.value }))}
                placeholder="My search query"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-query">Query *</Label>
              <Input
                id="edit-query"
                value={formData.query}
                onChange={(e) => setFormData(prev => ({ ...prev, query: e.target.value }))}
                placeholder="function authentication"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-search_type">Search Type</Label>
              <select
                id="edit-search_type"
                value={formData.search_type}
                onChange={(e) => setFormData(prev => ({ ...prev, search_type: e.target.value }))}
                className="w-full px-3 py-2 rounded-md border border-input bg-background"
              >
                <option value="unified">Unified</option>
                <option value="purpose">Purpose</option>
                <option value="patterns">Patterns</option>
                <option value="callers">Callers</option>
                <option value="callees">Callees</option>
              </select>
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-description">Description</Label>
              <Input
                id="edit-description"
                value={formData.description}
                onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                placeholder="Find authentication-related functions"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="edit-tags">Tags</Label>
              <div className="flex gap-2">
                <Input
                  id="edit-tags"
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault();
                      handleAddTag();
                    }
                  }}
                  placeholder="Add a tag"
                />
                <Button type="button" variant="outline" onClick={handleAddTag}>
                  Add
                </Button>
              </div>
              {formData.tags.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-2">
                  {formData.tags.map((tag) => (
                    <Badge key={tag} variant="secondary" className="text-xs">
                      {tag}
                      <button
                        onClick={() => handleRemoveTag(tag)}
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
            <Button variant="outline" onClick={() => setShowEditDialog(false)}>
              Cancel
            </Button>
            <Button onClick={() => handleSaveSearch(true)} disabled={!formData.name || !formData.query}>
              Update Search
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Saved Search</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{selectedSearch?.name}"? This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
