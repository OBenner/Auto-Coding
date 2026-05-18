/**
 * PluginCard - Individual plugin display card
 *
 * Displays plugin metadata, status, permissions, and action buttons
 * for enabling/disabling/uninstalling plugins.
 */
import { useTranslation } from 'react-i18next';
import { Activity, ExternalLink, FileText, Shield, ShieldCheck, Power, Trash2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '../ui/card';
import { Badge } from '../ui/badge';
import { Button } from '../ui/button';
import { Tooltip, TooltipContent, TooltipTrigger } from '../ui/tooltip';
import { cn } from '../../lib/utils';
import type { PluginInfo, PluginType, PluginStatus } from '../../../main/plugins/types';

interface PluginCardProps {
  plugin: PluginInfo;
  onEnable: (pluginName: string) => void;
  onDisable: (pluginName: string) => void;
  onUninstall: (pluginName: string) => void;
  onInspectPermissions: (pluginName: string) => void;
  onViewTraces: (pluginName: string) => void;
  onPreviewContext: (pluginName: string) => void;
  isLoading?: boolean;
}

/**
 * Get color scheme for plugin type badge
 */
function getPluginTypeColor(type: PluginType): string {
  switch (type) {
    case 'agent':
      return 'bg-blue-500/20 text-blue-700 dark:text-blue-300';
    case 'integration':
      return 'bg-green-500/20 text-green-700 dark:text-green-300';
    case 'ui':
      return 'bg-purple-500/20 text-purple-700 dark:text-purple-300';
    default:
      return 'bg-muted text-muted-foreground';
  }
}

/**
 * Get color scheme for plugin status badge
 */
function getPluginStatusColor(status: PluginStatus): string {
  switch (status) {
    case 'enabled':
      return 'bg-success/20 text-success';
    case 'disabled':
      return 'bg-muted text-muted-foreground';
    case 'loaded':
      return 'bg-primary/20 text-primary';
    case 'error':
      return 'bg-destructive/20 text-destructive';
    default:
      return 'bg-muted text-muted-foreground';
  }
}

export function PluginCard({
  plugin,
  onEnable,
  onDisable,
  onUninstall,
  onInspectPermissions,
  onViewTraces,
  onPreviewContext,
  isLoading
}: Readonly<PluginCardProps>) {
  const { t } = useTranslation(['plugins', 'common']);
  const { metadata, status, error } = plugin;

  const isEnabled = status === 'enabled';
  const isDisabled = status === 'disabled';
  const hasError = status === 'error';

  return (
    <Card className={cn(
      'transition-all',
      hasError && 'border-destructive/50 bg-destructive/5'
    )}>
      <CardHeader>
        <div className="flex items-start justify-between gap-3">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-lg flex items-center gap-2">
              <span className="truncate">{metadata.name}</span>
              {metadata.homepage && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <a
                      href={metadata.homepage}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-muted-foreground hover:text-foreground transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <ExternalLink className="h-4 w-4" />
                    </a>
                  </TooltipTrigger>
                  <TooltipContent>{t('plugins:actions.viewDocs')}</TooltipContent>
                </Tooltip>
              )}
            </CardTitle>
            <CardDescription className="mt-1">
              {metadata.description}
            </CardDescription>
          </div>
          <div className="flex flex-col gap-1 items-end shrink-0">
            <Badge className={getPluginTypeColor(metadata.plugin_type)}>
              {t(`plugins:types.${metadata.plugin_type}`)}
            </Badge>
            <Badge className={getPluginStatusColor(status)}>
              {t(`plugins:status.${status}`)}
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Error message */}
        {hasError && error && (
          <div className="rounded-lg bg-destructive/10 border border-destructive/30 px-3 py-2 text-sm text-destructive">
            {error}
          </div>
        )}

        {/* Plugin metadata */}
        <div className="grid grid-cols-2 gap-3 text-sm">
          <div>
            <span className="text-muted-foreground">{t('plugins:info.version')}:</span>
            <span className="ml-2 font-mono">{metadata.version}</span>
          </div>
          <div>
            <span className="text-muted-foreground">{t('plugins:info.author')}:</span>
            <span className="ml-2">{metadata.author}</span>
          </div>
          {metadata.license && (
            <div>
              <span className="text-muted-foreground">{t('plugins:info.license')}:</span>
              <span className="ml-2">{metadata.license}</span>
            </div>
          )}
        </div>

        {/* Capabilities */}
        {metadata.capabilities.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{t('plugins:capabilities.title')}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {metadata.capabilities.map((capability) => (
                <Badge key={capability} variant="secondary" className="text-xs">
                  {t(`plugins:capabilities.${capability}`, { defaultValue: capability })}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Permissions */}
        {metadata.required_permissions.length > 0 && (
          <div>
            <div className="flex items-center gap-2 mb-2">
              <Shield className="h-4 w-4 text-muted-foreground" />
              <span className="text-sm font-medium">{t('plugins:permissions.title')}</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {metadata.required_permissions.map((permission) => (
                <Badge key={permission} variant="outline" className="text-xs">
                  {t(`plugins:permissions.${permission}`)}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Dependencies */}
        {metadata.dependencies.length > 0 && (
          <div>
            <span className="text-sm text-muted-foreground">
              {t('plugins:info.dependencies')}:
            </span>
            <div className="flex flex-wrap gap-1.5 mt-1">
              {metadata.dependencies.map((dep) => (
                <Badge key={dep} variant="outline" className="text-xs font-mono">
                  {dep}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex flex-wrap gap-2">
        {isDisabled && (
          <Button
            onClick={() => onEnable(metadata.name)}
            disabled={isLoading}
            size="sm"
            className="gap-2"
          >
            <Power className="h-4 w-4" />
            {t('plugins:actions.enable')}
          </Button>
        )}
        {isEnabled && (
          <Button
            onClick={() => onDisable(metadata.name)}
            disabled={isLoading}
            variant="outline"
            size="sm"
            className="gap-2"
          >
            <Power className="h-4 w-4" />
            {t('plugins:actions.disable')}
          </Button>
        )}
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => onInspectPermissions(metadata.name)}
              disabled={isLoading}
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0"
              aria-label={t('plugins:actions.permissionDiff')}
            >
              <ShieldCheck className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('plugins:actions.permissionDiff')}</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => onViewTraces(metadata.name)}
              disabled={isLoading}
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0"
              aria-label={t('plugins:actions.traces')}
            >
              <Activity className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('plugins:actions.traces')}</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <Button
              onClick={() => onPreviewContext(metadata.name)}
              disabled={isLoading}
              variant="outline"
              size="sm"
              className="h-8 w-8 p-0"
              aria-label={t('plugins:actions.previewContext')}
            >
              <FileText className="h-4 w-4" />
            </Button>
          </TooltipTrigger>
          <TooltipContent>{t('plugins:actions.previewContext')}</TooltipContent>
        </Tooltip>
        <Button
          onClick={() => onUninstall(metadata.name)}
          disabled={isLoading || isEnabled}
          variant="destructive"
          size="sm"
          className="gap-2"
        >
          <Trash2 className="h-4 w-4" />
          {t('plugins:actions.uninstall')}
        </Button>
      </CardFooter>
    </Card>
  );
}
