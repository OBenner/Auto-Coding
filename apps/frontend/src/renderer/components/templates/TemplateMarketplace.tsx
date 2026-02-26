/**
 * Template Marketplace
 *
 * Browse and import community-shared agent templates.
 * Displays templates from the community marketplace with ratings, downloads, and author info.
 */

import { useState, useEffect, useMemo } from 'react';
import {
  Search,
  Star,
  Download,
  User,
  Globe,
  FileText,
  Zap,
  Filter,
  Badge as BadgeIcon,
  Loader2,
  AlertCircle
} from 'lucide-react';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { useTranslation } from 'react-i18next';
import type { SharedTemplateMetadata, TemplateCategory } from '../../../shared/types';
import { cn } from '../../lib/utils';

// Category icons mapping (reused from TemplateLibrary)
function getCategoryIcon(category: TemplateCategory) {
  const icons = {
    api: <Zap className="h-4 w-4" />,
    authentication: <Globe className="h-4 w-4" />,
    database: <FileText className="h-4 w-4" />,
    ui: <FileText className="h-4 w-4" />,
    file: <FileText className="h-4 w-4" />,
    search: <Search className="h-4 w-4" />,
    pagination: <FileText className="h-4 w-4" />,
    caching: <Zap className="h-4 w-4" />,
    notification: <FileText className="h-4 w-4" />,
    data_processing: <FileText className="h-4 w-4" />,
    user_management: <User className="h-4 w-4" />,
    settings: <FileText className="h-4 w-4" />,
    dashboard: <FileText className="h-4 w-4" />,
    admin: <FileText className="h-4 w-4" />,
    logging: <FileText className="h-4 w-4" />,
    testing: <FileText className="h-4 w-4" />,
    documentation: <FileText className="h-4 w-4" />,
    cicd: <FileText className="h-4 w-4" />,
    security: <FileText className="h-4 w-4" />,
    performance: <Zap className="h-4 w-4" />,
    other: <FileText className="h-4 w-4" />
  };
  return icons[category] || <FileText className="h-4 w-4" />;
}

// Category color mapping (reused from TemplateLibrary)
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

interface TemplateMarketplaceProps {
  onTemplateImport?: (templateJson: string) => void;
}

export function TemplateMarketplace({ onTemplateImport }: TemplateMarketplaceProps) {
  const { t } = useTranslation(['templates', 'common']);

  // Helper function for pluralization
  const tPlural = (key: string, count: number) => {
    const pluralKey = count === 1 ? key : `${key}_plural`;
    return t(`templates:marketplace.${pluralKey}`, { count });
  };

  // State
  const [templates, setTemplates] = useState<SharedTemplateMetadata[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<TemplateCategory | 'all'>('all');
  const [importingTemplateId, setImportingTemplateId] = useState<string | null>(null);

  // Load community templates
  useEffect(() => {
    async function loadCommunityTemplates() {
      try {
        setLoading(true);
        setError(null);

        // TODO: Replace with actual API call when marketplace backend is ready
        // const result = await window.electronAPI.listCommunityTemplates();
        // For now, use mock data or empty array
        setTemplates([]);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load marketplace templates');
      } finally {
        setLoading(false);
      }
    }

    loadCommunityTemplates();
  }, []);

  // Filter templates
  const filteredTemplates = useMemo(() => {
    return templates.filter(template => {
      // Category filter
      // if (selectedCategory !== 'all' && template.category !== selectedCategory) {
      //   return false;
      // }

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase();
        return (
          template.templateName.toLowerCase().includes(query) ||
          template.author.toLowerCase().includes(query) ||
          template.tags?.some(tag => tag.toLowerCase().includes(query))
        );
      }

      return true;
    });
  }, [templates, searchQuery, selectedCategory]);

  // Handle template import
  const handleImport = async (templateId: string) => {
    setImportingTemplateId(templateId);

    try {
      // TODO: Fetch template JSON from marketplace API
      // const result = await window.electronAPI.fetchCommunityTemplate(templateId);
      // const templateJson = result.data;

      // For now, we can't import without the actual template data
      // This would be implemented when marketplace backend is ready
      console.log('Import template:', templateId);

      if (onTemplateImport) {
        // onTemplateImport(templateJson);
      }
    } catch (err) {
      console.error('Failed to import template:', err);
    } finally {
      setImportingTemplateId(null);
    }
  };

  // Render star rating
  const renderStars = (rating: number) => {
    const fullStars = Math.floor(rating);
    const hasHalfStar = rating % 1 >= 0.5;
    const emptyStars = 5 - fullStars - (hasHalfStar ? 1 : 0);

    return (
      <div className="flex items-center gap-0.5">
        {[...Array(fullStars)].map((_, i) => (
          <Star key={`full-${i}`} className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
        ))}
        {hasHalfStar && (
          <Star className="h-3.5 w-3.5 fill-amber-400/50 text-amber-400" />
        )}
        {[...Array(emptyStars)].map((_, i) => (
          <Star key={`empty-${i}`} className="h-3.5 w-3.5 text-muted-foreground/30" />
        ))}
      </div>
    );
  };

  // Format download count
  const formatDownloads = (count: number): string => {
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <Loader2 className="h-8 w-8 mx-auto mb-3 text-muted-foreground/30 animate-spin" />
          <p className="text-sm text-muted-foreground">{t('common:loading')}</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center max-w-md">
          <AlertCircle className="h-8 w-8 mx-auto mb-3 text-destructive/50" />
          <p className="text-sm text-destructive mb-2">{error}</p>
          <Button
            variant="outline"
            size="sm"
            onClick={() => window.location.reload()}
          >
            {t('common:retry')}
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
              placeholder={t('templates:marketplace.searchPlaceholder')}
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
            />
          </div>
          <Button variant="outline" size="icon" title={t('templates:marketplace.filter')}>
            <Filter className="h-4 w-4" />
          </Button>
        </div>

        {/* Category filter */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          <Button
            variant={selectedCategory === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setSelectedCategory('all')}
            className="whitespace-nowrap"
          >
            {t('templates:marketplace.all')} ({templates.length})
          </Button>
          {/* Categories would be shown here when we have category data in SharedTemplateMetadata */}
        </div>
      </div>

      {/* Marketplace grid */}
      <ScrollArea className="flex-1">
        <div className="p-4">
          {filteredTemplates.length === 0 ? (
            <div className="text-center py-12">
              <Globe className="h-12 w-12 mx-auto mb-4 text-muted-foreground/30" />
              <h3 className="text-sm font-medium text-foreground mb-1">
                {searchQuery ? t('templates:marketplace.noTemplates') : t('templates:marketplace.emptyMarketplace')}
              </h3>
              <p className="text-xs text-muted-foreground/70 max-w-sm mx-auto">
                {searchQuery
                  ? t('templates:marketplace.searchEmptyHint')
                  : t('templates:marketplace.emptyMarketplaceHint')}
              </p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between text-xs text-muted-foreground pb-2 border-b border-border/50 mb-4">
                <span>{tPlural('templateCount', filteredTemplates.length)}</span>
                {searchQuery && (
                  <span>{t('templates:marketplace.filteredCount', { total: templates.length })}</span>
                )}
              </div>

              {/* Grid layout */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {filteredTemplates.map((template) => (
                  <div
                    key={template.id}
                    className="rounded-lg border border-border bg-card overflow-hidden hover:border-border/80 transition-all"
                  >
                    {/* Template header */}
                    <div className="p-4 border-b border-border/50">
                      <div className="flex items-start gap-3">
                        <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-muted">
                          {getCategoryIcon('other')} {/* Would use template.category when available */}
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="text-sm font-semibold text-foreground truncate">
                            {template.templateName}
                          </h3>
                          <div className="flex items-center gap-2 text-xs text-muted-foreground">
                            <span className="flex items-center gap-1">
                              <User className="h-3 w-3" />
                              {t('templates:marketplace.author', { author: template.author })}
                            </span>
                            <span>•</span>
                            <span>{t('templates:marketplace.version', { version: template.version })}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Template body */}
                    <div className="p-4 space-y-3">
                      {/* Stats */}
                      <div className="flex items-center gap-4 text-xs">
                        <div className="flex items-center gap-1.5">
                          {renderStars(template.rating)}
                          <span className="text-muted-foreground ml-1">
                            {template.rating.toFixed(1)}
                          </span>
                          <span className="text-muted-foreground/70">
                            ({template.reviews})
                          </span>
                        </div>
                        <div className="flex items-center gap-1 text-muted-foreground">
                          <Download className="h-3 w-3" />
                          <span>{formatDownloads(template.downloads)}</span>
                        </div>
                      </div>

                      {/* Tags */}
                      {template.tags?.length > 0 && (
                        <div className="flex flex-wrap gap-1.5">
                          {template.tags?.slice(0, 3).map((tag) => (
                            <Badge
                              key={tag}
                              variant="outline"
                              className="text-xs px-2 py-0"
                            >
                              {tag}
                            </Badge>
                          ))}
                          {template.tags?.length > 3 && (
                            <Badge variant="outline" className="text-xs px-2 py-0">
                              +{template.tags?.length - 3}
                            </Badge>
                          )}
                        </div>
                      )}

                      {/* Import button */}
                      <Button
                        variant="default"
                        size="sm"
                        className="w-full"
                        onClick={() => handleImport(template.id)}
                        disabled={importingTemplateId === template.id}
                      >
                        {importingTemplateId === template.id ? (
                          <>
                            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                            {t('templates:marketplace.importing')}
                          </>
                        ) : (
                          <>
                            <Download className="h-4 w-4 mr-2" />
                            {t('templates:marketplace.import')}
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
