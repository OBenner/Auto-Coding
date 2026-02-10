import { useState, useMemo, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  RefreshCw,
  Database,
  Brain,
  Search,
  CheckCircle,
  XCircle,
  GitPullRequest,
  Lightbulb,
  FolderTree,
  Code,
  AlertTriangle,
  List,
  Network,
  Download
} from 'lucide-react';
import { Button } from '../ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { ScrollArea } from '../ui/scroll-area';
import { cn } from '../../lib/utils';
import { MemoryCard } from './MemoryCard';
import { InfoItem } from './InfoItem';
import { MemoryGraph } from './MemoryGraph';
import { MemoryExportDialog } from './MemoryExportDialog';
import { memoryFilterCategories } from './constants';
import { loadRecentMemories } from '../../stores/context-store';
import type { GraphitiMemoryStatus, GraphitiMemoryState, MemoryEpisode, GraphNode, GraphEdge } from '../../../shared/types';

type FilterCategory = keyof typeof memoryFilterCategories;

interface MemoriesTabProps {
  projectId: string;
  memoryStatus: GraphitiMemoryStatus | null;
  memoryState: GraphitiMemoryState | null;
  recentMemories: MemoryEpisode[];
  memoriesLoading: boolean;
  searchResults: Array<{ type: string; content: string; score: number }>;
  searchLoading: boolean;
  onSearch: (query: string) => void;
}

// Helper to check if memory is a PR review (by type or content)
function isPRReview(memory: MemoryEpisode): boolean {
  if (['pr_review', 'pr_finding', 'pr_pattern', 'pr_gotcha'].includes(memory.type)) {
    return true;
  }
  try {
    const parsed = JSON.parse(memory.content);
    return parsed.prNumber !== undefined && parsed.verdict !== undefined;
  } catch {
    return false;
  }
}

// Get the effective category for a memory
function getMemoryCategory(memory: MemoryEpisode): FilterCategory {
  if (isPRReview(memory)) return 'pr';
  if (['session_insight', 'task_outcome'].includes(memory.type)) return 'sessions';
  if (['codebase_discovery', 'codebase_map'].includes(memory.type)) return 'codebase';
  if (['pattern', 'pr_pattern'].includes(memory.type)) return 'patterns';
  if (['gotcha', 'pr_gotcha'].includes(memory.type)) return 'gotchas';
  return 'sessions'; // default
}

// Filter icons for each category
const filterIcons: Record<FilterCategory, React.ElementType> = {
  all: Brain,
  pr: GitPullRequest,
  sessions: Lightbulb,
  codebase: FolderTree,
  patterns: Code,
  gotchas: AlertTriangle
};

export function MemoriesTab({
  projectId,
  memoryStatus,
  memoryState: _memoryState,
  recentMemories,
  memoriesLoading,
  searchResults,
  searchLoading,
  onSearch
}: MemoriesTabProps) {
  const { t } = useTranslation('context');
  const [localSearchQuery, setLocalSearchQuery] = useState('');
  const [activeFilter, setActiveFilter] = useState<FilterCategory>('all');
  const [viewMode, setViewMode] = useState<'list' | 'graph'>('list');
  const [graphNodes, setGraphNodes] = useState<GraphNode[]>([]);
  const [graphEdges, setGraphEdges] = useState<GraphEdge[]>([]);
  const [graphLoading, setGraphLoading] = useState(false);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);

  // Calculate memory counts by category
  const memoryCounts = useMemo(() => {
    const counts: Record<FilterCategory, number> = {
      all: recentMemories.length,
      pr: 0,
      sessions: 0,
      codebase: 0,
      patterns: 0,
      gotchas: 0
    };

    for (const memory of recentMemories) {
      const category = getMemoryCategory(memory);
      counts[category]++;
    }

    return counts;
  }, [recentMemories]);

  // Filter memories based on active filter
  const filteredMemories = useMemo(() => {
    if (activeFilter === 'all') return recentMemories;
    return recentMemories.filter(memory => getMemoryCategory(memory) === activeFilter);
  }, [recentMemories, activeFilter]);

  const handleSearch = () => {
    if (localSearchQuery.trim()) {
      onSearch(localSearchQuery);
    }
  };

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  // Fetch graph data when switching to graph view
  useEffect(() => {
    const fetchGraphData = async () => {
      if (viewMode === 'graph' && memoryStatus?.available && projectId) {
        setGraphLoading(true);
        try {
          const result = await window.electronAPI.getGraphData(projectId, 50);
          if (result.success && result.data) {
            setGraphNodes(result.data.nodes);
            setGraphEdges(result.data.edges);
          }
        } catch (error) {
          // Silently handle errors - graph view will show empty state
        } finally {
          setGraphLoading(false);
        }
      }
    };

    void fetchGraphData();
  }, [viewMode, memoryStatus?.available, projectId]);

  // Handle memory deletion
  const handleDeleteMemory = async (memoryId: string) => {
    try {
      const result = await window.electronAPI.deleteMemory(projectId, memoryId);
      if (result.success) {
        // Refresh memories list after successful deletion
        await loadRecentMemories(projectId);
      }
    } catch (error) {
      // Silently handle errors - the memory list will remain unchanged
    }
  };

  return (
    <ScrollArea className="h-full">
      <div className="p-6 space-y-6">
        {/* Memory Status */}
        <Card>
          <CardHeader className="pb-3">
            <div className="flex items-center justify-between">
              <CardTitle className="text-base flex items-center gap-2">
                <Database className="h-4 w-4" />
                {t('memories.status.title')}
              </CardTitle>
              {memoryStatus?.available ? (
                <Badge variant="outline" className="bg-success/10 text-success border-success/30">
                  <CheckCircle className="h-3 w-3 mr-1" />
                  {t('memories.status.connected')}
                </Badge>
              ) : (
                <Badge variant="outline" className="bg-muted text-muted-foreground">
                  <XCircle className="h-3 w-3 mr-1" />
                  {t('memories.status.notAvailable')}
                </Badge>
              )}
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            {memoryStatus?.available ? (
              <>
                <div className="grid gap-3 sm:grid-cols-2 text-sm">
                  <InfoItem label={t('memories.status.database')} value={memoryStatus.database || 'auto_claude_memory'} />
                  <InfoItem label={t('memories.status.path')} value={memoryStatus.dbPath || '~/.auto-claude/memories'} />
                </div>

                {/* Memory Stats Summary */}
                {recentMemories.length > 0 && (
                  <div className="pt-3 border-t border-border/50">
                    <div className="grid grid-cols-3 sm:grid-cols-6 gap-2">
                      <div className="text-center p-2 rounded-lg bg-muted/30">
                        <div className="text-lg font-semibold text-foreground">{memoryCounts.all}</div>
                        <div className="text-xs text-muted-foreground">{t('memories.stats.total')}</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-cyan-500/10">
                        <div className="text-lg font-semibold text-cyan-400">{memoryCounts.pr}</div>
                        <div className="text-xs text-muted-foreground">{t('memories.stats.prReviews')}</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-amber-500/10">
                        <div className="text-lg font-semibold text-amber-400">{memoryCounts.sessions}</div>
                        <div className="text-xs text-muted-foreground">{t('memories.stats.sessions')}</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-blue-500/10">
                        <div className="text-lg font-semibold text-blue-400">{memoryCounts.codebase}</div>
                        <div className="text-xs text-muted-foreground">{t('memories.stats.codebase')}</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-purple-500/10">
                        <div className="text-lg font-semibold text-purple-400">{memoryCounts.patterns}</div>
                        <div className="text-xs text-muted-foreground">{t('memories.stats.patterns')}</div>
                      </div>
                      <div className="text-center p-2 rounded-lg bg-red-500/10">
                        <div className="text-lg font-semibold text-red-400">{memoryCounts.gotchas}</div>
                        <div className="text-xs text-muted-foreground">{t('memories.stats.gotchas')}</div>
                      </div>
                    </div>
                  </div>
                )}
              </>
            ) : (
              <div className="text-sm text-muted-foreground">
                <p>{memoryStatus?.reason || t('memories.status.notConfigured')}</p>
                <p className="mt-2 text-xs" dangerouslySetInnerHTML={{ __html: t('memories.status.enableHint') }} />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Search */}
        <div className="space-y-4">
          <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
            {t('memories.search.title')}
          </h3>
          <div className="flex gap-2">
            <Input
              placeholder={t('memories.search.placeholder')}
              value={localSearchQuery}
              onChange={(e) => setLocalSearchQuery(e.target.value)}
              onKeyDown={handleSearchKeyDown}
            />
            <Button onClick={handleSearch} disabled={searchLoading}>
              <Search className={cn('h-4 w-4', searchLoading && 'animate-pulse')} />
            </Button>
          </div>

          {/* Search Results */}
          {searchResults.length > 0 && (
            <div className="space-y-3">
              <p className="text-sm text-muted-foreground">
                {t('memories.search.resultCount', { count: searchResults.length })}
              </p>
              {searchResults.map((result, idx) => (
                /* biome-ignore lint/suspicious/noArrayIndexKey: Search results don't have unique IDs */
                <Card key={idx} className="bg-muted/50">
                  <CardContent className="pt-4">
                    <div className="flex items-center gap-2 mb-2">
                      <Badge variant="outline" className="text-xs capitalize">
                        {result.type.replace('_', ' ')}
                      </Badge>
                      <span className="text-xs text-muted-foreground">
                        {t('memories.search.score', { score: result.score.toFixed(2) })}
                      </span>
                    </div>
                    <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono max-h-40 overflow-auto">
                      {result.content}
                    </pre>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Memory Browser */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-muted-foreground uppercase tracking-wider">
              {t('memories.browser.title')}
            </h3>
            <div className="flex items-center gap-3">
              <span className="text-xs text-muted-foreground">
                {t('memories.browser.memoryCount', { filtered: filteredMemories.length, total: recentMemories.length })}
              </span>
              {/* Export Button */}
              <Button
                variant="outline"
                size="sm"
                className="h-7 gap-1.5"
                onClick={() => setExportDialogOpen(true)}
                disabled={recentMemories.length === 0}
              >
                <Download className="h-3.5 w-3.5" />
                <span className="hidden sm:inline">{t('memories.browser.export')}</span>
              </Button>
              {/* View Mode Toggle */}
              {memoryStatus?.available && (
                <div className="flex items-center gap-1 bg-muted/30 rounded-lg p-1">
                  <Button
                    variant={viewMode === 'list' ? 'default' : 'ghost'}
                    size="sm"
                    className="h-7 px-2"
                    onClick={() => setViewMode('list')}
                  >
                    <List className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant={viewMode === 'graph' ? 'default' : 'ghost'}
                    size="sm"
                    className="h-7 px-2"
                    onClick={() => setViewMode('graph')}
                  >
                    <Network className="h-3.5 w-3.5" />
                  </Button>
                </div>
              )}
            </div>
          </div>

          {/* List View */}
          {viewMode === 'list' && (
            <>
              {/* Filter Pills */}
              <div className="flex flex-wrap gap-2">
                {(Object.keys(memoryFilterCategories) as FilterCategory[]).map((category) => {
                  const config = memoryFilterCategories[category];
                  const count = memoryCounts[category];
                  const Icon = filterIcons[category];
                  const isActive = activeFilter === category;

                  return (
                    <Button
                      key={category}
                      variant={isActive ? 'default' : 'outline'}
                      size="sm"
                      className={cn(
                        'gap-1.5 h-8',
                        isActive && 'bg-accent text-accent-foreground',
                        !isActive && count === 0 && 'opacity-50'
                      )}
                      onClick={() => setActiveFilter(category)}
                      disabled={count === 0 && category !== 'all'}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span>{config.label}</span>
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

              {/* Memory List */}
              {memoriesLoading && (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}

              {!memoriesLoading && filteredMemories.length === 0 && recentMemories.length === 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Brain className="h-10 w-10 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">
                    {t('memories.browser.noMemories')}
                  </p>
                </div>
              )}

              {!memoriesLoading && filteredMemories.length === 0 && recentMemories.length > 0 && (
                <div className="flex flex-col items-center justify-center py-8 text-center">
                  <Brain className="h-10 w-10 text-muted-foreground mb-3" />
                  <p className="text-sm text-muted-foreground">
                    {t('memories.browser.noMatch')}
                  </p>
                  <Button
                    variant="link"
                    size="sm"
                    onClick={() => setActiveFilter('all')}
                    className="mt-2"
                  >
                    {t('memories.browser.showAll')}
                  </Button>
                </div>
              )}

              {filteredMemories.length > 0 && (
                <div className="space-y-3">
                  {filteredMemories.map((memory) => (
                    <MemoryCard key={memory.id} memory={memory} onDelete={handleDeleteMemory} />
                  ))}
                </div>
              )}
            </>
          )}

          {/* Graph View */}
          {viewMode === 'graph' && (
            <>
              {graphLoading && (
                <div className="flex items-center justify-center py-8">
                  <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              )}
              {!graphLoading && (
                <MemoryGraph nodes={graphNodes} edges={graphEdges} />
              )}
            </>
          )}
        </div>
      </div>

      {/* Export Dialog */}
      <MemoryExportDialog
        projectId={projectId}
        memories={recentMemories}
        open={exportDialogOpen}
        onOpenChange={setExportDialogOpen}
      />
    </ScrollArea>
  );
}
