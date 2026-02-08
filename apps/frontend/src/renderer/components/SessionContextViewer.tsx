import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  Clock,
  MessageSquare,
  FileCode,
  RefreshCw,
  AlertCircle,
  Loader2
} from 'lucide-react';
import { Button } from './ui/button';
import { ScrollArea } from './ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card';
import { Badge } from './ui/badge';
import { cn } from '../lib/utils';

interface SessionContextViewerProps {
  projectId: string;
}

export function SessionContextViewer({ projectId }: SessionContextViewerProps) {
  const { t } = useTranslation(['common', 'navigation']);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Placeholder state - will be populated by IPC handlers in next subtask
  const [sessionData, setSessionData] = useState<{
    conversationRounds: number;
    codeReferences: number;
    sessionDuration: string;
  } | null>(null);

  // Placeholder effect - will be implemented with IPC handlers in next subtask
  useEffect(() => {
    // TODO: Load session context data via IPC
    setIsLoading(false);
  }, [projectId]);

  const handleRefresh = () => {
    setIsLoading(true);
    setError(null);
    // TODO: Refresh session context data via IPC
    setTimeout(() => setIsLoading(false), 500);
  };

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Header */}
      <div className="border-b border-border px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-2xl font-bold">{t('navigation:items.sessionContext')}</h2>
            <p className="text-sm text-muted-foreground mt-1">
              {t('common:sessionContext.description')}
            </p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={cn('h-4 w-4 mr-2', isLoading && 'animate-spin')} />
            {t('common:accessibility.refreshAriaLabel')}
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-6 space-y-6">
          {/* Error State */}
          {error && (
            <Card className="border-destructive">
              <CardContent className="pt-6">
                <div className="flex items-center gap-3 text-destructive">
                  <AlertCircle className="h-5 w-5" />
                  <p className="text-sm">{error}</p>
                </div>
              </CardContent>
            </Card>
          )}

          {/* Loading State */}
          {isLoading && !sessionData && (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          )}

          {/* Session Overview */}
          {!isLoading && !error && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <MessageSquare className="h-4 w-4 text-muted-foreground" />
                      {t('common:sessionContext.conversationRounds')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {sessionData?.conversationRounds ?? 0}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <FileCode className="h-4 w-4 text-muted-foreground" />
                      {t('common:sessionContext.codeReferences')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {sessionData?.codeReferences ?? 0}
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-3">
                    <CardTitle className="text-sm font-medium flex items-center gap-2">
                      <Clock className="h-4 w-4 text-muted-foreground" />
                      {t('common:sessionContext.sessionDuration')}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-2xl font-bold">
                      {sessionData?.sessionDuration ?? '0h'}
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* Session Timeline Placeholder */}
              <Card>
                <CardHeader>
                  <CardTitle>{t('common:sessionContext.timeline')}</CardTitle>
                  <CardDescription>
                    {t('common:sessionContext.timelineDescription')}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8 text-muted-foreground">
                    <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                    <p className="text-sm">
                      {t('common:sessionContext.noSessionData')}
                    </p>
                    <p className="text-xs mt-1">
                      {t('common:sessionContext.startAgentSession')}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
