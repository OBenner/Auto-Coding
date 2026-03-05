/**
 * Search results display for code search
 */

import { useMemo } from 'react';
import {
  FileCode,
  Search,
  AlertCircle,
  ChevronRight,
  Target,
  GitBranch,
  Type,
  Loader2
} from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { ScrollArea } from '../ui/scroll-area';

/**
 * Search result types matching the IPC handler types
 */
export interface FileMatch {
  file_path: string;
  score: number;
  matches: string[];
}

export interface PurposeResult {
  entity_name: string;
  entity_type: string;
  purpose: string;
  file_path: string;
  lineno: string | number;
  score: number;
}

export interface PatternResult {
  content: string;
  score: number;
  type: string;
  category?: string;
}

export interface CallerCalleeResult {
  caller?: string;
  callee?: string;
  file_path: string;
  lineno: string | number;
  call_type: string;
}

export interface UnifiedSearchResult {
  files: FileMatch[];
  purpose: PurposeResult[];
  patterns: PatternResult[];
  total: number;
}

export type SearchResultData = UnifiedSearchResult | PurposeResult[] | PatternResult[] | CallerCalleeResult[];

interface SearchResultsProps {
  results: SearchResultData | null;
  isLoading?: boolean;
  searchType?: 'unified' | 'purpose' | 'patterns' | 'callers' | 'callees';
  searchQuery?: string;
}

interface ResultItemProps {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  subtitle?: string;
  metadata?: Array<{ label: string; value: string | number }>;
  score?: number;
  children?: React.ReactNode;
  onClick?: () => void;
}

function ResultItem({ icon: Icon, title, subtitle, metadata, score, children, onClick }: ResultItemProps) {
  return (
    <div
      className={`p-4 rounded-lg bg-muted/30 border border-border/50 hover:bg-muted/50 transition-colors ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
    >
      <div className="flex items-start gap-3">
        <div className="p-2 rounded-lg bg-accent/10 text-accent shrink-0">
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between gap-2 mb-1">
            <h4 className="text-sm font-semibold text-foreground truncate">{title}</h4>
            {score !== undefined && (
              <Badge variant="outline" className="text-xs shrink-0">
                {Math.round(score * 100)}%
              </Badge>
            )}
          </div>
          {subtitle && (
            <p className="text-xs text-muted-foreground mb-2 truncate">{subtitle}</p>
          )}
          {metadata && metadata.length > 0 && (
            <div className="flex flex-wrap items-center gap-2 mb-2">
              {metadata.map((item, idx) => (
                <div key={idx} className="flex items-center gap-1 text-xs text-muted-foreground">
                  <span className="font-medium">{item.label}:</span>
                  <span className="truncate max-w-[150px]">{item.value}</span>
                </div>
              ))}
            </div>
          )}
          {children && (
            <div className="mt-2">
              {children}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FileMatchResult({ match }: { match: FileMatch }) {
  return (
    <ResultItem
      icon={FileCode}
      title={match.file_path.split('/').pop() || match.file_path}
      subtitle={match.file_path}
      score={match.score}
    >
      {match.matches.length > 0 && (
        <div className="flex flex-wrap gap-1">
          {match.matches.slice(0, 3).map((matchItem, idx) => (
            <Badge key={idx} variant="secondary" className="text-xs">
              {matchItem}
            </Badge>
          ))}
          {match.matches.length > 3 && (
            <Badge variant="secondary" className="text-xs">
              +{match.matches.length - 3} more
            </Badge>
          )}
        </div>
      )}
    </ResultItem>
  );
}

function PurposeResultItem({ result }: { result: PurposeResult }) {
  const entityTypeIcons: Record<string, React.ComponentType<{ className?: string }>> = {
    function: Type,
    class: Target,
    variable: GitBranch,
    method: ChevronRight,
  };

  const Icon = entityTypeIcons[result.entity_type] || Type;

  return (
    <ResultItem
      icon={Icon}
      title={result.entity_name}
      subtitle={result.purpose}
      metadata={[
        { label: 'Type', value: result.entity_type },
        { label: 'File', value: result.file_path },
        { label: 'Line', value: String(result.lineno) },
      ]}
      score={result.score}
    />
  );
}

function PatternResultItem({ result }: { result: PatternResult }) {
  return (
    <ResultItem
      icon={Search}
      title={result.type}
      subtitle={result.content.slice(0, 100) + (result.content.length > 100 ? '...' : '')}
      metadata={result.category ? [{ label: 'Category', value: result.category }] : undefined}
      score={result.score}
    />
  );
}

function CallerCalleeResultItem({ result }: { result: CallerCalleeResult }) {
  return (
    <ResultItem
      icon={GitBranch}
      title={result.caller || result.callee || 'Unknown'}
      subtitle={result.call_type}
      metadata={[
        { label: 'File', value: result.file_path },
        { label: 'Line', value: String(result.lineno) },
      ]}
    />
  );
}


export function SearchResults({
  results,
  isLoading = false,
  searchType = 'unified',
  searchQuery = ''
}: SearchResultsProps) {
  const resultSummary = useMemo(() => {
    if (!results) {
      return { total: 0, byType: {} };
    }

    if (searchType === 'unified') {
      const unified = results as UnifiedSearchResult;
      return {
        total: unified.total,
        byType: {
          files: unified.files.length,
          purpose: unified.purpose.length,
          patterns: unified.patterns.length,
        }
      };
    }

    return {
      total: Array.isArray(results) ? results.length : 0,
      byType: {}
    };
  }, [results, searchType]);

  const hasResults = resultSummary.total > 0;

  return (
    <Card className="bg-muted/30 border-border/50 h-full flex flex-col">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg font-semibold flex items-center gap-2">
            <Search className="h-5 w-5 text-accent" />
            Search Results
          </CardTitle>
          {hasResults && (
            <Badge variant="outline" className="text-xs">
              {resultSummary.total} {resultSummary.total === 1 ? 'result' : 'results'}
            </Badge>
          )}
        </div>
        {searchQuery && (
          <p className="text-sm text-muted-foreground mt-1">
            Query: &quot;{searchQuery}&quot;
          </p>
        )}
      </CardHeader>
      <CardContent className="flex-1 overflow-hidden p-0">
        {isLoading ? (
          <div className="flex items-center justify-center py-8 text-muted-foreground">
            <Loader2 className="h-5 w-5 animate-spin mr-2" />
            Searching codebase...
          </div>
        ) : !hasResults ? (
          <div className="flex flex-col items-center justify-center py-8 text-center px-6">
            <AlertCircle className="h-12 w-12 text-muted-foreground/50 mb-3" />
            <p className="text-sm text-muted-foreground">
              {searchQuery ? 'No results found' : 'Enter a search query to find code'}
            </p>
            {searchQuery && (
              <p className="text-xs text-muted-foreground/70 mt-1">
                Try different keywords or check your search filters
              </p>
            )}
          </div>
        ) : (
          <ScrollArea className="h-full px-6 pb-6">
            <div className="space-y-4">
              {searchType === 'unified' && (
                <>
                  {(results as UnifiedSearchResult).files.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                        <FileCode className="h-4 w-4" />
                        Files ({(results as UnifiedSearchResult).files.length})
                      </h3>
                      <div className="space-y-2">
                        {(results as UnifiedSearchResult).files.map((match, idx) => (
                          <FileMatchResult key={`file-${idx}`} match={match} />
                        ))}
                      </div>
                    </div>
                  )}

                  {(results as UnifiedSearchResult).purpose.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                        <Target className="h-4 w-4" />
                        Purpose ({(results as UnifiedSearchResult).purpose.length})
                      </h3>
                      <div className="space-y-2">
                        {(results as UnifiedSearchResult).purpose.map((result, idx) => (
                          <PurposeResultItem key={`purpose-${idx}`} result={result} />
                        ))}
                      </div>
                    </div>
                  )}

                  {(results as UnifiedSearchResult).patterns.length > 0 && (
                    <div>
                      <h3 className="text-sm font-semibold text-foreground mb-2 flex items-center gap-2">
                        <Search className="h-4 w-4" />
                        Patterns ({(results as UnifiedSearchResult).patterns.length})
                      </h3>
                      <div className="space-y-2">
                        {(results as UnifiedSearchResult).patterns.map((result, idx) => (
                          <PatternResultItem key={`pattern-${idx}`} result={result} />
                        ))}
                      </div>
                    </div>
                  )}
                </>
              )}

              {searchType === 'purpose' && (
                <div className="space-y-2">
                  {(results as PurposeResult[]).map((result, idx) => (
                    <PurposeResultItem key={`purpose-${idx}`} result={result} />
                  ))}
                </div>
              )}

              {searchType === 'patterns' && (
                <div className="space-y-2">
                  {(results as PatternResult[]).map((result, idx) => (
                    <PatternResultItem key={`pattern-${idx}`} result={result} />
                  ))}
                </div>
              )}

              {(searchType === 'callers' || searchType === 'callees') && (
                <div className="space-y-2">
                  {(results as CallerCalleeResult[]).map((result, idx) => (
                    <CallerCalleeResultItem key={`call-${idx}`} result={result} />
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        )}
      </CardContent>
    </Card>
  );
}
