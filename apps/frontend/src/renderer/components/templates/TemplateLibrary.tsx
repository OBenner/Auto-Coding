import { useState, useEffect } from 'react';
import { Search, Filter, FileText, Zap, Circle } from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import type { TemplateInfo, TemplateCategory } from '../../../shared/types';

interface TemplateLibraryProps {
  projectId?: string;
  onTemplateSelect?: (template: TemplateInfo) => void;
}

// Category icons mapping
function getCategoryIcon(category: TemplateCategory) {
  const icons = {
    api: <Zap className="h-4 w-4" />,
    authentication: <Circle className="h-4 w-4" />,
    database: <Circle className="h-4 w-4" />,
    ui: <FileText className="h-4 w-4" />,
    file: <FileText className="h-4 w-4" />,
    search: <Search className="h-4 w-4" />,
    pagination: <Circle className="h-4 w-4" />,
    caching: <Zap className="h-4 w-4" />,
    notification: <Circle className="h-4 w-4" />,
    data_processing: <FileText className="h-4 w-4" />,
    user_management: <Circle className="h-4 w-4" />,
    settings: <Circle className="h-4 w-4" />,
    dashboard: <Circle className="h-4 w-4" />,
    admin: <Circle className="h-4 w-4" />,
    logging: <FileText className="h-4 w-4" />,
    testing: <Circle className="h-4 w-4" />,
    documentation: <FileText className="h-4 w-4" />,
    cicd: <Circle className="h-4 w-4" />,
    security: <Circle className="h-4 w-4" />,
    performance: <Zap className="h-4 w-4" />,
    other: <FileText className="h-4 w-4" />
  };
  return icons[category] || <FileText className="h-4 w-4" />;
}

// Category color mapping
function getCategoryColor(category: TemplateCategory): string {
  const colors = {
    api: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    authentication: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    database: 'bg-green-500/20 text-green-400 border-green-500/30',
    ui: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
    file: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    search: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    pagination: 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30',
    caching: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
    notification: 'bg-red-500/20 text-red-400 border-red-500/30',
    data_processing: 'bg-teal-500/20 text-teal-400 border-teal-500/30',
    user_management: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    settings: 'bg-slate-500/20 text-slate-400 border-slate-500/30',
    dashboard: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    admin: 'bg-red-500/20 text-red-400 border-red-500/30',
    logging: 'bg-amber-500/20 text-amber-400 border-amber-500/30',
    testing: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
    documentation: 'bg-sky-500/20 text-sky-400 border-sky-500/30',
    cicd: 'bg-violet-500/20 text-violet-400 border-violet-500/30',
    security: 'bg-rose-500/20 text-rose-400 border-rose-500/30',
    performance: 'bg-lime-500/20 text-lime-400 border-lime-500/30',
    other: 'bg-gray-500/20 text-gray-400 border-gray-500/30'
  };
  return colors[category] || colors.other;
}

export function TemplateLibrary({ projectId, onTemplateSelect }: TemplateLibraryProps) {
  const [templates, setTemplates] = useState<TemplateInfo[]>([]);
  const [categories, setCategories] = useState<TemplateCategory[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>('all');

  // Load templates
  useEffect(() => {
    async function loadTemplates() {
      if (!projectId) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError(null);

        // Load templates
        const result = await window.electronAPI.listTemplates(projectId, {
          category: selectedCategory !== 'all' ? selectedCategory : undefined
        });

        if (result.success && result.data) {
          setTemplates(result.data);
        } else {
          setError(result.error || 'Failed to load templates');
        }

        // Load categories
        const categoriesResult = await window.electronAPI.getTemplateCategories(projectId);
        if (categoriesResult.success && categoriesResult.data) {
          setCategories(categoriesResult.data as TemplateCategory[]);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    loadTemplates();
  }, [projectId, selectedCategory]);

  // Filter templates by search query
  const filteredTemplates = templates.filter(template => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      template.name.toLowerCase().includes(query) ||
      template.description.toLowerCase().includes(query) ||
      template.tags?.some(tag => tag.toLowerCase().includes(query))
    );
  });

  // Handle template selection
  const handleTemplateClick = (template: TemplateInfo) => {
    if (onTemplateSelect) {
      onTemplateSelect(template);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Circle className="h-8 w-8 mx-auto mb-3 text-muted-foreground/30 animate-pulse" />
          <p className="text-sm text-muted-foreground">Loading templates...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md">
          <p className="text-sm text-destructive mb-2">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
          >
            Retry
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header with search and filter */}
      <div className="p-4 border-b border-border/50 space-y-3">
        <div className="flex items-center gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search templates..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button variant="outline" size="icon">
                <Filter className="h-4 w-4" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>Filter by category</p>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Category filter */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Button
            variant={selectedCategory === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory('all')}
            className="whitespace-nowrap"
          >
            All ({templates.length})
          </Button>
          {categories.map((category) => {
            const count = templates.filter(t => t.category === category).length;
            if (count === 0) return null;
            return (
              <Button
                key={category}
                variant={selectedCategory === category ? 'default' : 'outline'}
                size="sm"
                onClick={() => setSelectedCategory(category)}
                className="whitespace-nowrap"
              >
                {category} ({count})
              </Button>
            );
          })}
        </div>
      </div>

      {/* Template list */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-3">
          {filteredTemplates.length === 0 ? (
            <div className="text-center py-12">
              <FileText className="h-10 w-10 mx-auto mb-3 text-muted-foreground/30" />
              <p className="text-sm font-medium text-muted-foreground mb-1">
                {searchQuery ? 'No templates found' : 'No templates available'}
              </p>
              <p className="text-xs text-muted-foreground/70">
                {searchQuery
                  ? 'Try adjusting your search or filters'
                  : 'Templates will appear here once available'}
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs text-muted-foreground pb-2 border-b border-border/50">
                <span>{filteredTemplates.length} template{filteredTemplates.length !== 1 ? 's' : ''}</span>
                {searchQuery && (
                  <span>Filtered from {templates.length}</span>
                )}
              </div>
              {filteredTemplates.map((template) => (
                <div
                  key={template.name}
                  className={cn(
                    'rounded-xl border border-border bg-secondary/30 p-4 transition-all duration-200 hover:bg-secondary/50 cursor-pointer hover:border-border/80'
                  )}
                  onClick={() => handleTemplateClick(template)}
                >
                  <div className="flex items-start gap-3">
                    {/* Category icon */}
                    <div className={cn(
                      'flex items-center justify-center w-10 h-10 rounded-lg border',
                      getCategoryColor(template.category)
                    )}>
                      {getCategoryIcon(template.category)}
                    </div>

                    {/* Template info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="text-sm font-semibold text-foreground">
                          {template.name}
                        </h3>
                        <Badge
                          variant="secondary"
                          className={cn('text-xs', getCategoryColor(template.category))}
                        >
                          {template.category}
                        </Badge>
                      </div>

                      <Tooltip>
                        <TooltipTrigger asChild>
                          <p className="text-xs text-muted-foreground line-clamp-2 cursor-default">
                            {template.description}
                          </p>
                        </TooltipTrigger>
                        {template.description.length > 80 && (
                          <TooltipContent side="bottom" className="max-w-sm">
                            <p className="text-xs">{template.description}</p>
                          </TooltipContent>
                        )}
                      </Tooltip>

                      {/* Parameters */}
                      <div className="mt-2 flex items-center gap-2 text-xs text-muted-foreground">
                        <span>{Object.keys(template.parameters).length} parameter{Object.keys(template.parameters).length !== 1 ? 's' : ''}</span>
                        {template.tags && template.tags.length > 0 && (
                          <>
                            <span>•</span>
                            <div className="flex flex-wrap gap-1">
                              {template.tags.slice(0, 3).map((tag) => (
                                <Badge
                                  key={tag}
                                  variant="outline"
                                  className="text-xs px-1.5 py-0"
                                >
                                  {tag}
                                </Badge>
                              ))}
                              {template.tags.length > 3 && (
                                <Badge variant="outline" className="text-xs px-1.5 py-0">
                                  +{template.tags.length - 3}
                                </Badge>
                              )}
                            </div>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Chevron indicator */}
                    <div className="flex items-center">
                      <Circle className="h-4 w-4 text-muted-foreground/30" />
                    </div>
                  </div>
                </div>
              ))}
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
